import importlib


def test_phase1_ui_modules_are_available():
    for module in (
        "financeiro_dr.ui.login_dialog",
        "financeiro_dr.ui.app_window",
        "financeiro_dr.ui.pages.entries_page",
        "financeiro_dr.ui.pages.payables_page",
        "financeiro_dr.ui.pages.receivables_page",
        "financeiro_dr.ui.pages.agenda_page",
    ):
        importlib.import_module(module)
