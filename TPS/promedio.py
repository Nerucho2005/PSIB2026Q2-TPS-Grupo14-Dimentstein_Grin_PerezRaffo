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
# Entradas (salida de segmentar_epocas):
#   epocas  (n_epocas, n_canales, n_muestras), en V
#   tiempos (n_muestras,), en s (0 = estímulo)
# Las ventanas también van en segundos.
import numpy as np


def promedio_homogeneo(epocas):
    """Media simple: todas las épocas pesan 1/M. Devuelve (n_canales, n_muestras)."""
    return epocas.mean(axis=0)


def _mascara(tiempos, ventana):
    m = (tiempos >= ventana[0]) & (tiempos < ventana[1])
    if m.sum() < 2:
        raise ValueError(f"La ventana {ventana} s tiene menos de 2 muestras.")
    return m


def varianza_ruido(epocas, tiempos, ventana_ruido):
    """sigma_m^2 de cada época y canal, medida donde no hay PEP (pre-estímulo).
    Devuelve (n_epocas, n_canales)."""
    m = _mascara(tiempos, ventana_ruido)
    return epocas[..., m].var(axis=-1, ddof=1)


def amplitudes(epocas, tiempos, ventana_senal):
    """a_m de cada época y canal: proyección de la época sobre el promedio de
    las OTRAS épocas, dentro de la ventana del PEP.
        a_m = <x_m, r_m> / <r_m, r_m>,   r_m = promedio sin la época m
    Se excluye la propia época para que su ruido no se correlacione consigo
    mismo. Se normaliza para que la media de a sea 1 (misma escala que el
    promedio homogéneo). Devuelve (n_epocas, n_canales)."""
    M = epocas.shape[0]
    if M < 3:
        raise ValueError("Se necesitan al menos 3 épocas.")
    x = epocas[..., _mascara(tiempos, ventana_senal)]
    r = (x.sum(axis=0) - x) / (M - 1)
    a = (x * r).sum(axis=-1) / (r * r).sum(axis=-1)
    media = a.mean(axis=0, keepdims=True)
    if np.any(media <= 0):
        raise ValueError("Amplitud media no positiva: revisá la ventana de señal.")
    return a / media


def pesos_inhomogeneos(a, sigma2):
    """w_m = (a_m/sigma_m^2) / sum_k(a_k^2/sigma_k^2), por canal."""
    num = a / sigma2
    return num / (a * num).sum(axis=0, keepdims=True)


def promedio_inhomogeneo(epocas, modo, tiempos,
                         ventana_ruido=(-0.020, 0.0), ventana_senal=(0.015, 0.080)):
    """Promedio pesado. modo: "s", "n" o "sn".
    Devuelve (pe, pesos): pe (n_canales, n_muestras), pesos (n_epocas, n_canales)."""
    if modo not in ("s", "n", "sn"):
        raise ValueError(f'modo debe ser "s", "n" o "sn", no {modo!r}.')
    forma = epocas.shape[:2]

    a = np.ones(forma) if modo == "n" else amplitudes(epocas, tiempos, ventana_senal)
    sigma2 = np.ones(forma) if modo == "s" else varianza_ruido(epocas, tiempos, ventana_ruido)

    pesos = pesos_inhomogeneos(a, sigma2)
    pe = np.einsum("mc,mcn->cn", pesos, epocas)
    return pe, pesos
