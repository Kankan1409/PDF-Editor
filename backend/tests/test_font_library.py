import os
from pathlib import Path
from io import BytesIO
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import pdf_engine as pdf
from test_editor import client,upload


def test_bundled_fonts_cover_thai_and_english(client):
    upload(client)
    result=client.get('/api/fonts')
    assert result.status_code==200
    fonts={font['name']:font for font in result.json()['fonts']}
    for name in ['Sarabun-SemiBold','Kanit-Regular','Prompt-Regular','BaiJamjuree-Regular','THSarabunPSK','THSarabunPSK-Bold','THSarabunPSK-Italic','THSarabunPSK-BoldItalic']:
        assert fonts[name]['thai'] and fonts[name]['english']
    assert fonts['Lato-Regular']['english']


def test_import_validation_and_session_isolation(client):
    upload(client)
    font=pdf.TTFont(pdf.FONTS/'Sarabun-Regular.ttf')
    for record in font['name'].names:
        if record.nameID in (4,6): record.string='PrivateTestFont'.encode(record.getEncoding())
    buf=BytesIO();font.save(buf)
    response=client.post('/api/fonts',files={'file':('../../private.ttf',buf.getvalue())})
    assert response.status_code==200,response.text
    assert any(f['name']=='PrivateTestFont' for f in client.get('/api/fonts').json()['fonts'])
    with TestClient(app,headers={'X-Smart-PDF':'1'}) as other:
        upload(other)
        assert all(f['name']!='PrivateTestFont' for f in other.get('/api/fonts').json()['fonts'])
    assert client.post('/api/fonts',files={'file':('bad.ttf',b'not a font')}).status_code==422
    font['OS/2'].fsType=2;buf=BytesIO();font.save(buf)
    assert client.post('/api/fonts',files={'file':('restricted.ttf',buf.getvalue())}).status_code==422


def test_resume_explicit_font_choice_edits_thai(client):
    path=os.getenv('RESUME_TEST_PDF')
    if not path: pytest.skip('Set RESUME_TEST_PDF; private document not distributed')
    data=Path(path).read_bytes()
    state=client.post('/api/upload',files={'file':('resume.pdf',data)}).json()
    line=next(l for l in state['pages'][0]['lines'] if 'Kanyarat' in l['text'])
    op=dict(kind='edit',page=0,line_id=line['id'],revision=0,text='Kanyarat ด',font_name='Sarabun-SemiBold')
    context=client.post('/api/editing-context',json=op)
    assert context.status_code==200,context.text
    assert client.get('/api/pdf').content==data
    result=client.post('/api/apply',json=op)
    assert result.status_code==200,result.text
    with pdf.open_pdf(client.get('/api/pdf').content) as doc:
        actual=next(l for l in pdf.lines(doc[0]) if l['text']=='Kanyarat ด')
        assert actual['font']=='Sarabun-SemiBold'
        assert actual['size']==pytest.approx(line['size'],abs=.001)
        assert actual['origin']==pytest.approx(line['origin'],abs=.001)
    client.post('/api/history/undo')
    assert client.get('/api/pdf').content==data
