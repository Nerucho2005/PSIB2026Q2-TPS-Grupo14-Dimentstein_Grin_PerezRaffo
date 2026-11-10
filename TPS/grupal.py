# grupal.py
# Análisis GRUPAL: junta los CSV que main.py dejó en results/ para cada sujeto y
# resume el objetivo del trabajo a nivel de grupo:
#   - ganancia de SNR de cada promedio inhomogéneo (n, s, sn) respecto del homogéneo,
#     por sujeto (IC 95 % por jackknife dentro del registro) y en el grupo (media con
#     IC 95 % t de Student entre sujetos y prueba de rangos con signo de Wilcoxon, que
#     no supone normalidad con N chico);
#   - curvas SNR vs. N de todos los sujetos y su pendiente (teórica: 10 dB/década);
#   - latencia del N20 de cada sujeto frente al paper (Nierula et al. 2024) y la IFCN.
# No recalcula nada del pipeline: solo lee resultados. Antes hay que correr main.py con
# cada sujeto (config.SUJETO / config.RUN).
#
# Salidas en informe/figuras/: 11_grupal_ganancia, 12_grupal_curvas, 13_grupal_n20
# (PNG + PDF), grupal_sujetos.csv y grupal_resumen.csv.
#
# Ejecutar desde la raíz del repo:   python TPS/grupal.py
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

import config as cfg
from filtrado import nombre_referencia
from graficos import (COLOR_METODO, METODOS, NOMBRE_METODO, _ejes_coma, _leyenda_figura,
                      _ticks_n, estilo, fmt, guardar)
from teoria import COMPONENTES

# Sujetos que se informan aparte en el análisis de sensibilidad. sub-009: las primeras
# ~100 épocas son muy ruidosas, el N20 es débil (-0,7 µV) y no pasa la reproducibilidad
# IFCN, así que su latencia no es confiable (se excluye de la figura 13).
SUJETOS_SENSIBILIDAD = ["009"]


def _sufijo_config():
    ref = nombre_referencia(cfg.REFERENCIA)
    return f"{cfg.CANAL}-{ref}_{cfg.F_BAJO:g}-{cfg.F_ALTO:g}Hz"


def sujetos_disponibles(carpeta=None, sufijo=None):
    """Sujetos con todos los CSV de main.py para la configuración actual."""
    carpeta, sufijo = carpeta or cfg.DIR_RESULTADOS, sufijo or _sufijo_config()
    patron = re.compile(rf"snr_sub-(\d+)_{re.escape(sufijo)}\.csv$")
    sujetos = sorted(m.group(1) for f in carpeta.glob("snr_sub-*.csv") if (m := patron.match(f.name)))
    necesarios = ("diferencia_metodos_{}.csv", "curva_snr_{}.csv",
                  "componentes_{}_homogeneo.csv", "reproducibilidad_{}.csv")
    completos = []
    for s in sujetos:
        base = f"sub-{s}_{sufijo}"
        faltan = [n.format(base) for n in necesarios if not (carpeta / n.format(base)).is_file()]
        if faltan:
            print(f"  sub-{s}: faltan {faltan}, se omite")
        else:
            completos.append(s)
    return completos


