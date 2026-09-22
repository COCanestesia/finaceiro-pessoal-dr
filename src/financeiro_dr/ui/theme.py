from __future__ import annotations


def _hex_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    if len(value) != 6:
        raise ValueError("Cor hexadecimal inválida.")
    return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))


def _channel_luminance(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def contrast_ratio(background: str, foreground: str) -> float:
    bg = _hex_rgb(background)
    fg = _hex_rgb(foreground)
    bg_l = 0.2126 * _channel_luminance(bg[0]) + 0.7152 * _channel_luminance(bg[1]) + 0.0722 * _channel_luminance(bg[2])
    fg_l = 0.2126 * _channel_luminance(fg[0]) + 0.7152 * _channel_luminance(fg[1]) + 0.0722 * _channel_luminance(fg[2])
    lighter = max(bg_l, fg_l)
    darker = min(bg_l, fg_l)
    return (lighter + 0.05) / (darker + 0.05)


APP_STYLESHEET = """
QFrame#sidebar {
    background: #18202a;
}
QLabel#brand {
    color: white;
    font-size: 20px;
    font-weight: 700;
}
QFrame#sidebar QPushButton {
    min-height: 30px;
    text-align: left;
    padding: 8px 10px;
    color: #eef2f6;
    background: transparent;
    border: 0;
    border-radius: 6px;
}
QFrame#sidebar QPushButton:hover {
    background: #2b3948;
}
QFrame#sidebar QPushButton:checked {
    background: #35475a;
    font-weight: 600;
}

QStackedWidget {
    background: #f6f7f9;
    color: #111827;
}
QStackedWidget QWidget {
    background: #f6f7f9;
    color: #111827;
}
QStackedWidget QLabel,
QStackedWidget QCheckBox,
QStackedWidget QRadioButton,
QStackedWidget QGroupBox {
    color: #111827;
    background: transparent;
}
QStackedWidget QLineEdit,
QStackedWidget QComboBox,
QStackedWidget QDateEdit,
QStackedWidget QSpinBox,
QStackedWidget QDoubleSpinBox,
QStackedWidget QTextEdit,
QStackedWidget QPlainTextEdit {
    background: #ffffff;
    color: #111827;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 8px;
    min-height: 24px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QStackedWidget QLineEdit:focus,
QStackedWidget QComboBox:focus,
QStackedWidget QDateEdit:focus,
QStackedWidget QSpinBox:focus,
QStackedWidget QDoubleSpinBox:focus {
    border: 1px solid #2563eb;
}
QStackedWidget QComboBox QAbstractItemView {
    background: #ffffff;
    color: #111827;
    selection-background-color: #dbeafe;
    selection-color: #111827;
}
QStackedWidget QPushButton {
    background: #2563eb;
    color: #ffffff;
    border: 1px solid #1d4ed8;
    border-radius: 6px;
    padding: 7px 12px;
    min-height: 24px;
    font-weight: 600;
}
QStackedWidget QPushButton:hover {
    background: #1d4ed8;
}
QStackedWidget QPushButton:pressed {
    background: #1e40af;
}
QStackedWidget QPushButton:disabled {
    background: #e5e7eb;
    color: #6b7280;
    border-color: #d1d5db;
}
QStackedWidget QTableWidget,
QStackedWidget QTableView,
QStackedWidget QTreeWidget,
QStackedWidget QListWidget {
    background: #ffffff;
    color: #111827;
    gridline-color: #d1d5db;
    alternate-background-color: #f8fafc;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    selection-background-color: #dbeafe;
    selection-color: #111827;
}
QStackedWidget QTableWidget::item,
QStackedWidget QTableView::item,
QStackedWidget QTreeWidget::item,
QStackedWidget QListWidget::item {
    color: #111827;
    background: #ffffff;
    padding: 5px;
}
QStackedWidget QTableWidget::item:selected,
QStackedWidget QTableView::item:selected,
QStackedWidget QTreeWidget::item:selected,
QStackedWidget QListWidget::item:selected {
    background: #dbeafe;
    color: #111827;
}
QStackedWidget QHeaderView::section {
    background: #e5e7eb;
    color: #111827;
    border: 0;
    border-right: 1px solid #cbd5e1;
    border-bottom: 1px solid #cbd5e1;
    padding: 7px 8px;
    font-weight: 600;
}
QStackedWidget QAbstractScrollArea QWidget:viewport {
    background: #ffffff;
    color: #111827;
}
QStackedWidget QScrollBar:vertical {
    background: #eef2f7;
    width: 12px;
    margin: 0;
}
QStackedWidget QScrollBar::handle:vertical {
    background: #94a3b8;
    border-radius: 6px;
    min-height: 28px;
}
QStackedWidget QScrollBar:horizontal {
    background: #eef2f7;
    height: 12px;
    margin: 0;
}
QStackedWidget QScrollBar::handle:horizontal {
    background: #94a3b8;
    border-radius: 6px;
    min-width: 28px;
}
"""
