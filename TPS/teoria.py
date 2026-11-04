# teoria.py
# Etapa 7: latencias y amplitudes del PEP (tibial o mediano), medidas
# automáticamente y comparadas con valores de referencia.
#
# Nomenclatura: polaridad + latencia típica en ms.
#
# Nervio TIBIAL (canales CPz/Cz; en la literatura P40/N50 = P37/N45):
#   P40 (P37): primer componente cortical, área somatosensorial del pie (cara
#              medial del hemisferio). Máximo en CPz/Cz', o en CP1/CP2 del lado
#              ipsilateral a la pierna estimulada (dipolo horizontal).
#   N50 (N45), P60, N75: componentes siguientes.
#
# Nervio MEDIANO (canal CP3 o CP4 CONTRALATERAL al brazo estimulado = C3'/C4'):
#   N20: primer componente cortical (área 3b, giro poscentral).
#   P25 (P27), N35 (N33), P45: componentes parietales siguientes.
#   En el canal ipsilateral el N20 no aparece: sirve para identificar el lado.
#
# Medición:
#   - Cada pico es el extremo con la polaridad esperada dentro de su ventana de
#     búsqueda. La ventana de cada componente empieza después del pico anterior,
#     para respetar el orden P40 -> N50 -> P60 -> N75.
#   - Si el extremo cae en el borde de la ventana, no es un pico real (la señal
#     sigue subiendo/bajando): se marca en la columna "borde".
#   - Si el extremo tiene la polaridad CONTRARIA a la esperada (p. ej. un "N35"
#     positivo porque toda la ventana es positiva), el componente no está presente:
#     se marca "polaridad_ok" = False. Pasa en el mediano con referencia Fz, donde el
#     N30 frontal invertido vuelve positiva la región del N35.
#   - "valido" = pico real (no borde) y con la polaridad esperada. Solo los válidos se
#     comparan con las normas y el paper.
#   - Amplitud base-pico: valor en el pico (la época ya tiene la línea de base
#     restada en segmentar_epocas).
#   - Amplitud pico a pico P40-N50: medida clínica habitual, menos sensible a
#     corrimientos lentos de la línea de base y al pasaaltos.
#
# VALORES CLÍNICOS (lat_ref, amp_ref): guía de la IFCN, Mauguière et al. (1999),
# "Somatosensory evoked potentials", EEG Suppl. 52, Tablas 3 y 4 (adultos jóvenes,
# altura 1,70 ± 0,1 m). Límite superior de latencia = media + 3 SD.
#   Mediano: N20 (Pc-EPc) 19,8 ms, límite 23,0 ms. N20-P25 pico a pico (Pc-Fz)
#            3,2 µV, límite inferior 0,8 µV.
#   Tibial:  P39 (= P40) (Cz'-Ei) 38,0 ms, límite 43,9 ms. P39-N50 1,8 µV,
#            límite inferior 0,5 µV.
# Para N50, P60, N75, P25, N35 y P45 la guía no da latencias: se usan valores
# nominales (el número del nombre) sin límite.
# OJO: las normas se definen para montajes clínicos (Pc-Fz, Cz'-Fz/Ei), que son los
# que usa el pipeline (REFERENCIA = "Fz"); con otra
# referencia las amplitudes no son directamente comparables y la latencia puede
# correrse ~1 ms (ver comparar_referencias.py).
#
# VALORES DEL DATASET (lat_paper): media y desvío estándar del grupo de Nierula
# et al. (2024, PLOS Biol, Tabla 1; N = 36, estímulo en muñeca/tobillo izquierdos).
# El paper reporta media ± error estándar: N20 19,81 ± 0,20 ms y P40 40,86 ±
# 0,38 ms. SD = EE·√36 -> N20 ≈ 1,20 ms, P40 ≈ 2,28 ms. Ojo: ellos extraen los
# componentes con CCA (filtro espacial) sobre referencia promedio y 30-400 Hz,
# así que la comparación de latencias es razonable pero no la de amplitudes
# (unidades arbitrarias). Se reporta z = (lat - media) / SD.
import numpy as np
import pandas as pd

