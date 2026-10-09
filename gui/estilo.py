"""Aparência da interface: tema claro, cartões e avisos."""
from __future__ import annotations

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication

ESTILO = """
QWidget {
    color: #1c2430;
    font-size: 13px;
}
QWidget#pagina {
    background: #f3f5f8;
}
QWidget#barra {
    background: #ffffff;
    border-bottom: 1px solid #e6e9ee;
}
QLabel#tituloApp {
    font-size: 16px;
    font-weight: 600;
    color: #1c2430;
}
QLabel#subtituloApp {
    font-size: 12px;
    color: #5c6b7a;
}
QLabel#tituloInicio {
    font-size: 22px;
    font-weight: 600;
    color: #1c2430;
}
QLabel#subtituloInicio {
    font-size: 15px;
    color: #3d4c5c;
}
QLabel#numeroPasso {
    background: #e8f1ff;
    color: #1f6feb;
    border-radius: 12px;
    font-weight: 600;
}
QScrollArea, QScrollArea > QWidget > QWidget {
    background: #f3f5f8;
}
QLabel#secao {
    font-size: 12px;
    font-weight: 600;
    color: #1c2430;
    letter-spacing: 0.2px;
}
QLabel#campo {
    color: #5c6b7a;
}
QLabel#modelo {
    background: #ffffff;
    color: #1c2430;
    border: 1px solid #e6e9ee;
    border-radius: 8px;
    padding: 8px 12px;
}
QLabel#nota {
    color: #5c6b7a;
    font-size: 12px;
}
QLabel#ok, QLabel#alerta, QLabel#erro, QLabel#neutro {
    border-radius: 8px;
    padding: 8px 12px;
}
QLabel#ok { background: #e7f6ee; color: #146c43; }
QLabel#alerta { background: #fff6e5; color: #8a5a00; }
QLabel#erro { background: #fdecec; color: #9f1d1d; }
QLabel#neutro { background: #eef2f6; color: #3d4c5c; }

QFrame#cartao {
    background: #ffffff;
    border: 1px solid #e6e9ee;
    border-radius: 12px;
}
QFrame#segmento {
    background: #e7ebf0;
    border-radius: 9px;
}
QFrame#segmento QRadioButton {
    background: transparent;
    border-radius: 7px;
    padding: 5px 14px;
    spacing: 0px;
    color: #3d4c5c;
}
QFrame#segmento QRadioButton:checked {
    background: #ffffff;
    color: #1c2430;
}
QFrame#segmento QRadioButton::indicator {
    width: 0px;
    height: 0px;
    border: none;
    image: none;
}

QTabWidget::pane {
    background: #f3f5f8;
    border: none;
}
QTabBar::tab {
    background: transparent;
    color: #5c6b7a;
    min-width: 118px;
    padding: 10px 18px 8px 18px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #1c2430;
    border-bottom: 2px solid #1f6feb;
}
QTabBar::tab:disabled {
    color: #b4bdc8;
}

QLineEdit {
    background: #ffffff;
    border: 1px solid #d5dbe3;
    border-radius: 8px;
    padding: 6px 8px;
    min-height: 18px;
    selection-background-color: #d6e6ff;
}
QLineEdit:hover { border-color: #b7c3d1; }
QLineEdit:focus { border: 1px solid #1f6feb; }
QLineEdit:read-only {
    background: #f6f8fa;
    color: #1c2430;
}
QLineEdit:disabled {
    background: #f3f5f8;
    color: #98a2b0;
}
QLineEdit[alerta="true"] {
    background: #fff6e5;
    color: #8a5a00;
    border-color: #f0d7a2;
}

QComboBox {
    background: #ffffff;
    border: 1px solid #d5dbe3;
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 18px;
}
QComboBox:hover { border-color: #b7c3d1; }
QComboBox:focus { border: 1px solid #1f6feb; }
QComboBox:disabled {
    background: #f3f5f8;
    color: #98a2b0;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #e6e9ee;
    selection-background-color: #e8f1ff;
    selection-color: #1c2430;
    outline: none;
    padding: 4px;
}

QPushButton {
    background: #ffffff;
    border: 1px solid #d5dbe3;
    border-radius: 8px;
    padding: 7px 14px;
    min-height: 18px;
}
QPushButton:hover { background: #f4f7fb; }
QPushButton:pressed { background: #e8edf3; }
QPushButton:disabled {
    background: #f3f5f8;
    color: #98a2b0;
}
QPushButton#primario {
    background: #1f6feb;
    color: #ffffff;
    border: none;
    font-weight: 600;
}
QPushButton#primario:hover { background: #1a62d6; }
QPushButton#primario:pressed { background: #164fb0; }
QPushButton#primario:disabled { background: #c5d8f6; color: #ffffff; }

QToolButton#icone {
    background: transparent;
    border: none;
    color: #8b98a8;
    border-radius: 6px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    font-size: 14px;
}
QToolButton#icone:hover { background: #eef2f6; color: #1c2430; }
QToolButton#icone:disabled { color: #d5dbe3; }

QCheckBox { spacing: 6px; color: #5c6b7a; }
QToolBar { background: transparent; border: none; spacing: 2px; }
QToolButton { background: transparent; border-radius: 6px; padding: 3px; }
QToolButton:hover { background: #eef2f6; }
"""


def aplicar(app: QApplication):
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(ESTILO)
