# main.py
# Corre el pipeline completo del PES (nervio según config.NERVIO):
#   carga + re-referencia + interpolación + filtrado -> segmentación -> promedios
#   -> SNR con incertidumbre (jackknife) -> componentes vs. normas -> figuras
# Los parámetros están en config.py. Todas las salidas llevan el nervio y la
# referencia en el nombre, para poder correr con distintas referencias sin pisarse.
#
# Ejecutar desde la raíz del repo:   python TPS/main.py
import logging

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as cfg
from filtrado import nombre_referencia, preprocesar_eeg
from promedio import varianza_ruido
from segmentacion import cargar_eventos, segmentar_epocas
from snr import (METODOS, ajustar_pendiente, curva_snr, diferencia_metodos, jackknife_snr,
                 snr_teorica_ajustada, snr_todos_los_metodos)
from teoria import comparar_con_teoria, reproducibilidad, tabla_metodos


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg.DIR_RESULTADOS.mkdir(exist_ok=True)

    # 1. Eventos del .tsv (se necesitan antes de filtrar, para interpolar el artefacto)
    eventos = cargar_eventos(cfg.ARCHIVO_EVENTOS)
    muestras = eventos["sample"].to_numpy().astype(int) if cfg.INTERPOLAR_ARTEFACTO else None

    # 2. Carga, re-referencia, interpolación del artefacto y filtrado
    res = preprocesar_eeg(cfg.ARCHIVO_EEG, canales=cfg.CANALES, f_bajo=cfg.F_BAJO,
                          f_alto=cfg.F_ALTO, orden=cfg.ORDEN, f_notch=cfg.F_NOTCH,
                          q_notch=cfg.Q_NOTCH, muestras_estimulo=muestras,
                          t_artefacto=cfg.T_ARTEFACTO, referencia=cfg.REFERENCIA)
    ref = nombre_referencia(cfg.REFERENCIA)
    sufijo = f"{cfg.NERVIO}_{ref}"
    canales = res.canales

    # 3. Segmentación
    epocas, tiempos = segmentar_epocas(res.raw, eventos, tmin=cfg.TMIN, tmax=cfg.TMAX)
    M = epocas.shape[0]

    # 4. Promedios y SNR con todas las épocas, con error estándar (jackknife por bloques)
    r = snr_todos_los_metodos(epocas, tiempos, cfg.VENTANA_SENAL, cfg.TAM_BLOQUE)
    jk = jackknife_snr(epocas, tiempos, METODOS, cfg.N_BLOQUES_JK, cfg.VENTANA_SENAL,
                       cfg.TAM_BLOQUE)
    filas_snr, filas_dif = [], []
    for met in METODOS:
        for i, canal in enumerate(canales):
            filas_snr.append(dict(metodo=met, canal=canal, snr_db=jk[met]["snr_db"][i],
                                  se_db=jk[met]["se_db"][i]))
    for met in METODOS[1:]:
        d = diferencia_metodos(jk, met, "homogeneo")
        for i, canal in enumerate(canales):
            filas_dif.append(dict(comparacion=f"{met} - homogeneo", canal=canal,
                                  dif_db=d["dif_db"][i], se_db=d["se_db"][i],
                                  ic95_inf=d["ic_inf"][i], ic95_sup=d["ic_sup"][i],
                                  significativa=bool(d["ic_inf"][i] > 0 or d["ic_sup"][i] < 0)))
    tabla_snr, tabla_dif = pd.DataFrame(filas_snr), pd.DataFrame(filas_dif)

    # 5. Latencias y amplitudes vs. normas, y reproducibilidad (IFCN)
    tabla = comparar_con_teoria(tiempos, r["homogeneo"]["pe"], canales, cfg.NERVIO)
    tm = tabla_metodos(tiempos, {met: r[met]["pe"] for met in METODOS}, canales, cfg.NERVIO)
    rep = reproducibilidad(tiempos, epocas, canales, cfg.NERVIO)

    with pd.option_context("display.width", 180, "display.max_columns", 20):
        print(f"\nSNR con M = {M} épocas (dB, ± error estándar jackknife) | referencia {ref}")
        print(tabla_snr.pivot(index="metodo", columns="canal", values="snr_db").loc[list(METODOS)]
              .round(2).astype(str) + " ± " +
              tabla_snr.pivot(index="metodo", columns="canal", values="se_db").loc[list(METODOS)]
              .round(2).astype(str))
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

    # 6. Curvas SNR vs. N (bloques disjuntos) y pendiente
    n_valores = sorted({n for n in cfg.N_VALORES if n < M} | {M})
    curvas = {met: curva_snr(epocas, tiempos, n_valores, met, cfg.VENTANA_SENAL,
                             cfg.TAM_BLOQUE, n_bloques_jk=cfg.N_BLOQUES_JK)
              for met in METODOS}
    filas_curva = []
    print("\nPendiente de la SNR vs. log10(N) (teórica: 10 dB/década = +3 dB por duplicación)")
    for met in METODOS:
        c = curvas[met]
        for i, canal in enumerate(canales):
            _, b, sb = ajustar_pendiente(c["n"], c["snr_db"][:, i], c["se_db"][:, i])
            print(f"  {met:>10} {canal:>5}: {b:5.1f} ± {sb:.1f} dB/década")
            for k, n in enumerate(c["n"]):
                filas_curva.append(dict(metodo=met, canal=canal, N=n, snr_db=c["snr_db"][k, i],
                                        se_db=c["se_db"][k, i], n_bloques=c["n_bloques"][k],
                                        pendiente_db_decada=b, se_pendiente=sb))
    pd.DataFrame(filas_curva).to_csv(cfg.DIR_RESULTADOS / f"curva_snr_{sufijo}.csv", index=False)

    # ---- Figuras provisorias (reemplazar por graficos.py) ----
    t_ms = tiempos * 1e3
    for i, canal in enumerate(canales):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        for met in METODOS:
            ax1.plot(t_ms, r[met]["pe"][i] * 1e6, lw=1, label=met)
        ax1.axvspan(*(np.array(cfg.VENTANA_SENAL) * 1e3), color="0.9", zorder=0)
        ax1.axvline(0, color="k", lw=0.5)
        ax1.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)",
                title=f"PEP {cfg.NERVIO} — {canal} (ref. {ref})")
        ax1.legend()

        for k, met in enumerate(METODOS):
            c = curvas[met]
            x = c["n"] * (1 + 0.025 * (k - 1.5))            # leve corrimiento para que no se tapen
            ax2.errorbar(x, c["snr_db"][:, i], yerr=c["se_db"][:, i], fmt="o-", capsize=3,
                         label=met)
        h = curvas["homogeneo"]
        ax2.plot(h["n"], snr_teorica_ajustada(h["n"], h["snr_db"][:, i], h["se_db"][:, i]),
                 "k--", lw=1, label="+10·log10(N) (ajustada)")
        ax2.set_xscale("log")
        ax2.set(xlabel="N épocas promediadas", ylabel="SNR (dB)",
                title=f"SNR vs. N — {canal} (± error estándar)")
        ax2.grid(True, which="both", alpha=0.3)
        ax2.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(cfg.DIR_RESULTADOS / f"pep_snr_{sufijo}_{canal}.png", dpi=150)

    # Pesos del inhomogéneo "n" y varianza del ruido por época: de dónde sale la ganancia
    sigma2 = varianza_ruido(epocas, np.ones(epocas.shape[:2]))
    w_rel = r["n"]["pesos"] * M                            # 1 = peso del homogéneo
    fig, axs = plt.subplots(2, 1, figsize=(10, 5.5), sharex=True)
    for i, canal in enumerate(canales):
        axs[0].plot(np.arange(M), sigma2[:, i] * 1e12, lw=0.8, label=canal)
        axs[1].plot(np.arange(M), w_rel[:, i], lw=0.8, label=canal)
    axs[1].axhline(1, color="k", lw=0.8, ls="--", label="homogéneo (1/M)")
    axs[0].set(ylabel="σ² del ruido (µV²)",
               title=f"Varianza del ruido y pesos del promedio inhomogéneo \"n\" — {cfg.NERVIO}, ref. {ref}")
    axs[1].set(xlabel="Número de época (orden temporal)", ylabel="Peso relativo (w·M)")
    for ax in axs:
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(cfg.DIR_RESULTADOS / f"pesos_{sufijo}.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()