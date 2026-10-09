import pytest
pytest.importorskip("PySide6")
from financeiro_dr.ui.pages.remote_consultation_page import RemoteConsultationPage


class FakeRemoteClient:
    def __init__(self, url):
        self.url = url
    def login(self, username, password):
        return {"role": "consulta" if username == "reader" else "financeiro"}
    def entries(self):
        return []


def test_remote_form_obeys_profile(qtbot, monkeypatch):
    import financeiro_dr.ui.pages.remote_consultation_page as module
    monkeypatch.setattr(module, "RemoteReadClient", FakeRemoteClient)
    page = RemoteConsultationPage()
    qtbot.addWidget(page)
    page.address.setText("https://example.com")
    page.password.setText("example")
    page.username.setText("reader")
    page.connect_remote()
    assert not page.save_button.isEnabled()
    page.username.setText("financeiro")
    page.connect_remote()
    assert page.save_button.isEnabled()
