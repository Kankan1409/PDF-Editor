import asyncio
import base64
import os
import re
import secrets
import time
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from . import pdf_engine as pdf
from . import store

@asynccontextmanager
async def lifespan(app):
    async def sweep():
        while True:
            await asyncio.sleep(60); store.cleanup()
    task=asyncio.create_task(sweep())
    yield
    task.cancel()

app=FastAPI(title='Smart PDF Editor',lifespan=lifespan)

@app.exception_handler(ValueError)
async def invalid(request,exc): return JSONResponse({'detail':str(exc)},status_code=422)

@app.middleware('http')
async def security(request, call_next):
    if request.method not in ('GET','HEAD','OPTIONS'):
        try:
            if int(request.headers.get('content-length','0')) > 26*1024*1024:
                return JSONResponse({'detail':'ขนาดคำขอสูงสุด 26 MB'},status_code=413)
        except ValueError:
            return JSONResponse({'detail':'Content-Length ไม่ถูกต้อง'},status_code=400)
        origin=request.headers.get('origin')
        if origin and origin.rstrip('/') != str(request.base_url).rstrip('/'):
            # Vite/nginx preserves browser Host when proxying.
            return JSONResponse({'detail':'Origin ไม่ตรงกับเซิร์ฟเวอร์'},status_code=403)
        if request.headers.get('x-smart-pdf') != '1':
            return JSONResponse({'detail':'ต้องใช้แอป Smart PDF'},status_code=403)
    result=await call_next(request)
    result.headers['Cache-Control']='no-store'
    result.headers['X-Content-Type-Options']='nosniff'
    return result

def session(request):
    token=request.cookies.get('smart_session','')
    s=store.sessions.get(token)
    if not s or time.time()-s.touched>store.TTL:
        if s: store.sessions.pop(token,None)
        raise HTTPException(401,'เซสชันหมดอายุ กรุณาเปิด PDF ใหม่')
    s.touched=time.time(); pdf.session_fonts.set(s.fonts); return s

def state(s):
    return dict(**pdf.inspect(s.current),name=s.name,revision=s.revision,
                can_undo=s.cursor>0,can_redo=s.cursor<len(s.history)-1)

