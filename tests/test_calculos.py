"""Testes dos cálculos com casos de resposta conhecida.

Execute a partir da raiz do projeto:  python -m pytest
"""
import math

import numpy as np
import pytest
from scipy.io import savemat

from src import graficos, identificacao, metricas, simulacao, sintonia
from src.config import DATASET_PADRAO
from src.dataset import Dataset, carregar
from src.modelo import ModeloFOPDT


def dataset_sintetico(k=2.0, tau=10.0, theta=3.0, du=5.0, y0=1.0) -> Dataset:
    """Ensaio sem ruído gerado por um FOPDT conhecido."""
    t = np.arange(0, 120, 0.05)
    t0 = 10.0
    u = np.where(t >= t0, du, 0.0)
    y = y0 + k * du * (1 - np.exp(-np.clip(t - t0 - theta, 0, None) / tau))
    return Dataset(t=t, u=u, y=y, unidade="bar")


@pytest.mark.parametrize("metodo", [identificacao.smith, identificacao.sundaresan])
def test_identificacao_recupera_modelo_sem_ruido(metodo):
    modelo = metodo(dataset_sintetico())
    assert modelo.k == pytest.approx(2.0, rel=1e-3)
    assert modelo.tau == pytest.approx(10.0, abs=0.3)
    assert modelo.theta == pytest.approx(3.0, abs=0.3)


def test_eqm_do_modelo_exato_e_zero():
    ds = dataset_sintetico()
    y = identificacao.resposta_do_modelo(ModeloFOPDT(2.0, 10.0, 3.0), ds)
    assert identificacao.eqm(ds.y, y) == pytest.approx(0.0, abs=1e-9)


def test_dataset_do_grupo():
    ds = carregar(DATASET_PADRAO)
    assert ds.t0 == pytest.approx(5.0)
    assert ds.du == pytest.approx(65.0)
    assert ds.referencia["tau"] == pytest.approx(10.0)
    assert ds.referencia["theta"] == pytest.approx(2.0)
    assert ds.referencia["k"] == pytest.approx(0.01374231, rel=1e-4)
    resultados = identificacao.identificar(ds)
    fino = identificacao.ajuste_fino(ds, identificacao.melhor(resultados).modelo)
    assert fino.eqm <= min(r.eqm for r in resultados.values())


def test_grandeza_vem_da_unidade_ou_fica_saida(tmp_path):
    assert carregar(DATASET_PADRAO).grandeza == "Pressão"   # unidade "bar"
    ds = dataset_sintetico()
    savemat(tmp_path / "sem_unidade.mat", {"t": ds.t, "degrau": ds.u, "saida": ds.y})
    assert carregar(tmp_path / "sem_unidade.mat").grandeza == "Saída"
    savemat(tmp_path / "nivel.mat", {"t": ds.t, "degrau": ds.u, "saida": ds.y,
                                     "unidade_saida": "m", "grandeza_saida": "Nível"})
    assert carregar(tmp_path / "nivel.mat").grandeza == "Nível"


def test_arquivo_invalido(tmp_path):
    ruim = tmp_path / "ruim.mat"
    ruim.write_text("isto não é um .mat")
    with pytest.raises(ValueError):
        carregar(ruim)


def test_formulas_de_sintonia():
    """Valores calculados à mão pelas Tabelas 1 a 6 para k=2, tau=10, theta=2."""
    m = ModeloFOPDT(2.0, 10.0, 2.0)
    zn = sintonia.ziegler_nichols(m)
    assert (zn.kp, zn.ti, zn.td) == pytest.approx((3.0, 4.0, 1.0))
    imc = sintonia.imc(m, lam=4.0)
    assert (imc.kp, imc.ti, imc.td) == pytest.approx((22 / 20, 11.0, 20 / 22))
    chr0 = sintonia.chr_sem_sobrevalor(m)
    assert (chr0.kp, chr0.ti, chr0.td) == pytest.approx((1.5, 10.0, 1.0))
    chr20 = sintonia.chr_com_sobrevalor(m)
    assert (chr20.kp, chr20.ti, chr20.td) == pytest.approx((2.375, 13.57, 0.946))
    cc = sintonia.cohen_coon(m)
    assert cc.kp == pytest.approx(10 / 4 * 166 / 120)
    assert cc.ti == pytest.approx(2 * 33.2 / 14.6)
    assert cc.td == pytest.approx(8 / 11.4)
    itae = sintonia.itae(m)
    assert itae.kp == pytest.approx(0.965 / 2 * 0.2 ** -0.85)
    assert itae.ti == pytest.approx(10 / (0.796 - 0.147 * 0.2))
    assert itae.td == pytest.approx(10 * 0.308 * 0.2 ** 0.929)


def test_imc_rejeita_lambda_pequeno():
    m = ModeloFOPDT(2.0, 10.0, 2.0)
    with pytest.raises(ValueError):
        sintonia.sintonizar("IMC", m, lam=1.0)   # lambda/theta = 0,5


def test_metricas_de_primeira_ordem():
    """Para 1 - exp(-t/tau): tr = tau*ln(9) e ts = tau*ln(50)."""
    tau = 5.0
    t = np.linspace(0, 60, 60001)
    q = metricas.calcular(t, 1 - np.exp(-t / tau), 0.0, 1.0, 1.0)
    assert q.tr == pytest.approx(tau * math.log(9), abs=0.01)
    assert q.ts == pytest.approx(tau * math.log(50), abs=0.01)
    assert q.mp == 0.0


