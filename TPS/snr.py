# snr.py
# Etapa 6: relación señal/ruido (SNR) de cada promedio.
#
# Problema: el PEP verdadero s(n) es desconocido, así que no se puede medir el
# ruido residual del promedio como pe - s. Se estima con el promedio alternado
# (plus-minus averaging, Schimmel 1967):
#
#     pe(n)    = sum_m      w_m x_m(n)   = s(n)  + ruido
#     ruido(n) = sum_m (-1)^m w_m x_m(n) ≈ 0     + ruido'
#
# Al alternar el signo de épocas consecutivas, el PEP se cancela (si su amplitud
# cambia lento entre épocas vecinas), mientras que el ruido, independiente entre
# épocas, conserva la misma varianza: Var = sum_m w_m^2 sigma_m^2. Sirve igual
# para el promedio homogéneo (w_m = 1/M) y para los inhomogéneos, porque usa los
# mismos pesos que el promedio que se evalúa.
#
# SNR por canal:
#     P_ruido = media de ruido(n)^2 en la ventana del PEP
#     P_pe    = media de pe(n)^2 en la misma ventana (incluye señal + ruido)
#     P_senal = P_pe - P_ruido
#     SNR     = 10 log10(P_senal / P_ruido)   [dB]
# Si P_senal <= 0 (N muy chico, el PEP no emerge del ruido) se devuelve NaN.
#
# Requisito: épocas en orden temporal (salida de segmentar_epocas). Con M impar
# queda una época sin pareja; su aporte de señal es ~1/M y se desprecia.
#
# Ambas potencias se miden en la MISMA ventana: la corrección de línea de base
# fuerza media cero en el pre-estímulo y vuelve el ruido no estacionario dentro
# de la época, así que medir P_ruido en toda la época lo subestima (~0,5 dB).
#
# Para reducir la varianza de P_ruido (la ventana dura 65 ms y, tras el
# pasabanda, tiene pocos grados de libertad), se promedian n_perm patrones de
# signo: cada par de épocas consecutivas recibe signos opuestos, con orden
# aleatorio dentro del par. Todos cancelan el PEP y dan realizaciones distintas
# del ruido residual.
#
# LIMITACIÓN (modos "s" y "sn"): las amplitudes a_b se estiman con las mismas
# épocas que se promedian, así que los pesos quedan correlacionados con el ruido
# de su bloque. Parte del ruido entra al promedio con la forma del PEP y el
# promedio alternado no la detecta: la SNR de esos modos sale optimista. En
# simulación (ruido de varianza 1:9 entre mitades) la sobreestimación fue de
# ~3-6 dB. Para "homogeneo" y "n" la estimación es aproximadamente insesgada.
#
# Para la curva SNR vs. N se usan bloques de N épocas CONSECUTIVAS con inicio
# aleatorio: conserva el orden temporal (necesario para el promedio alternado y
# para los bloques de amplitud de promedio.py). Para los modos "s" y "sn",
# promedio.py exige >= 2 bloques de amplitud, así que con N chico se reduce
# tam_bloque a N // 2 (ver _promediar). Esto hay que aclararlo en el informe.
import numpy as np

from promedio import promedio_homogeneo, promedio_inhomogeneo

METODOS = ("homogeneo", "n", "s", "sn")
VENTANA_SENAL = (0.015, 0.080)  # s; mover a config.py


def _mascara(tiempos, ventana):
    m = (tiempos >= ventana[0]) & (tiempos < ventana[1])
    if m.sum() < 2:
        raise ValueError(f"La ventana {ventana} s tiene menos de 2 muestras.")
    return m


def pesos_homogeneos(epocas):
    """Pesos 1/M con la misma forma que los de promedio_inhomogeneo: (n_epocas, n_canales)."""
    M, C = epocas.shape[:2]
    return np.full((M, C), 1.0 / M)


def _signos(M, n_perm, rng):
    """(n_perm, M) patrones de signo: +-1 opuestos dentro de cada par (0,1), (2,3)...
    El primer patrón es el alternado clásico +,-,+,-. Con M impar la última es 0."""
    n_pares = M // 2
    s = np.zeros((n_perm, M))
    primero = np.ones((n_perm, n_pares))
    if n_perm > 1:
        primero[1:] = rng.choice([-1.0, 1.0], size=(n_perm - 1, n_pares))
    s[:, 0:2 * n_pares:2] = primero
    s[:, 1:2 * n_pares:2] = -primero
    return s


def ruido_residual(epocas, pesos, n_perm=1, semilla=0):
    """Promedio alternado sum_m s_m w_m x_m(n) para n_perm patrones de signo.
    Devuelve (n_perm, n_canales, n_muestras)."""
    signos = _signos(epocas.shape[0], n_perm, np.random.default_rng(semilla))
    return np.einsum("pm,mc,mcn->pcn", signos, pesos, epocas)


