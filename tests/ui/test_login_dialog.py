import pytest
pytest.importorskip("PySide6")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.security.auth_service import AuthService
from financeiro_dr.ui.login_dialog import LoginDialog

@pytest.fixture
def auth_service(tmp_path):
    con=Database(tmp_path/"login.db").connect(); MigrationRunner().apply_all(con); service=AuthService(con); service.initialize_password("Senha Forte 123!")
    try: yield service
    finally: con.close()

def test_login_rejects_wrong_password(qtbot,auth_service):
    dialog=LoginDialog(auth_service); qtbot.addWidget(dialog); dialog.password_input.setText("errada"); qtbot.mouseClick(dialog.login_button,Qt.LeftButton); assert dialog.result()==QDialog.Rejected; assert "Senha incorreta" in dialog.error_label.text()

def test_login_accepts_correct_password(qtbot,auth_service):
    dialog=LoginDialog(auth_service); qtbot.addWidget(dialog); dialog.password_input.setText("Senha Forte 123!"); qtbot.mouseClick(dialog.login_button,Qt.LeftButton); assert dialog.result()==QDialog.Accepted

def test_first_use_setup_saves_password(qtbot,tmp_path):
    con=Database(tmp_path/"setup.db").connect(); MigrationRunner().apply_all(con); auth=AuthService(con); dialog=LoginDialog(auth,setup_mode=True); qtbot.addWidget(dialog)
    try:
        dialog.password_input.setText("Primeira Senha 123!"); dialog.confirm_input.setText("Primeira Senha 123!"); qtbot.mouseClick(dialog.login_button,Qt.LeftButton); assert dialog.result()==QDialog.Accepted; assert auth.authenticate("Primeira Senha 123!") is True
    finally: con.close()