def test_metricas_com_overshoot():
    """Segunda ordem subamortecida: Mp = exp(-pi*zeta/sqrt(1-zeta^2))."""
    zeta, wn = 0.5, 2.0
    t = np.linspace(0, 20, 20001)
    wd = wn * math.sqrt(1 - zeta ** 2)
    y = 1 - np.exp(-zeta * wn * t) * (np.cos(wd * t) + zeta / math.sqrt(1 - zeta ** 2) * np.sin(wd * t))
    q = metricas.calcular(t, y, 0.0, 1.0, 1.0)
    assert q.mp == pytest.approx(100 * math.exp(-math.pi * zeta / math.sqrt(1 - zeta ** 2)), abs=0.05)
    assert q.t_pico == pytest.approx(math.pi / wd, abs=0.01)


def test_malha_fechada_segue_o_setpoint():
    m = ModeloFOPDT(0.0137, 9.6, 2.5)
    r = simulacao.simular_controle(m, sintonia.imc(m, 3.0), sp=1.0, y_inicial=0.12)
    assert r.metricas.valor_final == pytest.approx(1.0)
    assert r.pv[-1] == pytest.approx(1.0, abs=1e-3)
    assert r.mv[-1] == pytest.approx((1.0 - 0.12) / m.k, rel=1e-3)   # MV de regime = Δy / k


def test_ganho_excessivo_e_detectado_como_instavel():
    m = ModeloFOPDT(0.0137, 9.6, 2.5)
    assert simulacao.pid_estavel(m, sintonia.imc(m, 3.0))
    assert not simulacao.pid_estavel(m, sintonia.PID(5000.0, 8.0, 0.0))


def test_saturacao_sem_atingir_o_limite_coincide_com_a_linear():
    """Degrau pequeno a partir de 50 % do motor: a MV nunca encosta nos limites."""
    m = ModeloFOPDT(0.0137, 9.6, 2.5)
    pid = sintonia.imc(m, 3.0)
    linear = simulacao.simular_controle(m, pid, sp=0.81, y_inicial=0.80, u_inicial=50.0)
    limitada = simulacao.simular_controle_saturado(m, pid, sp=0.81, y_inicial=0.80, u_inicial=50.0)
    assert limitada.mv.max() < 100 and limitada.mv.min() > 0
    # Compara as curvas, não o tr: no IMC a resposta fica num patamar em ~90 % e um
    # desvio mínimo muda o instante do cruzamento. A diferença que sobra é Padé x atraso exato.
    depois = linear.t > m.theta + 0.5
    diferenca = np.abs(np.interp(linear.t, limitada.t, limitada.pv) - linear.pv)[depois]
    assert diferenca.max() < 0.05 * (0.81 - 0.80)
    assert limitada.metricas.ts == pytest.approx(linear.metricas.ts, abs=0.3)


def test_saturacao_limita_o_motor_e_deixa_a_subida_mais_lenta():
    m = ModeloFOPDT(0.0137, 9.6, 2.5)
    pid = sintonia.imc(m, 3.0)
    linear = simulacao.simular_controle(m, pid, sp=1.0, y_inicial=0.12)
    limitada = simulacao.simular_controle_saturado(m, pid, sp=1.0, y_inicial=0.12)
    assert linear.mv.max() > 100
    assert limitada.mv.max() == pytest.approx(100.0) and limitada.mv.min() >= 0.0
    assert limitada.pv[-1] == pytest.approx(1.0, abs=1e-3)
    assert limitada.metricas.tr > linear.metricas.tr


@pytest.mark.parametrize("td", [0.0, 0.001, 0.01, 0.04])
def test_saturacao_com_derivada_pequena_nao_diverge(td):
    """Td pequeno deixa o filtro da derivada muito rápido em relação ao passo dt."""
    m = ModeloFOPDT(0.0137, 9.6, 2.5)
    r = simulacao.simular_controle_saturado(m, sintonia.PID(50.0, 10.0, td), sp=1.0, y_inicial=0.12)
    assert np.all(np.isfinite(r.pv))
    assert r.pv[-1] == pytest.approx(1.0, abs=1e-3)


def test_setpoint_inalcancavel_para_no_limite_do_motor():
    m = ModeloFOPDT(0.0137, 9.6, 2.5)
    r = simulacao.simular_controle_saturado(m, sintonia.imc(m, 3.0), sp=2.0, y_inicial=0.12)
    teto = 0.12 + m.k * 100.0
    assert r.metricas.valor_final == pytest.approx(teto)
    assert r.pv[-1] == pytest.approx(teto, abs=1e-3)


@pytest.mark.parametrize("marcar, esperados", [
    (("tr", "ts", "mp"), ["Subida", "Acomodação", "Pico"]),
    (("ts",), ["Acomodação"]),
    ((), []),
])
def test_rotulos_so_aparecem_nos_pontos_marcados(marcar, esperados):
    m = ModeloFOPDT(0.0137, 9.6, 2.5)
    r = simulacao.simular_controle(m, sintonia.itae(m), sp=1.0, y_inicial=0.12)
    fig = graficos.figura_controle(r, "", "bar", marcar)
    textos = [filho.get_text() for filho in fig.axes[0].texts
              if not filho.get_text().startswith("ondulação")]
    assert [t.split(":")[0] for t in textos] == esperados
    if "mp" in marcar:
        assert textos[-1].startswith("Pico: ") and "bar / Overshoot: " in textos[-1]


def test_nota_do_pade_so_aparece_na_simulacao_com_pade():
    m = ModeloFOPDT(0.0137, 9.6, 2.5)
    pid = sintonia.imc(m, 3.0)
    for simular, tem_nota in ((simulacao.simular_controle, True),
                              (simulacao.simular_controle_saturado, False)):
        fig = graficos.figura_controle(simular(m, pid, sp=1.0, y_inicial=0.12), "", "bar", ())
        notas = [t for t in fig.axes[0].texts if "Padé" in t.get_text()]
        assert bool(notas) == tem_nota
