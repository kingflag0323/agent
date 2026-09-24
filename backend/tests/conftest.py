import os
import tempfile
from pathlib import Path
os.environ['SXF_DATA_DIR']=tempfile.mkdtemp(prefix='sentinel-tests-')
os.environ['SXF_REPO_ROOTS']=str(Path(__file__).resolve().parents[2]/'demo')+os.pathsep+os.environ['SXF_DATA_DIR']
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import settings

@pytest.fixture()
def client():
    with TestClient(app,headers={'X-Sentinel-Client':'console'}) as c:
        settings.save({'xdr':{'mode':'demo'},'llm':{'mode':'mock'},'agent':{'max_steps':20,'reviewer':True,'timeout':120}})
        yield c
