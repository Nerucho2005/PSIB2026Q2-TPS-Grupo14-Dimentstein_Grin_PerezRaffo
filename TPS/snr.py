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
# INCERTIDUMBRE: no se usa bootstrap con reemplazo, porque repite épocas (dos copias
# de una época con signos opuestos se cancelan en el promedio alternado) y rompe el
# orden temporal. Se usa JACKKNIFE POR BLOQUES de épocas consecutivas:
#   - jackknife_snr: SNR con todas las épocas ± error estándar (quitando 1 de 10 bloques).
#   - diferencia_metodos: diferencia de SNR entre métodos con IC pareado.
#   - curva_snr: para cada N, bloques DISJUNTOS de N épocas consecutivas (estimaciones
#     independientes) y jackknife sobre los bloques.
#   - ajustar_pendiente: pendiente de SNR vs. log10(N) (teórica: 10 dB/década).
# Para los modos "s" y "sn", promedio.py exige >= 2 bloques de amplitud, así que con
# N chico se reduce tam_bloque a N // 2 (ver _promediar). Aclararlo en el informe.
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
        pass
    # promedio.amplitudes falla si CUALQUIER canal no tiene un PEP estimable (p. ej. el
    # canal ipsilateral del mediano): se reintenta canal por canal y se deja NaN solo
    # en los que fallan, para no perder los demás.
    M, C, N = epocas.shape
    pe, pesos = np.full((C, N), np.nan), np.full((M, C), np.nan)
    algun_ok = False
    for c in range(C):
        try:
            pe_c, w_c = promedio_inhomogeneo(epocas[:, [c]], metodo, tiempos, ventana_senal,
                                             tam_bloque)
            pe[c], pesos[:, c], algun_ok = pe_c[0], w_c[:, 0], True
        except ValueError:
            continue
    return (pe, pesos) if algun_ok else None


def snr_todos_los_metodos(epocas, tiempos, ventana_senal=VENTANA_SENAL, tam_bloque=50):
    """Calcula los cuatro promedios y su SNR con todas las épocas.
    Devuelve {metodo: {"pe", "pesos", "snr_db", "p_senal", "p_ruido", "rms_ruido"}}."""
    res = {}
    for metodo in METODOS:
        prom = _promediar(epocas, metodo, tiempos, ventana_senal, tam_bloque)
        if prom is None:
            raise ValueError(
                f'Modo "{metodo}": la amplitud media del PEP estimada en {ventana_senal} s '
                "no es positiva. Revisá la ventana de señal, los canales o la polaridad.")
        pe, pesos = prom
        res[metodo] = dict(pe=pe, pesos=pesos,
                           **calcular_snr(epocas, pe, pesos, tiempos, ventana_senal))
    return res


MIN_BLOQUES_DISJUNTOS = 4


def _snr_db(p_s, p_r):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(p_s > 0, 10 * np.log10(p_s / p_r), np.nan)


def _potencias(epocas, metodo, tiempos, ventana_senal, tam_bloque, n_perm):
    """(p_senal, p_ruido) por canal de un subconjunto, o None si no se puede promediar."""
    res = _promediar(epocas, metodo, tiempos, ventana_senal, tam_bloque)
    if res is None:
        return None
    r = calcular_snr(epocas, *res, tiempos, ventana_senal, n_perm)
    return r["p_senal"], r["p_ruido"]


def _bloques(M, k):
    """Índices de k bloques consecutivos que cubren 0..M-1 (tamaños pares cuando se puede,
    para no romper los pares del promedio alternado)."""
    bordes = np.round(np.linspace(0, M, k + 1) / 2).astype(int) * 2
    bordes[-1] = M
    return [np.arange(bordes[i], bordes[i + 1]) for i in range(k)]


