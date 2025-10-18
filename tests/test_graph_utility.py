from types import SimpleNamespace
import hmac

from core.utilities import graph_utility as gu
from azure.core.credentials import AccessToken


def test_access_token_credential_get_token():
    cred = gu.AccessTokenCredential('my-token')
    token = cred.get_token('scope')
    assert isinstance(token, AccessToken)
    # Use compare_digest to avoid timing-attack lint warnings
    assert hmac.compare_digest(token.token, 'my-token')
    # expiry should be large (2**31 -1)
    assert token.expires_on == 2**31 - 1


def test_get_graph_client_passes_credential_and_scopes(monkeypatch):
    # Replace GraphServiceClient in the module with a dummy that captures arguments
    captured = {}

    class DummyClient:
        def __init__(self, credentials=None, scopes=None):
            captured['credentials'] = credentials
            captured['scopes'] = scopes
            self._credentials = credentials
            self._scopes = scopes

    monkeypatch.setattr(gu, 'GraphServiceClient', DummyClient)

    # Create a fake user object
    user = SimpleNamespace(id=1, username='alice')

    client = gu.get_graph_client(user, 'tk')

    # Ensure returned object is our dummy and captured credential is AccessTokenCredential
    assert isinstance(client, DummyClient)
    assert 'credentials' in captured and 'scopes' in captured
    assert isinstance(captured['credentials'], gu.AccessTokenCredential)
    assert captured['scopes'] == ['https://graph.microsoft.com/.default']
    # Check credential produces the token we passed
    token = captured['credentials'].get_token()
    assert hmac.compare_digest(token.token, 'tk')
