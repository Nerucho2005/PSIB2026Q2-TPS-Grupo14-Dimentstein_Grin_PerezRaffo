# main.py
# Pipeline completo del PES del nervio mediano para UN sujeto (config.SUJETO / RUN):
#   Etapas 1-2 (filtrado.py)     carga, re-referencia CP4-Fz, interpolación del
#                                artefacto y filtrado 30-400 Hz + notch, fase cero
#   Etapa 3 (segmentacion.py)    épocas de -30 a 80 ms alineadas al estímulo
#   Etapa 4 (promedio.py)        promedio homogéneo e inhomogéneos n, s y sn
#   Etapa 5 (snr.py)             SNR por promedio alternado (par/impar) ± jackknife,
#                                diferencia entre métodos, curvas SNR vs. N y SNR del paper
#   Etapa 6 (teoria.py)          latencias y amplitudes vs. IFCN y paper; reproducibilidad
# Imprime las tablas, las guarda en results/ con el sujeto en el nombre (las lee
# figuras/grupal.py) y muestra dos figuras rápidas de control.
#
# Ejecutar desde la raíz del repo:   python TPS/main/main.py
import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as cfg
from filtrado import nombre_referencia, preprocesar_eeg
from promedio import varianza_ruido
from segmentacion import cargar_eventos, segmentar_epocas
from snr import (METODOS, ajustar_pendiente, curva_snr, curva_snr_paper, diferencia_metodos,
                 jackknife_snr, snr_paper, snr_teorica_ajustada, snr_todos_los_metodos)
from teoria import comparar_con_teoria, reproducibilidad, tabla_metodos