def _jackknife(replicas, estimado):
    """Error estándar jackknife a partir de las k réplicas leave-one-out (axis 0)."""
    k = replicas.shape[0]
    validas = np.isfinite(replicas).all(axis=0) & np.isfinite(estimado)
    import warnings
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)      # canales sin réplicas válidas
        media = np.nanmean(replicas, axis=0)
        se = np.sqrt((k - 1) / k * np.nansum((replicas - media) ** 2, axis=0))
    return np.where(validas, se, np.nan)


def jackknife_snr(epocas, tiempos, metodos=METODOS, n_bloques=10, ventana_senal=VENTANA_SENAL,
                  tam_bloque=50, n_perm=50, estricto=True):
    """SNR con todas las épocas y su error estándar por JACKKNIFE POR BLOQUES.
    Se divide el registro en n_bloques bloques consecutivos y se recalcula la SNR
    quitando uno por vez (sin repetir épocas y respetando el orden temporal, que
    necesitan el promedio alternado y los bloques de amplitud de promedio.py).
    Devuelve {metodo: {"snr_db", "se_db", "replicas"}} con arrays por canal;
    "replicas" (n_bloques, n_canales) sirve para comparar métodos de forma pareada."""
    M = epocas.shape[0]
    bloques = _bloques(M, n_bloques)
    res = {}
    for met in metodos:
        completo = _potencias(epocas, met, tiempos, ventana_senal, tam_bloque, n_perm)
        if completo is None:
            if estricto:
                raise ValueError(f'Modo "{met}": no se pudo promediar con todas las épocas.')
            nan = np.full(epocas.shape[1], np.nan)
            res[met] = dict(snr_db=nan, se_db=nan, replicas=np.full((n_bloques, nan.size), np.nan))
            continue
        reps = []
        for b in bloques:
            sub = epocas[np.setdiff1d(np.arange(M), b)]
            p = _potencias(sub, met, tiempos, ventana_senal, tam_bloque, n_perm)
            reps.append(_snr_db(*p) if p is not None else np.full(epocas.shape[1], np.nan))
        reps = np.array(reps)
        snr = _snr_db(*completo)
        res[met] = dict(snr_db=snr, se_db=_jackknife(reps, snr), replicas=reps)
    return res


def diferencia_metodos(jk, metodo="n", referencia="homogeneo", confianza=0.95):
    """Diferencia de SNR (dB) entre dos métodos con IC por jackknife PAREADO: cada
    réplica quita el mismo bloque en ambos métodos, así se cancela la variabilidad
    común y el IC refleja solo la diferencia. jk: salida de jackknife_snr.
    Devuelve dict con arrays por canal: dif_db, se_db, ic_inf, ic_sup."""
    from scipy.stats import t as t_student
    dif = jk[metodo]["snr_db"] - jk[referencia]["snr_db"]
    reps = jk[metodo]["replicas"] - jk[referencia]["replicas"]
    se = _jackknife(reps, dif)
    q = t_student.ppf(0.5 + confianza / 2, reps.shape[0] - 1)
    return dict(dif_db=dif, se_db=se, ic_inf=dif - q * se, ic_sup=dif + q * se)


