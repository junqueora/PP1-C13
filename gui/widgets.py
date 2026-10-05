"""Componentes reutilizados pelas abas: cabeçalho, campo numérico e área de gráfico."""
from __future__ import annotations

import math

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QFileDialog, QLabel, QLineEdit, QVBoxLayout, QWidget

# O PyQt5 precisa ser importado antes do backend para o matplotlib usar a mesma biblioteca.
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from src.config import PASTA_FIGURAS

TITULO = "Projeto Prático C13 – Sistemas Embarcados"
SUBTITULO = "Identificação de Processos & Sintonia de Controladores PID"


def cabecalho() -> QWidget:
    """Título e subtítulo mostrados no topo de cada aba."""
    caixa = QWidget()
    layout = QVBoxLayout(caixa)
    layout.setContentsMargins(0, 4, 0, 8)
    titulo = QLabel(f"<b>{TITULO}</b>")
    titulo.setAlignment(Qt.AlignCenter)
    fonte = titulo.font()
    fonte.setPointSize(fonte.pointSize() + 3)
    titulo.setFont(fonte)
    subtitulo = QLabel(SUBTITULO)
    subtitulo.setAlignment(Qt.AlignCenter)
    layout.addWidget(titulo)
    layout.addWidget(subtitulo)
    return caixa


class CampoNumerico(QLineEdit):
    """Campo de texto para números. Aceita vírgula ou ponto como separador decimal."""

    def __init__(self, travado: bool = False, largura: int = 100):
        super().__init__()
        self.setAlignment(Qt.AlignRight)
        self.setFixedWidth(largura)
        self._base_editavel = self.palette().color(QPalette.Base)
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
        """Campo travado fica só para leitura, com o fundo da cor da janela."""
        self.setReadOnly(travado)
        paleta = self.palette()
        cor = paleta.color(QPalette.Window) if travado else self._base_editavel
        paleta.setColor(QPalette.Base, cor)
        self.setPalette(paleta)


class Grafico(QWidget):
    """Figura do matplotlib dentro da janela, com barra de zoom e exportação."""

    def __init__(self):
        super().__init__()
        self.figura = Figure(layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figura)
        self.canvas.setMinimumSize(520, 420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas, stretch=1)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))

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
