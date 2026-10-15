import base64
from test_editor import client,upload
from app import pdf_engine as pdf


def test_editing_context_is_temporary_and_uses_original_font(client):
    state=upload(client)
    line=next(l for l in state['pages'][0]['lines'] if 'ตอนรับ' in l['text'])
    before=client.get('/api/pdf').content
    response=client.post('/api/editing-context',json=dict(kind='edit',page=0,line_id=line['id'],revision=0))
    assert response.status_code==200,response.text
    context=response.json()
    with pdf.TTFont(pdf.BytesIO(base64.b64decode(context['font']))) as font:
        assert 'cmap' in font
    with pdf.open_pdf(base64.b64decode(context['background'])) as background,pdf.open_pdf(before) as original:
        assert line['text'] not in background[0].get_text()
        assert len(background)==len(original)
        assert len(background[0].get_drawings())==len(original[0].get_drawings())
    assert client.get('/api/pdf').content==before
    assert client.get('/api/document').json()['revision']==0
    assert not client.get('/api/document').json()['can_undo']
    assert context['ascent']>0 and context['descent']>=0


def test_editing_context_rejects_stale_revision(client):
    state=upload(client)
    response=client.post('/api/editing-context',json=dict(kind='edit',page=0,line_id=state['pages'][0]['lines'][0]['id'],revision=99))
    assert response.status_code==409
