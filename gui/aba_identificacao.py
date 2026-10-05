"""Aba 'Identificação': carrega o dataset e mostra o modelo FOPDT de cada método."""
from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                             QPushButton, QVBoxLayout, QWidget)

from gui.widgets import CampoNumerico, Grafico, cabecalho
from src import dataset, graficos, identificacao
from src.config import PASTA_DADOS


class AbaIdentificacao(QWidget):
    # Emitido sempre que há um modelo válido selecionado: (Dataset, Identificacao).
    modelo_definido = pyqtSignal(object, object)

    def __init__(self):
        super().__init__()
        self.ds = None
        self.resultados = {}

        self.botao_arquivo = QPushButton("Escolher arquivo")
        self.botao_arquivo.clicked.connect(self.escolher_arquivo)
        self.rotulo_status = QLabel("⚠ Selecione um dataset.")
        self.rotulo_status.setWordWrap(True)
        topo = QHBoxLayout()
        topo.addWidget(self.botao_arquivo)
        topo.addWidget(self.rotulo_status, stretch=1)

        self.grafico = Grafico()
        self.grafico.limpar("Dados de identificação do sistema")
        self.rotulo_modelo = QLabel("")
        self.rotulo_modelo.setWordWrap(True)

        self.combo_metodo = QComboBox()
        self.combo_metodo.setEnabled(False)
        self.combo_metodo.currentTextChanged.connect(self._mostrar_metodo)

        # Os parâmetros identificados nunca são editáveis pelo usuário.
        self.campo_k = CampoNumerico(travado=True)
        self.campo_tau = CampoNumerico(travado=True)
        self.campo_theta = CampoNumerico(travado=True)
        self.campo_razao = CampoNumerico(travado=True)
        self.campo_eqm = CampoNumerico(travado=True)
        self.botao_exportar = QPushButton("Exportar")
        self.botao_exportar.setEnabled(False)
        self.botao_exportar.clicked.connect(self._exportar)

        formulario = QFormLayout()
        formulario.addRow("Identificação:", self.combo_metodo)
        formulario.addRow("k:", self.campo_k)
        formulario.addRow("τ (s):", self.campo_tau)
        formulario.addRow("θ (s):", self.campo_theta)
        formulario.addRow("θ/τ:", self.campo_razao)
        formulario.addRow("EQM:", self.campo_eqm)
        lateral = QVBoxLayout()
        lateral.addLayout(formulario)
        lateral.addWidget(self.botao_exportar)
        lateral.addStretch(1)

        esquerda = QVBoxLayout()
        esquerda.addWidget(self.grafico, stretch=1)
        esquerda.addWidget(self.rotulo_modelo)
        corpo = QHBoxLayout()
        corpo.addLayout(esquerda, stretch=1)
        corpo.addLayout(lateral)

        layout = QVBoxLayout(self)
        layout.addWidget(cabecalho())
        layout.addLayout(topo)
        layout.addLayout(corpo, stretch=1)

    # ------------------------------------------------------------------ #
    def escolher_arquivo(self):
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Selecionar dataset", str(PASTA_DADOS), "Arquivos MATLAB (*.mat)")
        if caminho:
            self.carregar(caminho)

    def carregar(self, caminho) -> bool:
        """Lê e valida o arquivo, identifica o modelo e seleciona, entre Smith e
        Sundaresan, o método de menor EQM."""
        try:
            ds = dataset.carregar(caminho)
            resultados = identificacao.identificar(ds)
        except ValueError as erro:
            self.rotulo_status.setText(f"⚠ Dataset inválido: {erro}")
            return False

        escolhido = identificacao.melhor(resultados)
        resultados["Ajuste fino"] = identificacao.ajuste_fino(ds, escolhido.modelo)
        self.ds, self.resultados = ds, resultados

        # O ajuste fino parte do melhor método e minimiza o EQM, então costuma ter o
        # menor erro de todos. A mensagem informa os dois resultados separadamente.
        menor = min(resultados.values(), key=lambda r: r.eqm)
        mensagem = (f"✔ {ds.nome} válido: {len(ds.t)} amostras, degrau de {ds.u0:g} para "
                    f"{ds.u1:g} em t = {ds.t0:g} s. Menor EQM: {menor.metodo} ({menor.eqm:.4g}).")
        if menor is not escolhido:
            mensagem += (f" Entre Smith e Sundaresan, o menor é o de {escolhido.metodo} "
                         f"({escolhido.eqm:.4g}).")
        self.rotulo_status.setText(mensagem)
        self.rotulo_status.setToolTip(ds.descricao)

        self.combo_metodo.blockSignals(True)
        self.combo_metodo.clear()
        self.combo_metodo.addItems(list(resultados))
        self.combo_metodo.setCurrentText(escolhido.metodo)
        self.combo_metodo.blockSignals(False)
        self.combo_metodo.setEnabled(True)
        self.botao_exportar.setEnabled(True)
        self._mostrar_metodo(escolhido.metodo)
        return True

    def _mostrar_metodo(self, metodo: str):
        if self.ds is None or metodo not in self.resultados:
            return
        r = self.resultados[metodo]
        self.campo_k.definir(r.modelo.k, ".5g")
        self.campo_tau.definir(r.modelo.tau)
        self.campo_theta.definir(r.modelo.theta)
        self.campo_razao.definir(r.modelo.incontrolabilidade, ".3g")
        self.campo_eqm.definir(r.eqm, ".4g")
        self.rotulo_modelo.setText(str(r.modelo))

        self.grafico.figura.clear()
        ax = self.grafico.figura.add_subplot()
        graficos.desenhar_identificacao(ax, self.ds, [r], f"Identificação por {metodo}")
        self.grafico.atualizar()
        self.modelo_definido.emit(self.ds, r)

    def _exportar(self):
        metodo = self.combo_metodo.currentText().lower().replace(" ", "_")
        caminho = self.grafico.exportar(f"identificacao_{metodo}.png")
        if caminho:
            self.rotulo_status.setText(f"✔ Gráfico salvo em {caminho}")
