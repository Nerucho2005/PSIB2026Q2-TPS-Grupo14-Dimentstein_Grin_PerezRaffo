# main.py
# Corre el pipeline completo del PEP tibial:
#   carga + filtrado -> segmentación -> promedios -> SNR -> figuras
# Los parámetros están en config.py.
#
# Ejecutar desde la raíz del repo:   python TPS/main.py
import logging

import matplotlib.pyplot as plt
import numpy as np

import config as cfg
from filtrado import preprocesar_eeg
from segmentacion import cargar_eventos, segmentar_epocas
from snr import METODOS, curva_snr, snr_teorica_homogeneo, snr_todos_los_metodos


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg.DIR_RESULTADOS.mkdir(exist_ok=True)

    # 1. Eventos del .tsv (se necesitan antes de filtrar, para interpolar el artefacto)
    eventos = cargar_eventos(cfg.ARCHIVO_EVENTOS)
    muestras = eventos["sample"].to_numpy().astype(int) if cfg.INTERPOLAR_ARTEFACTO else None

    # 2. Carga, selección de canales, interpolación del artefacto y filtrado
    res = preprocesar_eeg(cfg.ARCHIVO_EEG, canales=cfg.CANALES, f_bajo=cfg.F_BAJO,
                          f_alto=cfg.F_ALTO, orden=cfg.ORDEN, f_notch=cfg.F_NOTCH,
                          q_notch=cfg.Q_NOTCH, muestras_estimulo=muestras,
                          t_artefacto=cfg.T_ARTEFACTO)

    # 3. Segmentación
    epocas, tiempos = segmentar_epocas(res.raw, eventos, tmin=cfg.TMIN, tmax=cfg.TMAX)
    M = epocas.shape[0]

    # 4. Promedios y SNR con todas las épocas
    r = snr_todos_los_metodos(epocas, tiempos, cfg.VENTANA_SENAL, cfg.TAM_BLOQUE)
    print(f"\nSNR con M = {M} épocas (dB)")
    print(f"{'método':>10} " + " ".join(f"{c:>8}" for c in res.canales))
    for met in METODOS:
        print(f"{met:>10} " + " ".join(f"{v:8.2f}" for v in r[met]["snr_db"]))

    # Curvas SNR vs. N
    n_valores = sorted({n for n in cfg.N_VALORES if n < M} | {M})
    curvas = {met: curva_snr(epocas, tiempos, n_valores, met, n_rep=cfg.N_REP,
                             ventana_senal=cfg.VENTANA_SENAL, tam_bloque=cfg.TAM_BLOQUE)
              for met in METODOS}

    # ---- Figuras provisorias (reemplazar por graficos.py) ----
    t_ms = tiempos * 1e3
    for i, canal in enumerate(res.canales):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

        for met in METODOS:
            ax1.plot(t_ms, r[met]["pe"][i] * 1e6, lw=1, label=met)
        ax1.axvspan(*(np.array(cfg.VENTANA_SENAL) * 1e3), color="0.9", zorder=0)
        ax1.axvline(0, color="k", lw=0.5)
        ax1.set(xlabel="Tiempo (ms)", ylabel="Amplitud (µV)", title=f"PEP tibial — {canal}")
        ax1.legend()

        for met in METODOS:
            c = curvas[met]
            ax2.semilogx(c["n"], c["snr_db"][:, i], "o-", label=met)
        h = curvas["homogeneo"]
        ax2.semilogx(h["n"], snr_teorica_homogeneo(h["n"], h["snr_db"][-1, i], M),
                     "k--", lw=1, label="+3 dB/duplicación")
        ax2.set(xlabel="N épocas promediadas", ylabel="SNR (dB)", title=f"SNR vs. N — {canal}")
        ax2.grid(True, which="both", alpha=0.3)
        ax2.legend()

        fig.tight_layout()
        fig.savefig(cfg.DIR_RESULTADOS / f"pep_snr_{canal}.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()