"""Aba 'Relatório': escolhe as seções, mostra a prévia das páginas e gera o PDF."""
from __future__ import annotations

import io

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget)

from gui.widgets import cartao, definir_aviso, pintar
from src import relatorio
from src.config import PASTA_FIGURAS

DPI_PREVIA = 90                 # A4 a 90 dpi: cerca de 745 px de largura


class AbaRelatorio(QWidget):
    def __init__(self, coletar):
        """`coletar()` devolve um DadosRelatorio com o estado atual, ou None."""
        super().__init__()
        self.setObjectName("pagina")
        pintar(self)
        self.coletar = coletar
        self.previas = []        # QPixmap de cada página
        self.pagina = 0

        # --- seções e geração ---------------------------------------------------
        secao = QLabel("CONTEÚDO")
        secao.setObjectName("secao")
        self.marcas = {}
        quadro_lateral, lateral = cartao()
        quadro_lateral.setFixedWidth(320)
        lateral.addWidget(secao)
        for chave, texto in relatorio.SECOES.items():
            marca = QCheckBox(texto)
            marca.setChecked(True)
            marca.setCursor(Qt.PointingHandCursor)
            marca.toggled.connect(self.atualizar)
            self.marcas[chave] = marca
            lateral.addWidget(marca)
        nota = QLabel("O relatório usa o modelo, a sintonia, o SetPoint e a opção de limite "
                      "do motor que estão selecionados nas abas Identificação e Controle PID.")
        nota.setObjectName("nota")
        nota.setWordWrap(True)
        lateral.addWidget(nota)
        self.botao_gerar = QPushButton("Gerar PDF")
        self.botao_gerar.setObjectName("primario")
        self.botao_gerar.setCursor(Qt.PointingHandCursor)
        self.botao_gerar.clicked.connect(self._gerar)
        lateral.addWidget(self.botao_gerar)
        lateral.addStretch(1)

        # --- prévia --------------------------------------------------------------
        self.imagem = QLabel()
        self.imagem.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        rolagem = QScrollArea()
        rolagem.setWidgetResizable(True)
        rolagem.setFrameShape(QFrame.NoFrame)
        rolagem.setWidget(self.imagem)
        self.botao_anterior = self._seta("‹", -1)
        self.botao_proxima = self._seta("›", +1)
        self.rotulo_pagina = QLabel("")
        self.rotulo_pagina.setObjectName("campo")
        navegacao = QHBoxLayout()
        navegacao.addStretch(1)
        navegacao.addWidget(self.botao_anterior)
        navegacao.addWidget(self.rotulo_pagina)
        navegacao.addWidget(self.botao_proxima)
        navegacao.addStretch(1)
        quadro_previa, previa = cartao(8)
        previa.addWidget(rolagem, stretch=1)
        previa.addLayout(navegacao)

        corpo = QHBoxLayout()
        corpo.setSpacing(12)
        corpo.addWidget(quadro_previa, stretch=1)
        corpo.addWidget(quadro_lateral)
        self.rotulo_status = QLabel()
        self.rotulo_status.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        layout.addLayout(corpo, stretch=1)
        layout.addWidget(self.rotulo_status)
        definir_aviso(self.rotulo_status, "", "neutro")

    # ------------------------------------------------------------------ #
    def atualizar(self):
        """Refaz a prévia com o estado atual das outras abas."""
        dados = self.coletar()
        if dados is None:
            self._sem_previa("Carregue um dataset na aba Identificação.")
            return
        sem_sintonia = dados.resposta is None
        self.marcas["controle"].setEnabled(not sem_sintonia)
        self.marcas["controle"].setToolTip(
            "Não há sintonia válida na aba Controle PID." if sem_sintonia else "")
        figuras = relatorio.paginas(dados, self._secoes())
        if not figuras:
            self._sem_previa("Escolha ao menos uma seção.")
            return
        self.previas = [self._renderizar(fig) for fig in figuras]
        self.pagina = min(self.pagina, len(self.previas) - 1)
        self.botao_gerar.setEnabled(True)
        aviso = ("A seção 'Sintonia atual' foi omitida: não há sintonia válida na aba Controle PID."
                 if sem_sintonia and "controle" in self._secoes() else "")
        definir_aviso(self.rotulo_status, aviso, "alerta")
        self._mostrar()

    def _secoes(self) -> tuple:
        return tuple(chave for chave, marca in self.marcas.items() if marca.isChecked())

    def _gerar(self):
        dados = self.coletar()
        if dados is None:
            return
        figuras = relatorio.paginas(dados, self._secoes())   # data e hora do momento
        if not figuras:
            return
        destino = PASTA_FIGURAS.parent / "relatorio_pp1_c13.pdf"
        destino.parent.mkdir(parents=True, exist_ok=True)
        caminho, _ = QFileDialog.getSaveFileName(self, "Gerar relatório", str(destino),
                                                 "PDF (*.pdf)")
        if not caminho:
            return
        try:
            relatorio.salvar_pdf(caminho, figuras)
        except OSError as erro:              # arquivo aberto em outro programa, sem permissão...
            definir_aviso(self.rotulo_status, f"Não foi possível salvar o PDF: {erro}", "erro")
            return
        definir_aviso(self.rotulo_status,
                      f"Relatório salvo em {caminho} ({len(figuras)} páginas).", "ok")

    # ------------------------------------------------------------------ #
    def _mostrar(self):
        total = len(self.previas)
        self.imagem.setPixmap(self.previas[self.pagina])
        self.rotulo_pagina.setText(f"Página {self.pagina + 1} de {total}")
        self.botao_anterior.setEnabled(self.pagina > 0)
        self.botao_proxima.setEnabled(self.pagina < total - 1)

    def _virar(self, passo: int):
        if self.previas:
            self.pagina = max(0, min(self.pagina + passo, len(self.previas) - 1))
            self._mostrar()

    def _sem_previa(self, mensagem: str):
        self.previas = []
        self.imagem.clear()
        self.imagem.setText(mensagem)
        self.rotulo_pagina.setText("")
        self.botao_anterior.setEnabled(False)
        self.botao_proxima.setEnabled(False)
        self.botao_gerar.setEnabled(False)

    def _renderizar(self, fig) -> QPixmap:
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=DPI_PREVIA)
        imagem = QPixmap()
        imagem.loadFromData(buffer.getvalue(), "PNG")
        return imagem

    def _seta(self, texto: str, passo: int) -> QToolButton:
        botao = QToolButton()
        botao.setObjectName("icone")
        botao.setText(texto)
        botao.setCursor(Qt.PointingHandCursor)
        botao.clicked.connect(lambda: self._virar(passo))
        return botao
