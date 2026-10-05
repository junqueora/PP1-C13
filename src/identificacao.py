"""Identificação do modelo FOPDT pelos métodos de Smith e Sundaresan."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from src.config import JANELA_SUAVIZACAO
from src.dataset import Dataset
from src.modelo import ModeloFOPDT


@dataclass(frozen=True)
class Identificacao:
    """Resultado de um método: modelo, erro e resposta estimada."""

    metodo: str
    modelo: ModeloFOPDT
    eqm: float
    y_modelo: np.ndarray


def suavizar(y: np.ndarray, janela: int = JANELA_SUAVIZACAO) -> np.ndarray:
    """Média móvel centrada (não desloca o sinal no tempo)."""
    if janela <= 1:
        return y.copy()
    metade = janela // 2
    estendido = np.pad(y, metade, mode="edge")
    return np.convolve(estendido, np.ones(janela) / janela, mode="valid")[: len(y)]


def tempo_de_cruzamento(ds: Dataset, fracao: float, janela: int = JANELA_SUAVIZACAO) -> float:
    """Tempo, contado a partir do degrau, em que a saída atinge `fracao` de delta y."""
    normalizada = (suavizar(ds.y, janela) - ds.y0) / ds.dy
    depois = np.nonzero((ds.t > ds.t0) & (normalizada >= fracao))[0]
    if depois.size == 0:
        raise ValueError(f"A saída não atinge {fracao:.1%} da variação total.")
    return float(ds.t[depois[0]] - ds.t0)


def ganho(ds: Dataset) -> float:
    """Ganho estático k = delta y / delta u."""
    return ds.dy / ds.du


def smith(ds: Dataset) -> ModeloFOPDT:
    """Smith: pontos de 28,3 % e 63,2 %."""
    t1 = tempo_de_cruzamento(ds, 0.283)
    t2 = tempo_de_cruzamento(ds, 0.632)
    tau = 1.5 * (t2 - t1)
    theta = t2 - tau
    return ModeloFOPDT(ganho(ds), tau, max(theta, 0.0))


def sundaresan(ds: Dataset) -> ModeloFOPDT:
    """Sundaresan: pontos de 35,3 % e 85,3 %."""
    t1 = tempo_de_cruzamento(ds, 0.353)
    t2 = tempo_de_cruzamento(ds, 0.853)
    tau = (2.0 / 3.0) * (t2 - t1)
    theta = 1.3 * t1 - 0.29 * t2
    return ModeloFOPDT(ganho(ds), tau, max(theta, 0.0))


def resposta_do_modelo(modelo: ModeloFOPDT, ds: Dataset) -> np.ndarray:
    """Saída do modelo para o mesmo degrau do ensaio.

    Usa a solução analítica do FOPDT, que trata o atraso de forma exata:
    y(t) = y0 + k*du*(1 - exp(-(t - t0 - theta)/tau)) para t >= t0 + theta.
    """
    atrasado = ds.t - ds.t0 - modelo.theta
    subida = 1.0 - np.exp(-np.clip(atrasado, 0.0, None) / modelo.tau)
    return ds.y0 + modelo.k * ds.du * subida


def eqm(y: np.ndarray, y_modelo: np.ndarray) -> float:
    """Erro Quadrático Médio (RMSE) entre os dados e o modelo."""
    return float(np.sqrt(np.mean((y_modelo - y) ** 2)))


def avaliar(metodo: str, modelo: ModeloFOPDT, ds: Dataset) -> Identificacao:
    y_modelo = resposta_do_modelo(modelo, ds)
    return Identificacao(metodo, modelo, eqm(ds.y, y_modelo), y_modelo)


def identificar(ds: Dataset) -> dict[str, Identificacao]:
    """Aplica os dois métodos e devolve os resultados pelo nome."""
    return {
        "Smith": avaliar("Smith", smith(ds), ds),
        "Sundaresan": avaliar("Sundaresan", sundaresan(ds), ds),
    }


def melhor(resultados: dict[str, Identificacao]) -> Identificacao:
    """Método com o menor EQM."""
    return min(resultados.values(), key=lambda r: r.eqm)


def ajuste_fino(ds: Dataset, inicial: ModeloFOPDT) -> Identificacao:
    """Refina k, tau e theta minimizando o EQM a partir de um modelo inicial."""

    def custo(p):
        k, tau, theta = p
        if tau <= 0 or theta < 0:
            return 1e9
        return eqm(ds.y, resposta_do_modelo(ModeloFOPDT(k, tau, theta), ds))

    otimo = minimize(custo, [inicial.k, inicial.tau, inicial.theta], method="Nelder-Mead",
                     options={"xatol": 1e-6, "fatol": 1e-10})
    return avaliar("Ajuste fino", ModeloFOPDT(*map(float, otimo.x)), ds)
