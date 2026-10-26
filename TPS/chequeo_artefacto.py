# chequeo_artefacto.py
# Verifica el artefacto de estimulación en el EEG SIN filtrar.
#
# El pulso del estimulador (0,2 ms) llega al cuero cabelludo por conducción de
# volumen y aparece en t = 0 en todas las épocas. Como está sincronizado con el
# estímulo, el promediado no lo atenúa. Este script:
#   1. promedia las épocas SIN filtrar (solo se resta la media de -10 a -1 ms),
#   2. estima la amplitud del artefacto y cuánto dura,
#   3. compara el promedio crudo con el filtrado, sin y con interpolación del
#      artefacto, para ver cuánto lo dispersa el filtro de fase cero y si la
#      interpolación lo resuelve.
#
# Ejecutar desde la raíz del repo:   python TPS/chequeo_artefacto.py
import matplotlib.pyplot as plt
import numpy as np

import config as cfg
from filtrado import (_disenar_filtros, _filtrar, cargar_eeg, interpolar_artefacto,
                      seleccionar_canales)
from segmentacion import cargar_eventos

T_BASE = (-0.010, -0.001)   # s, línea de base para el promedio crudo
UMBRAL_SD = 5               # el artefacto "terminó" cuando |x| < UMBRAL_SD * sd(base)
N_EPOCAS_GRAFICO = 30       # épocas individuales superpuestas en el zoom


def epocar(datos, muestras, fs, tmin, tmax):
    desp = np.arange(int(round(tmin * fs)), int(round(tmax * fs)) + 1)
    validos = (muestras + desp[0] >= 0) & (muestras + desp[-1] < datos.shape[1])
    idx = muestras[validos][:, None] + desp[None, :]
    return datos[:, idx].transpose(1, 0, 2), desp / fs


def restar_base(epocas, t, ventana):
    m = (t >= ventana[0]) & (t < ventana[1])
    return epocas - epocas[..., m].mean(axis=-1, keepdims=True)


def duracion_artefacto(prom, t, ventana_base, k):
    """Último instante en 0-5 ms en que |prom| supera k * sd de la línea de base.
    Se acota a 5 ms porque más tarde la deriva lenta y el inicio del PEP también
    superan el umbral (el sd del promedio de cientos de épocas es muy chico)."""
    sd = prom[(t >= ventana_base[0]) & (t < ventana_base[1])].std()
    post = (t >= 0) & (t <= 0.005)
    fuera = np.abs(prom[post]) > k * sd
    return (t[post][fuera].max() if fuera.any() else np.nan), sd


