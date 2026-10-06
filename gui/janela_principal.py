"""Janela principal: reúne as abas Identificação e Controle PID."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from gui.aba_controle import AbaControle
from gui.aba_identificacao import AbaIdentificacao
from gui.widgets import SUBTITULO, TITULO, pintar


class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PP1-C13  ·  Sintonia de PID")
        self.resize(1240, 820)
        self.setMinimumSize(980, 680)

        raiz = QWidget()
        raiz.setObjectName("pagina")
        pintar(raiz)
        coluna = QVBoxLayout(raiz)
        coluna.setContentsMargins(0, 0, 0, 0)
        coluna.setSpacing(0)

        barra = QWidget()
        barra.setObjectName("barra")
        pintar(barra)
        topo = QVBoxLayout(barra)
        topo.setContentsMargins(20, 14, 20, 12)
        topo.setSpacing(2)
        titulo = QLabel(TITULO)
        titulo.setObjectName("tituloApp")
        subtitulo = QLabel(SUBTITULO)
        subtitulo.setObjectName("subtituloApp")
        topo.addWidget(titulo)
        topo.addWidget(subtitulo)

        self.aba_identificacao = AbaIdentificacao()
        self.aba_controle = AbaControle()
        self.abas = QTabWidget()
        self.abas.setDocumentMode(True)
        self.abas.tabBar().setDrawBase(False)
        self.abas.addTab(self.aba_identificacao, "Identificação")
        self.indice_controle = self.abas.addTab(self.aba_controle, "Controle PID")
        # A aba de controle só é liberada depois que um dataset válido é selecionado.
        self.abas.setTabEnabled(self.indice_controle, False)
        self.abas.setElideMode(Qt.ElideNone)

        coluna.addWidget(barra)
        coluna.addWidget(self.abas, stretch=1)
        self.setCentralWidget(raiz)

        self.aba_identificacao.modelo_definido.connect(self._ao_definir_modelo)

    def _ao_definir_modelo(self, ds, identificacao):
        self.aba_controle.definir_modelo(ds, identificacao)
        self.abas.setTabEnabled(self.indice_controle, True)
