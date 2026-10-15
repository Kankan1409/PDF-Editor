from pathlib import Path
import time
import pytest
import pymupdf as fitz
from PIL import Image, ImageChops, ImageDraw
from fastapi.testclient import TestClient
from app.main import app
from app import pdf_engine as pdf, store

SAMPLES=Path(__file__).resolve().parents[2]/'samples'
@pytest.fixture
def client():
    store.sessions.clear()
    with TestClient(app,headers={'X-Smart-PDF':'1'}) as c: yield c

def upload(c,name='demo.pdf'):
    r=c.post('/api/upload',files={'file':(name,(SAMPLES/name).read_bytes(),'application/pdf')})
    assert r.status_code==200,r.text
    return r.json()

def edit(c,op):
    state=c.get('/api/document').json()
    r=c.post('/api/preview',json={**op,'revision':state['revision']})
    assert r.status_code==200,r.text
    preview=r.json()
    r=c.post('/api/commit',json={'preview_id':preview['preview_id'],'revision':state['revision']})
    assert r.status_code==200,r.text
    return r.json(),preview

def contents(c):
    with pdf.open_pdf(c.get('/api/pdf').content) as doc: return '\n'.join(p.get_text() for p in doc)

def test_upload_all_pages_and_isolation(client):
    s=upload(client);assert s['page_count']==2
    assert all(p['lines'] for p in s['pages'])
    assert TestClient(app).get('/api/pdf').status_code==401

def test_english_preview_cancel_commit_undo_redo(client):
    s=upload(client);line=next(l for l in s['pages'][0]['lines'] if 'welcom' in l['text'])
    original=client.get('/api/pdf').content
    op={'kind':'edit','page':0,'line_id':line['id'],'text':'A warm welcome to Northstar','revision':0}
    p=client.post('/api/preview',json=op);assert p.status_code==200,p.text
    assert client.get('/api/pdf').content==original
    client.post('/api/cancel');assert client.get('/api/pdf?version=preview').status_code==404
    edit(client,{k:v for k,v in op.items() if k!='revision'})
    assert 'A warm welcome to Northstar' in contents(client)
    client.post('/api/history/undo');assert client.get('/api/pdf').content==original
    client.post('/api/history/redo');assert 'A warm welcome to Northstar' in contents(client)

def test_thai_typo_and_graphics_preserved(client):
    upload(client)
    hits=client.get('/api/search',params={'q':'ตอนรับ'}).json()['hits'];assert len(hits)==1
    before=client.get('/api/pdf').content
    edit(client,{'kind':'replace','query':'ตอนรับ','text':'ต้อนรับ','all':True})
    text=contents(client);assert 'ต้อนรับ' in text;assert 'ตอนรับ' not in text
    after=client.get('/api/pdf').content
    with pdf.open_pdf(before) as a,pdf.open_pdf(after) as b:
        assert len(a[0].get_drawings())==len(b[0].get_drawings())
        assert a[0].rect==b[0].rect

def test_add_delete_text(client):
    upload(client)
    s,_=edit(client,{'kind':'add_text','page':1,'text':'Added note','rect':[50,400,400,440]})
    assert 'Added note' in contents(client)
    line=next(l for l in s['pages'][1]['lines'] if 'Added note' in l['text'])
    edit(client,{'kind':'delete_text','page':1,'line_id':line['id']})
    assert 'Added note' not in contents(client)

def test_pages_merge_split_export(client):
    upload(client)
    s,_=edit(client,{'kind':'add_page','page':0});assert s['page_count']==3
    s,_=edit(client,{'kind':'reorder','order':[2,0,1]});assert 'PROJECT' in s['pages'][0]['lines'][0]['text']
    s,_=edit(client,{'kind':'rotate','page':1});assert s['pages'][1]['rotation']==90
    s,_=edit(client,{'kind':'delete_page','page':2});assert s['page_count']==2
    r=client.post('/api/merge',files={'file':('extra.pdf',(SAMPLES/'demo.pdf').read_bytes())});assert r.status_code==200,r.text
    r=client.post('/api/commit',json={'preview_id':r.json()['preview_id'],'revision':s['revision']});assert r.json()['page_count']==4
    r=client.get('/api/pdf',params={'name':'../../report.pdf','pages':'1,3'})
    with pdf.open_pdf(r.content) as d:
        assert len(d)==2
        for p in d: assert p.get_pixmap().width>0
    assert '/' not in r.headers['content-disposition'].split('filename=')[1]

@pytest.mark.parametrize('filename',['corrupt.pdf','encrypted.pdf'])
def test_invalid_files(client,filename):
    r=client.post('/api/upload',files={'file':(filename,(SAMPLES/filename).read_bytes())});assert r.status_code==422

