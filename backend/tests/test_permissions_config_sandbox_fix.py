"""Production permissions, canonical settings and restricted code regressions."""
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.models.system_config import SystemConfig
from app.services.function_runtime.sandbox import UnifiedSandbox
from app.services.skill_sandbox import CodeValidationError, execute_in_sandbox
from test_core_review import auth, fixture  # noqa: F401


def grant(client, permissions):
    response = client.put('/api/v1/auth/roles/editor/permissions', headers=auth('admin'),
                          json={'permissions': permissions})
    assert response.status_code == 200, response.text


def test_reads_follow_module_permissions_and_administration_can_be_delegated(fixture):
    client, _ = fixture
    grant(client, ['entity:read'])
    assert client.get('/api/v1/entities', headers=auth('editor')).status_code == 200
    assert client.get('/api/v1/functions', headers=auth('editor')).status_code == 403
    assert client.get('/api/v1/agents', headers=auth('editor')).status_code == 403
    grant(client, ['rule:read'])
    assert client.get('/api/v1/functions', headers=auth('editor')).status_code == 200
    assert client.get('/api/v1/entities', headers=auth('editor')).status_code == 403
    grant(client, ['strategy:read'])
    assert client.get('/api/v1/agents', headers=auth('editor')).status_code == 200
    assert client.get('/api/v1/functions', headers=auth('editor')).status_code == 403
    grant(client, ['admin:users'])
    assert client.get('/api/v1/auth/users', headers=auth('editor')).status_code == 200
    assert client.get('/api/v1/system-config', headers=auth('editor')).status_code == 200
    grant(client, [])
    assert client.get('/api/v1/auth/users', headers=auth('editor')).status_code == 403


def test_model_management_and_mcp_read_permissions_follow_persisted_matrix(fixture):
    client, _ = fixture
    grant(client, ['rule:read', 'rule:write'])
    model = client.post('/api/v1/models', headers=auth('editor'), json={
        'name': 'Scoped model', 'provider': 'fixture', 'model_name': 'fixture'})
    assert model.status_code == 201, model.text
    grant(client, ['rule:read'])
    assert client.put('/api/v1/models/' + model.json()['id'], headers=auth('editor'), json={'name': 'Blocked'}).status_code == 403
    def mcp(name):
        return client.post('/api/v1/mcp', headers=auth('editor'), json={
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': name, 'arguments': {'ontology_name': 'a', 'user_id': 'editor'}}}).json()
    assert mcp('ontology_query_instances')['error']['code'] == -32003
    grant(client, ['entity:read'])
    assert mcp('ontology_list_capabilities')['error']['code'] == -32003


def test_management_changes_cannot_lock_out_the_last_admin(fixture):
    client, _ = fixture
    assert client.put('/api/v1/auth/roles/admin/permissions', headers=auth('admin'), json={'permissions': []}).status_code == 409
    assert client.put('/api/v1/auth/users/admin/status', headers=auth('admin')).status_code == 409
    assert client.put('/api/v1/auth/users/admin', headers=auth('admin'), json={'role': 'viewer'}).status_code == 409
    grant(client, ['admin:users'])
    assert client.put('/api/v1/auth/users/admin', headers=auth('admin'), json={'role': 'viewer'}).status_code == 200
    assert client.get('/api/v1/auth/users', headers=auth('editor')).status_code == 200
    assert client.put('/api/v1/auth/roles/editor/permissions', headers=auth('editor'), json={'permissions': []}).status_code == 409


@pytest.mark.parametrize('spelling', ['5.0', '5e0', '005'])
def test_integer_settings_save_canonically_and_login_refresh_remain_usable(fixture, spelling):
    client, db = fixture
    response = client.put('/api/v1/system-config', headers=auth('admin'), json={
        'group': 'auth', 'items': [{'key': 'session_timeout', 'value': spelling}]})
    assert response.status_code == 200, response.text
    assert db.query(SystemConfig).filter_by(key='session_timeout').one().value == '5'
    login = client.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'Fixture123!'})
    assert login.status_code == 200, login.text
    assert client.post('/api/v1/auth/refresh', json={'refresh_token': login.json()['refresh_token']}).status_code == 200


def test_legacy_decimal_integer_rows_are_usable_and_config_validation_is_atomic(fixture):
    client, db = fixture
    row = SystemConfig(group='auth', key='auth.session_timeout', value='5.0')
    db.add(row)
    db.commit()
    assert client.post('/api/v1/auth/login', json={'username': 'admin', 'password': 'Fixture123!'}).status_code == 200
    response = client.put('/api/v1/system-config', headers=auth('admin'), json={
        'group': 'auth', 'items': [{'key': 'auth.session_timeout', 'value': '10'},
                                 {'key': 'password_min_length', 'value': '8.5'}]})
    assert response.status_code == 422
    db.expire_all()
    assert row.value == '5.0'
    from app.services.data_plane.storage_policy import storage_policy
    db.add(SystemConfig(group='storage', key='max_upload_mb', value='5.0'))
    db.commit()
    assert storage_policy(db)['max_bytes'] == 5 * 1024 * 1024


def test_unsupported_sso_is_rejected_and_legacy_configuration_hides_login_entry(fixture):
    client, db = fixture
    for provider in ('saml', 'ldap'):
        response = client.put('/api/v1/system-config', headers=auth('admin'), json={
            'group': 'auth', 'items': [{'key': 'sso_enabled', 'value': 'true'},
                                     {'key': 'sso_provider', 'value': provider}]})
        assert response.status_code == 422
    db.add_all([SystemConfig(group='auth', key='sso_enabled', value='true'),
                SystemConfig(group='auth', key='sso_provider', value='saml')])
    db.commit()
    assert client.get('/api/v1/auth/sso/config').json()['enabled'] is False


