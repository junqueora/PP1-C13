"""Simulação da malha fechada com PID e das malhas sem controlador."""
from __future__ import annotations

from dataclasses import dataclass

import control as ct
import numpy as np

from src import metricas, modelo as mod, sintonia
from src.config import MV_MAX, MV_MIN
from src.metricas import Metricas
from src.modelo import ModeloFOPDT
from src.sintonia import PID


@dataclass(frozen=True)
class RespostaControle:
    """Resposta da malha fechada a um degrau de SetPoint."""

    t: np.ndarray
    pv: np.ndarray       # variável controlada (saída do processo)
    mv: np.ndarray       # variável manipulada (saída do controlador)
    sp: float
    y_inicial: float
    metricas: Metricas

    @property
    def mv_max(self) -> float:
        return float(self.mv.max())

    @property
    def mv_min(self) -> float:
        return float(self.mv.min())

    @property
    def satura(self) -> bool:
        """Indica se o sinal de controle sai da faixa física do atuador."""
        return self.mv_max > MV_MAX or self.mv_min < MV_MIN


def malha_com_pid(m: ModeloFOPDT, pid: PID):
    """Devolve (PV/SP, MV/SP) para o processo com o controlador PID."""
    processo = mod.ft_processo(m)
    controlador = sintonia.ft_pid(pid)
    return mod.malha_fechada(processo, controlador), mod.malha_do_controle(processo, controlador)


def pid_estavel(m: ModeloFOPDT, pid: PID) -> bool:
    """Verifica a estabilidade da malha fechada antes de simular."""
    pv_sp, _ = malha_com_pid(m, pid)
    return mod.estavel(pv_sp)


def simular_controle(m: ModeloFOPDT, pid: PID, sp: float, y_inicial: float,
                     u_inicial: float = 0.0, t_final: float | None = None) -> RespostaControle:
    """Simula um degrau de SetPoint de `y_inicial` até `sp`.

    O sistema é linear, então a resposta ao degrau unitário é escalada pela
    variação do SetPoint e somada ao ponto de operação inicial.
    """
    pv_sp, mv_sp = malha_com_pid(m, pid)
    if not mod.estavel(pv_sp):
        raise ValueError("Malha fechada instável para estes parâmetros.")
    if t_final is None:
        t_final = mod.horizonte(pv_sp, minimo=6 * (m.tau + m.theta))
    degrau = sp - y_inicial
    t, pv_unitario = mod.resposta_degrau(pv_sp, t_final)
    _, mv_unitario = mod.resposta_degrau(mv_sp, t_final)
    pv = y_inicial + degrau * pv_unitario
    mv = u_inicial + degrau * mv_unitario
    valor_final = y_inicial + degrau * float(np.real(ct.dcgain(pv_sp)))
    medidas = metricas.calcular(t, pv, y_inicial, sp, valor_final)
    return RespostaControle(t, pv, mv, sp, y_inicial, medidas)


def simular_malha(sistema, ganho_final: float, t_final: float):
    """Resposta ao degrau unitário de uma malha qualquer, com suas métricas.

    `ganho_final` é o valor de regime esperado (ganho estático do sistema).
    """
    t, y = mod.resposta_degrau(sistema, t_final)
    return t, y, metricas.calcular(t, y, 0.0, 1.0, ganho_final)