def cargar_epocas():
    """Etapas 1 a 3: eventos, preprocesamiento y segmentación con los parámetros de
    config.py. Devuelve (epocas, tiempos, canales)."""
    eventos = cargar_eventos(cfg.ARCHIVO_EVENTOS)
    muestras = eventos["sample"].to_numpy().astype(int) if cfg.INTERPOLAR_ARTEFACTO else None
    res = preprocesar_eeg(cfg.ARCHIVO_EEG, canales=cfg.CANALES, f_bajo=cfg.F_BAJO,
                          f_alto=cfg.F_ALTO, orden=cfg.ORDEN, f_notch=cfg.F_NOTCH,
                          q_notch=cfg.Q_NOTCH, muestras_estimulo=muestras,
                          t_artefacto=cfg.T_ARTEFACTO, referencia=cfg.REFERENCIA)
    epocas, tiempos = segmentar_epocas(res.raw, eventos, tmin=cfg.TMIN, tmax=cfg.TMAX)
    return epocas, tiempos, res.canales


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg.DIR_RESULTADOS.mkdir(exist_ok=True)
    epocas, tiempos, canales = cargar_epocas()
    M = epocas.shape[0]
    ref = nombre_referencia(cfg.REFERENCIA)
    sufijo = f"sub-{cfg.SUJETO}_{cfg.CANAL}-{ref}_{cfg.F_BAJO:g}-{cfg.F_ALTO:g}Hz"

    # Etapas 4-5: los cuatro promedios y su SNR con todas las épocas, con error estándar
    # (jackknife por bloques) y diferencia de cada inhomogéneo con el homogéneo (IC 95 %)
    r = snr_todos_los_metodos(epocas, tiempos, cfg.VENTANA_SENAL, cfg.TAM_BLOQUE)
    jk = jackknife_snr(epocas, tiempos, METODOS, cfg.N_BLOQUES_JK, cfg.VENTANA_SENAL,
                       cfg.TAM_BLOQUE)
    tabla_snr = pd.DataFrame([dict(metodo=met, snr_db=jk[met]["snr_db"][0],
                                   se_db=jk[met]["se_db"][0]) for met in METODOS])
    filas_dif = []
    for met in METODOS[1:]:
        d = diferencia_metodos(jk, met, "homogeneo")
        filas_dif.append(dict(comparacion=f"{met} - homogeneo", dif_db=d["dif_db"][0],
                              se_db=d["se_db"][0], ic95_inf=d["ic_inf"][0],
                              ic95_sup=d["ic_sup"][0],
                              significativa=bool(d["ic_inf"][0] > 0 or d["ic_sup"][0] < 0)))
    tabla_dif = pd.DataFrame(filas_dif)

    # Etapa 6: componentes vs. normas, según el método, y reproducibilidad (IFCN)
    tabla = comparar_con_teoria(tiempos, r["homogeneo"]["pe"], canales)
    tm = tabla_metodos(tiempos, {met: r[met]["pe"] for met in METODOS}, canales)
    rep = reproducibilidad(tiempos, epocas, canales)

    # Etapa 5 (métrica complementaria): SNR estilo paper en la latencia del N20
    n20 = tabla[tabla["componente"] == "N20"].iloc[0]
    lat_n20 = n20["lat_ms"] / 1e3 if n20["valido"] else np.nan
    sp = {met: snr_paper(r[met]["pe"], tiempos, lat_n20, cfg.SEMIANCHO_SNR_PAPER)["snr_db"][0]
          for met in METODOS}
    tabla_snr["snr_paper_db"] = tabla_snr["metodo"].map(sp)

    with pd.option_context("display.width", 180, "display.max_columns", 20):
        print(f"\nSNR con M = {M} épocas — {cfg.CANAL}–{ref}, {cfg.F_BAJO:g}–{cfg.F_ALTO:g} Hz, "
              f"ventana {cfg.VENTANA_SENAL[0] * 1e3:g}–{cfg.VENTANA_SENAL[1] * 1e3:g} ms")
        print(tabla_snr.round(2).to_string(index=False))
        print("\nDiferencia de SNR respecto del homogéneo (IC 95 %, jackknife pareado)")
        print(tabla_dif.round(2).to_string(index=False))
        print("\nComponentes del PEP (promedio homogéneo)")
        print(tabla.round(2).to_string(index=False))
        print("\nComponentes según método de promediado")
        print(tm.to_string())
        print("\nReproducibilidad (IFCN): primera vs. segunda mitad del registro")
        print(rep.round(3).to_string(index=False))
    tabla_snr.to_csv(cfg.DIR_RESULTADOS / f"snr_{sufijo}.csv", index=False)
    tabla_dif.to_csv(cfg.DIR_RESULTADOS / f"diferencia_metodos_{sufijo}.csv", index=False)
    tabla.to_csv(cfg.DIR_RESULTADOS / f"componentes_{sufijo}_homogeneo.csv", index=False)
    tm.to_csv(cfg.DIR_RESULTADOS / f"componentes_{sufijo}_por_metodo.csv")
    rep.to_csv(cfg.DIR_RESULTADOS / f"reproducibilidad_{sufijo}.csv", index=False)

    # Etapa 5: curvas SNR vs. N (bloques disjuntos) y su pendiente (teórica 10 dB/década)
    n_valores = sorted({n for n in cfg.N_VALORES if n < M} | {M})
    curvas = {met: curva_snr(epocas, tiempos, n_valores, met, cfg.VENTANA_SENAL,
                             cfg.TAM_BLOQUE, n_bloques_jk=cfg.N_BLOQUES_JK)
              for met in METODOS}
    cp = curva_snr_paper(epocas, tiempos, n_valores, lat_n20, cfg.SEMIANCHO_SNR_PAPER,
                         cfg.N_BLOQUES_JK)
    filas_curva = []
    print("\nPendiente de la SNR vs. log10(N) (teórica: 10 dB/década = +3 dB por duplicación)")
    for met, c in [*curvas.items(), ("homogeneo (SNR paper)", cp)]:
        _, b, sb = ajustar_pendiente(c["n"], c["snr_db"][:, 0], c["se_db"][:, 0])
        print(f"  {met:>22}: {b:5.1f} ± {sb:.1f} dB/década")
        for k, n in enumerate(c["n"]):
            filas_curva.append(dict(metodo=met, N=n, snr_db=c["snr_db"][k, 0],
                                    se_db=c["se_db"][k, 0], pendiente_db_decada=b,
                                    se_pendiente=sb))
    pd.DataFrame(filas_curva).to_csv(cfg.DIR_RESULTADOS / f"curva_snr_{sufijo}.csv", index=False)

    # ---- Figuras rápidas de control (las del informe salen de figuras/graficos.py) ----
    t_ms = tiempos * 1e3
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    for met in METODOS:
        ax1.plot(t_ms, r[met]["pe"][0] * 1e6, lw=1, label=met)
    ax1.axvspan(*(np.array(cfg.VENTANA_SENAL) * 1e3), color="0.9", zorder=0)
    ax1.axvline(0, color="k", lw=0.5)
    ax1.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)", title=f"PEP mediano — {cfg.CANAL}–{ref}")
    ax1.legend()
    for k, met in enumerate(METODOS):
        c = curvas[met]
        ax2.errorbar(c["n"] * (1 + 0.025 * (k - 1.5)), c["snr_db"][:, 0], yerr=c["se_db"][:, 0],
                     fmt="o-", capsize=3, label=met)
    h = curvas["homogeneo"]
    ax2.plot(h["n"], snr_teorica_ajustada(h["n"], h["snr_db"][:, 0], h["se_db"][:, 0]),
             "k--", lw=1, label="+10·log10(N) (ajustada)")
    ax2.set_xscale("log")
    ax2.set(xlabel="N épocas promediadas", ylabel="SNR (dB)", title="SNR vs. N (± error estándar)")
    ax2.grid(True, which="both", alpha=0.3)
    ax2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(cfg.DIR_RESULTADOS / f"pep_snr_{sufijo}.png", dpi=150)

    # Varianza del ruido y pesos relativos de cada época: de dónde sale la ganancia
    sigma2 = varianza_ruido(epocas, np.ones(epocas.shape[:2]))
    fig, axs = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True)
    axs[0].plot(np.arange(M), sigma2[:, 0] * 1e12, lw=0.8, color="0.3")
    for met in METODOS[1:]:
        axs[1].plot(np.arange(M), r[met]["pesos"][:, 0] * M, lw=0.8, label=met)
    axs[1].axhline(1, color="k", lw=0.8, ls="--", label="homogéneo (1/M)")
    axs[0].set(ylabel="σ² del ruido (µV²)", title=f"Varianza del ruido y pesos — {cfg.CANAL}–{ref}")
    axs[1].set(xlabel="Número de época (orden temporal)", ylabel="Peso relativo (w·M)")
    for ax in axs:
        ax.grid(alpha=0.3)
    axs[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(cfg.DIR_RESULTADOS / f"pesos_{sufijo}.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()
