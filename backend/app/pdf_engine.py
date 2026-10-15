"""Conservative PDF edits. Original bytes never mutate before preview acceptance."""
from pathlib import Path
from io import BytesIO
import html
import re
import hashlib
import unicodedata
import os
from functools import lru_cache
from contextvars import ContextVar
import pymupdf as fitz
from fontTools.ttLib import TTFont
from fontTools.merge import Merger
from fontTools.pens.recordingPen import DecomposingRecordingPen

FONTS = Path(__file__).resolve().parents[1] / 'fonts'
session_fonts=ContextVar('session_fonts',default=None)
# Full ascender/descender boxes include Thai marks above/below the baseline.
fitz.TOOLS.set_small_glyph_heights(False)

def canonical(text):
    return ''.join(unicodedata.normalize('NFKC',text).split())

def repair_generated_thai_cmaps(doc, start_xref):
    """MuPDF Story omits GSUB alternate glyphs from ToUnicode. Repair ONLY
    newly embedded Noto Thai fonts, whose licensed glyph names are known."""
    for xref in range(start_xref,doc.xref_length()):
        if doc.xref_get_key(xref,'Type') != ('name','/Font'): continue
        try:
            name,ext,_,content=doc.extract_font(xref)
            if not content or 'notosansthai' not in re.sub('[^a-z]','',name.lower()): continue
            font=TTFont(BytesIO(content)); cmap=font.getBestCmap() or {}
            reverse={glyph:chr(code) for code,glyph in cmap.items()}
            special={'nikhahit_maiChattawathai':'\u0e4d\u0e4b','nikhahit_maiEkthai':'\u0e4d\u0e48',
                     'nikhahit_maiThothai':'\u0e4d\u0e49','nikhahit_maiTrithai':'\u0e4d\u0e4a'}
            pairs=[]
            for gid,glyph in enumerate(font.getGlyphOrder()):
                base=glyph.split('.')[0]
                text=reverse.get(glyph) or reverse.get(base) or special.get(base)
                if not text and re.fullmatch(r'uni(?:[0-9A-Fa-f]{4})+',base):
                    text=''.join(chr(int(base[i:i+4],16)) for i in range(3,len(base),4))
                if text: pairs.append(f'<{gid:04x}> <{text.encode("utf-16-be").hex()}>')
            header='/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n'
            for i in range(0,len(pairs),100):
                block=pairs[i:i+100];header+=f'{len(block)} beginbfchar\n'+'\n'.join(block)+'\nendbfchar\n'
            header+='endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend'
            kind,ref=doc.xref_get_key(xref,'ToUnicode')
            if kind=='xref': doc.update_stream(int(ref.split()[0]),header.encode())
        except (KeyError,ValueError):
            continue

def open_pdf(data: bytes):
    if not data.startswith(b'%PDF-'):
        raise ValueError('ไฟล์ไม่ใช่ PDF')
    try:
        doc = fitz.open(stream=data, filetype='pdf')
    except Exception as exc:
        raise ValueError('ไฟล์ PDF เสียหายหรืออ่านไม่ได้') from exc
    if doc.needs_pass:
        doc.close()
        raise ValueError('PDF เข้ารหัส: กรุณาปลดล็อกด้วยโปรแกรมที่ได้รับอนุญาตก่อน')
    if not 1 <= len(doc) <= 200:
        doc.close()
        raise ValueError('รองรับเอกสาร 1–200 หน้า')
    if any(max(p.rect.width, p.rect.height) > 3000 for p in doc):
        doc.close()
        raise ValueError('ขนาดหน้าเกินขอบเขตที่รองรับ 3000 pt')
    return doc

