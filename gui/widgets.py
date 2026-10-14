"""Componentes reutilizados pelas abas: campo numérico, cartão e área de gráfico."""
from __future__ import annotations

import math

import numpy as np
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtWidgets import (QFileDialog, QFrame, QLabel, QLineEdit, QSizePolicy,
                             QVBoxLayout, QWidget)

# O PyQt5 precisa ser importado antes do backend para o matplotlib usar a mesma biblioteca.
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from src.config import PASTA_FIGURAS, SUBTITULO, TITULO  # noqa: F401 (reexportados para as abas)

# Rótulos no hover: distância do mouse ao ponto e animação de aparecer/sumir.
RAIO_HOVER_PX = 15
PASSOS_FADE = 5
INTERVALO_FADE_MS = 25       # 5 passos de 25 ms: o rótulo aparece em ~0,12 s


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

        # Rótulos que só aparecem com o mouse sobre o ponto: {anotação: [(x, y), ...]}.
        self.destaques = {}
        self._opacidade = {}     # opacidade atual de cada rótulo (0 a 1)
        self._alvo = {}          # opacidade para onde cada rótulo está indo
        self._fade = QTimer(self)
        self._fade.setInterval(INTERVALO_FADE_MS)
        self._fade.timeout.connect(self._passo_fade)
        self.canvas.mpl_connect("motion_notify_event", self._ao_mover)
        self.canvas.mpl_connect("figure_leave_event", lambda _: self._mirar(set()))

    def limpar(self, mensagem: str = ""):
        self.definir_destaques([])
        self.figura.clear()
        if mensagem:
            self.figura.text(0.5, 0.5, mensagem, ha="center", va="center", color="#52514e")
        self.canvas.draw_idle()

    def atualizar(self):
        self.canvas.draw_idle()

    # ------------------------------------------------------------------ #
    # Rótulos no hover
    # ------------------------------------------------------------------ #
    def definir_destaques(self, destaques):
        """Esconde os rótulos dados e passa a mostrá-los só no hover dos seus pontos.

        `destaques` é a lista (anotação, [(x, y), ...]) devolvida por desenhar_controle.
        """
        self._fade.stop()
        self.destaques = {anotacao: pontos for anotacao, pontos in destaques}
        self._opacidade = dict.fromkeys(self.destaques, 0.0)
        self._alvo = dict.fromkeys(self.destaques, 0.0)
        for anotacao in self.destaques:
            _aplicar_opacidade(anotacao, 0.0)
        self.canvas.unsetCursor()

    def _ao_mover(self, evento):
        if not self.destaques:
            return
        perto = set()
        if evento.x is not None:
            for anotacao, pontos in self.destaques.items():
                # Distância em pixels de tela, para o raio não depender da escala dos eixos.
                pixels = anotacao.axes.transData.transform(pontos)
                if np.hypot(pixels[:, 0] - evento.x, pixels[:, 1] - evento.y).min() <= RAIO_HOVER_PX:
                    perto.add(anotacao)
        self._mirar(perto)

    def _mirar(self, visiveis: set):
        """Define quais rótulos devem aparecer e dispara a animação se algo mudou."""
        if not self.destaques:
            return
        for anotacao in self.destaques:
            self._alvo[anotacao] = 1.0 if anotacao in visiveis else 0.0
        if visiveis:
            self.canvas.setCursor(Qt.PointingHandCursor)
        else:
            self.canvas.unsetCursor()
        if self._alvo != self._opacidade:
            self._fade.start()

    def _passo_fade(self):
        passo = 1.0 / PASSOS_FADE
        for anotacao, alvo in self._alvo.items():
            atual = self._opacidade[anotacao]
            if atual != alvo:
                atual = min(atual + passo, alvo) if alvo > atual else max(atual - passo, alvo)
                self._opacidade[anotacao] = atual
                _aplicar_opacidade(anotacao, atual)
        if self._alvo == self._opacidade:
            self._fade.stop()
        self.canvas.draw_idle()

    def exportar(self, nome_sugerido: str) -> str | None:
        """Abre o diálogo de salvar e grava a figura. Devolve o caminho escolhido.

        A imagem não tem hover, então todos os rótulos saem visíveis no arquivo.
        """
        PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Exportar gráfico", str(PASTA_FIGURAS / nome_sugerido),
            "Imagem PNG (*.png);;PDF (*.pdf)")
        if not caminho:
            return None
        for anotacao in self.destaques:
            _aplicar_opacidade(anotacao, 1.0)
        self.figura.savefig(caminho, dpi=200)
        for anotacao, opacidade in self._opacidade.items():
            _aplicar_opacidade(anotacao, opacidade)
        return caminho


def _aplicar_opacidade(anotacao, opacidade: float):
    """Aplica a opacidade ao texto, à caixa e à linha de ligação do rótulo."""
    anotacao.set_visible(opacidade > 0)
    anotacao.set_alpha(opacidade)
    if anotacao.get_bbox_patch() is not None:
        anotacao.get_bbox_patch().set_alpha(0.96 * opacidade)
    if anotacao.arrow_patch is not None:
        anotacao.arrow_patch.set_alpha(opacidade)
