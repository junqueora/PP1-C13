"""Leitura e validação do conjunto de dados do Ensaio da Curva de Reação."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from src.config import FRACAO_REGIME

# Nomes aceitos para cada sinal dentro do arquivo .mat (comparação sem maiúsculas).
_NOMES_TEMPO = ("t", "tempo", "time")
_NOMES_ENTRADA = ("degrau", "entrada", "u", "step")
_NOMES_SAIDA = ("saida", "saída", "y", "output")


@dataclass(frozen=True)
class Dataset:
    """Ensaio em malha aberta: tempo, entrada (degrau) e saída do processo."""

    t: np.ndarray
    u: np.ndarray
    y: np.ndarray
    unidade: str = ""
    descricao: str = ""
    nome: str = ""
    referencia: dict | None = None   # parâmetros de referência, se o arquivo trouxer

    @property
    def indice_degrau(self) -> int:
        """Índice da primeira amostra em que a entrada muda de valor."""
        mudou = np.nonzero(self.u != self.u[0])[0]
        return int(mudou[0]) if mudou.size else 0

    @property
    def t0(self) -> float:
        """Instante de aplicação do degrau."""
        return float(self.t[self.indice_degrau])

    @property
    def u0(self) -> float:
        """Entrada antes do degrau (zero se o degrau já começa aplicado)."""
        return float(self.u[0]) if self.indice_degrau > 0 else 0.0

    @property
    def u1(self) -> float:
        return float(self.u[-1])

    @property
    def du(self) -> float:
        """Amplitude do degrau (delta u)."""
        return self.u1 - self.u0

    @property
    def y0(self) -> float:
        """Saída inicial: média das amostras anteriores ao degrau."""
        i = self.indice_degrau
        return float(self.y[:i].mean()) if i > 0 else float(self.y[0])

    @property
    def yf(self) -> float:
        """Saída final: média do trecho final, para reduzir o efeito do ruído."""
        n = max(1, int(len(self.y) * FRACAO_REGIME))
        return float(self.y[-n:].mean())

    @property
    def dy(self) -> float:
        """Variação total da saída (delta y)."""
        return self.yf - self.y0


def _buscar(conteudo: dict, nomes: tuple) -> np.ndarray | None:
    for chave, valor in conteudo.items():
        if chave.lower() in nomes:
            return np.asarray(valor, dtype=float).ravel()
    return None


def carregar(caminho) -> Dataset:
    """Lê um arquivo .mat e devolve um Dataset validado.

    Levanta ValueError com uma mensagem legível se o arquivo não servir.
    """
    caminho = Path(caminho)
    try:
        conteudo = loadmat(str(caminho), squeeze_me=True, struct_as_record=False)
    except Exception as erro:
        raise ValueError(f"Não foi possível ler o arquivo: {erro}") from erro

    t = _buscar(conteudo, _NOMES_TEMPO)
    u = _buscar(conteudo, _NOMES_ENTRADA)
    y = _buscar(conteudo, _NOMES_SAIDA)
    if t is None or u is None or y is None:
        raise ValueError("O arquivo precisa conter os vetores de tempo, degrau e saída.")
    if not (len(t) == len(u) == len(y)):
        raise ValueError("Tempo, degrau e saída têm tamanhos diferentes.")
    if len(t) < 20:
        raise ValueError("O conjunto de dados tem amostras de menos.")
    if np.any(np.diff(t) <= 0):
        raise ValueError("O vetor de tempo precisa ser crescente.")
    if not np.all(np.isfinite(np.concatenate([t, u, y]))):
        raise ValueError("O conjunto de dados contém valores inválidos (NaN ou infinito).")

    referencia = None
    parametros = conteudo.get("parametros")
    if parametros is not None and hasattr(parametros, "_fieldnames"):
        referencia = {campo: float(getattr(parametros, campo)) for campo in parametros._fieldnames}

    ds = Dataset(
        t=t, u=u, y=y,
        unidade=str(conteudo.get("unidade_saida", "")).strip(),
        descricao=str(conteudo.get("descricao", "")).strip(),
        nome=caminho.name,
        referencia=referencia,
    )
    if ds.du == 0:
        raise ValueError("A entrada não apresenta um degrau.")
    if ds.dy == 0:
        raise ValueError("A saída não variou após o degrau.")
    return ds
