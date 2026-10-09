"""Malha aberta × fechada e sintonia do PID por IMC e ITAE (itens 4 a 6 da parte prática).

Execute a partir da raiz do projeto:  python scripts/rodar_sintonia.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from src import dataset, graficos, identificacao, modelo, simulacao, sintonia  # noqa: E402
from src.config import (DATASET_PADRAO, METODOS_GRUPO, PASTA_FIGURAS,  # noqa: E402
                        RAZAO_LAMBDA_PADRAO)

TECNICAS = ["Ziegler-Nichols", "IMC", "CHR sem sobrevalor", "CHR com sobrevalor",
            "Cohen e Coon", "ITAE"]   # na ordem da Tabela 8


def salvar(fig, nome):
    PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
    fig.savefig(PASTA_FIGURAS / nome, dpi=200)
    print(f"Figura salva: resultados/figuras/{nome}")


def malhas_sem_controlador(m):
    """Item 4: resposta em malha aberta e em malha fechada com realimentação unitária."""
    processo = modelo.ft_processo(m)
    fechada = modelo.malha_fechada(processo)
    t_final = 6 * (m.tau + m.theta)
    ganho_fechada = m.k / (1 + m.k)
    curvas = {}
    print(f"\n{'Malha':<10}{'tr (s)':>9}{'ts (s)':>9}{'Valor final':>13}{'Erro regime':>13}")
    for nome, sistema, ganho in [("Aberta", processo, m.k), ("Fechada", fechada, ganho_fechada)]:
        t, y, q = simulacao.simular_malha(sistema, ganho, t_final)
        curvas[f"Malha {nome.lower()} (valor final = {q.valor_final:.5f})"] = (t, y)
        print(f"{nome:<10}{q.tr:>9.2f}{q.ts:>9.2f}{q.valor_final:>13.5f}{q.erro_regime:>13.5f}")
    fig = graficos.figura_malhas(curvas, "Resposta ao degrau unitário, sem controlador")
    salvar(fig, "03_malha_aberta_fechada.png")


def efeito_do_ajuste_fino(ds, base, fino):
    """Item 3: recalcula IMC e ITAE no modelo refinado, no mesmo degrau de SetPoint.

    Cada modelo usa λ = 1,2·θ do próprio atraso, que é a mesma regra da sintonia principal.
    """
    print("\nEfeito do ajuste fino na sintonia (λ = 1,2·θ de cada modelo)")
    print(f"{'Modelo':<14}{'Método':<8}{'λ (s)':>8}{'Kp':>9}{'tr (s)':>9}{'ts (s)':>9}{'Mp (%)':>9}")
    curvas = {}
    for rotulo, m in (("Smith", base), ("Ajuste fino", fino)):
        lam = RAZAO_LAMBDA_PADRAO * m.theta
        for nome in METODOS_GRUPO:
            pid = sintonia.sintonizar(nome, m, lam)
            r = simulacao.simular_controle(m, pid, ds.yf, ds.y0, ds.u0)
            q = r.metricas
            print(f"{rotulo:<14}{nome:<8}{lam:>8.3f}{pid.kp:>9.2f}{q.tr:>9.2f}{q.ts:>9.2f}{q.mp:>9.2f}")
            curvas[f"{nome}, {rotulo}"] = r
    salvar(graficos.figura_comparacao(
        curvas, "Smith × ajuste fino", ds.unidade, t_max=40, grandeza=ds.grandeza),
        "09_sintonia_ajuste_fino.png")


def main():
    ds = dataset.carregar(DATASET_PADRAO)
    resultados = identificacao.identificar(ds)
    escolhido = identificacao.melhor(resultados)
    fino = identificacao.ajuste_fino(ds, escolhido.modelo)
    m = escolhido.modelo
    lam = RAZAO_LAMBDA_PADRAO * m.theta
    print(f"Modelo: {m}")
    print(f"λ do IMC: {lam:.3g} s (λ/θ = {RAZAO_LAMBDA_PADRAO})")

    malhas_sem_controlador(m)

    # Itens 5 e 6: degrau de SetPoint igual ao do ensaio (de y0 até yf).
    print(f"\nDegrau de SetPoint: {ds.y0:.3f} → {ds.yf:.3f} {ds.unidade}")
    print(f"{'Método':<20}{'Kp':>9}{'Ti':>8}{'Td':>8}{'tr (s)':>9}{'ts (s)':>9}{'Mp (%)':>9}")
    respostas, linhas_csv = {}, []
    for tecnica, nome in enumerate(TECNICAS, start=1):
        pid = sintonia.sintonizar(nome, m, lam)
        r = simulacao.simular_controle(m, pid, ds.yf, ds.y0, ds.u0)
        q = r.metricas
        marca = " *" if nome in METODOS_GRUPO else ""
        print(f"{nome + marca:<20}{pid.kp:>9.2f}{pid.ti:>8.3f}{pid.td:>8.3f}"
              f"{q.tr:>9.2f}{q.ts:>9.2f}{q.mp:>9.2f}")
        linhas_csv.append([tecnica, nome, "sim" if marca else "não", f"{pid.kp:.4f}",
                           f"{pid.ti:.4f}", f"{pid.td:.4f}", f"{q.tr:.3f}", f"{q.ts:.3f}",
                           f"{q.mp:.3f}"])
        if nome in METODOS_GRUPO:
            respostas[nome] = r
    print("* métodos do Grupo 3")

    tabela = PASTA_FIGURAS.parent / "sintonia.csv"
    with open(tabela, "w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["tecnica", "metodo", "grupo3", "Kp", "Ti", "Td", "tr_s", "ts_s", "Mp_pct"])
        escritor.writerows(linhas_csv)
    print("Tabela salva: resultados/sintonia.csv")

    salvar(graficos.figura_controle(respostas["IMC"], f"Controle PID por IMC (λ = {lam:.3g} s)",
                                    ds.unidade, grandeza=ds.grandeza), "04_pid_imc.png")
    salvar(graficos.figura_controle(respostas["ITAE"], "Controle PID por ITAE",
                                    ds.unidade, grandeza=ds.grandeza), "05_pid_itae.png")
    rotulados = {f"IMC (λ = {lam:.3g} s)": respostas["IMC"], "ITAE": respostas["ITAE"]}
    salvar(graficos.figura_comparacao(rotulados, "IMC × ITAE", ds.unidade, t_max=40,
                                      grandeza=ds.grandeza), "06_comparacao_imc_itae.png")

    # Efeito de lambda no IMC.
    varredura = {}
    for razao in (0.85, 1.0, 1.2, 1.5, 2.0):
        pid = sintonia.imc(m, razao * m.theta)
        varredura[f"λ/θ = {razao:g}"] = simulacao.simular_controle(m, pid, ds.yf, ds.y0, ds.u0)
    salvar(graficos.figura_comparacao(varredura, "IMC: efeito de λ", ds.unidade, t_max=40,
                                      grandeza=ds.grandeza), "07_imc_efeito_lambda.png")
    print(f"\nRegra do IMC: ts ≈ 4λ = {4 * lam:.2f} s "
          f"(ts simulado = {respostas['IMC'].metricas.ts:.2f} s)")
    efeito_do_ajuste_fino(ds, m, fino.modelo)


if __name__ == "__main__":
    main()
