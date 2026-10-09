"""Aba 'Controle PID': sintonia por método clássico ou manual e métricas da resposta."""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QFrame, QGridLayout,
                             QHBoxLayout, QLabel, QPushButton, QRadioButton, QToolButton,
                             QVBoxLayout, QWidget)

from gui.widgets import CampoNumerico, Grafico, cartao, definir_aviso, pintar
from src import graficos, simulacao, sintonia
from src.config import METODOS_GRUPO, MV_MAX, MV_MIN, RAZAO_LAMBDA_PADRAO
from src.sintonia import PID


class AbaControle(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("pagina")
        pintar(self)
        self.ds = None
        self.modelo = None
        self.resposta = None
        self.pid = None          # última sintonia simulada, para refazer ao mudar opções
        self.titulo_base = ""
        self.titulo = ""

        # --- seleção da forma de sintonia ---------------------------------
        self.radio_metodo = QRadioButton("Método")
        self.radio_manual = QRadioButton("Manual")
        self.radio_metodo.setChecked(True)
        self.radio_metodo.setCursor(Qt.PointingHandCursor)
        self.radio_manual.setCursor(Qt.PointingHandCursor)
        pintar(self.radio_metodo)
        pintar(self.radio_manual)
        grupo = QButtonGroup(self)
        grupo.addButton(self.radio_metodo)
        grupo.addButton(self.radio_manual)
        self.radio_metodo.toggled.connect(self._ao_trocar_modo)
        segmento = QFrame()
        segmento.setObjectName("segmento")
        pintar(segmento)
        faixa = QHBoxLayout(segmento)
        faixa.setContentsMargins(3, 3, 3, 3)
        faixa.setSpacing(2)
        faixa.addWidget(self.radio_metodo)
        faixa.addWidget(self.radio_manual)

        self.combo_metodo = QComboBox()
        self.combo_metodo.setMinimumWidth(180)
        self.combo_metodo.addItems(METODOS_GRUPO)            # métodos do grupo primeiro
        self.combo_metodo.insertSeparator(len(METODOS_GRUPO))
        self.combo_metodo.addItems([m for m in sintonia.METODOS if m not in METODOS_GRUPO])
        self.combo_metodo.currentTextChanged.connect(self._ao_trocar_metodo)
        self.rotulo_regra = QLabel("Regra")
        self.rotulo_regra.setObjectName("campo")

        # --- opções de simulação ----------------------------------------------
        self.marca_limitar = QCheckBox("Limitar motor a 0–100 %")
        self.marca_limitar.setCursor(Qt.PointingHandCursor)
        self.marca_limitar.setToolTip("Simula com o comando do motor saturado na faixa física "
                                      "do atuador (com anti-windup e atraso exato).")
        self.marca_limitar.toggled.connect(self._ressimular)
        self.botao_comparar = QPushButton("Comparar IMC × ITAE")
        self.botao_comparar.setCheckable(True)
        self.botao_comparar.setCursor(Qt.PointingHandCursor)
        self.botao_comparar.setToolTip("Mostra as respostas do IMC e do ITAE no mesmo gráfico, "
                                       "com o mesmo SetPoint.")
        self.botao_comparar.toggled.connect(self._redesenhar)

        topo = QHBoxLayout()
        topo.setSpacing(12)
        topo.addWidget(segmento)
        topo.addStretch(1)
        topo.addWidget(self.marca_limitar)
        topo.addWidget(self.botao_comparar)
        topo.addSpacing(12)
        topo.addWidget(self.rotulo_regra)
        topo.addWidget(self.combo_metodo)

        self.rotulo_modelo = QLabel("")
        self.rotulo_modelo.setObjectName("modelo")
        pintar(self.rotulo_modelo)
        self.rotulo_modelo.setWordWrap(True)
        self.rotulo_modelo.setVisible(False)

        # --- parâmetros do controlador -------------------------------------
        self.campo_kp = CampoNumerico()
        self.campo_ti = CampoNumerico()
        self.campo_td = CampoNumerico()
        self.campo_lambda = CampoNumerico()
        self.campo_lambda.setToolTip("Folga do IMC. O método pede λ/θ > 0,8. λ menor responde mais rápido.")
        self.campo_lambda.editingFinished.connect(self._recalcular_metodo)
        for campo in (self.campo_kp, self.campo_ti, self.campo_td):
            campo.returnPressed.connect(self._sintonizar_manual)

        painel = QGridLayout()
        painel.setHorizontalSpacing(8)
        painel.setVerticalSpacing(8)
        painel.setColumnStretch(1, 1)
        self.botoes_limpar = {}
        linhas = [("Kp", self.campo_kp), ("Ti (s)", self.campo_ti),
                  ("Td (s)", self.campo_td), ("λ (s)", self.campo_lambda)]
        for linha, (texto, campo) in enumerate(linhas):
            limpar = QToolButton()
            limpar.setObjectName("icone")
            limpar.setText("×")
            limpar.setCursor(Qt.PointingHandCursor)
            limpar.setToolTip("Limpar o valor")
            limpar.clicked.connect(campo.clear)
            self.botoes_limpar[campo] = limpar
            painel.addWidget(self._rotulo(texto), linha, 0)
            painel.addWidget(campo, linha, 1)
            painel.addWidget(limpar, linha, 2)

        self.botao_sintonizar = QPushButton("Sintonizar")
        self.botao_sintonizar.setObjectName("primario")
        self.botao_sintonizar.setCursor(Qt.PointingHandCursor)
        self.botao_sintonizar.clicked.connect(self._sintonizar_manual)
        self.botao_exportar = QPushButton("Exportar")
        self.botao_exportar.setCursor(Qt.PointingHandCursor)
        self.botao_exportar.setToolTip("Salva o gráfico em PNG ou PDF.")
        self.botao_exportar.clicked.connect(self._exportar)
        botoes = QHBoxLayout()
        botoes.setSpacing(8)
        botoes.addWidget(self.botao_sintonizar, stretch=1)
        botoes.addWidget(self.botao_exportar, stretch=1)

        # --- parâmetros de controle e métricas ------------------------------
        self.campo_sp = CampoNumerico()
        self.campo_sp.editingFinished.connect(self._ao_mudar_sp)
        self.rotulo_sp = self._rotulo("SP")
        # As métricas são resultados da simulação e nunca são editáveis.
        self.campo_tr = CampoNumerico(travado=True)
        self.campo_ts = CampoNumerico(travado=True)
        self.campo_mp = CampoNumerico(travado=True)
        self.campo_pico = CampoNumerico(travado=True)
        self.campo_erro = CampoNumerico(travado=True)
        self.campo_mv = CampoNumerico(travado=True)
        self.rotulo_pico = self._rotulo("Pico")
        self.rotulo_erro = self._rotulo("Erro regime")
        self.campo_tr.setToolTip("Tempo de subida, de 10 % a 90 % da variação.")
        self.campo_ts.setToolTip("Tempo de acomodação, critério dos 2 %.")
        self.campo_mp.setToolTip("Overshoot, em % da variação até o SetPoint.")

        metricas = QGridLayout()
        metricas.setHorizontalSpacing(8)
        metricas.setVerticalSpacing(8)
        metricas.setColumnStretch(1, 1)
        metricas.addWidget(self.rotulo_sp, 0, 0)
        metricas.addWidget(self.campo_sp, 0, 1)
        self.marcas = {}
        dicas = {
            "tr": "Marcar o tempo de subida no gráfico",
            "ts": "Marcar o tempo de acomodação no gráfico",
            "mp": "Marcar o pico e o overshoot no gráfico",
        }
        for linha, (chave, texto, campo) in enumerate(
                [("tr", "tr (s)", self.campo_tr), ("ts", "ts (s)", self.campo_ts),
                 ("mp", "Mp (%)", self.campo_mp)], start=1):
            marca = QCheckBox()
            marca.setToolTip(dicas[chave])
            marca.setChecked(True)
            marca.toggled.connect(self._redesenhar)
            self.marcas[chave] = marca
            metricas.addWidget(self._rotulo(texto), linha, 0)
            metricas.addWidget(campo, linha, 1)
            metricas.addWidget(marca, linha, 2)
        metricas.addWidget(self.rotulo_pico, 4, 0)
        metricas.addWidget(self.campo_pico, 4, 1)
        metricas.addWidget(self.rotulo_erro, 5, 0)
        metricas.addWidget(self.campo_erro, 5, 1)
        metricas.addWidget(self._rotulo("MV máx (%)"), 6, 0)
        metricas.addWidget(self.campo_mv, 6, 1)

        quadro_lateral, lateral = cartao()
        quadro_lateral.setFixedWidth(332)
        lateral.addWidget(self._secao("CONTROLADOR"))
        lateral.addLayout(painel)
        lateral.addLayout(botoes)
        lateral.addSpacing(6)
        lateral.addWidget(self._secao("RESPOSTA"))
        lateral.addLayout(metricas)
        lateral.addStretch(1)

        # --- gráfico e mensagens ---------------------------------------------
        self.grafico = Grafico()
        self.rotulo_status = QLabel()
        self.rotulo_status.setWordWrap(True)
        self.rotulo_alerta = QLabel()
        self.rotulo_alerta.setWordWrap(True)
        quadro_grafico, miolo = cartao(8)
        miolo.addWidget(self.grafico)
        corpo = QHBoxLayout()
        corpo.setSpacing(12)
        corpo.addWidget(quadro_grafico, stretch=1)
        corpo.addWidget(quadro_lateral)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        layout.addLayout(topo)
        layout.addWidget(self.rotulo_modelo)
        layout.addLayout(corpo, stretch=1)
        layout.addWidget(self.rotulo_status)
        layout.addWidget(self.rotulo_alerta)

        self._atualizar_estado()
        self._sem_resultado("Carregue um dataset na aba Identificação.", "neutro")

    # ------------------------------------------------------------------ #
    # Estado da interface
    # ------------------------------------------------------------------ #
    def definir_modelo(self, ds, identificacao):
        """Recebe o dataset e o modelo escolhidos na aba Identificação."""
        novo_dataset = ds is not self.ds
        self.ds, self.modelo = ds, identificacao.modelo
        self.rotulo_modelo.setText(f"{identificacao.metodo}    ·    {identificacao.modelo}")
        self.rotulo_modelo.setVisible(True)
        if ds.unidade:
            self.rotulo_sp.setText(f"SP ({ds.unidade})")
            self.rotulo_pico.setText(f"Pico ({ds.unidade})")
            self.rotulo_erro.setText(f"Erro ({ds.unidade})")
        else:
            self.rotulo_sp.setText("SP")
            self.rotulo_pico.setText("Pico")
            self.rotulo_erro.setText("Erro regime")
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
        self.rotulo_regra.setEnabled(metodo)
        for campo in (self.campo_kp, self.campo_ti, self.campo_td):
            campo.travar(metodo)                       # calculados: não podem ser editados
            self.botoes_limpar[campo].setVisible(not metodo)
        self.campo_lambda.travar(not imc)              # λ só existe no método IMC
        self.campo_lambda.setEnabled(imc)
        self.botoes_limpar[self.campo_lambda].setVisible(imc)
        # Sempre visível; no modo Método os valores vêm da regra, então fica desabilitado.
        self.botao_sintonizar.setEnabled(not metodo and self.modelo is not None)
        self.botao_exportar.setEnabled(self.resposta is not None)
        self.botao_comparar.setEnabled(self.resposta is not None)

    def _ao_trocar_modo(self):
        self._atualizar_estado()
        if self._modo_metodo():
            self._recalcular_metodo()
        elif self.resposta is None:
            self._publicar("Edite Kp, Ti e Td e clique em Sintonizar.", "neutro")

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
            self._sem_resultado(str(erro), "alerta")
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
            self._sem_resultado("Preencha Kp, Ti e Td com valores numéricos.", "alerta")
            return
        if kp <= 0 or ti <= 0 or td < 0:
            self._sem_resultado("Use Kp > 0, Ti > 0 e Td ≥ 0.", "alerta")
            return
        self._simular(PID(kp, ti, td),
                      f"Sintonia manual: Kp = {kp:.4g}, Ti = {ti:.4g}, Td = {td:.4g}")

    def _simular(self, pid: PID, titulo: str):
        sp = self.campo_sp.valor()
        if sp is None:
            self._sem_resultado("Informe um valor numérico para o SetPoint.", "alerta")
            return
        if sp == self.ds.y0:
            self._sem_resultado("O SetPoint é igual ao valor inicial: não há degrau a simular.", "alerta")
            return
        # A estabilidade é verificada antes de simular (polos da malha fechada).
        if not simulacao.pid_estavel(self.modelo, pid):
            self._sem_resultado("Malha fechada instável para estes parâmetros. "
                                "Reduza Kp ou aumente Ti.", "erro")
            return
        self.pid, self.titulo_base = pid, titulo
        if self.marca_limitar.isChecked():
            self.resposta = simulacao.simular_controle_saturado(
                self.modelo, pid, sp, self.ds.y0, self.ds.u0)
            titulo += "  ·  motor limitado"
        else:
            self.resposta = simulacao.simular_controle(self.modelo, pid, sp, self.ds.y0, self.ds.u0)
        self.titulo = titulo
        q = self.resposta.metricas
        self.campo_tr.definir(q.tr, ".2f")
        self.campo_ts.definir(q.ts, ".2f")
        self.campo_mp.definir(q.mp, ".2f")
        self.campo_pico.definir(q.pico)
        self.campo_erro.definir(round(q.erro_regime, 9) + 0.0, ".3g")
        self.campo_mv.definir(self.resposta.mv_max, ".0f")
        self.campo_mv.marcar_alerta(self.resposta.satura)
        self._redesenhar()
        ok, alerta = self._mensagens()
        definir_aviso(self.rotulo_status, ok, "ok")
        definir_aviso(self.rotulo_alerta, alerta, "alerta")
        self._atualizar_estado()

    def _mensagens(self) -> tuple[str, str]:
        ok = "Malha fechada estável."
        if self._modo_metodo() and self.combo_metodo.currentText() == "IMC":
            lam = self.campo_lambda.valor()
            ts = self.resposta.metricas.ts
            if lam and ts == ts:
                ok += f"  Regra do IMC: ts ≈ 4λ = {4 * lam:.2f} s (simulado {ts:.2f} s)."
        # Motor necessário em regime: vem do ganho do modelo, vale com ou sem limite.
        mv_final = self.ds.u0 + (self.resposta.sp - self.ds.y0) / self.modelo.k
        r = self.resposta
        if not (MV_MIN <= mv_final <= MV_MAX):
            alerta = (f"Este SetPoint exige {mv_final:.0f} % do motor em regime, fora da faixa "
                      f"de {MV_MIN:g} a {MV_MAX:g} %. Não é alcançável na planta real.")
        elif r.limitada:
            no_limite = (r.mv >= MV_MAX) | (r.mv <= MV_MIN)
            tempo = float(no_limite.sum() * (r.t[1] - r.t[0]))
            alerta = (f"Motor limitado a {MV_MIN:g}–{MV_MAX:g} %: ficou {tempo:.1f} s no limite. "
                      "Simulação com atraso exato e anti-windup." if tempo > 0 else "")
        elif self.resposta.satura:
            alerta = (f"O comando passa de {MV_MIN:g}–{MV_MAX:g} % no transitório. "
                      "A simulação não limita o motor; na planta a subida seria mais lenta.")
        else:
            alerta = ""
        return ok, alerta

    def _ressimular(self):
        """Refaz a última simulação válida, por exemplo ao ligar o limite do motor."""
        if self.pid is not None and self.resposta is not None:
            self._simular(self.pid, self.titulo_base)

    def _publicar(self, texto: str, papel: str):
        definir_aviso(self.rotulo_status, texto, papel)
        definir_aviso(self.rotulo_alerta, "", "alerta")

    # ------------------------------------------------------------------ #
    # Gráfico
    # ------------------------------------------------------------------ #
    def _redesenhar(self):
        if self.resposta is None:
            return
        self.grafico.figura.clear()
        ax_pv, ax_mv = self.grafico.figura.subplots(2, 1, sharex=True, height_ratios=[3, 1.2])
        if self.botao_comparar.isChecked():
            titulo = "IMC × ITAE" + ("  ·  motor limitado" if self.resposta.limitada else "")
            graficos.desenhar_comparacao(ax_pv, self._respostas_comparacao(), titulo,
                                         self.ds.unidade, grandeza=self.ds.grandeza, ax_mv=ax_mv)
        else:
            marcar = [chave for chave, marca in self.marcas.items() if marca.isChecked()]
            graficos.desenhar_controle(ax_pv, ax_mv, self.resposta, self.titulo, self.ds.unidade,
                                       marcar, grandeza=self.ds.grandeza)
        self.grafico.atualizar()

    def _respostas_comparacao(self) -> dict:
        """IMC e ITAE com o SetPoint atual e a mesma opção de limite do motor.

        O IMC usa o λ do campo; se ele for inválido, volta para λ = 1,2·θ.
        """
        lam = self.campo_lambda.valor()
        if lam is None or lam / self.modelo.theta <= sintonia.RAZAO_LAMBDA_MINIMA:
            lam = RAZAO_LAMBDA_PADRAO * self.modelo.theta
        simular = (simulacao.simular_controle_saturado if self.resposta.limitada
                   else simulacao.simular_controle)
        sintonias = {f"IMC (λ = {lam:.3g} s)": sintonia.imc(self.modelo, lam),
                     "ITAE": sintonia.itae(self.modelo)}
        return {nome: simular(self.modelo, pid, self.resposta.sp, self.ds.y0, self.ds.u0)
                for nome, pid in sintonias.items()}

    def _sem_resultado(self, mensagem: str, papel: str = "alerta"):
        """Apaga o gráfico e as métricas quando não há uma sintonia válida."""
        self.resposta = None
        for campo in (self.campo_tr, self.campo_ts, self.campo_mp, self.campo_pico,
                      self.campo_erro, self.campo_mv):
            campo.clear()
        self.campo_mv.marcar_alerta(False)
        self.grafico.limpar("A resposta do controle aparece aqui")
        self._publicar(mensagem, papel)
        self._atualizar_estado()

    def _secao(self, texto: str) -> QLabel:
        rotulo = QLabel(texto)
        rotulo.setObjectName("secao")
        return rotulo

    def _rotulo(self, texto: str) -> QLabel:
        rotulo = QLabel(texto)
        rotulo.setObjectName("campo")
        return rotulo

    def _exportar(self):
        if self.resposta is None:
            return
        if self.botao_comparar.isChecked():
            nome = "comparacao_imc_itae"
        else:
            nome = "manual" if not self._modo_metodo() else self.combo_metodo.currentText()
        nome = nome.lower().replace(" ", "_").replace("-", "_")
        caminho = self.grafico.exportar(f"pid_{nome}.png")
        if caminho:
            definir_aviso(self.rotulo_status, f"Gráfico salvo em {caminho}", "ok")
