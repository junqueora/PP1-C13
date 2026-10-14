"""Identificação do processo: Smith, Sundaresan e ajuste fino (itens 1 a 3 da parte prática).

Execute a partir da raiz do projeto:  python scripts/rodar_identificacao.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from src import dataset, graficos, identificacao  # noqa: E402
from src.config import DATASET_PADRAO, PASTA_FIGURAS  # noqa: E402


def main():
    ds = dataset.carregar(DATASET_PADRAO)
    print(f"Dataset: {ds.nome}")
    print(f"Descrição: {ds.descricao}")
    print(f"Degrau de {ds.u0:g} % para {ds.u1:g} % em t = {ds.t0:g} s")
    print(f"Saída de {ds.y0:.4f} para {ds.yf:.4f} {ds.unidade} (Δy = {ds.dy:.4f})\n")

    resultados = identificacao.identificar(ds)
    escolhido = identificacao.melhor(resultados)
    fino = identificacao.ajuste_fino(ds, escolhido.modelo)

    print(f"{'Método':<14}{'k':>10}{'τ (s)':>9}{'θ (s)':>9}{'θ/τ':>8}{'EQM':>10}")
    for r in [*resultados.values(), fino]:
        m = r.modelo
        print(f"{r.metodo:<14}{m.k:>10.5f}{m.tau:>9.3f}{m.theta:>9.3f}"
              f"{m.incontrolabilidade:>8.3f}{r.eqm:>10.5f}")
    if ds.referencia and {"k", "tau", "theta"} <= ds.referencia.keys():
        ref = ds.referencia
        print(f"{'(referência)':<14}{ref['k']:>10.5f}{ref['tau']:>9.3f}{ref['theta']:>9.3f}"
              f"{ref['theta'] / ref['tau']:>8.3f}{'':>10}")
    print(f"\nMenor EQM entre os métodos: {escolhido.metodo}")
    print(f"Modelo escolhido: {escolhido.modelo}")

    PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
    figuras = {
        "01_identificacao.png": graficos.figura_identificacao(
            ds, list(resultados.values()), "Identificação: Smith × Sundaresan", ds.grandeza),
        "02_ajuste_fino.png": graficos.figura_identificacao(
            ds, [escolhido, fino], f"Ajuste fino a partir de {escolhido.metodo}", ds.grandeza),
    }
    for nome, fig in figuras.items():
        fig.savefig(PASTA_FIGURAS / nome, dpi=200)
        print(f"Figura salva: resultados/figuras/{nome}")


if __name__ == "__main__":
    main()
