from __future__ import annotations

from financeiro_dr.ui.theme import APP_STYLESHEET, contrast_ratio


def test_light_content_theme_has_readable_contrast():
    assert contrast_ratio("#f6f7f9", "#111827") >= 4.5
    assert contrast_ratio("#ffffff", "#111827") >= 4.5
    assert "QStackedWidget QLabel" in APP_STYLESHEET
    assert "QStackedWidget QLineEdit" in APP_STYLESHEET
    assert "QStackedWidget QTableWidget" in APP_STYLESHEET
    assert "QStackedWidget QHeaderView::section" in APP_STYLESHEET
    assert "QStackedWidget QPushButton" in APP_STYLESHEET


def test_theme_does_not_rely_on_windows_dark_palette():
    # The main content is intentionally light, so foreground/background colors
    # must be explicitly set instead of inherited from the OS palette.
    assert "color:#111827" in APP_STYLESHEET.replace(" ", "")
    assert "background:#ffffff" in APP_STYLESHEET.replace(" ", "")
