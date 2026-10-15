from pathlib import Path
import hashlib
import pytest
import pymupdf as fitz
from app import pdf_engine as pdf

SAMPLES=Path(__file__).resolve().parents[2]/'samples'

def matching_line(data,word):
    with pdf.open_pdf(data) as doc:
        return next(line for line in pdf.lines(doc[0]) if word in line['text'])

def font_hashes(data):
    with pdf.open_pdf(data) as doc:
        return {hashlib.sha256(doc.extract_font(entry[0])[3]).hexdigest()
                for entry in doc[0].get_fonts(full=True) if entry[1] in ('ttf','otf')}

def test_thai_keeps_font_bytes_size_color_and_baseline():
    original=(SAMPLES/'demo.pdf').read_bytes()
    before=matching_line(original,'ตอนรับ')
    edited,warnings=pdf.apply(original,{'kind':'replace','query':'ตอนรับ','text':'ต้อนรับ','all':True})
    after=matching_line(edited,'บริษัท')
    assert after['text']=='บริษัทมีความยินดีต้อนรับลูกค้า'
    assert after['font']==before['font']
    assert after['size']==pytest.approx(before['size'],abs=.001)
    assert after['origin']==pytest.approx(before['origin'],abs=.001)
    assert after['color']==before['color']
    assert font_hashes(edited)==font_hashes(original)
    assert any('ฟอนต์เดิม' in w for w in warnings)

def test_english_correction_does_not_shrink():
    original=(SAMPLES/'demo.pdf').read_bytes()
    before=matching_line(original,'welcom')
    edited,_=pdf.apply(original,{'kind':'replace','query':'welcom','text':'welcome','all':True})
    after=matching_line(edited,'welcome')
    assert after['size']==pytest.approx(before['size'],abs=.001)
    assert after['origin']==pytest.approx(before['origin'],abs=.001)

def test_table_edge_blocks_expansion_instead_of_shrinking():
    with fitz.open() as d:
        p=d.new_page();p.insert_text((50,80),'Short',fontsize=12)
        p.draw_line((85,60),(85,100))
        original=d.tobytes()
    line=matching_line(original,'Short')
    with pytest.raises(ValueError,match='ยาวเกิน'):
        pdf.apply(original,{'kind':'edit','line_id':line['id'],'text':'Long text crossing cell'})

def test_missing_original_font_never_uses_noto(monkeypatch):
    original=(SAMPLES/'demo.pdf').read_bytes()
    monkeypatch.setattr(pdf,'reusable_font',lambda *args:None)
    monkeypatch.setattr(pdf,'exact_local_font',lambda *args:None)
    with pytest.raises(ValueError,match='เพิ่มฟอนต์'):
        pdf.apply(original,{'kind':'replace','query':'ตอนรับ','text':'ต้อนรับ','all':True})

def test_non_noto_thai_font_is_retained():
    path=Path('C:/Windows/Fonts/tahoma.ttf')
    if not path.exists(): pytest.skip('Windows font fixture not available')
    with fitz.open() as d:
        p=d.new_page()
        p.insert_font(fontname='Original',fontfile=str(path))
        p.insert_text((50,100),'ภาษาไทย',fontname='Original',fontsize=16)
        original=d.tobytes()
    before=matching_line(original,'ภาษาไทย')
    edited,_=pdf.apply(original,{'kind':'edit','line_id':before['id'],'text':'ภาษาเรา'})
    after=matching_line(edited,'ภาษาเรา')
    assert after['font']==before['font']
    assert after['size']==pytest.approx(16,abs=.001)
    assert after['origin']==pytest.approx(before['origin'],abs=.001)
    assert font_hashes(edited)==font_hashes(original)
