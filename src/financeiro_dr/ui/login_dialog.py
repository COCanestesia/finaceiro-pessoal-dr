from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox, QInputDialog,
)
from financeiro_dr.security.auth_service import AuthService, AuthenticationError


def show_recovery_code(parent, code: str) -> None:
    QMessageBox.information(
        parent,
        "Guarde sua chave de recuperação",
        "Anote e guarde esta chave em local seguro, separado do computador. "
        "Ela permite recuperar a senha SEM internet. Não será exibida novamente.\n\n"
        f"CHAVE: {code}\n\n"
        "Depois de usar a chave, uma nova será gerada e a antiga não funcionará.",
    )


class LoginDialog(QDialog):
    def __init__(self, auth_service: AuthService, setup_mode: bool = False, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.setup_mode = setup_mode
        self.setWindowTitle("Financeiro Pessoal do Dr. — Primeiro acesso" if setup_mode else "Financeiro Pessoal do Dr. — Login")
        self.setMinimumWidth(390)
        title = QLabel("Defina a senha local" if setup_mode else "Acesso ao financeiro pessoal")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Senha")
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Confirme a senha")
        self.confirm_input.setVisible(setup_mode)
        form = QFormLayout()
        form.addRow("Senha:", self.password_input)
        if setup_mode:
            form.addRow("Confirmar:", self.confirm_input)
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.login_button = QPushButton("Salvar senha" if setup_mode else "Entrar")
        self.login_button.clicked.connect(self._submit)
        self.password_input.returnPressed.connect(self._submit)
        if setup_mode:
            self.confirm_input.returnPressed.connect(self._submit)
        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addWidget(self.login_button)
        if not setup_mode:
            forgot_button = QPushButton("Esqueci minha senha")
            forgot_button.clicked.connect(self._recover)
            layout.addWidget(forgot_button)
            self.forgot_button = forgot_button

    def _submit(self) -> None:
        password = self.password_input.text()
        self.error_label.clear()
        if self.setup_mode:
            if password != self.confirm_input.text():
                self.error_label.setText("As senhas não conferem.")
                return
            try:
                code = self.auth_service.initialize_password(password)
            except (ValueError, RuntimeError) as exc:
                self.error_label.setText(str(exc))
                return
            show_recovery_code(self, code)
            self.accept()
            return
        if self.auth_service.authenticate(password):
            # Existing installations predate recovery keys. Create one with the valid password.
            row = self.auth_service.connection.execute(
                "SELECT 1 FROM password_recovery WHERE id = 1"
            ).fetchone()
            if row is None:
                show_recovery_code(self, self.auth_service.regenerate_recovery_code(password))
            self.accept()
        else:
            self.error_label.setText("Senha incorreta.")

    def _recover(self) -> None:
        row = self.auth_service.connection.execute(
            "SELECT 1 FROM password_recovery WHERE id = 1"
        ).fetchone()
        if row is None:
            QMessageBox.warning(
                self, "Recuperação indisponível",
                "Este acesso ainda não possui chave de recuperação. "
                "Entre com a senha atual para emitir uma chave. "
                "Se perdeu ambos, será necessário atendimento técnico com verificação de titularidade.",
            )
            return
        code, ok = QInputDialog.getText(
            self, "Recuperação de senha", "Digite a chave de recuperação:",
            QLineEdit.Normal
        )
        if not ok or not code.strip():
            return
        new_password, ok = QInputDialog.getText(
            self, "Nova senha", "Nova senha (mínimo 8 caracteres):",
            QLineEdit.Password,
        )
        if not ok:
            return
        confirm, ok = QInputDialog.getText(
            self, "Confirmar senha", "Repita a nova senha:",
            QLineEdit.Password,
        )
        if not ok:
            return
        if new_password != confirm:
            self.error_label.setText("As senhas não conferem.")
            return
        try:
            new_code = self.auth_service.reset_password(code, new_password)
        except (AuthenticationError, ValueError) as exc:
            self.error_label.setText(str(exc))
            return
        show_recovery_code(self, new_code)
        self.password_input.clear()
        self.error_label.setText("Senha redefinida. Entre com a nova senha.")