def main():
    raw = seleccionar_canales(cargar_eeg(cfg.ARCHIVO_EEG), cfg.CANALES)
    raw.load_data()
    fs = raw.info["sfreq"]
    crudo = raw.get_data()

    filtros = _disenar_filtros(fs, cfg.F_BAJO, cfg.F_ALTO, cfg.ORDEN, cfg.F_NOTCH, cfg.Q_NOTCH)
    padlen = min(int(3 * fs / cfg.F_BAJO), crudo.shape[1] - 1)

    eventos = cargar_eventos(cfg.ARCHIVO_EVENTOS)
    if "sample" in eventos:
        muestras = eventos["sample"].to_numpy().astype(int)
    else:
        muestras = np.round(eventos["onset"].to_numpy() * fs).astype(int)

    filtrado = _filtrar(crudo, filtros, padlen)
    filtrado_int = _filtrar(interpolar_artefacto(crudo, muestras, fs, *cfg.T_ARTEFACTO),
                            filtros, padlen)

    ep_c, t = epocar(crudo, muestras, fs, cfg.TMIN, cfg.TMAX)
    ep_f, _ = epocar(filtrado, muestras, fs, cfg.TMIN, cfg.TMAX)
    ep_fi, _ = epocar(filtrado_int, muestras, fs, cfg.TMIN, cfg.TMAX)
    ep_c = restar_base(ep_c, t, T_BASE)
    ep_f = restar_base(ep_f, t, (cfg.TMIN, 0))   # igual que segmentar_epocas
    ep_fi = restar_base(ep_fi, t, (cfg.TMIN, 0))
    prom_c, prom_f, prom_fi = ep_c.mean(axis=0), ep_f.mean(axis=0), ep_fi.mean(axis=0)

    t_ms = t * 1e3
    m_art = (t >= -0.001) & (t <= 0.003)
    m_pep = (t >= cfg.VENTANA_SENAL[0]) & (t < cfg.VENTANA_SENAL[1])
    print(f"\n{ep_c.shape[0]} épocas | fs = {fs:g} Hz")
    for i, canal in enumerate(raw.ch_names):
        pico_art = np.abs(prom_c[i, m_art]).max()
        pico_pep = np.abs(prom_c[i, m_pep]).max()
        fin, sd = duracion_artefacto(prom_c[i], t, T_BASE, UMBRAL_SD)
        print(f"{canal}: artefacto {pico_art*1e6:8.1f} µV | PEP (crudo) {pico_pep*1e6:5.1f} µV | "
              f"cociente {pico_art/pico_pep:6.1f} | |x| > {UMBRAL_SD}·sd(base) hasta "
              f"{fin*1e3:5.2f} ms")
        base = t < 0
        print(f"      línea de base filtrada (rms, -20 a 0 ms): sin interpolar "
              f"{np.sqrt((prom_f[i, base]**2).mean())*1e6:.3f} µV | interpolada "
              f"{np.sqrt((prom_fi[i, base]**2).mean())*1e6:.3f} µV")

        fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4))
        sel = np.linspace(0, ep_c.shape[0] - 1, N_EPOCAS_GRAFICO).astype(int)
        z = (t >= -0.005) & (t <= 0.015)
        a1.plot(t_ms[z], ep_c[sel, i][:, z].T * 1e6, color="0.75", lw=0.5)
        a1.plot(t_ms[z], prom_c[i, z] * 1e6, "k", lw=1.5, label="promedio crudo")
        a1.axhspan(-UMBRAL_SD * sd * 1e6, UMBRAL_SD * sd * 1e6, color="tab:green", alpha=0.15,
                   label=f"±{UMBRAL_SD}·sd línea de base")
        a1.axvline(0, color="r", lw=0.5)
        a1.set(xlabel="Tiempo (ms)", ylabel="µV",
               title=f"{canal}: zoom sin filtrar ({N_EPOCAS_GRAFICO} épocas en gris)")
        a1.legend(loc="upper right")

        a2.plot(t_ms, prom_c[i] * 1e6, color="0.5", lw=1, label="sin filtrar")
        a2.plot(t_ms, prom_f[i] * 1e6, "tab:blue", lw=1.2,
                label=f"filtrado {cfg.F_BAJO:g}-{cfg.F_ALTO:g} Hz")
        a2.plot(t_ms, prom_fi[i] * 1e6, "tab:orange", lw=1.2, ls="--",
                label="filtrado con artefacto interpolado")
        a2.axvspan(*(np.array(cfg.T_ARTEFACTO) * 1e3), color="tab:orange", alpha=0.2)
        a2.axvspan(*(np.array(cfg.VENTANA_SENAL) * 1e3), color="0.92", zorder=0)
        a2.axvline(0, color="r", lw=0.5)
        a2.set(xlabel="Tiempo (ms)", ylabel="µV", title=f"{canal}: crudo vs. filtrado (sin y con interpolación)")
        lim = 1.5 * np.abs(prom_f[i]).max() * 1e6        # escala del PEP, no del artefacto
        a2.set_ylim(-lim, lim)
        a2.legend(loc="upper right")
        fig.tight_layout()
        cfg.DIR_RESULTADOS.mkdir(exist_ok=True)
        fig.savefig(cfg.DIR_RESULTADOS / f"artefacto_{canal}.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()