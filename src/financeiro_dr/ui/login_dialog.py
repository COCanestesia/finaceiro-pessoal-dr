from __future__ import annotations

from PySide6.QtWidgets import QDialog,QFormLayout,QLabel,QLineEdit,QPushButton,QVBoxLayout
from financeiro_dr.security.auth_service import AuthService

class LoginDialog(QDialog):
    def __init__(self, auth_service: AuthService, setup_mode: bool=False, parent=None):
        super().__init__(parent); self.auth_service=auth_service; self.setup_mode=setup_mode
        self.setWindowTitle("Financeiro Pessoal do Dr. — Primeiro acesso" if setup_mode else "Financeiro Pessoal do Dr. — Login"); self.setMinimumWidth(390)
        title=QLabel("Defina a senha local" if setup_mode else "Acesso ao financeiro pessoal")
        self.password_input=QLineEdit(); self.password_input.setEchoMode(QLineEdit.Password); self.password_input.setPlaceholderText("Senha")
        self.confirm_input=QLineEdit(); self.confirm_input.setEchoMode(QLineEdit.Password); self.confirm_input.setPlaceholderText("Confirme a senha"); self.confirm_input.setVisible(setup_mode)
        form=QFormLayout(); form.addRow("Senha:",self.password_input)
        if setup_mode: form.addRow("Confirmar:",self.confirm_input)
        self.error_label=QLabel(""); self.error_label.setWordWrap(True)
        self.login_button=QPushButton("Salvar senha" if setup_mode else "Entrar"); self.login_button.clicked.connect(self._submit); self.password_input.returnPressed.connect(self._submit)
        if setup_mode: self.confirm_input.returnPressed.connect(self._submit)
        layout=QVBoxLayout(self); layout.addWidget(title); layout.addLayout(form); layout.addWidget(self.error_label); layout.addWidget(self.login_button)
    def _submit(self)->None:
        password=self.password_input.text(); self.error_label.clear()
        if self.setup_mode:
            if password != self.confirm_input.text(): self.error_label.setText("As senhas não conferem."); return
            try: self.auth_service.initialize_password(password)
            except (ValueError,RuntimeError) as exc: self.error_label.setText(str(exc)); return
            self.accept(); return
        if self.auth_service.authenticate(password): self.accept()
        else: self.error_label.setText("Senha incorreta.")
