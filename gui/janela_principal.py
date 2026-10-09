"""Janela principal: reúne as abas Início, Identificação, Controle PID e Relatório."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from gui.aba_controle import AbaControle
from gui.aba_identificacao import AbaIdentificacao
from gui.aba_inicio import AbaInicio
from gui.aba_relatorio import AbaRelatorio
from gui.widgets import SUBTITULO, TITULO, pintar
from src.relatorio import DadosRelatorio


class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITULO)
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

        self.aba_inicio = AbaInicio()
        self.aba_identificacao = AbaIdentificacao()
        self.aba_controle = AbaControle()
        self.abas = QTabWidget()
        self.abas.setDocumentMode(True)
        self.abas.tabBar().setDrawBase(False)
        self.abas.addTab(self.aba_inicio, "Início")
        self.indice_identificacao = self.abas.addTab(self.aba_identificacao, "Identificação")
        self.indice_controle = self.abas.addTab(self.aba_controle, "Controle PID")
        self.aba_relatorio = AbaRelatorio(self._dados_relatorio)
        self.indice_relatorio = self.abas.addTab(self.aba_relatorio, "Relatório")
        # Controle e relatório só são liberados depois que um dataset válido é selecionado.
        self.abas.setTabEnabled(self.indice_controle, False)
        self.abas.setTabEnabled(self.indice_relatorio, False)
        self.abas.setElideMode(Qt.ElideNone)

        coluna.addWidget(barra)
        coluna.addWidget(self.abas, stretch=1)
        self.setCentralWidget(raiz)

        self.aba_inicio.comecar.connect(
            lambda: self.abas.setCurrentIndex(self.indice_identificacao))
        self.aba_identificacao.modelo_definido.connect(self._ao_definir_modelo)
        self.abas.currentChanged.connect(self._ao_trocar_aba)

    def _ao_definir_modelo(self, ds, identificacao):
        self.aba_controle.definir_modelo(ds, identificacao)
        self.abas.setTabEnabled(self.indice_controle, True)
        self.abas.setTabEnabled(self.indice_relatorio, True)

    def _ao_trocar_aba(self, indice: int):
        # A prévia é refeita ao abrir a aba, para refletir o estado atual das outras.
        if indice == self.indice_relatorio:
            self.aba_relatorio.atualizar()

    def _dados_relatorio(self) -> DadosRelatorio | None:
        """Estado atual das abas Identificação e Controle, no formato do relatório."""
        ident, controle = self.aba_identificacao, self.aba_controle
        if ident.ds is None or controle.identificacao is None:
            return None
        resposta = controle.resposta
        if resposta is not None:
            sp = resposta.sp
        else:                                # SP = 0 é válido; só cai no padrão se vazio
            sp = controle.campo_sp.valor()
            sp = ident.ds.yf if sp is None else sp
        return DadosRelatorio(
            ds=ident.ds, resultados=ident.resultados,
            metodo_modelo=controle.identificacao.metodo, modelo=controle.modelo, sp=sp,
            lam=controle.campo_lambda.valor(), resposta=resposta, pid=controle.pid,
            titulo_controle=controle.titulo, limitada=controle.marca_limitar.isChecked())