def test_notification_reads_saved_legacy_settings_and_integer_port(fixture, monkeypatch):
    import asyncio
    import smtplib
    from app.services.action_executors.notification import NotificationExecutor
    client, db = fixture
    db.add_all([SystemConfig(group='notification', key='smtp_host', value='old.invalid'),
                SystemConfig(group='notification', key='smtp_port', value='2525.0'),
                SystemConfig(group='notification', key='smtp_username', value='sender@example.invalid'),
                SystemConfig(group='notification', key='smtp_encryption', value='none')])
    db.commit()
    response = client.put('/api/v1/system-config', headers=auth('admin'), json={
        'group': 'notification', 'items': [{'key': 'notification.smtp_host', 'value': 'saved.example.invalid'}]})
    assert response.status_code == 200
    observed = {}
    class SMTP:
        def __init__(self, host, port, timeout):
            observed.update(host=host, port=port)
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def send_message(self, message):
            observed.update(sender=message['From'], recipient=message['To'])
            return {}
    monkeypatch.setattr(smtplib, 'SMTP', SMTP)
    result = asyncio.run(NotificationExecutor(db).execute({'channel': 'email',
        'recipient': 'recipient@example.invalid', 'message_template': 'Config compatibility'}, {}))
    assert result.success, result.message
    assert observed == {'host': 'saved.example.invalid', 'port': 2525,
                        'sender': 'sender@example.invalid', 'recipient': 'recipient@example.invalid'}


def test_standard_modules_expose_only_data_apis_and_cannot_replace_host_modules():
    sandbox = UnifiedSandbox()
    # Public back references are deliberately absent from module facades.
    with pytest.raises(AttributeError):
        sandbox.execute_expression('dataclasses.sys', {'params': {}})
    assert sandbox.execute('import json\ndef f(params):\n    json.extra = 7\n    return json.loads(json.dumps(params))', 'f', {'params': {'x': 2}}) == {'x': 2}
    import json
    assert not hasattr(json, 'extra')
    assert not sandbox.validate('from dataclasses import sys\ndef f(params): return 0').valid
    assert not sandbox.validate('import json.decoder\ndef f(params): return 0').valid
    assert not sandbox.validate('def f(params): return params._private').valid
    assert not sandbox.validate('def f(params): return "{0}".format(params)').valid
    assert not sandbox.validate('def f(params): return __builtins__').valid
    assert sandbox.execute('from dataclasses import dataclass\n@dataclass\nclass Item:\n    value: int\ndef f(params): return Item(4).value', 'f', {'params': {}}) == 4
    assert sandbox.execute('from dataclasses import dataclass\n@dataclass\nclass Item:\n    value: "int"\ndef f(params): return Item(4).value', 'f', {'params': {}}) == 4
    assert sandbox.execute_expression("datetime.datetime.strptime(params['date'], '%Y-%m-%d').strftime('%Y/%m/%d')", {'params': {'date': '2026-10-12'}}) == '2026/10/12'
    assert not sandbox.validate('import time\ndef f(params): return 0').valid


def test_skills_share_import_controls_and_keep_keyword_arguments():
    assert execute_in_sandbox('import math\ndef f(value): return math.sqrt(value)', 'f', {'value': 16}) == 4
    with pytest.raises(CodeValidationError):
        execute_in_sandbox('from dataclasses import sys\ndef f(): return 0', 'f', {})
    with pytest.raises(CodeValidationError):
        execute_in_sandbox('def f(): return 0', 'f', {}, {'__builtins__': {}})


def test_decimal_precision_is_local_to_one_execution():
    from decimal import getcontext
    before = getcontext().prec
    sandbox = UnifiedSandbox()
    assert sandbox.execute('import decimal\ndecimal.getcontext().prec = 3\ndef f(params):\n    return str(decimal.Decimal(1) / decimal.Decimal(7))', 'f', {'params': {}}) == '0.143'
    assert getcontext().prec == before
    assert sandbox.execute_expression('decimal.getcontext().prec', {'params': {}}) == before
    with pytest.raises(RuntimeError):
        sandbox.execute('import decimal\ndef f(params):\n    decimal.getcontext().prec = 1\n    raise RuntimeError("business failure")', 'f', {'params': {}})
    assert getcontext().prec == before


def test_worker_deadline_cannot_be_caught_by_business_exception_handler():
    sandbox = UnifiedSandbox()
    code = 'def f(params):\n    try:\n        while True: pass\n    except Exception:\n        return "ignored"'
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(TimeoutError):
            pool.submit(sandbox.execute, code, 'f', {'params': {}}, 0.05).result(timeout=2)
    assert not sandbox.validate('def f(params):\n    try: return 1\n    except: return 0').valid


@pytest.mark.parametrize('dialect', ['sqlite', 'mysql', 'postgresql', 'oracle', 'sqlserver'])
def test_grouped_predicates_keep_named_parameters_for_every_connector(dialect):
    from app.services.mcp_tools.data_query import _binding_predicate
    predicate = _binding_predicate('temp >= ? OR temp = ?', [20, 30], dialect)
    assert ':p0' in predicate and ':p1' in predicate
    assert '%(p0)s' not in predicate
    assert predicate.startswith('(') and predicate.endswith(')')