def test_scan_not_automatically_text(client):
    s=upload(client,'scanned.pdf');assert s['pages'][0]['kind']=='scan';assert not s['pages'][0]['lines']
    before=client.get('/api/pdf').content
    r=client.post('/api/ocr/0');assert r.status_code in (200,503)
    assert client.get('/api/pdf').content==before

def test_embedded_font_and_no_silent_fallback(client):
    s=upload(client)
    line=next(l for l in s['pages'][1]['lines'] if 'Embedded font example' in l['text'])
    _,p=edit(client,{'kind':'edit','page':1,'line_id':line['id'],'text':'Embedded font example: Hello customer.'})
    assert any('นำฟอนต์ฝังเดิม' in w for w in p['warnings'])
    assert 'Hello customer.' in contents(client)
    s=client.get('/api/document').json();line=s['pages'][1]['lines'][0]
    before=client.get('/api/pdf').content
    r=client.post('/api/preview',json={'revision':s['revision'],'kind':'edit','page':1,'line_id':line['id'],'text':'บันทึกโครงการ'})
    assert r.status_code==422
    assert 'เพิ่มฟอนต์' in r.json()['detail']
    assert client.get('/api/pdf').content==before

def test_stale_preview_and_origin(client):
    upload(client)
    assert client.post('/api/preview',json={'kind':'rotate','revision':999}).status_code==409
    assert client.post('/api/history/undo',headers={'Origin':'https://evil.example'}).status_code==403

def test_restricted_signed_collision_and_overflow():
    d=fitz.open();p=d.new_page();p.insert_text((50,60),'Keep this text');p.insert_text((50,60),'Overlap')
    data=d.tobytes();line=pdf.inspect(data)['pages'][0]['lines'][0]
    with pytest.raises(ValueError,match='ซ้อน'): pdf.apply(data,{'kind':'edit','line_id':line['id'],'text':'Changed'})
    d=fitz.open();p=d.new_page();p.insert_text((50,60),'Short')
    data=d.tobytes();line=pdf.inspect(data)['pages'][0]['lines'][0]
    with pytest.raises(ValueError,match='ยาวเกิน'): pdf.apply(data,{'kind':'edit','line_id':line['id'],'text':'Long '*100})
    secured=d.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',permissions=fitz.PDF_PERM_PRINT)
    assert not pdf.inspect(secured)['editable']
    with pytest.raises(ValueError): pdf.apply(secured,{'kind':'rotate'})
    widget=fitz.Widget();widget.field_name='Signature1';widget.field_type=fitz.PDF_WIDGET_TYPE_SIGNATURE;widget.rect=fitz.Rect(20,100,200,150);p.add_widget(widget)
    assert not pdf.inspect(d.tobytes())['editable']

def test_session_expiry(client):
    upload(client)
    for s in store.sessions.values(): s.touched=time.time()-store.TTL-10
    store.cleanup();assert client.get('/api/document').status_code==401

def test_thai_combining_marks_roundtrip(client):
    s=upload(client)
    original=contents(client)
    assert 'ขอบคุณที่ไว้วางใจ' in original
    assert 'ทุกขั้นตอน' in original
    edit(client,{'kind':'add_text','page':1,'rect':[50,400,540,470],
                 'text':'ขอบคุณที่ไว้วางใจ ทุกขั้นตอน น้ำ ผู้ใช้ กุ้ง'})
    assert pdf.canonical('ขอบคุณที่ไว้วางใจ ทุกขั้นตอน น้ำ ผู้ใช้ กุ้ง') in pdf.canonical(contents(client))

def test_pixels_outside_edited_region_unchanged():
    before=(SAMPLES/'demo.pdf').read_bytes()
    target=next(l for l in pdf.inspect(before)['pages'][0]['lines'] if 'ตอนรับ' in l['text'])
    after,_=pdf.apply(before,{'kind':'replace','query':'ตอนรับ','text':'ต้อนรับ','all':True})
    with pdf.open_pdf(before) as a,pdf.open_pdf(after) as b:
        ap=a[0].get_pixmap();bp=b[0].get_pixmap()
        diff=ImageChops.difference(Image.frombytes('RGB',(ap.width,ap.height),ap.samples),Image.frombytes('RGB',(bp.width,bp.height),bp.samples))
        x0,y0,x1,y1=target['bbox']
        ImageDraw.Draw(diff).rectangle((int(x0)-2,int(y0)-2,int(x1)+2,int(y1)+2),fill='black')
        assert diff.getbbox() is None

def test_replace_single_and_not_found(client):
    s=upload(client)
    hit=client.get('/api/search',params={'q':'Northstar'}).json()['hits'][0]
    edit(client,{'kind':'replace','page':hit['page'],'line_id':hit['line_id'],'start':hit['start'],'query':'Northstar','text':'NorthStar'})
    assert 'NorthStar' in contents(client)
    assert client.get('/api/search',params={'q':'does-not-exist'}).json()['hits']==[]