def leer_sujeto(s, carpeta=None, sufijo=None):
    """Una fila con los resultados de un sujeto, y su curva SNR vs. N (DataFrame)."""
    carpeta, sufijo = carpeta or cfg.DIR_RESULTADOS, sufijo or _sufijo_config()
    base = f"sub-{s}_{sufijo}"
    snr = pd.read_csv(carpeta / f"snr_{base}.csv").set_index("metodo")
    dif = pd.read_csv(carpeta / f"diferencia_metodos_{base}.csv").set_index("comparacion")
    curva = pd.read_csv(carpeta / f"curva_snr_{base}.csv")
    comp = pd.read_csv(carpeta / f"componentes_{base}_homogeneo.csv").set_index("componente")
    rep = pd.read_csv(carpeta / f"reproducibilidad_{base}.csv").iloc[0]
    pend = curva.groupby("metodo")[["pendiente_db_decada", "se_pendiente"]].first()

    fila = {"sujeto": s}
    for m in METODOS:
        fila[f"snr_{m}_db"] = snr.loc[m, "snr_db"]
        fila[f"se_{m}_db"] = snr.loc[m, "se_db"]
    for m in METODOS[1:]:
        d = dif.loc[f"{m} - homogeneo"]
        fila.update({f"dif_{m}_db": d["dif_db"], f"ic_inf_{m}": d["ic95_inf"],
                     f"ic_sup_{m}": d["ic95_sup"], f"sig_{m}": bool(d["significativa"])})
    for m in METODOS:
        fila[f"pendiente_{m}"] = pend.loc[m, "pendiente_db_decada"] if m in pend.index else np.nan
    fila["snr_paper_homogeneo_db"] = snr.loc["homogeneo", "snr_paper_db"]
    n20 = comp.loc["N20"]
    fila.update({"N20_lat_ms": n20["lat_ms"], "N20_amp_uV": n20["amp_uV"],
                 "N20_valido": bool(n20["valido"]),
                 "N20_P25_pp_uV": comp.loc["N20-P25 (pico a pico)", "amp_uV"],
                 "rep_dif_lat_ms": rep["dif_lat_ms"], "rep_dif_amp_rel": rep["dif_amp_rel"],
                 "rep_cumple": bool(rep["cumple_lat"] and rep["cumple_amp"])})
    curva = curva[curva["metodo"].isin(METODOS)].assign(sujeto=s)
    return fila, curva