COMPONENTES_POR_NERVIO = {
    # polaridad, ventana de búsqueda (s), latencia de referencia (ms): (típica, lím. sup.)
    # El primer par de cada nervio define la amplitud pico a pico.
    "tibial": {
        "P40": dict(pol=+1, ventana=(0.032, 0.050), lat_ref=(38.0, 43.9),
                    lat_paper=(40.86, 0.38 * 6)),
        "N50": dict(pol=-1, ventana=(0.042, 0.060), lat_ref=(47.0, None)),
        "P60": dict(pol=+1, ventana=(0.052, 0.070), lat_ref=(60.0, None)),
        "N75": dict(pol=-1, ventana=(0.062, 0.095), lat_ref=(75.0, None)),
    },
    "mediano": {
        "N20": dict(pol=-1, ventana=(0.015, 0.025), lat_ref=(19.8, 23.0),
                    lat_paper=(19.81, 0.20 * 6)),
        "P25": dict(pol=+1, ventana=(0.020, 0.032), lat_ref=(25.0, None)),
        "N35": dict(pol=-1, ventana=(0.028, 0.042), lat_ref=(33.0, None)),
        "P45": dict(pol=+1, ventana=(0.038, 0.055), lat_ref=(45.0, None)),
    },
}
SEPARACION_MIN = 0.002   # s entre picos consecutivos

# Amplitud pico a pico de los dos primeros componentes (IFCN): (media, límite inferior) en µV
AMP_PICO_A_PICO_REF = {"tibial": (1.8, 0.5), "mediano": (3.2, 0.8)}

# Control de calidad de la IFCN: dos repeticiones deben coincidir en latencia
# (0,25 ms; 0,5 ms para el P39 tibial) y en amplitud (dentro del 20 %).
TOLERANCIA_REPRODUCIBILIDAD = {"tibial": (0.5, 0.20), "mediano": (0.25, 0.20)}


def componentes_de(nervio):
    if nervio not in COMPONENTES_POR_NERVIO:
        raise ValueError(f"nervio debe ser uno de {list(COMPONENTES_POR_NERVIO)}, no {nervio!r}.")
    return COMPONENTES_POR_NERVIO[nervio]


def medir_componentes(t, pe, componentes):
    """Latencia y amplitud de cada componente en UN canal.
    t: (n_muestras,) en s | pe: (n_muestras,) en V.
    Devuelve una lista de dicts (uno por componente)."""
    filas, t_prev = [], -np.inf
    for nombre, c in componentes.items():
        ini = max(c["ventana"][0], t_prev + SEPARACION_MIN)
        m = (t >= ini) & (t <= c["ventana"][1])
        if m.sum() < 3:
            filas.append(dict(componente=nombre, lat_ms=np.nan, amp_uV=np.nan, borde=True,
                              polaridad_ok=False, valido=False))
            continue
        idx = np.flatnonzero(m)
        k = idx[np.argmax(c["pol"] * pe[idx])]
        borde = k in (idx[0], idx[-1])
        polaridad_ok = bool(c["pol"] * pe[k] > 0)
        t_prev = t[k]
        filas.append(dict(componente=nombre, lat_ms=t[k] * 1e3, amp_uV=pe[k] * 1e6, borde=borde,
                          polaridad_ok=polaridad_ok, valido=bool(not borde and polaridad_ok)))
    return filas


def comparar_con_teoria(t, pe, canales, nervio="tibial"):
    """Tabla medido vs. teórico para todos los canales de un promedio.
    pe: (n_canales, n_muestras) | nervio: "tibial" o "mediano".
    Devuelve un DataFrame con una fila por canal y componente, más la amplitud
    pico a pico de los dos primeros componentes (P40-N50 o N20-P25)."""
    componentes = componentes_de(nervio)
    c1, c2 = list(componentes)[:2]
    filas = []
    for i, canal in enumerate(canales):
        medidas = medir_componentes(t, pe[i], componentes)
        amp = {f["componente"]: f["amp_uV"] for f in medidas}
        for f in medidas:
            tip, sup = componentes[f["componente"]]["lat_ref"]
            media, sd = componentes[f["componente"]].get("lat_paper", (np.nan, np.nan))
            z = (f["lat_ms"] - media) / sd if f["valido"] else np.nan
            f.update(canal=canal, lat_ref_ms=tip, lat_lim_sup_ms=sup,
                     lat_paper_ms=media, sd_paper_ms=sd, z_paper=z,
                     dif_ms=f["lat_ms"] - tip,
                     # un extremo en el borde o con polaridad invertida no es un pico: no se evalúa
                     dentro_rango=(f["lat_ms"] <= sup) if sup is not None and f["valido"]
                     else None)
            filas.append(f)
        pp = abs(amp[c1] - amp[c2])
        amp_media, amp_lim = AMP_PICO_A_PICO_REF[nervio]
        en_borde = any(not f["valido"] for f in medidas if f["componente"] in (c1, c2))
        filas.append(dict(canal=canal, componente=f"{c1}-{c2} (pico a pico)", amp_uV=pp,
                          amp_ref_uV=amp_media, amp_lim_inf_uV=amp_lim,
                          # sin picos reales no se evalúa
                          dentro_rango=None if en_borde else bool(pp >= amp_lim)))
    cols = ["canal", "componente", "lat_ms", "lat_ref_ms", "dif_ms", "lat_lim_sup_ms",
            "dentro_rango", "lat_paper_ms", "sd_paper_ms", "z_paper", "amp_uV",
            "amp_ref_uV", "amp_lim_inf_uV", "borde", "polaridad_ok", "valido"]
    return pd.DataFrame(filas)[cols]