class Operation(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    kind: str
    font_name: str | None = Field(default=None,max_length=200)
    revision: int
    page: int = Field(default=0,ge=0)
    line_id: str | None = None
    text: str = Field(default='',max_length=10000)
    query: str = Field(default='',max_length=500)
    all: bool = False
    start: int = Field(default=0,ge=0)
    rect: tuple[float,float,float,float] | None = None
    size: float = Field(default=14,ge=6,le=144)
    color: str = Field(default='#172b3a',pattern=r'^#[0-9a-fA-F]{6}$')
    order: list[int] = Field(default_factory=list,max_length=200)

class Accept(BaseModel):
    preview_id: str
    revision: int

@app.get('/api/health')
def health(): return {'status':'ok'}

def font_description(content):
    try:
        with pdf.TTFont(pdf.BytesIO(content)) as font:
            if 'fvar' in font: raise ValueError('กรุณาใช้ไฟล์ฟอนต์แบบ static TTF/OTF')
            if 'OS/2' not in font or font['OS/2'].fsType & (2|256|512): raise ValueError('ฟอนต์นี้จำกัดสิทธิ์การฝังใน PDF')
            name=font['name'].getDebugName(6)
            if not name: raise ValueError('ฟอนต์ไม่มีชื่อ PostScript')
            cmap=font.getBestCmap() or {}
            pdf.fitz.Font(fontbuffer=content)
            return dict(name=name,thai=all(c in cmap for c in range(0xe01,0xe2f)),english=all(c in cmap for c in range(65,91)))
    except ValueError: raise
    except Exception as exc: raise ValueError('อ่านฟอนต์ไม่ได้ กรุณาเลือกไฟล์ TTF/OTF ที่สมบูรณ์') from exc

@app.get('/api/fonts')
def fonts(request:Request):
    with store.LOCK:
        s=session(request); result={}
        for paths in [set(path for paths in pdf.local_font_index().values() for path in paths)]:
            for path in paths:
                try:
                    info=font_description(path.read_bytes());result[info['name']]=info
                except Exception: continue
        for content in s.fonts.values():
            info=font_description(content);result[info['name']]=info
        return {'fonts':sorted(result.values(),key=lambda f:f['name'])}

@app.post('/api/fonts')
async def import_font(request:Request,file:UploadFile=File(...)):
    content=await file.read(10*1024*1024+1);await file.close()
    if len(content)>10*1024*1024: raise HTTPException(413,'ขนาดฟอนต์สูงสุด 10 MB')
    info=font_description(content)
    with store.LOCK:
        s=session(request)
        if sum(map(len,s.fonts.values()))+len(content)>30*1024*1024: raise ValueError('ฟอนต์ในเซสชันรวมได้สูงสุด 30 MB')
        s.fonts[info['name']]=content
        return info

@app.post('/api/upload')
async def upload(request:Request,response:Response,file:UploadFile=File(...)):
    data=await file.read(25*1024*1024+1); await file.close()
    if len(data)>25*1024*1024: raise HTTPException(413,'ขนาดไฟล์สูงสุด 25 MB')
    name=(file.filename or 'document.pdf').replace('\\','/').split('/')[-1][:150]
    with store.LOCK:
        pdf.inspect(data)
        old=request.cookies.get('smart_session')
        if old: store.sessions.pop(old,None)
        token=store.create(name,data)
        response.set_cookie('smart_session',token,httponly=True,samesite='strict',
            secure=os.getenv('COOKIE_SECURE','false').lower()=='true',max_age=store.TTL)
        return state(store.sessions[token])

@app.get('/api/document')
def document(request:Request):
    with store.LOCK: return state(session(request))

@app.get('/api/pdf')
def download(request:Request,version:str='current',name:str='edited.pdf',pages:str=''):
    with store.LOCK:
        s=session(request)
        if version=='original': data=s.original
        elif version=='preview':
            if not s.pending: raise HTTPException(404,'ไม่มี Preview')
            data=s.pending[1]
        elif version=='current': data=s.current
        else: raise HTTPException(422,'version ไม่ถูกต้อง')
        if pages:
            try:
                selected=[int(x)-1 for x in pages.split(',')]
                with pdf.open_pdf(data) as doc:
                    if not selected or any(x<0 or x>=len(doc) for x in selected): raise ValueError()
                    doc.select(selected); data=doc.tobytes(garbage=4,deflate=True)
            except Exception: raise HTTPException(422,'ระบุหน้าที่ต้องการ เช่น 1,3,4')
        safe=re.sub(r'[^a-zA-Z0-9._-]','_',name)[:100]
        if not safe.lower().endswith('.pdf'): safe+='.pdf'
        return Response(data,media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename="{safe}"'})

@app.post('/api/apply')
def apply_immediately(request:Request,op:Operation):
    """Validate and save one undoable change atomically, without a review step."""
    with store.LOCK:
        s=session(request)
        if op.revision!=s.revision: raise HTTPException(409,'เอกสารเปลี่ยนแล้ว กรุณาโหลดใหม่')
        if op.kind=='add_text' and not op.rect: raise ValueError('ต้องระบุขอบเขตข้อความ')
        data,warnings=pdf.apply(s.current,op.model_dump())
        if len(data)+sum(map(len,s.history))+len(s.original)>store.MAX_BYTES:
            raise ValueError('พื้นที่เซสชันไม่เพียงพอ กรุณาส่งออกและเปิดไฟล์ใหม่')
        s.commit(data)
        return {**state(s),'edit_warnings':warnings}

@app.post('/api/editing-context')
def editing_context(request:Request,op:Operation):
    """Temporary canvas and licensed original font; never commits a change."""
    with store.LOCK:
        s=session(request)
        if op.revision!=s.revision: raise HTTPException(409,'เอกสารเปลี่ยนแล้ว กรุณาเปิดข้อความใหม่')
        pdf.require_editable(s.current)
        with pdf.open_pdf(s.current) as doc:
            if op.page>=len(doc): raise ValueError('เลขหน้าไม่ถูกต้อง')
            page=doc[op.page]
            line=next((line for line in pdf.lines(page) if line['id']==op.line_id),None)
            if not line or not line['editable']: raise ValueError('ข้อความนี้ยังแก้ไขไม่ได้')
            local=pdf.exact_local_font(line,line['text'])
            font=local or pdf.reusable_font(doc,page,line,line['text'])
            if op.font_name: font=pdf.exact_local_font({'font':op.font_name},op.text or line['text'])
            if not font: raise ValueError('ไม่พบไฟล์ฟอนต์เดิมที่ใช้แสดงระหว่างพิมพ์ได้ กรุณาติดตั้งฟอนต์เดิมบนเซิร์ฟเวอร์')
            subsets=[]
            for entry in page.get_fonts(full=True):
                if pdf.font_key(entry[3])!=pdf.font_key(line['font']): continue
                content=doc.extract_font(entry[0])[3]
                if content and content not in subsets: subsets.append(content)
            # Load all compatible original subsets, so Latin typed into Thai
            # text does not silently use a browser fallback font.
            try:
                chars=set()
                for content in subsets:
                    with pdf.TTFont(pdf.BytesIO(content)) as candidate:
                        chars.update((candidate.getBestCmap() or {}).keys())
                if not op.font_name and not local: font=pdf.merge_original_subsets(tuple(subsets),''.join(map(chr,sorted(chars)))) or font
            except Exception: pass
            with pdf.TTFont(pdf.BytesIO(font[1])) as original:
                units=original['head'].unitsPerEm
                ascent=original['hhea'].ascent/units
                descent=abs(original['hhea'].descent)/units
            # Removing text from a temporary copy preserves colored backgrounds,
            # rules and pictures. Original/current/history remain untouched.
            background,_=pdf.apply(s.current,dict(kind='delete_text',page=op.page,line_id=op.line_id))
            return dict(font=base64.b64encode(font[1]).decode('ascii'),
                        background=base64.b64encode(background).decode('ascii'),
                        ascent=ascent,descent=descent,revision=s.revision)

@app.post('/api/preview')
def preview(request:Request,op:Operation):
    with store.LOCK:
        s=session(request)
        if op.revision!=s.revision: raise HTTPException(409,'เอกสารเปลี่ยนแล้ว กรุณาโหลดใหม่')
        if op.kind=='add_text' and not op.rect: raise ValueError('ต้องระบุขอบเขตข้อความ')
        data,warnings=pdf.apply(s.current,op.model_dump())
        if len(data)+sum(map(len,s.history))+len(s.original)>store.MAX_BYTES: raise ValueError('พื้นที่เซสชันไม่เพียงพอ กรุณาส่งออกและเปิดไฟล์ใหม่')
        ident=secrets.token_urlsafe(16); s.pending=(ident,data,s.revision)
        info=pdf.inspect(data)
        return {**info,'preview_id':ident,'warnings':warnings+info['warnings']}

@app.post('/api/commit')
def commit(request:Request,body:Accept):
    with store.LOCK:
        s=session(request)
        if not s.pending or s.pending[0]!=body.preview_id or s.revision!=body.revision:
            raise HTTPException(409,'Preview หมดอายุ กรุณาทำใหม่')
        s.commit(s.pending[1]); return state(s)

@app.post('/api/cancel')
def cancel(request:Request):
    with store.LOCK: session(request).pending=None; return {'ok':True}

@app.post('/api/history/{direction}')
def history(request:Request,direction:str):
    with store.LOCK:
        s=session(request)
        offset={'undo':-1,'redo':1}.get(direction)
        if offset is None or not 0<=s.cursor+offset<len(s.history): raise ValueError('ไม่มีประวัติให้ย้อนกลับ')
        s.cursor+=offset; s.revision+=1; s.pending=None; return state(s)

@app.get('/api/search')
def search(request:Request,q:str):
    with store.LOCK: return {'hits':pdf.search(session(request).current,q)}

@app.post('/api/merge')
async def merge(request:Request,file:UploadFile=File(...)):
    extra=await file.read(25*1024*1024+1); await file.close()
    if len(extra)>25*1024*1024: raise HTTPException(413,'ไฟล์ใหญ่เกิน 25 MB')
    pdf.require_editable(extra)
    with store.LOCK:
        s=session(request); pdf.require_editable(s.current)
        with pdf.open_pdf(s.current) as doc, pdf.open_pdf(extra) as other:
            if len(doc)+len(other)>200: raise ValueError('รวมแล้วเกิน 200 หน้า')
            doc.insert_pdf(other); data=doc.tobytes(garbage=4,deflate=True)
        if len(data)+sum(map(len,s.history))+len(s.original)>store.MAX_BYTES: raise ValueError('พื้นที่เซสชันไม่เพียงพอ')
        ident=secrets.token_urlsafe(16); s.pending=(ident,data,s.revision)
        return dict(preview_id=ident,**pdf.inspect(data))

@app.post('/api/ocr/{page}')
def ocr(request:Request,page:int):
    with store.LOCK:
        s=session(request)
        with pdf.open_pdf(s.current) as doc:
            if not 0<=page<len(doc): raise ValueError('เลขหน้าไม่ถูกต้อง')
            try:
                tp=doc[page].get_textpage_ocr(language='tha+eng',dpi=150,full=True)
                return {'text':doc[page].get_text(textpage=tp),'notice':'ผล OCR เพื่ออ่านและคัดลอกเท่านั้น ยังไม่ได้แก้ไขภาพสแกน'}
            except Exception as exc:
                raise HTTPException(503,'OCR ยังไม่พร้อม: ติดตั้ง Tesseract และข้อมูลภาษา tha/eng แล้วตั้ง TESSDATA_PREFIX') from exc

@app.delete('/api/document')
def close(request:Request,response:Response):
    with store.LOCK: store.sessions.pop(request.cookies.get('smart_session',''),None)
    response.delete_cookie('smart_session'); return {'ok':True}

# Built frontend can also run on the same Python server without Node at runtime.
frontend_dist=Path(__file__).resolve().parents[2]/'frontend'/'dist'
if frontend_dist.is_dir():
    app.mount('/',StaticFiles(directory=frontend_dist,html=True),name='frontend')