def resumen(x):
    """Media, IC 95 % t, mediana, n.º de positivos y Wilcoxon (bilateral) de un vector."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    media = x.mean()
    se = x.std(ddof=1) / np.sqrt(n)
    t = stats.t.ppf(0.975, n - 1)
    p_w = stats.wilcoxon(x).pvalue if n >= 5 and np.any(x != 0) else np.nan
    return dict(n=n, media=media, ic95_inf=media - t * se, ic95_sup=media + t * se,
                mediana=np.median(x), sd=x.std(ddof=1), positivos=int((x > 0).sum()),
                p_wilcoxon=p_w, p_t=stats.ttest_1samp(x, 0).pvalue)


# --------------------------------------------------------------------------
# Figuras
# --------------------------------------------------------------------------
def fig_ganancia(tabla, res):
    """11. Ganancia de cada inhomogéneo por sujeto (IC jackknife) y media grupal (IC t)."""
    fig, ax = plt.subplots(figsize=(6.3, 3.2))
    sujetos = tabla["sujeto"].tolist()
    x = np.arange(len(sujetos))
    for k, m in enumerate(METODOS[1:]):
        dx = (k - 1) * 0.25
        d = tabla[f"dif_{m}_db"].to_numpy()
        lo, hi = tabla[f"ic_inf_{m}"].to_numpy(), tabla[f"ic_sup_{m}"].to_numpy()
        ax.errorbar(x + dx, d, yerr=[d - lo, hi - d], fmt="o", ms=3.5, capsize=2, lw=0.8,
                    color=COLOR_METODO[m], label=NOMBRE_METODO[m])
        sig = tabla[f"sig_{m}"].to_numpy()
        ax.plot(x[sig] + dx, d[sig], "o", ms=7, mfc="none", mec="k", mew=0.8)
        r = res[m]
        xg = len(sujetos) + 0.6 + dx
        ax.errorbar(xg, r["media"], yerr=[[r["media"] - r["ic95_inf"]], [r["ic95_sup"] - r["media"]]],
                    fmt="D", ms=5, capsize=3, lw=1.4, color=COLOR_METODO[m])
    ax.plot([], [], "o", ms=7, mfc="none", mec="k", mew=0.8, label="IC 95 % que excluye el 0")
    ax.axhline(0, color="k", lw=0.8)
    ax.axvline(len(sujetos) - 0.2, color="0.6", lw=0.6, ls=":")
    ax.set_xticks(list(x) + [len(sujetos) + 0.6])
    ax.set_xticklabels([f"{s}" for s in sujetos] + ["Grupo"])
    ax.set(xlabel="Sujeto", ylabel="SNR inhomogéneo − homogéneo (dB)",
           title="Ganancia del promedio inhomogéneo por sujeto y en el grupo")
    rn = res["n"]
    ax.text(0.01, 0.97, f"n: media {fmt(rn['media'], 2)} dB [{fmt(rn['ic95_inf'], 2)}; "
                        f"{fmt(rn['ic95_sup'], 2)}], {rn['positivos']}/{rn['n']} positivos, "
                        f"Wilcoxon p = {fmt(rn['p_wilcoxon'], 3)}",
            transform=ax.transAxes, va="top", fontsize=6.5,
            bbox=dict(boxstyle="round", fc="white", ec="0.8", alpha=0.9))
    ax.grid(axis="x", alpha=0)
    _ejes_coma(ax, x=False)
    _leyenda_figura(fig, ax, ncol=4, alto=0.12)
    return fig


def fig_curvas_grupo(curvas, tabla):
    """12. (a) SNR del homogéneo vs. N de cada sujeto y media grupal; (b) pendiente de
    cada método por sujeto, con la teórica (10 dB/década)."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.3, 3.0), gridspec_kw=dict(width_ratios=(1.3, 1)))
    h = curvas[curvas["metodo"] == "homogeneo"]
    for s, c in h.groupby("sujeto"):
        a1.plot(c["N"], c["snr_db"], color="0.75", lw=0.7)
    a1.plot([], [], color="0.75", lw=0.7, label="Cada sujeto (homogéneo)")
    for m, ls in (("homogeneo", "-"), ("n", "--")):
        g = curvas[curvas["metodo"] == m].groupby("N")["snr_db"]
        media, se = g.mean(), g.std(ddof=1) / np.sqrt(g.count())
        a1.errorbar(media.index, media, yerr=1.96 * se, fmt="o" + ls, ms=3, capsize=2, lw=1.2,
                    color=COLOR_METODO[m], label=f"Media del grupo — {NOMBRE_METODO[m]}")
    n = np.array(sorted(h["N"].unique()), float)
    media_h = curvas[curvas["metodo"] == "homogeneo"].groupby("N")["snr_db"].mean()
    ancla = np.mean(media_h.to_numpy() - 10 * np.log10(n))
    a1.plot(n, ancla + 10 * np.log10(n), "k:", lw=1, label="+10·log₁₀(N) (teórica)")
    a1.set(xlabel="N épocas promediadas", ylabel="SNR (dB)", title="SNR vs. N")
    _ticks_n(a1, n.astype(int))
    _ejes_coma(a1, x=False)
    for k, m in enumerate(METODOS):
        p = tabla[f"pendiente_{m}"].to_numpy()
        jit = np.linspace(-0.12, 0.12, len(p))
        a2.plot(k + jit, p, "o", ms=3, color=COLOR_METODO[m], alpha=0.8)
        a2.plot([k - 0.25, k + 0.25], [np.median(p)] * 2, color="k", lw=1.2)
    a2.axhline(10, color="k", lw=0.8, ls=":")
    a2.set_xticks(range(len(METODOS)))
    a2.set_xticklabels(["Hom.", "n", "s", "sn"])
    a2.set(ylabel="Pendiente (dB/década)", title="Pendiente por sujeto\n(línea: mediana)")
    a2.grid(axis="x", alpha=0)
    _ejes_coma(a2, x=False)
    _leyenda_figura(fig, (a1, a2), ncol=2, alto=0.17)
    return fig


def fig_n20(tabla, excluidos):
    """13. Latencia del N20 de cada sujeto vs. media ± SD del paper y límite IFCN."""
    media_p, sd_p = COMPONENTES["N20"]["lat_paper"]
    lim_ifcn = COMPONENTES["N20"]["lat_ref"][1]
    fig, ax = plt.subplots(figsize=(6.3 * 0.75, 2.7))
    t = tabla.reset_index(drop=True)
    x = np.arange(len(t))
    ok = ~t["sujeto"].isin(excluidos) & t["N20_valido"]
    ax.axhspan(media_p - sd_p, media_p + sd_p, color="#1f77b4", alpha=0.12, lw=0,
               label=f"Paper: {fmt(media_p, 2)} ± {fmt(sd_p, 1)} ms (media ± SD)")
    ax.axhline(media_p, color="#1f77b4", lw=0.8)
    ax.axhline(lim_ifcn, color="#d62728", lw=0.8, ls="--", label=f"Límite IFCN ({fmt(lim_ifcn)} ms)")
    ax.plot(x[ok], t.loc[ok, "N20_lat_ms"], "o", color="k", ms=4, label="Sujeto")
    ax.plot(x[~ok], t.loc[~ok, "N20_lat_ms"], "o", mfc="none", mec="0.5", ms=4,
            label="N20 no confiable (excluido)")
    m = t.loc[ok, "N20_lat_ms"]
    ax.set_xticks(x)
    ax.set_xticklabels(t["sujeto"])
    ax.set(xlabel="Sujeto", ylabel="Latencia del N20 (ms)",
           title=f"N20 en {cfg.CANAL}–{cfg.REFERENCIA}: {fmt(m.mean())} ± {fmt(m.std(ddof=1))} ms "
                 f"(N = {ok.sum()})", ylim=(15, lim_ifcn + 1))
    ax.grid(axis="x", alpha=0)
    _ejes_coma(ax, x=False)
    _leyenda_figura(fig, ax, ncol=2, alto=0.2)
    return fig