def tabla_metodos(t, pes, canales, nervio="tibial"):
    """Compara los componentes entre métodos de promediado.
    pes: {metodo: pe (n_canales, n_muestras)}. Devuelve un DataFrame ancho:
    filas (canal, componente), columnas (lat_ms | amp_uV) x método."""
    partes = []
    for met, pe in pes.items():
        df = comparar_con_teoria(t, pe, canales, nervio)
        df["metodo"] = met
        partes.append(df)
    df = pd.concat(partes)
    return df.pivot_table(index=["canal", "componente"], columns="metodo",
                          values=["lat_ms", "amp_uV"], sort=False).round(2)

def reproducibilidad(t, epocas, canales, nervio="tibial", modo="mitades"):
    """Control de calidad de la IFCN: las respuestas deben replicarse. Se divide el
    ensamble en dos subpromedios y se compara el primer componente cortical (N20 o
    P40) y la amplitud pico a pico de los dos primeros componentes.
    modo: "mitades" (primera vs. segunda mitad del registro: imita dos corridas
    sucesivas, sensible a cambios lentos) o "par_impar" (épocas alternadas).
    epocas: (n_epocas, n_canales, n_muestras), en orden temporal.
    Devuelve un DataFrame por canal con las dos mediciones, las diferencias y si
    cumplen la tolerancia (latencia en ms, amplitud relativa)."""
    M = epocas.shape[0]
    if modo == "mitades":
        a, b = epocas[: M // 2], epocas[M // 2:]
    elif modo == "par_impar":
        a, b = epocas[0::2], epocas[1::2]
    else:
        raise ValueError('modo debe ser "mitades" o "par_impar".')
    tol_lat, tol_amp = TOLERANCIA_REPRODUCIBILIDAD[nervio]
    c1 = list(componentes_de(nervio))[0]
    ta = comparar_con_teoria(t, a.mean(axis=0), canales, nervio).set_index(["canal", "componente"])
    tb = comparar_con_teoria(t, b.mean(axis=0), canales, nervio).set_index(["canal", "componente"])
    filas = []
    for canal in canales:
        pp = [c for c in ta.loc[canal].index if "pico a pico" in c][0]
        lat_a, lat_b = ta.loc[(canal, c1), "lat_ms"], tb.loc[(canal, c1), "lat_ms"]
        amp_a, amp_b = ta.loc[(canal, pp), "amp_uV"], tb.loc[(canal, pp), "amp_uV"]
        d_lat = abs(lat_a - lat_b)
        d_amp = abs(amp_a - amp_b) / max(amp_a, amp_b)
        valido = bool(ta.loc[(canal, c1), "valido"] and tb.loc[(canal, c1), "valido"])
        filas.append(dict(canal=canal, componente=c1, lat_1_ms=lat_a, lat_2_ms=lat_b,
                          dif_lat_ms=d_lat, pp_1_uV=amp_a, pp_2_uV=amp_b, dif_amp_rel=d_amp,
                          cumple_lat=bool(d_lat <= tol_lat) if valido else None,
                          cumple_amp=bool(d_amp <= tol_amp) if valido else None))
    return pd.DataFrame(filas)