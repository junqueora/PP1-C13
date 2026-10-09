"""Aba 'Início': apresenta o projeto, o grupo, a planta e o passo a passo de uso."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

from gui.widgets import SUBTITULO, TITULO, cartao, pintar

INTEGRANTES = ("Pedro Paulo de Paiva Junqueira",
               "Leandro Teixeira Ambrósio",
               "Luiz Augusto Moreira Barbosa")

PLANTA = [("Planta", "Cilindro pneumático (compressor + reservatório)"),
          ("Variável controlada", "Pressão no reservatório (bar)"),
          ("Variável manipulada", "Comando do motor (0 a 100 %)")]

METODOS = [("Sintonia", "IMC (técnica 2) e ITAE (técnica 6)"),
           ("Critério", "Menor índice de overshoot")]

PASSOS = ("Na aba Identificação, clique em “Escolher arquivo” e carregue o .mat do ensaio.",
          "Escolha o modelo: Smith, Sundaresan ou o ajuste fino. O de menor EQM já vem selecionado.",
          "Vá para a aba Controle PID, liberada depois que o dataset é carregado.",
          "Escolha “Método” (IMC, ITAE…) ou “Manual” para digitar Kp, Ti e Td.",
          "Ajuste o SetPoint (SP) e passe o mouse sobre os pontos do gráfico para ver tr, ts e Mp.",
          "Clique em “Exportar” para salvar o gráfico em PNG ou PDF.")


class AbaInicio(QWidget):
    # Emitido pelo botão "Começar"; a janela principal troca para a aba Identificação.
    comecar = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("pagina")
        pintar(self)

        titulo = QLabel(TITULO)
        titulo.setObjectName("tituloInicio")
        titulo.setWordWrap(True)
        subtitulo = QLabel(SUBTITULO)
        subtitulo.setObjectName("subtituloInicio")
        subtitulo.setWordWrap(True)
        grupo = QLabel("Grupo 3  ·  " + "  ·  ".join(INTEGRANTES))
        grupo.setObjectName("nota")
        grupo.setWordWrap(True)

        self.botao_comecar = QPushButton("Começar")
        self.botao_comecar.setObjectName("primario")
        self.botao_comecar.setCursor(Qt.PointingHandCursor)
        self.botao_comecar.setMinimumWidth(160)
        self.botao_comecar.clicked.connect(self.comecar.emit)

        quadro_topo, topo = cartao(22)
        topo.setSpacing(6)
        topo.addWidget(titulo)
        topo.addWidget(subtitulo)
        topo.addSpacing(6)
        topo.addWidget(grupo)
        topo.addSpacing(10)
        linha_botao = QHBoxLayout()
        linha_botao.addWidget(self.botao_comecar)
        linha_botao.addStretch(1)
        topo.addLayout(linha_botao)

        detalhes = QHBoxLayout()
        detalhes.setSpacing(12)
        detalhes.addWidget(self._quadro_pares("PLANTA", PLANTA), stretch=1)
        detalhes.addWidget(self._quadro_pares("MÉTODOS DO GRUPO", METODOS), stretch=1)

        quadro_passos, passos = cartao(18)
        passos.addWidget(self._secao("COMO USAR"))
        for numero, texto in enumerate(PASSOS, start=1):
            passos.addLayout(self._passo(numero, texto))

        conteudo = QWidget()
        conteudo.setObjectName("pagina")
        pintar(conteudo)
        coluna = QVBoxLayout(conteudo)
        coluna.setContentsMargins(16, 14, 16, 16)
        coluna.setSpacing(12)
        coluna.addWidget(quadro_topo)
        coluna.addLayout(detalhes)
        coluna.addWidget(quadro_passos)
        coluna.addStretch(1)

        # A rolagem só aparece se a janela ficar baixa demais para o conteúdo.
        rolagem = QScrollArea()
        rolagem.setWidgetResizable(True)
        rolagem.setFrameShape(QFrame.NoFrame)
        rolagem.setWidget(conteudo)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(rolagem)

    # ------------------------------------------------------------------ #
    def _quadro_pares(self, secao: str, pares) -> QFrame:
        """Cartão com uma seção e pares rótulo/valor."""
        quadro, miolo = cartao(18)
        miolo.addWidget(self._secao(secao))
        grade = QGridLayout()
        grade.setHorizontalSpacing(14)
        grade.setVerticalSpacing(8)
        grade.setColumnStretch(1, 1)
        for linha, (rotulo, valor) in enumerate(pares):
            chave = QLabel(rotulo)
            chave.setObjectName("campo")
            texto = QLabel(valor)
            texto.setWordWrap(True)
            grade.addWidget(chave, linha, 0, Qt.AlignTop)
            grade.addWidget(texto, linha, 1, Qt.AlignTop)
        miolo.addLayout(grade)
        miolo.addStretch(1)
        return quadro

    def _passo(self, numero: int, texto: str) -> QHBoxLayout:
        marcador = QLabel(str(numero))
        marcador.setObjectName("numeroPasso")
        marcador.setAlignment(Qt.AlignCenter)
        marcador.setFixedSize(24, 24)
        pintar(marcador)
        descricao = QLabel(texto)
        descricao.setWordWrap(True)
        linha = QHBoxLayout()
        linha.setSpacing(10)
        linha.addWidget(marcador, alignment=Qt.AlignTop)
        linha.addWidget(descricao, stretch=1)
        return linha

    def _secao(self, texto: str) -> QLabel:
        rotulo = QLabel(texto)
        rotulo.setObjectName("secao")
        return rotulo
