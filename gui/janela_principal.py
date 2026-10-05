"""Janela principal: reúne as abas Identificação e Controle PID."""
from __future__ import annotations

from PyQt5.QtWidgets import QMainWindow, QTabWidget

from gui.aba_controle import AbaControle
from gui.aba_identificacao import AbaIdentificacao
from gui.widgets import SUBTITULO


class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(SUBTITULO)
        self.resize(1000, 760)

        self.aba_identificacao = AbaIdentificacao()
        self.aba_controle = AbaControle()
        self.abas = QTabWidget()
        self.abas.addTab(self.aba_identificacao, "Identificação")
        self.indice_controle = self.abas.addTab(self.aba_controle, "Controle PID")
        # A aba de controle só é liberada depois que um dataset válido é selecionado.
        self.abas.setTabEnabled(self.indice_controle, False)
        self.setCentralWidget(self.abas)

        self.aba_identificacao.modelo_definido.connect(self._ao_definir_modelo)

    def _ao_definir_modelo(self, ds, identificacao):
        self.aba_controle.definir_modelo(ds, identificacao)
        self.abas.setTabEnabled(self.indice_controle, True)
