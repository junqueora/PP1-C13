"""Aba 'Controle PID': sintonia por método clássico ou manual e métricas da resposta."""
from __future__ import annotations

from PyQt5.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFrame, QGridLayout,
                             QHBoxLayout, QLabel, QPushButton, QRadioButton, QToolButton,
                             QVBoxLayout, QWidget)

from gui.widgets import CampoNumerico, Grafico, cabecalho
from src import graficos, simulacao, sintonia
from src.config import METODOS_GRUPO, MV_MAX, MV_MIN, RAZAO_LAMBDA_PADRAO
from src.sintonia import PID


class AbaControle(QWidget):
    def __init__(self):
        super().__init__()
        self.ds = None
        self.modelo = None
        self.resposta = None
        self.titulo = ""

        # --- seleção da forma de sintonia ---------------------------------
        self.radio_metodo = QRadioButton("Método")
        self.radio_manual = QRadioButton("Manual")
        self.radio_metodo.setChecked(True)
        grupo = QButtonGroup(self)
        grupo.addButton(self.radio_metodo)
        grupo.addButton(self.radio_manual)
        self.radio_metodo.toggled.connect(self._ao_trocar_modo)

        self.combo_metodo = QComboBox()
        self.combo_metodo.addItems(METODOS_GRUPO)            # métodos do grupo primeiro
        self.combo_metodo.insertSeparator(len(METODOS_GRUPO))
        self.combo_metodo.addItems([m for m in sintonia.METODOS if m not in METODOS_GRUPO])
        self.combo_metodo.currentTextChanged.connect(self._ao_trocar_metodo)

        topo = QHBoxLayout()
        topo.addWidget(QLabel("<b>Seleção de sintonia:</b>"))
        topo.addWidget(self.radio_metodo)
        topo.addWidget(self.radio_manual)
        topo.addStretch(1)
        topo.addWidget(self.combo_metodo)

        # --- parâmetros do controlador -------------------------------------
        self.campo_kp = CampoNumerico()
        self.campo_ti = CampoNumerico()
        self.campo_td = CampoNumerico()
        self.campo_lambda = CampoNumerico()
        self.campo_lambda.editingFinished.connect(self._recalcular_metodo)
        for campo in (self.campo_kp, self.campo_ti, self.campo_td):
            campo.returnPressed.connect(self._sintonizar_manual)

        painel = QGridLayout()
        self.botoes_limpar = {}
        linhas = [("Kp:", self.campo_kp), ("Ti (s):", self.campo_ti),
                  ("Td (s):", self.campo_td), ("λ (s):", self.campo_lambda)]
        for linha, (texto, campo) in enumerate(linhas):
            limpar = QToolButton()
            limpar.setText("✕")
            limpar.setToolTip("Limpar o valor")
            limpar.clicked.connect(campo.clear)
            self.botoes_limpar[campo] = limpar
            painel.addWidget(QLabel(texto), linha, 0)
            painel.addWidget(campo, linha, 1)
            painel.addWidget(limpar, linha, 2)

        self.botao_sintonizar = QPushButton("Sintonizar")
        self.botao_sintonizar.clicked.connect(self._sintonizar_manual)
        self.botao_exportar = QPushButton("Exportar")
        self.botao_exportar.clicked.connect(self._exportar)
        botoes = QHBoxLayout()
        botoes.addWidget(self.botao_sintonizar)
        botoes.addWidget(self.botao_exportar)

        # --- parâmetros de controle e métricas ------------------------------
        self.campo_sp = CampoNumerico()
        self.campo_sp.editingFinished.connect(self._ao_mudar_sp)
        self.rotulo_sp = QLabel("SP:")
        # As métricas são resultados da simulação e nunca são editáveis.
        self.campo_tr = CampoNumerico(travado=True)
        self.campo_ts = CampoNumerico(travado=True)
        self.campo_mp = CampoNumerico(travado=True)
        self.campo_pico = CampoNumerico(travado=True)
        self.campo_erro = CampoNumerico(travado=True)
        self.campo_mv = CampoNumerico(travado=True)
        self.rotulo_pico = QLabel("Pico:")
        self.rotulo_erro = QLabel("Erro regime:")

        metricas = QGridLayout()
        metricas.addWidget(self.rotulo_sp, 0, 0)
        metricas.addWidget(self.campo_sp, 0, 1)
        self.marcas = {}
        for linha, (chave, texto, campo) in enumerate(
                [("tr", "tr (s):", self.campo_tr), ("ts", "ts (s):", self.campo_ts),
                 ("mp", "Mp (%):", self.campo_mp)], start=1):
            marca = QCheckBox()
            marca.setToolTip("Marcar este ponto no gráfico")
            marca.setChecked(True)
            marca.toggled.connect(self._redesenhar)
            self.marcas[chave] = marca
            metricas.addWidget(QLabel(texto), linha, 0)
            metricas.addWidget(campo, linha, 1)
            metricas.addWidget(marca, linha, 2)
        metricas.addWidget(self.rotulo_pico, 4, 0)
        metricas.addWidget(self.campo_pico, 4, 1)
        metricas.addWidget(self.rotulo_erro, 5, 0)
        metricas.addWidget(self.campo_erro, 5, 1)
        metricas.addWidget(QLabel("MV máx (%):"), 6, 0)
        metricas.addWidget(self.campo_mv, 6, 1)

        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)

        lateral = QVBoxLayout()
        lateral.addLayout(painel)
        lateral.addLayout(botoes)
        lateral.addWidget(separador)
        lateral.addWidget(QLabel("<b>Parâmetros de controle:</b>"))
        lateral.addLayout(metricas)
        lateral.addStretch(1)

        # --- gráfico e mensagens ---------------------------------------------
        self.grafico = Grafico()
        self.rotulo_status = QLabel("")
        self.rotulo_status.setWordWrap(True)
        esquerda = QVBoxLayout()
        esquerda.addWidget(self.grafico, stretch=1)
        esquerda.addWidget(self.rotulo_status)
        corpo = QHBoxLayout()
        corpo.addLayout(esquerda, stretch=1)
        corpo.addLayout(lateral)

        layout = QVBoxLayout(self)
        layout.addWidget(cabecalho())
        layout.addLayout(topo)
        layout.addLayout(corpo, stretch=1)

        self._atualizar_estado()
        self._sem_resultado("Selecione um dataset na aba Identificação.")

    # ------------------------------------------------------------------ #
    # Estado da interface
    # ------------------------------------------------------------------ #
    def definir_modelo(self, ds, identificacao):
        """Recebe o dataset e o modelo escolhidos na aba Identificação."""
        novo_dataset = ds is not self.ds
        self.ds, self.modelo = ds, identificacao.modelo
        unidade = f" ({ds.unidade})" if ds.unidade else ""
        self.rotulo_sp.setText(f"SP{unidade}:")
        self.rotulo_pico.setText(f"Pico{unidade}:")
        self.rotulo_erro.setText(f"Erro regime{unidade}:")
        if novo_dataset:
            # O SetPoint começa no valor final do ensaio selecionado.
            self.campo_sp.definir(ds.yf)
        self.campo_lambda.definir(RAZAO_LAMBDA_PADRAO * self.modelo.theta)
        if self._modo_metodo():
            self._recalcular_metodo()
        else:
            self._sintonizar_manual()

    def _modo_metodo(self) -> bool:
        return self.radio_metodo.isChecked()

    def _atualizar_estado(self):
        """Libera ou trava os campos conforme a forma de sintonia selecionada."""
        metodo = self._modo_metodo()
        imc = metodo and self.combo_metodo.currentText() == "IMC"
        self.combo_metodo.setEnabled(metodo)
        for campo in (self.campo_kp, self.campo_ti, self.campo_td):
            campo.travar(metodo)                       # calculados: não podem ser editados
            self.botoes_limpar[campo].setEnabled(not metodo)
        self.campo_lambda.travar(not imc)              # λ só existe no método IMC
        self.campo_lambda.setEnabled(imc)
        self.botoes_limpar[self.campo_lambda].setEnabled(imc)
        self.botao_sintonizar.setEnabled(not metodo and self.modelo is not None)
        self.botao_exportar.setEnabled(self.resposta is not None)

    def _ao_trocar_modo(self):
        self._atualizar_estado()
        if self._modo_metodo():
            self._recalcular_metodo()
        else:
            self.rotulo_status.setText("Edite Kp, Ti e Td e clique em Sintonizar.")

    def _ao_trocar_metodo(self):
        self._atualizar_estado()
        self._recalcular_metodo()

    def _ao_mudar_sp(self):
        if self._modo_metodo():
            self._recalcular_metodo()
        elif self.resposta is not None:
            self._sintonizar_manual()

    # ------------------------------------------------------------------ #
    # Sintonia
    # ------------------------------------------------------------------ #
    def _recalcular_metodo(self):
        """Modo 'Método': calcula Kp, Ti e Td pela regra escolhida e simula."""
        if self.modelo is None or not self._modo_metodo():
            return
        metodo = self.combo_metodo.currentText()
        lam = self.campo_lambda.valor()
        try:
            pid = sintonia.sintonizar(metodo, self.modelo, lam)
        except ValueError as erro:
            self._sem_resultado(f"⚠ {erro}")
            return
        self.campo_kp.definir(pid.kp)
        self.campo_ti.definir(pid.ti)
        self.campo_td.definir(pid.td)
        titulo = f"Controle PID por {metodo}"
        if metodo == "IMC":
            titulo += f" (λ = {lam:.4g} s)"
        self._simular(pid, titulo)

    def _sintonizar_manual(self):
        """Modo 'Manual': usa os valores digitados, depois de validá-los."""
        if self.modelo is None or self._modo_metodo():
            return
        kp, ti, td = self.campo_kp.valor(), self.campo_ti.valor(), self.campo_td.valor()
        if kp is None or ti is None or td is None:
            self._sem_resultado("⚠ Preencha Kp, Ti e Td com valores numéricos.")
            return
        if kp <= 0 or ti <= 0 or td < 0:
            self._sem_resultado("⚠ Use Kp > 0, Ti > 0 e Td ≥ 0.")
            return
        self._simular(PID(kp, ti, td),
                      f"Sintonia manual: Kp = {kp:.4g}, Ti = {ti:.4g}, Td = {td:.4g}")

    def _simular(self, pid: PID, titulo: str):
        sp = self.campo_sp.valor()
        if sp is None:
            self._sem_resultado("⚠ Informe um valor numérico para o SetPoint.")
            return
        if sp == self.ds.y0:
            self._sem_resultado("⚠ O SetPoint é igual ao valor inicial: não há degrau a simular.")
            return
        # A estabilidade é verificada antes de simular (polos da malha fechada).
        if not simulacao.pid_estavel(self.modelo, pid):
            self._sem_resultado("⚠ Malha fechada instável para estes parâmetros. "
                                "Reduza Kp ou aumente Ti.")
            return
        self.resposta = simulacao.simular_controle(self.modelo, pid, sp, self.ds.y0, self.ds.u0)
        self.titulo = titulo
        q = self.resposta.metricas
        self.campo_tr.definir(q.tr, ".2f")
        self.campo_ts.definir(q.ts, ".2f")
        self.campo_mp.definir(q.mp, ".2f")
        self.campo_pico.definir(q.pico)
        self.campo_erro.definir(round(q.erro_regime, 9) + 0.0, ".3g")
        self.campo_mv.definir(self.resposta.mv_max, ".0f")
        self._redesenhar()
        self.rotulo_status.setText(self._mensagem_de_status())
        self._atualizar_estado()

    def _mensagem_de_status(self) -> str:
        mensagens = ["✔ Malha fechada estável."]
        mv_final = float(self.resposta.mv[-1])
        if not (MV_MIN <= mv_final <= MV_MAX):
            mensagens.append(f"⚠ Este SetPoint exige {mv_final:.0f} % do motor em regime, fora "
                             f"da faixa de {MV_MIN:g} a {MV_MAX:g} %: não é alcançável na planta real.")
        elif self.resposta.satura:
            mensagens.append(
                f"⚠ O sinal de controle sai da faixa de {MV_MIN:g} a {MV_MAX:g} % no transitório. "
                "A simulação é linear e não limita o motor; na planta real a resposta seria mais lenta.")
        return " ".join(mensagens)

    # ------------------------------------------------------------------ #
    # Gráfico
    # ------------------------------------------------------------------ #
    def _redesenhar(self):
        if self.resposta is None:
            return
        self.grafico.figura.clear()
        ax_pv, ax_mv = self.grafico.figura.subplots(2, 1, sharex=True, height_ratios=[3, 1.2])
        marcar = [chave for chave, marca in self.marcas.items() if marca.isChecked()]
        graficos.desenhar_controle(ax_pv, ax_mv, self.resposta, self.titulo, self.ds.unidade, marcar)
        self.grafico.atualizar()

    def _sem_resultado(self, mensagem: str):
        """Apaga o gráfico e as métricas quando não há uma sintonia válida."""
        self.resposta = None
        for campo in (self.campo_tr, self.campo_ts, self.campo_mp, self.campo_pico,
                      self.campo_erro, self.campo_mv):
            campo.clear()
        self.grafico.limpar("Resposta do controle PID")
        self.rotulo_status.setText(mensagem)
        self._atualizar_estado()

    def _exportar(self):
        if self.resposta is None:
            return
        nome = "manual" if not self._modo_metodo() else self.combo_metodo.currentText()
        nome = nome.lower().replace(" ", "_").replace("-", "_")
        caminho = self.grafico.exportar(f"pid_{nome}.png")
        if caminho:
            self.rotulo_status.setText(f"✔ Gráfico salvo em {caminho}")
