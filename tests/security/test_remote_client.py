import pytest
from financeiro_dr.network.remote_client import RemoteReadClient


def test_remote_client_requires_secure_transport():
    with pytest.raises(ValueError):
        RemoteReadClient("http://example.com:8765")
    with pytest.raises(ValueError):
        RemoteReadClient("https://user:secret@example.com")
    assert RemoteReadClient("https://servidor-privado").base_url == "https://servidor-privado"
    assert RemoteReadClient("http://127.0.0.1:8765").base_url == "http://127.0.0.1:8765"


def test_remote_client_rejects_unauthenticated_query():
    with pytest.raises(PermissionError):
        RemoteReadClient("https://servidor-privado").entries()
