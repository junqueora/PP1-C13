"""Componentes reutilizados pelas abas: campo numérico, cartão e área de gráfico."""
from __future__ import annotations

import math

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (QFileDialog, QFrame, QLabel, QLineEdit, QSizePolicy,
                             QVBoxLayout, QWidget)

# O PyQt5 precisa ser importado antes do backend para o matplotlib usar a mesma biblioteca.
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from src.config import PASTA_FIGURAS

TITULO = "Projeto prático C13"
SUBTITULO = "Identificação de processos e sintonia de controladores PID"


def pintar(widget):
    """Faz o fundo definido no tema ser desenhado de fato."""
    widget.setAttribute(Qt.WA_StyledBackground, True)


def definir_aviso(rotulo: QLabel, texto: str, papel: str):
    """Mostra uma faixa de status. `papel` é ok, alerta, erro ou neutro."""
    rotulo.setText(texto)
    rotulo.setVisible(bool(texto))
    pintar(rotulo)
    rotulo.setObjectName(papel)
    rotulo.style().unpolish(rotulo)
    rotulo.style().polish(rotulo)


def cartao(margem: int = 14) -> tuple[QFrame, QVBoxLayout]:
    quadro = QFrame()
    quadro.setObjectName("cartao")
    pintar(quadro)
    layout = QVBoxLayout(quadro)
    layout.setContentsMargins(margem, margem, margem, margem)
    layout.setSpacing(10)
    return quadro, layout


class CampoNumerico(QLineEdit):
    """Campo de texto para números. Aceita vírgula ou ponto como separador decimal."""

    def __init__(self, travado: bool = False):
        super().__init__()
        self.setAlignment(Qt.AlignRight)
        self.setMinimumWidth(96)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.travar(travado)

    def valor(self) -> float | None:
        """Número digitado, ou None se o campo estiver vazio ou inválido."""
        try:
            numero = float(self.text().strip().replace(",", "."))
        except ValueError:
            return None
        return numero if math.isfinite(numero) else None

    def definir(self, numero: float | None, formato: str = ".4g"):
        if numero is None or not math.isfinite(numero):
            self.setText("–" if numero is not None else "")
        else:
            self.setText(format(numero, formato))

    def travar(self, travado: bool):
        """Campo travado fica só para leitura."""
        self.setReadOnly(travado)

    def marcar_alerta(self, ativo: bool):
        """Destaca o valor quando ele sai da faixa física do atuador."""
        self.setProperty("alerta", ativo)
        self.style().unpolish(self)
        self.style().polish(self)


class Grafico(QWidget):
    """Figura do matplotlib dentro da janela, com barra de zoom e exportação."""

    def __init__(self):
        super().__init__()
        self.figura = Figure(layout="constrained", facecolor="#ffffff")
        self.canvas = FigureCanvasQTAgg(self.figura)
        self.canvas.setMinimumSize(480, 380)
        self.canvas.setStyleSheet("background: #ffffff;")
        barra = NavigationToolbar2QT(self.canvas, self)
        barra.setIconSize(QSize(16, 16))
        barra.setStyleSheet(
            "QToolBar { background: transparent; border: none; spacing: 2px; }"
            "QToolButton { background: transparent; border-radius: 6px; padding: 3px; }"
            "QToolButton:hover { background: #eef2f6; }")
        for acao in barra.actions():
            texto = (acao.text() or "").lower()
            if any(p in texto for p in ("save", "salvar", "subplot", "customize", "configurar")):
                acao.setVisible(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.setSpacing(0)
        layout.addWidget(self.canvas, stretch=1)
        layout.addWidget(barra)

    def limpar(self, mensagem: str = ""):
        self.figura.clear()
        if mensagem:
            self.figura.text(0.5, 0.5, mensagem, ha="center", va="center", color="#52514e")
        self.canvas.draw_idle()

    def atualizar(self):
        self.canvas.draw_idle()

    def exportar(self, nome_sugerido: str) -> str | None:
        """Abre o diálogo de salvar e grava a figura. Devolve o caminho escolhido."""
        PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Exportar gráfico", str(PASTA_FIGURAS / nome_sugerido),
            "Imagem PNG (*.png);;PDF (*.pdf)")
        if not caminho:
            return None
        self.figura.savefig(caminho, dpi=200)
        return caminho