def lines(page):
    result = []
    for bi, block in enumerate(page.get_text('dict')['blocks']):
        for li, line in enumerate(block.get('lines', [])):
            spans = [s for s in line['spans'] if s['text']]
            if not spans:
                continue
            first = spans[0]
            mixed = any((s['font'], round(s['size'], 2), s['color'], s['flags']) !=
                        (first['font'], round(first['size'], 2), first['color'], first['flags']) for s in spans)
            result.append(dict(id=f'{bi}:{li}', text=''.join(s['text'] for s in spans),
                bbox=list(line['bbox']), origin=list(first['origin']), font=first['font'],
                size=first['size'], color=f'#{first["color"]:06x}', flags=first['flags'],
                editable=not mixed and tuple(line['dir']) == (1.0, 0.0), mixed=mixed))
    return result

def inspect(data):
    with open_pdf(data) as doc:
        signed = doc.get_sigflags() > 0 or any(w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE for p in doc for w in (p.widgets() or []))
        restricted = not bool(doc.permissions & fitz.PDF_PERM_MODIFY)
        pages = []
        for p in doc:
            text = lines(p)
            pages.append(dict(index=p.number, width=p.rect.width, height=p.rect.height,
                base_width=p.cropbox.width, base_height=p.cropbox.height, rotation=p.rotation,
                kind='text' if text else ('scan' if p.get_images() else 'vector/empty'), lines=text))
        warnings = ['แก้ข้อความเดิมโดยรักษาฟอนต์ ขนาด และ baseline; หากใช้ฟอนต์เดิมไม่ได้จะปฏิเสธแทนการเปลี่ยนฟอนต์ ตรวจระยะห่างตัวอักษรใน Preview ทุกครั้ง']
        if signed: warnings.append('พบฟิลด์ลายเซ็น: MVP เปิดดูได้ แต่ไม่อนุญาตให้แก้ไข')
        if restricted: warnings.append('เอกสารจำกัดสิทธิ์แก้ไข: เปิดดูได้เท่านั้น')
        if doc.is_repaired: warnings.append('PDF มีโครงสร้างที่ต้องซ่อมระหว่างเปิด กรุณาตรวจทุกหน้า')
        return dict(pages=pages, page_count=len(doc), size=len(data), metadata=doc.metadata,
            editable=not signed and not restricted, warnings=warnings)

def require_editable(data):
    if not inspect(data)['editable']:
        raise ValueError('ไม่สามารถแก้ไข PDF ที่จำกัดสิทธิ์หรือมีลายเซ็นได้')

def search(data, query):
    if not query or len(query) > 500:
        raise ValueError('กรุณาระบุคำค้น 1–500 ตัวอักษร')
    hits = []
    with open_pdf(data) as doc:
        for p in doc:
            for line in lines(p):
                start = 0
                while (pos := line['text'].find(query, start)) >= 0:
                    hits.append(dict(page=p.number, line_id=line['id'], start=pos,
                                     before=line['text'], bbox=line['bbox']))
                    start = pos + len(query)
                    if len(hits) > 2000: raise ValueError('พบมากกว่า 2,000 ตำแหน่ง กรุณาค้นหาชื่อหรือข้อความให้เฉพาะเจาะจงขึ้น ยังไม่ได้แก้ไขเอกสาร')
    return hits

def reusable_font(doc, page, line, text):
    """Only reuse embeddable, complete font data that contains required glyphs."""
    subsets=[]
    complete=[]
    for entry in page.get_fonts(full=True):
        normalize=lambda name: re.sub(r'[^a-z0-9]', '', name.split('+')[-1].lower())
        if normalize(entry[3]) != normalize(line['font']): continue
        try:
            _, ext, _, content = doc.extract_font(entry[0])
            if not content or ext not in ('ttf', 'otf'): continue
            font = TTFont(BytesIO(content))
            flags = font['OS/2'].fsType if 'OS/2' in font else 2
            if flags & (2 | 256 | 512): continue
            cmap = font.getBestCmap() or {}
            if content not in subsets: subsets.append(content)
            if not all(ord(c) in cmap for c in text if not c.isspace()): continue
            complete.append(content)
        except Exception:
            continue
    if complete:
        content=complete[0]
        return fitz.Font(fontbuffer=content),content,transfer_unicode_mapping(subsets,TTFont(BytesIO(content)),text)
    return merge_original_subsets(tuple(subsets),text)