def curva_snr(epocas, tiempos, n_valores, metodo, ventana_senal=VENTANA_SENAL, tam_bloque=50,
              n_perm=50, n_bloques_jk=10):
    """SNR en función del número de épocas promediadas, con error estándar.
    Para cada N se toman los M // N BLOQUES DISJUNTOS de N épocas consecutivas
    (estimaciones independientes). Las potencias se promedian entre bloques ANTES del
    logaritmo (descartar los bloques con P_senal < 0 sesgaría la SNR hacia arriba), y
    el error estándar sale de un jackknife sobre los bloques. Si entran menos de
    MIN_BLOQUES_DISJUNTOS bloques (N > M/4, incluido N = M), el jackknife con tan pocos
    bloques no es confiable y se usa el jackknife por bloques dentro de las primeras N épocas.
    Devuelve dict con arrays (len(n_valores), n_canales): n, snr_db, se_db, n_bloques."""
    M, C = epocas.shape[:2]
    n_valores = np.asarray(n_valores, dtype=int)
    if n_valores.min() < 4 or n_valores.max() > M:
        raise ValueError(f"Los N deben estar entre 4 y {M}.")
    snr = np.full((len(n_valores), C), np.nan)
    se = np.full((len(n_valores), C), np.nan)
    n_blq = np.zeros(len(n_valores), dtype=int)
    for i, n in enumerate(n_valores):
        k = M // n
        if k >= MIN_BLOQUES_DISJUNTOS:
            pot = [_potencias(epocas[b * n:(b + 1) * n], metodo, tiempos, ventana_senal,
                              tam_bloque, n_perm) for b in range(k)]
            pot = [p for p in pot if p is not None]
            if len(pot) < 2:
                continue
            ps, pr = np.array([p[0] for p in pot]), np.array([p[1] for p in pot])
            snr[i] = _snr_db(ps.mean(0), pr.mean(0))
            reps = np.array([_snr_db(np.delete(ps, j, 0).mean(0), np.delete(pr, j, 0).mean(0))
                             for j in range(len(pot))])
            se[i] = _jackknife(reps, snr[i])
            n_blq[i] = len(pot)
        else:
            jk = jackknife_snr(epocas[:n], tiempos, (metodo,), n_bloques_jk, ventana_senal,
                               tam_bloque, n_perm, estricto=False)[metodo]
            snr[i], se[i], n_blq[i] = jk["snr_db"], jk["se_db"], 1
    return dict(n=n_valores, snr_db=snr, se_db=se, n_bloques=n_blq)


def ajustar_pendiente(n_valores, snr_db, se_db=None):
    """Ajusta SNR = a + b·log10(N) por mínimos cuadrados (ponderados por 1/se² si se
    dan). Con ruido estacionario e independiente, b = 10 dB/década (+3 dB por
    duplicación). Devuelve (a, b, se_b) para un canal; NaN se ignoran."""
    x = np.log10(np.asarray(n_valores, float))
    y = np.asarray(snr_db, float)
    w = np.ones_like(y) if se_db is None else 1 / np.maximum(np.asarray(se_db, float), 1e-3) ** 2
    ok = np.isfinite(y) & np.isfinite(w)
    if ok.sum() < 3:
        return np.nan, np.nan, np.nan
    X = np.column_stack([np.ones(ok.sum()), x[ok]])
    W = np.diag(w[ok])
    cov = np.linalg.inv(X.T @ W @ X)
    a, b = cov @ X.T @ W @ y[ok]
    resid = y[ok] - X @ np.array([a, b])
    s2 = (w[ok] * resid ** 2).sum() / max(ok.sum() - 2, 1)
    return a, b, np.sqrt(cov[1, 1] * s2)


def snr_teorica_ajustada(n_valores, snr_db, se_db=None):
    """Recta teórica +10·log10(N) con la ordenada ajustada sobre TODOS los puntos
    (ponderados por 1/se²), en lugar de anclarla en el último (el más ruidoso)."""
    x = 10 * np.log10(np.asarray(n_valores, float))
    y = np.asarray(snr_db, float)
    w = np.ones_like(y) if se_db is None else 1 / np.maximum(np.asarray(se_db, float), 1e-3) ** 2
    ok = np.isfinite(y) & np.isfinite(w)
    if not ok.any():
        return np.full_like(x, np.nan)
    c = np.sum(w[ok] * (y[ok] - x[ok])) / np.sum(w[ok])
    return c + x


def snr_teorica_homogeneo(n_valores, snr_ref_db, n_ref):
    # Se conserva por compatibilidad; usar snr_teorica_ajustada.
    """Recta de referencia: con ruido blanco y estacionario, la SNR del promedio
    homogéneo crece 10 log10(N) (+3 dB por cada duplicación de N)."""
    return snr_ref_db + 10 * np.log10(np.asarray(n_valores) / n_ref)