from test_editor import client, upload, contents


def test_direct_edit_export_undo_redo(client):
    state = upload(client)
    original = client.get('/api/pdf').content
    line = next(l for l in state['pages'][0]['lines'] if 'welcom' in l['text'])
    op = dict(kind='edit', page=0, line_id=line['id'], text='A warm welcome to Northstar', revision=0)
    result = client.post('/api/apply', json=op)
    assert result.status_code == 200, result.text
    assert result.json()['can_undo']
    assert 'A warm welcome to Northstar' in contents(client)
    edited = client.get('/api/pdf').content
    assert client.get('/api/pdf?version=preview').status_code == 404
    assert client.post('/api/apply', json=op).status_code == 409
    assert client.get('/api/pdf').content == edited
    assert client.post('/api/history/undo').status_code == 200
    assert client.get('/api/pdf').content == original
    assert client.post('/api/history/redo').status_code == 200
    assert client.get('/api/pdf').content == edited


def test_direct_thai_replace_and_rejected_edit_is_atomic(client):
    upload(client)
    result = client.post('/api/apply', json=dict(kind='replace', query='ตอนรับ', text='ต้อนรับ', all=True, revision=0))
    assert result.status_code == 200, result.text
    assert 'ต้อนรับ' in contents(client)
    before = client.get('/api/pdf').content
    result = client.post('/api/apply', json=dict(kind='edit', line_id='missing-line', text='new', revision=1))
    assert result.status_code == 422
    assert client.get('/api/pdf').content == before
    assert client.get('/api/document').json()['revision'] == 1
