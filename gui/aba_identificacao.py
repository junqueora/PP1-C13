"""Aba 'Identificação': carrega o dataset e mostra o modelo FOPDT de cada método."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                             QPushButton, QVBoxLayout, QWidget)

from gui.widgets import CampoNumerico, Grafico, cartao, definir_aviso, pintar
from src import dataset, graficos, identificacao
from src.config import PASTA_DADOS


class AbaIdentificacao(QWidget):
    # Emitido sempre que há um modelo válido selecionado: (Dataset, Identificacao).
    modelo_definido = pyqtSignal(object, object)

    def __init__(self):
        super().__init__()
        self.setObjectName("pagina")
        pintar(self)
        self.ds = None
        self.resultados = {}

        self.botao_arquivo = QPushButton("Escolher arquivo")
        self.botao_arquivo.setObjectName("primario")
        self.botao_arquivo.setCursor(Qt.PointingHandCursor)
        self.botao_arquivo.clicked.connect(self.escolher_arquivo)
        self.rotulo_status = QLabel()
        self.rotulo_status.setWordWrap(True)
        self.rotulo_detalhe = QLabel()
        self.rotulo_detalhe.setWordWrap(True)
        definir_aviso(self.rotulo_status, "Selecione o arquivo do ensaio (.mat).", "neutro")
        definir_aviso(self.rotulo_detalhe, "", "neutro")
        topo = QHBoxLayout()
        topo.setSpacing(12)
        topo.addWidget(self.botao_arquivo)
        topo.addWidget(self.rotulo_status, stretch=1)

        self.grafico = Grafico()
        self.grafico.limpar("A curva de reação aparece aqui")
        quadro_grafico, miolo_grafico = cartao(8)
        miolo_grafico.addWidget(self.grafico)

        self.rotulo_modelo = QLabel("")
        self.rotulo_modelo.setObjectName("modelo")
        pintar(self.rotulo_modelo)
        self.rotulo_modelo.setWordWrap(True)
        self.rotulo_modelo.setVisible(False)
        self.rotulo_referencia = QLabel("")
        self.rotulo_referencia.setObjectName("nota")
        self.rotulo_referencia.setWordWrap(True)

        self.combo_metodo = QComboBox()
        self.combo_metodo.setEnabled(False)
        self.combo_metodo.currentTextChanged.connect(self._mostrar_metodo)

        # Os parâmetros identificados nunca são editáveis pelo usuário.
        self.campo_k = CampoNumerico(travado=True)
        self.campo_tau = CampoNumerico(travado=True)
        self.campo_theta = CampoNumerico(travado=True)
        self.campo_razao = CampoNumerico(travado=True)
        self.campo_eqm = CampoNumerico(travado=True)
        self.botao_exportar = QPushButton("Exportar gráfico")
        self.botao_exportar.setCursor(Qt.PointingHandCursor)
        self.botao_exportar.setEnabled(False)
        self.botao_exportar.clicked.connect(self._exportar)

        secao = QLabel("MODELO")
        secao.setObjectName("secao")
        formulario = QFormLayout()
        formulario.setSpacing(8)
        formulario.addRow(self._rotulo("Método"), self.combo_metodo)
        formulario.addRow(self._rotulo("k"), self.campo_k)
        formulario.addRow(self._rotulo("τ (s)"), self.campo_tau)
        formulario.addRow(self._rotulo("θ (s)"), self.campo_theta)
        formulario.addRow(self._rotulo("θ/τ"), self.campo_razao)
        formulario.addRow(self._rotulo("EQM"), self.campo_eqm)

        quadro_lateral, lateral = cartao()
        quadro_lateral.setFixedWidth(320)
        lateral.addWidget(secao)
        lateral.addLayout(formulario)
        lateral.addWidget(self.rotulo_modelo)
        lateral.addWidget(self.rotulo_referencia)
        lateral.addWidget(self.botao_exportar)
        lateral.addStretch(1)

        corpo = QHBoxLayout()
        corpo.setSpacing(12)
        corpo.addWidget(quadro_grafico, stretch=1)
        corpo.addWidget(quadro_lateral)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        layout.addLayout(topo)
        layout.addWidget(self.rotulo_detalhe)
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
            definir_aviso(self.rotulo_status, f"Dataset inválido. {erro}", "erro")
            definir_aviso(self.rotulo_detalhe, "", "neutro")
            return False

        escolhido = identificacao.melhor(resultados)
        resultados["Ajuste fino"] = identificacao.ajuste_fino(ds, escolhido.modelo)
        self.ds, self.resultados = ds, resultados

        # O ajuste fino parte do melhor método e minimiza o EQM, então costuma ter o
        # menor erro de todos. A mensagem informa os dois resultados separadamente.
        menor = min(resultados.values(), key=lambda r: r.eqm)
        definir_aviso(
            self.rotulo_status,
            f"{ds.nome}  ·  {len(ds.t)} amostras  ·  degrau de {ds.u0:g} para {ds.u1:g} em t = {ds.t0:g} s",
            "ok")
        detalhe = f"Menor EQM: {menor.metodo} ({menor.eqm:.4g})."
        if menor is not escolhido:
            detalhe += (f" Entre Smith e Sundaresan, o menor é {escolhido.metodo} "
                        f"({escolhido.eqm:.4g}).")
        definir_aviso(self.rotulo_detalhe, detalhe, "neutro")
        self.rotulo_status.setToolTip(ds.descricao)
        self.rotulo_referencia.setText(self._texto_referencia(ds))

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
        self.rotulo_modelo.setVisible(True)

        self.grafico.figura.clear()
        ax = self.grafico.figura.add_subplot()
        graficos.desenhar_identificacao(ax, self.ds, [r], f"Identificação por {metodo}",
                                        self.ds.grandeza)
        self.grafico.atualizar()
        self.modelo_definido.emit(self.ds, r)

    def _texto_referencia(self, ds) -> str:
        """Parâmetros com que o ensaio foi gerado, quando o arquivo os traz.

        O enunciado recomenda Sundaresan para sinal ruidoso. O critério que
        desempata os dois métodos continua sendo o menor EQM.
        """
        ref = ds.referencia or {}
        if not {"k", "tau", "theta"} <= ref.keys():
            return ""
        return (f"Referência do arquivo: k = {ref['k']:.5g}, τ = {ref['tau']:.4g} s, "
                f"θ = {ref['theta']:.4g} s. O ensaio tem ruído; Sundaresan é o método "
                f"indicado para isso, e a escolha entre Smith e Sundaresan usa o menor EQM.")

    def _rotulo(self, texto: str) -> QLabel:
        rotulo = QLabel(texto)
        rotulo.setObjectName("campo")
        return rotulo

    def _exportar(self):
        metodo = self.combo_metodo.currentText().lower().replace(" ", "_")
        caminho = self.grafico.exportar(f"identificacao_{metodo}.png")
        if caminho:
            definir_aviso(self.rotulo_status, f"Gráfico salvo em {caminho}", "ok")
