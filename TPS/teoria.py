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
#   - Amplitud base-pico: valor en el pico (la época ya tiene la línea de base
#     restada en segmentar_epocas).
#   - Amplitud pico a pico P40-N50: medida clínica habitual, menos sensible a
#     corrimientos lentos de la línea de base y al pasaaltos.
#
# VALORES DE REFERENCIA: orientativos. La latencia del P37/P40 en adultos ronda
# 37-40 ms y la del N20 ~19-20 ms; ambas dependen de la longitud del miembro y
# la altura. Límites superiores habituales: ~42-44 ms (P40) y ~22-23 ms (N20).
# Las amplitudes absolutas varían
# mucho entre sujetos (clínicamente importa más la asimetría entre lados).
# CONFIRMAR con la bibliografía de la materia (p. ej. Cruccu et al. 2008, Clin
# Neurophysiol; guía 9D de la ACNS) antes de usarlos en el informe.
import numpy as np
import pandas as pd

COMPONENTES_POR_NERVIO = {
    # polaridad, ventana de búsqueda (s), latencia de referencia (ms): (típica, lím. sup.)
    # El primer par de cada nervio define la amplitud pico a pico.
    "tibial": {
        "P40": dict(pol=+1, ventana=(0.032, 0.050), lat_ref=(38.0, 44.0)),
        "N50": dict(pol=-1, ventana=(0.042, 0.060), lat_ref=(47.0, None)),
        "P60": dict(pol=+1, ventana=(0.052, 0.070), lat_ref=(60.0, None)),
        "N75": dict(pol=-1, ventana=(0.062, 0.095), lat_ref=(75.0, None)),
    },
    "mediano": {
        "N20": dict(pol=-1, ventana=(0.015, 0.025), lat_ref=(19.5, 23.0)),
        "P25": dict(pol=+1, ventana=(0.020, 0.032), lat_ref=(25.0, None)),
        "N35": dict(pol=-1, ventana=(0.028, 0.042), lat_ref=(33.0, None)),
        "P45": dict(pol=+1, ventana=(0.038, 0.055), lat_ref=(45.0, None)),
    },
}
SEPARACION_MIN = 0.002   # s entre picos consecutivos


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
            filas.append(dict(componente=nombre, lat_ms=np.nan, amp_uV=np.nan, borde=True))
            continue
        idx = np.flatnonzero(m)
        k = idx[np.argmax(c["pol"] * pe[idx])]
        borde = k in (idx[0], idx[-1])
        t_prev = t[k]
        filas.append(dict(componente=nombre, lat_ms=t[k] * 1e3, amp_uV=pe[k] * 1e6, borde=borde))
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
            f.update(canal=canal, lat_ref_ms=tip, lat_lim_sup_ms=sup,
                     dif_ms=f["lat_ms"] - tip,
                     # un extremo en el borde de la ventana no es un pico: no se evalúa
                     dentro_rango=(f["lat_ms"] <= sup) if sup is not None and not f["borde"]
                     else None)
            filas.append(f)
        filas.append(dict(canal=canal, componente=f"{c1}-{c2} (pico a pico)",
                          amp_uV=abs(amp[c1] - amp[c2])))
    cols = ["canal", "componente", "lat_ms", "lat_ref_ms", "dif_ms", "lat_lim_sup_ms",
            "dentro_rango", "amp_uV", "borde"]
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