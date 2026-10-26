# promedio.py
# Etapas 3 y 4: promedio homogéneo e inhomogéneo de las épocas.
#
# Modelo de cada época m (por canal):  x_m(n) = a_m * s(n) + v_m(n)
#   s(n): PEP (igual en todas las épocas), a_m: amplitud de la época m,
#   v_m(n): ruido de media 0 y varianza sigma_m^2.
#
# Estimador: s_hat(n) = sum_m w_m x_m(n), con sum_m w_m a_m = 1 (sin sesgo).
# Minimizando la varianza del ruido que queda, sum_m w_m^2 sigma_m^2:
#     w_m = (a_m / sigma_m^2) / sum_k (a_k^2 / sigma_k^2)
#   modo "n":  a_m = 1                 -> w_m ∝ 1/sigma_m^2
#   modo "s":  sigma_m constante        -> w_m ∝ a_m
#   modo "sn": ambos varían             -> w_m ∝ a_m/sigma_m^2
#
# Cómo se estiman a_m y sigma_m^2:
#   sigma_m^2: varianza del residuo x_m - a_m * s_hat en TODA la época. Con el
#     pre-estímulo solo (20 ms) habría ~4 grados de libertad tras el pasabanda,
#     y 1/sigma^2 premiaría épocas tranquilas por casualidad.
#   a_m: en una época sola el PEP está enterrado en el EEG y a_m sale casi puro
#     ruido (pesos negativos). Se estima por BLOQUES de épocas consecutivas: el
#     promedio del bloque tiene SNR suficiente, y la amplitud del PEP cambia
#     lento (habituación, fatiga). Todas las épocas de un bloque comparten a.
#
# Entradas (salida de segmentar_epocas):
#   epocas  (n_epocas, n_canales, n_muestras), en V, en orden temporal
#   tiempos (n_muestras,), en s (0 = estímulo)
import numpy as np


def promedio_homogeneo(epocas):
    """Media simple: todas las épocas pesan 1/M. Devuelve (n_canales, n_muestras)."""
    return epocas.mean(axis=0)


def _mascara(tiempos, ventana):
    m = (tiempos >= ventana[0]) & (tiempos < ventana[1])
    if m.sum() < 2:
        raise ValueError(f"La ventana {ventana} s tiene menos de 2 muestras.")
    return m


def varianza_ruido(epocas, a):
    """sigma_m^2 de cada época y canal: varianza del residuo x_m - a_m * s_hat
    sobre toda la época, con s_hat el promedio homogéneo.
    a: (n_epocas, n_canales). Devuelve (n_epocas, n_canales)."""
    residuo = epocas - a[..., None] * promedio_homogeneo(epocas)
    return residuo.var(axis=-1, ddof=1)


def amplitudes(epocas, tiempos, ventana_senal, tam_bloque=50):
    """a_m por bloques de tam_bloque épocas consecutivas.
    Para cada bloque b, dentro de la ventana del PEP:
        a_b = <xbar_b, r_b> / <r_b, r_b>
    con xbar_b el promedio del bloque y r_b el promedio de las épocas de los
    OTROS bloques (así el ruido del bloque no se correlaciona consigo mismo).
    El último bloque absorbe las épocas sobrantes. Se normaliza para que la
    media de a sea 1. Devuelve (n_epocas, n_canales)."""
    M = epocas.shape[0]
    n_bloques = M // tam_bloque
    if n_bloques < 2:
        raise ValueError(f"Con {M} épocas y bloques de {tam_bloque} hay menos de 2 bloques.")
    bloque = np.minimum(np.arange(M) // tam_bloque, n_bloques - 1)
    n_por_bloque = np.bincount(bloque)

    x = epocas[..., _mascara(tiempos, ventana_senal)]
    suma_bloque = np.stack([x[bloque == b].sum(axis=0) for b in range(n_bloques)])
    xbar = suma_bloque / n_por_bloque[:, None, None]
    r = (x.sum(axis=0) - suma_bloque) / (M - n_por_bloque)[:, None, None]
    a_b = (xbar * r).sum(axis=-1) / (r * r).sum(axis=-1)
    a_b = np.clip(a_b, 0, None)   # el PEP no invierte polaridad: a_b < 0 es ruido

    a = a_b[bloque]
    media = a.mean(axis=0, keepdims=True)
    if np.any(media <= 0):
        raise ValueError("Amplitud media no positiva: revisá la ventana de señal.")
    return a / media


def pesos_inhomogeneos(a, sigma2):
    """w_m = (a_m/sigma_m^2) / sum_k(a_k^2/sigma_k^2), por canal."""
    num = a / sigma2
    return num / (a * num).sum(axis=0, keepdims=True)


def promedio_inhomogeneo(epocas, modo, tiempos, ventana_senal=(0.015, 0.080), tam_bloque=50):
    """Promedio pesado. modo: "s", "n" o "sn".
    ventana_senal: dónde está el PEP (s), para estimar amplitudes.
    tam_bloque: épocas por bloque para estimar amplitudes.
    Devuelve (pe, pesos): pe (n_canales, n_muestras), pesos (n_epocas, n_canales)."""
    if modo not in ("s", "n", "sn"):
        raise ValueError(f'modo debe ser "s", "n" o "sn", no {modo!r}.')
    forma = epocas.shape[:2]

    a = np.ones(forma) if modo == "n" else amplitudes(epocas, tiempos, ventana_senal, tam_bloque)
    sigma2 = np.ones(forma) if modo == "s" else varianza_ruido(epocas, a)

    pesos = pesos_inhomogeneos(a, sigma2)
    pe = np.einsum("mc,mcn->cn", pesos, epocas)
    return pe, pesos
