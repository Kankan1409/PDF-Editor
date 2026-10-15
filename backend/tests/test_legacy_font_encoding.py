import hashlib
import os
from io import BytesIO
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw
from fastapi.testclient import TestClient

from app import pdf_engine as pdf
from app.main import app


def test_gsub_pua_and_shared_hyphen_mapping():
    with TTFont(pdf.FONTS/'NotoSansThai.ttf') as font:
        cmap=font.getBestCmap()
        hyphen=cmap[ord('-')]
        alternate='uni0E49.small'
        for table in font['cmap'].tables:
            if table.isUnicode():
                table.cmap[0xAD]=hyphen
                table.cmap[0xF70B]=alternate
        buf=BytesIO();font.save(buf)
        mapping=pdf.generated_unicode_map(buf.getvalue(),'ชื่อ-สกุล ดีแล้ว')
        assert mapping[font.getGlyphID(hyphen)]=='-'
        assert mapping[font.getGlyphID(alternate)]=='้'
        ambiguous=pdf.generated_unicode_map(buf.getvalue(),'-\xad')
        assert font.getGlyphID(hyphen) not in ambiguous


@pytest.fixture
def ci08():
    path=os.getenv('CI08_TEST_PDF')
    if not path: pytest.skip('Set CI08_TEST_PDF to the private regression PDF; never bundle user documents')
    return Path(path).read_bytes()


def font_hashes(doc):
    return {hashlib.sha256(doc.extract_font(entry[0])[3]).hexdigest()
            for entry in doc[0].get_fonts(full=True) if entry[1] in ('ttf','otf')}


@pytest.mark.parametrize('replacement',['ชื่อ-สกุล นายวรเทพ ดีแล้ว','ชื่อ-สกุล ทดสอบ ดีแล้ว'])
def test_ci08_exact_font_roundtrip_and_unchanged_surroundings(ci08,replacement):
    with pdf.open_pdf(ci08) as before:
        selected=next(line for line in pdf.lines(before[0]) if line['text'].startswith('ชื่อ-สกุล'))
        result,_=pdf.apply(ci08,{'kind':'edit','line_id':selected['id'],'text':replacement})
        with pdf.open_pdf(result) as after:
            actual=next(line for line in pdf.lines(after[0]) if line['text']==replacement)
            assert actual['font']==selected['font']=='THSarabunPSK'
            assert actual['size']==pytest.approx(selected['size'],abs=.001)
            assert actual['origin']==pytest.approx(selected['origin'],abs=.001)
            assert actual['color']==selected['color']
            assert font_hashes(after)==font_hashes(before)
            assert after[0].rect==before[0].rect
            a=before[0].get_pixmap();b=after[0].get_pixmap()
            diff=ImageChops.difference(Image.frombytes('RGB',(a.width,a.height),a.samples),Image.frombytes('RGB',(b.width,b.height),b.samples))
            box=pdf.fitz.Rect(selected['bbox'])|pdf.fitz.Rect(actual['bbox'])
            ImageDraw.Draw(diff).rectangle((int(box.x0)-2,int(box.y0)-2,int(box.x1)+2,int(box.y1)+2),fill='black')
            assert diff.getbbox() is None


def test_ci08_preview_commit_download(ci08):
    with TestClient(app,headers={'X-Smart-PDF':'1'}) as client:
        response=client.post('/api/upload',files={'file':('regression.pdf',ci08)})
        assert response.status_code==200
        state=response.json()
        line=next(line for line in state['pages'][0]['lines'] if line['text'].startswith('ชื่อ-สกุล'))
        text='ชื่อ-สกุล นายวรเทพ ดีแล้ว'
        response=client.post('/api/preview',json={'revision':state['revision'],'kind':'edit','line_id':line['id'],'text':text})
        assert response.status_code==200,response.text
        assert client.get('/api/pdf').content==ci08
        response=client.post('/api/commit',json={'preview_id':response.json()['preview_id'],'revision':state['revision']})
        assert response.status_code==200
        with pdf.open_pdf(client.get('/api/pdf').content) as result:
            assert text in result[0].get_text()
