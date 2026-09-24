def test_workbench_private_session(monkeypatch,client):
    monkeypatch.setenv('SXF_DESKTOP_TOKEN','unit-test-session-secret')
    assert client.get('/api/health').status_code==403
    assert client.get('/api/settings',headers={'X-Sentinel-Token':'incorrect'}).status_code==403
    assert client.get('/api/health',headers={'X-Sentinel-Token':'unit-test-session-secret'}).status_code==200
    assert client.get('/api/settings',headers={'X-Sentinel-Token':'unit-test-session-secret'}).status_code==200
