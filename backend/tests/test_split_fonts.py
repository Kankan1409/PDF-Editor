import os
from pathlib import Path
from io import BytesIO
import pytest
from fontTools.ttLib import TTFont
from fontTools import subset
from PIL import Image, ImageChops, ImageDraw
from app import pdf_engine as pdf
from fastapi.testclient import TestClient
from app.main import app


def subset_font(text):
    font=TTFont(pdf.FONTS/'NotoSans.ttf')
    sub=subset.Subsetter();sub.populate(text=text);sub.subset(font)
    output=BytesIO();font.save(output);return output.getvalue()


def test_merge_same_font_subsets_and_missing_glyph():
    parts=(subset_font('AB'),subset_font('BC'))
    merged=pdf.merge_original_subsets(parts,'ABC')
    assert merged
    assert set(map(ord,'ABC')).issubset(TTFont(BytesIO(merged[1])).getBestCmap())
    assert pdf.merge_original_subsets(parts,'ABZ') is None


def test_conflicting_metrics_are_not_merged():
    first=subset_font('AB');font=TTFont(BytesIO(subset_font('BC')))
    name=font.getBestCmap()[ord('B')];advance,bearing=font['hmtx'][name]
    font['hmtx'][name]=(advance+10,bearing)
    output=BytesIO();font.save(output)
    assert pdf.merge_original_subsets((first,output.getvalue()),'ABC') is None


def test_private_ci03_mixed_text_repeat_edit_and_surroundings():
    path=os.getenv('CI03_TEST_PDF')
    if not path: pytest.skip('Set CI03_TEST_PDF; do not bundle private user PDF')
    original=Path(path).read_bytes()
    with pdf.open_pdf(original) as before:
        line=next(l for l in pdf.lines(before[0]) if l['text'].startswith('ข้าพเจ้า'))
        text=line['text'].replace('นายกิตติ','ssนายกิตติ')
        assert text!=line['text']
        result,_=pdf.apply(original,dict(kind='edit',line_id=line['id'],text=text))
        with pdf.open_pdf(result) as after:
            actual=next(l for l in pdf.lines(after[0]) if 'ssนายกิตติ' in l['text'])
            assert pdf.canonical(actual['text'])==pdf.canonical(text)
            assert actual['font']==line['font']
            assert actual['size']==pytest.approx(line['size'],abs=.001)
            assert actual['origin']==pytest.approx(line['origin'],abs=.001)
            assert actual['color']==line['color']
            for index in range(len(before)):
                a=before[index].get_pixmap();b=after[index].get_pixmap()
                diff=ImageChops.difference(Image.frombytes('RGB',(a.width,a.height),a.samples),Image.frombytes('RGB',(b.width,b.height),b.samples))
                if index==0:
                    box=pdf.fitz.Rect(line['bbox'])|pdf.fitz.Rect(actual['bbox'])
                    ImageDraw.Draw(diff).rectangle((int(box.x0)-2,int(box.y0)-2,int(box.x1)+2,int(box.y1)+2),fill='black')
                assert diff.getbbox() is None
            second,_=pdf.apply(result,dict(kind='edit',line_id=actual['id'],text=text.replace('ss','s')))
            with pdf.open_pdf(second) as reopened:
                assert pdf.canonical(text.replace('ss','s')) in pdf.canonical(reopened[0].get_text())
    with TestClient(app,headers={'X-Smart-PDF':'1'}) as client:
        response=client.post('/api/upload',files={'file':('regression.pdf',original)})
        assert response.status_code==200
        response=client.post('/api/apply',json=dict(kind='edit',revision=0,line_id=line['id'],text=text))
        assert response.status_code==200,response.text
        with pdf.open_pdf(client.get('/api/pdf').content) as exported:
            assert pdf.canonical(text) in pdf.canonical(exported[0].get_text())