def main():
    estilo()
    sujetos = sujetos_disponibles()
    if len(sujetos) < 3:
        raise SystemExit(f"Hay {len(sujetos)} sujeto(s) con resultados en {cfg.DIR_RESULTADOS}: "
                         "correr main.py con más sujetos.")
    filas, curvas = zip(*(leer_sujeto(s) for s in sujetos))
    tabla, curvas = pd.DataFrame(filas), pd.concat(curvas, ignore_index=True)

    # Resumen grupal de las ganancias (todos y sin los sujetos de sensibilidad), de las
    # pendientes, de la latencia del N20 y de la SNR del homogéneo
    filas_r, res = [], {}
    sin = tabla[~tabla["sujeto"].isin(SUJETOS_SENSIBILIDAD)]
    for m in METODOS[1:]:
        res[m] = resumen(tabla[f"dif_{m}_db"])
        filas_r.append(dict(medida=f"ganancia {m} - homogeneo (dB)", grupo="todos", **res[m]))
        filas_r.append(dict(medida=f"ganancia {m} - homogeneo (dB)",
                            grupo=f"sin {','.join(SUJETOS_SENSIBILIDAD)}", **resumen(sin[f"dif_{m}_db"])))
    for m in METODOS:
        filas_r.append(dict(medida=f"pendiente {m} - 10 (dB/decada)", grupo="todos",
                            **resumen(tabla[f"pendiente_{m}"] - 10)))
    lat = tabla.loc[~tabla["sujeto"].isin(SUJETOS_SENSIBILIDAD) & tabla["N20_valido"], "N20_lat_ms"]
    filas_r.append(dict(medida="N20 latencia - paper (ms)", grupo="confiables",
                        **resumen(lat - COMPONENTES["N20"]["lat_paper"][0])))
    filas_r.append(dict(medida="SNR homogeneo (dB)", grupo="todos",
                        **resumen(tabla["snr_homogeneo_db"])))
    tabla_r = pd.DataFrame(filas_r)

    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(f"\nSujetos: {', '.join(sujetos)} ({len(sujetos)})")
        cols = (["sujeto", "snr_homogeneo_db", "dif_n_db", "ic_inf_n", "ic_sup_n", "sig_n",
                 "dif_s_db", "dif_sn_db", "pendiente_homogeneo", "N20_lat_ms", "N20_P25_pp_uV",
                 "rep_cumple"])
        print(tabla[cols].round(2).to_string(index=False))
        print("\nResumen grupal (pendientes y N20 expresados como diferencia con 10 dB/década "
              "y con el paper)")
        print(tabla_r.round(3).to_string(index=False))

    cfg.DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(cfg.DIR_FIGURAS / "grupal_sujetos.csv", index=False)
    tabla_r.to_csv(cfg.DIR_FIGURAS / "grupal_resumen.csv", index=False)
    print("\nGenerando figuras en", cfg.DIR_FIGURAS)
    guardar(fig_ganancia(tabla, res), "11_grupal_ganancia")
    guardar(fig_curvas_grupo(curvas, tabla), "12_grupal_curvas")
    guardar(fig_n20(tabla, SUJETOS_SENSIBILIDAD), "13_grupal_n20")
    plt.show()


if __name__ == "__main__":
    main()
