import base64
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from solution_runner.dashboard.auth import DashboardAuth
from solution_runner.dashboard.server import make_server
from solution_runner.dashboard.store import DashboardStore


def basic(value):
    return 'Basic ' + base64.b64encode(value.encode()).decode()


@pytest.mark.parametrize('header,expected', [
    ('', False), ('Basic !!!', False), (basic('owner:wrong'), False),
    (basic('other:password'), False), (basic('owner:password'), True),
    ('Bearer secret', True), ('Bearer wrong', False),
])
def test_credentials(header, expected):
    assert DashboardAuth('password', 'secret').authorized(header) is expected


def test_empty_secrets_cannot_authenticate():
    auth = DashboardAuth()
    assert not auth.enabled
    assert not auth.authorized('Bearer ')
    assert not auth.authorized(basic('owner:'))


def test_non_loopback_binding_requires_authentication(tmp_path):
    with pytest.raises(ValueError, match='requires'):
        make_server(store=DashboardStore(tmp_path / 'db'), var_dir=tmp_path,
                    profiles={}, static_dir=tmp_path, host='0.0.0.0', port=0)


def test_server_protects_static_files_api_and_mutations(tmp_path):
    (tmp_path / 'index.html').write_text('dashboard')
    server = make_server(store=DashboardStore(tmp_path / 'db'), var_dir=tmp_path,
                         profiles={}, static_dir=tmp_path, port=0,
                         auth=DashboardAuth('password', 'secret'))
    thread = Thread(target=server.serve_forever)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        for path in ['/', '/api/groups']:
            with pytest.raises(HTTPError) as error:
                urlopen(origin + path)
            assert error.value.code == 401
            assert 'Basic' in error.value.headers['WWW-Authenticate']
        for credential in [basic('owner:password'), 'Bearer secret']:
            with urlopen(Request(origin + '/', headers={'Authorization': credential})) as response:
                assert response.read() == b'dashboard'
        with pytest.raises(HTTPError) as error:
            urlopen(Request(origin + '/api/groups', data=b'{}', headers={
                'Authorization': basic('owner:password'), 'Origin': 'https://attacker.example',
            }))
        assert error.value.code == 403
        with urlopen(Request(origin + '/api/groups', headers={'Authorization': 'Bearer secret'})) as response:
            assert response.status == 200
            assert response.headers.get('Access-Control-Allow-Origin') is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_job_history_and_logs_are_available_over_authenticated_api(tmp_path):
    import json
    import sqlite3
    from solution_runner.dashboard.job_queue import DurableJobQueue

    queue = DurableJobQueue(tmp_path / 'db')
    with sqlite3.connect(queue.database) as connection:
        connection.execute(
            "INSERT INTO dashboard_jobs(kind,payload,status,created_at) VALUES ('dry-run',?,'completed','2026-10-10')",
            (json.dumps({'args': ['123', 'all'], 'kwargs': {}}),),
        )
    queue.log_dir.mkdir()
    (queue.log_dir / 'job-1.log').write_text('diagnostic output')
    server = make_server(store=DashboardStore(queue.database), var_dir=tmp_path,
                         profiles={}, static_dir=tmp_path, port=0,
                         auth=DashboardAuth(token='secret'), job_queue=queue)
    thread = Thread(target=server.serve_forever)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        headers = {'Authorization': 'Bearer secret'}
        with urlopen(Request(origin + '/api/jobs?group=123', headers=headers)) as response:
            assert json.load(response)['jobs'][0]['id'] == 1
        with urlopen(Request(origin + '/api/jobs?group=456', headers=headers)) as response:
            assert json.load(response)['jobs'] == []
        with urlopen(Request(origin + '/api/jobs/1/log', headers=headers)) as response:
            assert json.load(response)['log'] == 'diagnostic output'
        for job_id in ['unknown', '999', str(2**64)]:
            with pytest.raises(HTTPError) as error:
                urlopen(Request(origin + f'/api/jobs/{job_id}/log', headers=headers))
            assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        queue.shutdown()