def calcular_snr(epocas, pe, pesos, tiempos, ventana_senal=VENTANA_SENAL, n_perm=50):
    """SNR por canal de un promedio ya calculado.
    epocas (M, C, N) en V | pe (C, N) | pesos (M, C) | tiempos (N,) en s.
    Devuelve dict con arrays (C,):
      snr_db, p_senal, p_ruido (V^2) y rms_ruido (V)."""
    ruido = ruido_residual(epocas, pesos, n_perm)
    m = _mascara(tiempos, ventana_senal)
    p_ruido = (ruido[..., m] ** 2).mean(axis=(0, -1))
    p_senal = (pe[:, m] ** 2).mean(axis=-1) - p_ruido
    with np.errstate(divide="ignore", invalid="ignore"):
        snr_db = np.where(p_senal > 0, 10 * np.log10(p_senal / p_ruido), np.nan)
    return dict(snr_db=snr_db, p_senal=p_senal, p_ruido=p_ruido, rms_ruido=np.sqrt(p_ruido))


def _promediar(epocas, metodo, tiempos, ventana_senal, tam_bloque):
    """Devuelve (pe, pesos) para cualquier método, con la misma interfaz.
    Devuelve None si promedio.py no puede estimar amplitudes (N chico: el PEP
    no emerge del ruido y la amplitud media sale <= 0)."""
    if metodo == "homogeneo":
        return promedio_homogeneo(epocas), pesos_homogeneos(epocas)
    if metodo in ("s", "sn"):
        tam_bloque = min(tam_bloque, epocas.shape[0] // 2)  # garantiza >= 2 bloques
    try:
        return promedio_inhomogeneo(epocas, metodo, tiempos, ventana_senal, tam_bloque)
    except ValueError:
        return None


def snr_todos_los_metodos(epocas, tiempos, ventana_senal=VENTANA_SENAL, tam_bloque=50):
    """Calcula los cuatro promedios y su SNR con todas las épocas.
    Devuelve {metodo: {"pe", "pesos", "snr_db", "p_senal", "p_ruido", "rms_ruido"}}."""
    res = {}
    for metodo in METODOS:
        pe, pesos = _promediar(epocas, metodo, tiempos, ventana_senal, tam_bloque)
        res[metodo] = dict(pe=pe, pesos=pesos,
                           **calcular_snr(epocas, pe, pesos, tiempos, ventana_senal))
    return res


def curva_snr(epocas, tiempos, n_valores, metodo, n_rep=20, ventana_senal=VENTANA_SENAL,
              tam_bloque=50, n_perm=20, semilla=0):
    """SNR en función del número de épocas promediadas.
    Para cada N toma n_rep bloques de N épocas consecutivas con inicio aleatorio.
    Las potencias se promedian entre repeticiones ANTES del logaritmo: con N
    chico P_senal sale negativa en muchas repeticiones, y descartarlas (NaN)
    sesgaría la SNR hacia arriba.
    Devuelve dict con arrays de forma (len(n_valores), n_canales):
      n (N evaluados), snr_db, p_senal, p_ruido, n_validas (repeticiones usadas).
    snr_db es NaN si la P_senal media es <= 0 (el PEP no emerge todavía)."""
    M, C = epocas.shape[:2]
    n_valores = np.asarray(n_valores, dtype=int)
    if n_valores.min() < 4 or n_valores.max() > M:
        raise ValueError(f"Los N deben estar entre 4 y {M}.")
    rng = np.random.default_rng(semilla)
    p_s = np.zeros((len(n_valores), C))
    p_r = np.zeros((len(n_valores), C))
    n_val = np.zeros((len(n_valores), C), dtype=int)
    for i, n in enumerate(n_valores):
        reps = 1 if n == M else n_rep
        for inicio in rng.integers(0, M - n + 1, size=reps):
            sub = epocas[inicio:inicio + n]
            res = _promediar(sub, metodo, tiempos, ventana_senal, tam_bloque)
            if res is None:
                continue
            r = calcular_snr(sub, *res, tiempos, ventana_senal, n_perm)
            p_s[i] += r["p_senal"]
            p_r[i] += r["p_ruido"]
            n_val[i] += 1
    with np.errstate(divide="ignore", invalid="ignore"):
        p_s, p_r = p_s / n_val, p_r / n_val
        snr_db = np.where(p_s > 0, 10 * np.log10(p_s / p_r), np.nan)
    return dict(n=n_valores, snr_db=snr_db, p_senal=p_s, p_ruido=p_r, n_validas=n_val)


def snr_teorica_homogeneo(n_valores, snr_ref_db, n_ref):
    """Recta de referencia: con ruido blanco y estacionario, la SNR del promedio
    homogéneo crece 10 log10(N) (+3 dB por cada duplicación de N)."""
    return snr_ref_db + 10 * np.log10(np.asarray(n_valores) / n_ref)