def glyph_signature(font, name):
    pen=DecomposingRecordingPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    return (font['hmtx'][name],pen.value)


def transfer_unicode_mapping(contents,target,text):
    identities={}
    for source in contents:
        font=TTFont(BytesIO(source))
        if font['head'].unitsPerEm!=target['head'].unitsPerEm: continue
        for gid,value in generated_unicode_map(source,text).items():
            signature=repr(glyph_signature(font,font.getGlyphName(gid)))
            identities.setdefault(signature,set()).add(value)
    mapping={}
    for gid,name in enumerate(target.getGlyphOrder()):
        values=identities.get(repr(glyph_signature(target,name)),set())
        if len(values)==1: mapping[gid]=next(iter(values))
    return mapping


@lru_cache(maxsize=16)
def merge_original_subsets(contents,text):
    """Reunite same-face subsets only when shared outlines and metrics agree."""
    if len(contents)<2 or len(contents)>8: return None
    try:
        fonts=[TTFont(BytesIO(content)) for content in contents]
        maps=[font.getBestCmap() or {} for font in fonts]
        required={ord(c) for c in text if not c.isspace()}
        if not required.issubset(set().union(*(set(cm) for cm in maps))): return None
        first=fonts[0]
        for font in fonts:
            if 'glyf' not in font or font['OS/2'].fsType & (2|256|512): return None
            if font_key(font['name'].getDebugName(6) or '') != font_key(first['name'].getDebugName(6) or ''): return None
            if font['head'].unitsPerEm!=first['head'].unitsPerEm: return None
            if any(getattr(font['hhea'],key)!=getattr(first['hhea'],key) for key in ('ascent','descent','lineGap')): return None
        # Same family names alone are insufficient: reject conflicting glyph designs.
        seen={}
        for font,cm in zip(fonts,maps):
            for code,name in cm.items():
                signature=glyph_signature(font,name)
                if code in seen and seen[code]!=signature: return None
                seen[code]=signature
        merged=Merger().merge([BytesIO(content) for content in contents])
        cm=merged.getBestCmap() or {}
        for code,signature in seen.items():
            if code not in cm or glyph_signature(merged,cm[code])!=signature: return None
        # Merger drops AAT morx. Preserve its proven Unicode identities by
        # matching unchanged glyph outlines, not by guessing PUA code points.
        mapping=transfer_unicode_mapping(contents,merged,text)
        out=BytesIO();merged.save(out);content=out.getvalue()
        return fitz.Font(fontbuffer=content),content,mapping
    except Exception:
        return None

def font_key(name):
    return re.sub(r'[^a-z0-9]', '', name.split('+')[-1].lower())

