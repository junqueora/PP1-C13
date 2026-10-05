"""Modelo FOPDT e montagem das malhas com a biblioteca control."""
from __future__ import annotations

from dataclasses import dataclass

import control as ct
import numpy as np

from src.config import ORDEM_PADE


@dataclass(frozen=True)
class ModeloFOPDT:
    """Primeira ordem com atraso: G(s) = k / (tau*s + 1) * exp(-theta*s)."""

    k: float
    tau: float
    theta: float

    @property
    def incontrolabilidade(self) -> float:
        """Fator de incontrolabilidade theta/tau."""
        return self.theta / self.tau

    def __str__(self) -> str:
        return f"G(s) = {self.k:.5g} / ({self.tau:.4g}s + 1) · e^(-{self.theta:.4g}s)"


def ft_processo(modelo: ModeloFOPDT, ordem_pade: int = ORDEM_PADE) -> ct.TransferFunction:
    """Processo com o atraso aproximado por Padé (o control não tem InputDelay)."""
    sem_atraso = ct.tf([modelo.k], [modelo.tau, 1])
    if modelo.theta <= 0:
        return sem_atraso
    num, den = ct.pade(modelo.theta, ordem_pade)
    return ct.series(ct.tf(num, den), sem_atraso)


def malha_fechada(processo, controlador=None) -> ct.TransferFunction:
    """PV(s)/SP(s) com realimentação unitária negativa."""
    direto = processo if controlador is None else ct.series(controlador, processo)
    return ct.feedback(direto, 1)


def malha_do_controle(processo, controlador) -> ct.TransferFunction:
    """MV(s)/SP(s): sinal que o controlador envia ao atuador."""
    return ct.feedback(controlador, processo)


def estavel(sistema) -> bool:
    """Um sistema é estável se todos os polos têm parte real negativa."""
    return bool(np.all(np.real(ct.poles(sistema)) < 0))


def horizonte(sistema, minimo: float) -> float:
    """Tempo de simulação suficiente para o polo mais lento acomodar."""
    reais = np.abs(np.real(ct.poles(sistema)))
    reais = reais[reais > 1e-9]
    if reais.size == 0:
        return minimo
    return float(np.clip(8.0 / reais.min(), minimo, 50 * minimo))


def resposta_degrau(sistema, t_final: float, pontos: int = 4001):
    """Resposta a um degrau unitário. Devolve (t, y)."""
    t = np.linspace(0.0, t_final, pontos)
    t, y = ct.step_response(sistema, t)
    return t, np.asarray(y).ravel()
