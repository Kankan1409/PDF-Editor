from pathlib import Path
import re
from fastapi.testclient import TestClient
from app.main import app

def test_built_frontend_and_api_share_origin():
    dist=Path(__file__).resolve().parents[2]/'frontend'/'dist'
    if not dist.exists():
        import pytest
        pytest.skip('Run npm run build before integration test')
    with TestClient(app,headers={'X-Smart-PDF':'1'}) as client:
        html=client.get('/');assert html.status_code==200
        assert 'Smart PDF Editor' in html.text
        assets=re.findall(r'(?:src|href)="(/assets/[^"]+)"',html.text)
        assert assets
        for asset in assets: assert client.get(asset).status_code==200
        sample=client.get('/samples/demo.pdf');assert sample.status_code==200
        state=client.post('/api/upload',files={'file':('sample.pdf',sample.content)}).json()
        assert state['page_count']==2
        result=client.post('/api/apply',json={'kind':'replace','revision':0,'query':'ตอนรับ','text':'ต้อนรับ','all':True})
        assert result.status_code==200
        assert client.get('/api/pdf').content.startswith(b'%PDF-')
