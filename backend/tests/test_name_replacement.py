import pytest
from app import pdf_engine as pdf
from test_editor import client


def repeated_names():
    with pdf.fitz.open() as doc:
        for _ in range(2):
            page=doc.new_page()
            page.insert_text((40,70),'Alice met Alice.',fontsize=12)
            page.insert_text((40,110),'Alice signed.',fontsize=12)
        return doc.tobytes()


def test_one_at_a_time_and_replace_all_are_separate_undo_steps(client):
    original=repeated_names()
    assert client.post('/api/upload',files={'file':('names.pdf',original)}).status_code==200
    hits=client.get('/api/search?q=Alice').json()['hits'];assert len(hits)==6
    for revision in range(2):
        hit=hits[0]
        result=client.post('/api/apply',json=dict(kind='replace',revision=revision,page=hit['page'],line_id=hit['line_id'],start=hit['start'],query='Alice',text='Bob'))
        assert result.status_code==200,result.text
        hits=client.get('/api/search?q=Alice').json()['hits']
        assert len(hits)==5-revision
    result=client.post('/api/apply',json=dict(kind='replace',revision=2,query='Alice',text='Bob',all=True))
    assert result.status_code==200,result.text
    assert not client.get('/api/search?q=Alice').json()['hits']
    client.post('/api/history/undo');assert len(client.get('/api/search?q=Alice').json()['hits'])==4
    client.post('/api/history/undo');client.post('/api/history/undo')
    assert client.get('/api/pdf').content==original


def test_failed_replace_all_leaves_document_unchanged(client):
    original=repeated_names();client.post('/api/upload',files={'file':('names.pdf',original)})
    result=client.post('/api/apply',json=dict(kind='replace',revision=0,query='Alice',text='Bob',all=True,font_name='Missing-font'))
    assert result.status_code==422
    assert client.get('/api/pdf').content==original


def test_many_matches_are_not_silently_partially_replaced(client):
    with pdf.fitz.open() as doc:
        page=doc.new_page()
        for row in range(67): page.insert_text((30,30+row*10),'A '*30,fontsize=6)
        original=doc.tobytes()
    client.post('/api/upload',files={'file':('many.pdf',original)})
    result=client.post('/api/apply',json=dict(kind='replace',revision=0,query='A',text='B',all=True))
    assert result.status_code==422
    assert '2,000' in result.json()['detail']
    assert client.get('/api/pdf').content==original
