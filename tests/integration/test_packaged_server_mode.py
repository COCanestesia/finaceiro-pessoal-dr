from financeiro_dr.main import main
import pytest


def test_packaged_server_mode_starts_without_gui(monkeypatch, tmp_path):
    import financeiro_dr.network.read_api as api
    import financeiro_dr.main as app
    class FakeServer:
        def __init__(self):
            self.started = False
            self.closed = False
        def serve_forever(self):
            self.started = True
        def server_close(self):
            self.closed = True
    fake = FakeServer()
    monkeypatch.setattr(api, "create_server", lambda path: fake)
    assert main(["--server"]) == 0
    assert fake.started and fake.closed


def test_packaged_server_rejects_other_args():
    with pytest.raises(ValueError):
        main(["--server", "--smoke-test"])