@lru_cache(maxsize=1)
def local_font_index():
    """Index exact PostScript/full names only: never choose a similar family."""
    directories=[FONTS]
    if os.name=='nt':
        directories.append(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts')
        if os.getenv('LOCALAPPDATA'): directories.append(Path(os.environ['LOCALAPPDATA'])/'Microsoft/Windows/Fonts')
    if os.getenv('PDF_FONT_DIR'): directories.append(Path(os.environ['PDF_FONT_DIR']))
    index={}
    for folder in directories:
        if not folder.is_dir(): continue
        for path in folder.iterdir():
            if path.suffix.lower() not in ('.ttf','.otf'): continue
            try:
                with TTFont(path,lazy=True) as font:
                    for name in font['name'].names:
                        if name.nameID in (4,6): index.setdefault(font_key(name.toUnicode()),[]).append(path)
            except Exception: continue
    return index

def exact_local_font(line,text):
    for content in (session_fonts.get() or {}).values():
        with TTFont(BytesIO(content)) as font:
            names={font_key(n.toUnicode()) for n in font['name'].names if n.nameID in (4,6)}
            if font_key(line['font']) not in names: continue
            cmap=font.getBestCmap() or {}
            if all(ord(c) in cmap for c in text if not c.isspace()): return fitz.Font(fontbuffer=content),content
    for path in local_font_index().get(font_key(line['font']),[]):
        try:
            content=path.read_bytes()
            with TTFont(BytesIO(content)) as font:
                rights=font['OS/2'].fsType if 'OS/2' in font else 2
                if rights & (2|256|512): continue
                cmap=font.getBestCmap() or {}
                if not all(ord(c) in cmap for c in text if not c.isspace()): continue
            return fitz.Font(fontbuffer=content),content
        except Exception: continue
    return None

def generated_unicode_map(font_bytes,text):
    """Recover Unicode for legacy PUA alternate glyphs from font GSUB data.

    Shared cmap glyphs (e.g. hyphen / soft hyphen) are resolved only when the
    requested text selects a unique character. Ambiguous cases remain subject
    to the existing exact read-back check; never normalize PUA in user text.
    """
    with TTFont(BytesIO(font_bytes)) as font:
        requested=set(text)
        candidates={}
        for code,glyph in (font.getBestCmap() or {}).items():
            char=chr(code)
            if unicodedata.category(char) not in ('Co','Cc'):
                candidates.setdefault(glyph,set()).add(char)
        singles=[]
        ligatures=[]
        if 'morx' in font:
            for chain in font['morx'].table.MorphChain:
                for subtable in chain.MorphSubtable:
                    state=getattr(subtable.SubStruct,'StateTable',None)
                    for lookup in getattr(state,'PerGlyphLookups',[]):
                        singles.extend((source,target) for source,target in lookup.items() if target!='.notdef')
        if 'GSUB' in font:
            for lookup in font['GSUB'].table.LookupList.Lookup:
                for sub in lookup.SubTable:
                    kind=lookup.LookupType
                    if kind==7: kind,sub=sub.ExtensionLookupType,sub.ExtSubTable
                    if kind==1: singles.extend(sub.mapping.items())
                    if kind==4:
                        for first,items in sub.ligatures.items():
                            ligatures.extend((tuple([first]+lig.Component),lig.LigGlyph) for lig in items)
        encoded=set(candidates)
        # Only infer for glyphs without an ordinary Unicode mapping (PUA or
        # GSUB-only). Do not reinterpret ordinary case/script substitutions.
        for _ in range(len(font.getGlyphOrder())):
            changed=False
            for source,target in singles:
                if target in encoded or source not in candidates: continue
                old=set(candidates.get(target,set()))
                candidates.setdefault(target,set()).update(candidates[source])
                changed |= old!=candidates[target]
            for sources,target in ligatures:
                if target in encoded or not all(len(candidates.get(s,set()))==1 for s in sources): continue
                value=''.join(next(iter(candidates[s])) for s in sources)
                if len(value)>16: continue
                old=set(candidates.get(target,set()))
                candidates.setdefault(target,set()).add(value)
                changed |= old!=candidates[target]
            if not changed: break
        mapping={}
        for gid,glyph in enumerate(font.getGlyphOrder()):
            choices=candidates.get(glyph,set())
            relevant={v for v in choices if (v in requested if len(v)==1 else v in text)}
            if len(relevant)==1: mapping[gid]=next(iter(relevant))
            elif len(choices)==1: mapping[gid]=next(iter(choices))
        return mapping

def repair_original_font_cmaps(doc,start_xref,font_bytes,text,proven_mapping=None):
    """Change only new Identity-H ToUnicode streams, never the font program."""
    mapping=generated_unicode_map(font_bytes,text)
    if proven_mapping: mapping.update(proven_mapping)
    expected_hash=hashlib.sha256(font_bytes).digest()
    for xref in range(start_xref,doc.xref_length()):
        if doc.xref_get_key(xref,'Type')!=('name','/Font'): continue
        if doc.xref_get_key(xref,'Encoding')!=('name','/Identity-H'): continue
        content=doc.extract_font(xref)[3]
        if hashlib.sha256(content).digest()!=expected_hash: continue
        kind,ref=doc.xref_get_key(xref,'ToUnicode')
        if kind!='xref': continue
        target=int(ref.split()[0])
        stream=doc.xref_stream(target).decode('ascii')
        # Later entries override only the proven mappings, retaining mappings
        # produced by the renderer for glyphs we cannot infer safely.
        pairs=[f'<{gid:04x}> <{value.encode("utf-16-be").hex()}>' for gid,value in mapping.items()]
        blocks=[]
        for i in range(0,len(pairs),100):
            block=pairs[i:i+100]
            blocks.append(f'{len(block)} beginbfchar\n'+'\n'.join(block)+'\nendbfchar\n')
        doc.update_stream(target,stream.replace('endcmap',''.join(blocks)+'endcmap').encode('ascii'))

def insert_original_shaped(doc,page,line,text,rect,font,warnings):
    """Shape with the exact font, then translate without scaling to old baseline."""
    if '\n' in text: raise ValueError('โหมดรักษาฟอนต์เดิมไม่ขึ้นบรรทัดใหม่ กรุณาแก้ภายในบรรทัดเดิม')
    with fitz.open() as scratch:
        temp=scratch.new_page(width=2800,height=max(200,line['size']*6))
        archive=fitz.Archive((font[1],'original.ttf'))
        css=f'''@font-face{{font-family:original;src:url(original.ttf)}}
        *{{margin:0;padding:0}} div{{font-family:original;font-size:{line['size']}pt;
        line-height:1;color:{line['color']};}}'''
        start=scratch.xref_length()
        layout=fitz.Rect(40,40,temp.rect.x1-40,temp.rect.y1-20)
        spare,scale=temp.insert_htmlbox(layout, '<div>'+html.escape(text)+'</div>',css=css,archive=archive,scale_low=1)
        repair_generated_thai_cmaps(scratch,start)
        repair_original_font_cmaps(scratch,start,font[1],text,font[2] if len(font)>2 else None)
        # Reopen so extraction uses the updated ToUnicode map.
        rendered=scratch.tobytes()
    with fitz.open(stream=rendered,filetype='pdf') as shaped:
        temp=shaped[0]
        shaped_lines=lines(temp)
        if spare<0 or scale!=1 or len(shaped_lines)!=1:
            raise ValueError('ไม่สามารถจัดข้อความด้วยฟอนต์เดิมในบรรทัดเดียวได้ จึงไม่เปลี่ยนฟอนต์อัตโนมัติ')
        shaped_line=shaped_lines[0]
        if canonical(shaped_line['text'])!=canonical(text):
            raise ValueError('ฟอนต์เดิมไม่สามารถเขียนข้อความใหม่และอ่านกลับได้ถูกต้อง จึงยกเลิกการแก้ไข')
        # Verify actual embedded bytes; Story must not silently use its fallback fonts.
        for entry in temp.get_fonts(full=True):
            embedded=shaped.extract_font(entry[0])[3]
            if hashlib.sha256(embedded).digest()!=hashlib.sha256(font[1]).digest():
                raise ValueError('ระบบจัดข้อความเลือกฟอนต์อื่น จึงยกเลิกเพื่อรักษาฟอนต์ต้นฉบับ')
        dx=line['origin'][0]-shaped_line['origin'][0]
        dy=line['origin'][1]-shaped_line['origin'][1]
        clip=fitz.Rect(shaped_line['bbox'])
        target=fitz.Rect(clip.x0+dx,clip.y0+dy,clip.x1+dx,clip.y1+dy)
        allowed=rect+(-.5,-.5,.5,.5)
        if not allowed.contains(target):
            raise ValueError('ข้อความใหม่ยาวเกินหรือสูงเกินพื้นที่เดิมเมื่อใช้ขนาดฟอนต์เดิม กรุณาย่อข้อความ; ระบบจะไม่ย่อขนาดหรือเปลี่ยนฟอนต์เอง')
        page.show_pdf_page(target,shaped,0,clip=clip,keep_proportion=False)
    warnings.append(f'ใช้ฟอนต์เดิม {line["font"]} ขนาด {line["size"]:g} pt และ baseline เดิม โดยไม่ย่อขนาด; โปรดตรวจระยะห่างตัวอักษร')

def insert_line(doc, page, line, text, rect, warnings):
    if not text: return
    rect=fitz.Rect(line.get('_available_rect',rect))
    color = tuple(int(line['color'][i:i+2], 16)/255 for i in (1,3,5))
    # Simple scripts can retain the original baseline and font metrics exactly.
    font = line.get('_font') or reusable_font(doc, page, line, text)
    simple = all(ord(c) < 256 for c in text) and '\n' not in text
    if line.get('_preserve') and font and not simple:
        insert_original_shaped(doc,page,line,text,rect,font,warnings)
        return
    if simple and font:
        size=line['size']
        if font[0].text_length(text,fontsize=size)>rect.width+.5: raise ValueError('ข้อความยาวเกินพื้นที่เมื่อใช้ขนาดเดิม กรุณาใช้ข้อความสั้นลง')
        alias='Edited'+hashlib.sha256(font[1]).hexdigest()[:12]
        page.insert_font(fontname=alias, fontbuffer=font[1])
        page.insert_text(line['origin'], text, fontname=alias, fontsize=size, color=color)
        warnings.append('นำฟอนต์ฝังเดิมกลับมาใช้; โปรดตรวจการเว้นวรรคและ baseline')
        return
    if simple and line['font'] in ('Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique', 'Times-Roman', 'Courier'):
        alias = {'Helvetica':'helv','Helvetica-Bold':'hebo','Helvetica-Oblique':'heit','Times-Roman':'tiro','Courier':'cour'}[line['font']]
        font_obj = fitz.Font(alias)
        size=line['size']
        if font_obj.text_length(text,fontsize=size)>rect.width+.5: raise ValueError('ข้อความยาวเกินพื้นที่เมื่อใช้ขนาดเดิม กรุณาใช้ข้อความสั้นลง')
        page.insert_text(line['origin'], text, fontsize=size, fontname=alias, color=color)
        return
    if line.get('_preserve'):
        raise ValueError(f'ฟอนต์ “{line["font"]}” ใช้กับข้อความใหม่นี้ไม่ได้ เลือกฟอนต์ไทย/อังกฤษจากรายการด้านขวา หรือกดเพิ่มฟอนต์เพื่อนำเข้าฟอนต์เดิมฉบับเต็ม')
    warnings.append('ใช้ฟอนต์ Noto ที่อนุญาตให้ฝังแทนฟอนต์เดิม พร้อมจัดรูปอักษรไทยใหม่; ตำแหน่งและขนาดอาจเปลี่ยน')
    if not (FONTS/'NotoSansThai.ttf').exists(): raise ValueError('ไม่พบฟอนต์ NotoSansThai.ttf บนเซิร์ฟเวอร์')
    css = f'''@font-face {{font-family:latin;src:url(NotoSans.ttf)}}
    @font-face {{font-family:thai;src:url(NotoSansThai.ttf)}}
    * {{margin:0;padding:0}} div {{font-family:thai,latin;font-size:{line['size']}pt;
    line-height:1; color:{line['color']}; font-weight:{'bold' if line['flags'] & 16 else 'normal'};
    font-style:{'italic' if line['flags'] & 2 else 'normal'};}}'''
    start_xref=doc.xref_length()
    spare, scale = page.insert_htmlbox(rect, '<div>'+html.escape(text).replace('\n','<br>')+'</div>',
        css=css, archive=fitz.Archive(str(FONTS)), scale_low=.65)
    repair_generated_thai_cmaps(doc,start_xref)
    if spare < 0: raise ValueError('ข้อความใหม่ไม่พอดีพื้นที่เดิม กรุณาย่อข้อความหรือเพิ่มกล่องใหม่')
    if scale < .99: warnings.append(f'ย่อขนาดข้อความเป็น {scale:.0%} เพื่อไม่ให้ล้นพื้นที่เดิม')

def available_line_rect(page,line,current):
    """Allow extra width only up to the next text, image or drawn cell edge."""
    rect=fitz.Rect(line['bbox'])
    right=max(rect.x1,page.rect.x1-18)
    for other in current.values():
        if other['id']==line['id']: continue
        box=fitz.Rect(other['bbox'])
        if box.y0<rect.y1 and box.y1>rect.y0 and box.x0>=rect.x1-.5:
            right=min(right,max(rect.x1,box.x0-2))
    for info in page.get_image_info():
        box=fitz.Rect(info['bbox'])
        if box.y0<rect.y1 and box.y1>rect.y0:
            if box.x0>=rect.x1: right=min(right,max(rect.x1,box.x0-2))
            elif box.x1>rect.x1: right=rect.x1
    for drawing in page.get_drawings():
        for item in drawing['items']:
            if item[0]=='l':
                a,b=item[1:3]
                if max(a.y,b.y)>=rect.y0 and min(a.y,b.y)<=rect.y1:
                    edge=min(a.x,b.x)
                    if edge>=rect.x1: right=min(right,max(rect.x1,edge-2))
            elif item[0]=='re':
                box=fitz.Rect(item[1])
                if box.y0<=rect.y1 and box.y1>=rect.y0:
                    for edge in (box.x0,box.x1):
                        if edge>=rect.x1: right=min(right,max(rect.x1,edge-2))
            else:
                # Unknown/curved artwork: do not expand through its bounding box.
                box=fitz.Rect(drawing['rect'])
                if box.y0<rect.y1 and box.y1>rect.y0:
                    if box.x0>=rect.x1: right=min(right,max(rect.x1,box.x0-2))
                    elif box.x1>rect.x1: right=rect.x1
    return [rect.x0,rect.y0,right,rect.y1]

def change_lines(doc, page_no, changes, warnings,font_name=None):
    page = doc[page_no]
    if page.rotation: raise ValueError('กรุณาหมุนหน้ากลับเป็น 0° ก่อนแก้ข้อความใน MVP')
    current = {line['id']:line for line in lines(page)}
    selected = []
    for ident, value in changes.items():
        if ident not in current: raise ValueError('ข้อความเปลี่ยนไปแล้ว กรุณาเลือกใหม่')
        line = current[ident]
        if not line['editable']: raise ValueError('บรรทัดนี้มีหลายรูปแบบหรือข้อความหมุน จึงไม่แก้ไขอัตโนมัติ')
        rect = fitz.Rect(line['bbox'])
        for other_id, other in current.items():
            if other_id != ident and (rect & fitz.Rect(other['bbox'])).get_area() > .01:
                raise ValueError('ขอบเขตข้อความซ้อนกับบรรทัดอื่น ไม่สามารถลบอย่างปลอดภัย')
        line['_preserve']=True
        line['_available_rect']=available_line_rect(page,line,current)
        if font_name:
            line['font']=font_name
            line['_font']=exact_local_font(line,value)
            if not line['_font']: raise ValueError('ฟอนต์ที่เลือกไม่มีตัวอักษรที่ต้องใช้ กรุณาเลือกฟอนต์อื่นหรือนำเข้าไฟล์ฟอนต์ฉบับเต็ม')
            warnings.append('เปลี่ยนฟอนต์ตามที่เลือก: '+font_name)
        else:
            line['_font']=reusable_font(doc,page,line,value) or exact_local_font(line,value)
        selected.append((line, value, rect))
    # Remove actual text content, keep images and vector graphics; never white-fill.
    for _, _, rect in selected: page.add_redact_annot(rect, fill=False, cross_out=False)
    page.apply_redactions(images=0, graphics=0, text=0)
    for line, value, rect in selected: insert_line(doc, page, line, value, rect, warnings)

def apply(data, op):
    require_editable(data)
    warnings = []
    verification=[]
    with open_pdf(data) as doc:
        kind = op['kind']; page_no = op.get('page', 0)
        if page_no < 0 or page_no >= len(doc): raise ValueError('เลขหน้าไม่ถูกต้อง')
        if kind in ('edit', 'delete_text'):
            if kind=='edit': verification.append((page_no,op.get('text','')))
            change_lines(doc, page_no, {op['line_id']:op.get('text','') if kind=='edit' else ''}, warnings,op.get('font_name'))
        elif kind == 'replace':
            query = op.get('query','')
            hits = search(data, query)
            if not hits: raise ValueError('ไม่พบข้อความที่ค้นหา')
            if not op.get('all', False):
                hits = [h for h in hits if h['page']==page_no and h['line_id']==op.get('line_id') and h['start']==op.get('start',0)]
                if not hits: raise ValueError('ตำแหน่งคำค้นเปลี่ยนไปแล้ว')
            changes = {}
            for h in hits:
                changes.setdefault(h['page'], {})[h['line_id']] = h['before']
            for pn, edits in changes.items():
                for ident, before in list(edits.items()):
                    if op.get('all'): edits[ident] = before.replace(query, op.get('text',''))
                    else:
                        start = op.get('start',0)
                        edits[ident] = before[:start] + op.get('text','') + before[start+len(query):]
                change_lines(doc, pn, edits, warnings,op.get('font_name'))
                verification.extend((pn,value) for value in edits.values())
        elif kind == 'add_text':
            p = doc[page_no]
            if p.rotation: raise ValueError('หมุนหน้ากลับ 0° ก่อนเพิ่มข้อความ')
            rect = fitz.Rect(op['rect'])
            if rect.is_empty or not p.rect.contains(rect): raise ValueError('ตำแหน่งอยู่นอกหน้า PDF')
            if any((rect & fitz.Rect(l['bbox'])).get_area() > 0 for l in lines(p)):
                raise ValueError('กล่องข้อความซ้อนกับข้อความเดิม กรุณาเปลี่ยนตำแหน่ง')
            line = dict(font='Noto', flags=0, color=op.get('color','#172b3a'),size=op.get('size',14),origin=[rect.x0,rect.y0+14])
            insert_line(doc,p,line,op.get('text',''),rect,warnings)
            verification.append((page_no,op.get('text','')))
        elif kind == 'add_page': doc.new_page(pno=page_no+1, width=doc[page_no].rect.width,height=doc[page_no].rect.height)
        elif kind == 'delete_page':
            if len(doc)==1: raise ValueError('ต้องเหลืออย่างน้อยหนึ่งหน้า')
            doc.delete_page(page_no)
        elif kind == 'rotate': doc[page_no].set_rotation((doc[page_no].rotation+90)%360)
        elif kind == 'reorder':
            order = op['order']
            if sorted(order) != list(range(len(doc))): raise ValueError('ลำดับหน้าไม่ถูกต้อง')
            doc.select(order)
        else: raise ValueError('ไม่รองรับการแก้ไขชนิดนี้')
        result = doc.tobytes(garbage=4, deflate=True)
    with open_pdf(result) as check:
        output_text=[canonical(p.get_text()) for p in check]
        for pn,text in verification:
            expected=canonical(text)
            if expected and expected not in output_text[pn]:
                raise ValueError('ข้อความหลังแก้ไขอ่านกลับไม่ตรงกับที่ระบุ จึงยกเลิกเพื่อป้องกันตัวอักษรผิด')
    return result, list(dict.fromkeys(warnings))
