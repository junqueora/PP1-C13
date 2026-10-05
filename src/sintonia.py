"""Regras de sintonia do PID (Seção 7 do enunciado) e função de transferência do controlador."""
from __future__ import annotations

from dataclasses import dataclass

import control as ct

from src.config import N_FILTRO_DERIVADA
from src.modelo import ModeloFOPDT

RAZAO_LAMBDA_MINIMA = 0.8   # critério de desempenho do IMC: lambda/theta > 0,8


@dataclass(frozen=True)
class PID:
    """PID(s) = Kp * (1 + 1/(Ti*s) + Td*s)."""

    kp: float
    ti: float
    td: float


def ziegler_nichols(m: ModeloFOPDT) -> PID:
    """Técnica 1: Ziegler-Nichols malha aberta (curva de reação)."""
    return PID(1.2 * m.tau / (m.k * m.theta), 2 * m.theta, m.theta / 2)


def imc(m: ModeloFOPDT, lam: float) -> PID:
    """Técnica 2: Modelo Interno. `lam` (lambda) ajusta a velocidade da malha."""
    kp = (2 * m.tau + m.theta) / (m.k * (2 * lam + m.theta))
    ti = m.tau + m.theta / 2
    td = m.tau * m.theta / (2 * m.tau + m.theta)
    return PID(kp, ti, td)


def chr_sem_sobrevalor(m: ModeloFOPDT) -> PID:
    """Técnica 3: CHR, resposta mais rápida sem overshoot."""
    return PID(0.6 * m.tau / (m.k * m.theta), m.tau, m.theta / 2)


def chr_com_sobrevalor(m: ModeloFOPDT) -> PID:
    """Técnica 4: CHR, resposta mais rápida com 20 % de overshoot."""
    return PID(0.95 * m.tau / (m.k * m.theta), 1.357 * m.tau, 0.473 * m.theta)


def cohen_coon(m: ModeloFOPDT) -> PID:
    """Técnica 5: Cohen e Coon."""
    r = m.theta / m.tau
    kp = m.tau / (m.k * m.theta) * (16 * m.tau + 3 * m.theta) / (12 * m.tau)
    ti = m.theta * (32 + 6 * r) / (13 + 8 * r)
    td = 4 * m.theta / (11 + 2 * r)
    return PID(kp, ti, td)


def itae(m: ModeloFOPDT) -> PID:
    """Técnica 6: ITAE, com as constantes A..F do enunciado."""
    a, b, c, d, e, f = 0.965, -0.85, 0.796, -0.147, 0.308, 0.929
    r = m.theta / m.tau
    return PID(a / m.k * r ** b, m.tau / (c + d * r), m.tau * e * r ** f)


# Métodos sem parâmetro livre, pelo nome mostrado na interface. O IMC fica à parte
# porque depende de lambda.
METODOS = {
    "Ziegler-Nichols": ziegler_nichols,
    "CHR sem sobrevalor": chr_sem_sobrevalor,
    "CHR com sobrevalor": chr_com_sobrevalor,
    "Cohen e Coon": cohen_coon,
    "ITAE": itae,
}


def sintonizar(metodo: str, m: ModeloFOPDT, lam: float | None = None) -> PID:
    """Calcula o PID pelo nome do método. O IMC exige `lam`."""
    if m.theta <= 0:
        raise ValueError("As regras de sintonia exigem atraso de transporte maior que zero.")
    if metodo == "IMC":
        if lam is None:
            raise ValueError("Informe o valor de λ para o método IMC.")
        if lam / m.theta <= RAZAO_LAMBDA_MINIMA:
            minimo = RAZAO_LAMBDA_MINIMA * m.theta
            raise ValueError(f"λ deve ser maior que {minimo:.4g} (critério λ/θ > 0,8).")
        return imc(m, lam)
    if metodo not in METODOS:
        raise ValueError(f"Método de sintonia desconhecido: {metodo}")
    return METODOS[metodo](m)


def ft_pid(pid: PID, n: float = N_FILTRO_DERIVADA) -> ct.TransferFunction:
    """Função de transferência do PID com filtro na ação derivativa.

    A derivada pura (Td*s) não é realizável nem simulável, então usa-se
    Td*s / (Td/N*s + 1). Com Td = 0 o controlador vira um PI.
    """
    if pid.ti <= 0:
        raise ValueError("Ti deve ser maior que zero.")
    if pid.td < 0:
        raise ValueError("Td não pode ser negativo.")
    acao = 1 + ct.tf([1], [pid.ti, 0])
    if pid.td > 0:
        acao = acao + ct.tf([pid.td, 0], [pid.td / n, 1])
    return pid.kp * acao
