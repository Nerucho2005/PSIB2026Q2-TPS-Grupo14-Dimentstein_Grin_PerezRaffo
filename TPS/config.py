# config.py
# Parámetros del pipeline de PES del nervio MEDIANO (sub-001, ds004388).
#
# Objetivo del trabajo: cuantificar cómo mejora la relación señal/ruido (SNR) del
# potencial evocado según el tipo de promediado (homogéneo e inhomogéneo "n", "s",
# "sn") y según la cantidad de épocas promediadas (N).
#
# Bibliografía de las decisiones de diseño:
#   [P]    Nierula et al. (2024), PLOS Biol 22(10): e3002828 (paper del dataset).
#   [IFCN] Mauguière et al. (1999), Recommendations for the Practice of Clinical
#          Neurophysiology, EEG Suppl. 52, cap. 2.4 "Somatosensory evoked potentials".
from pathlib import Path

# ---- Rutas ----
RAIZ = Path(__file__).resolve().parent.parent      # raíz del repo (config.py está en TPS/)
DIR_RESULTADOS = RAIZ / "results"                  # CSV y figuras exploratorias (fuera de git)
DIR_FIGURAS = RAIZ / "informe" / "figuras"         # figuras finales del informe (graficos.py)

# ---- Registro ----
# [P] Experimento 1: mediano izquierdo en la muñeca, pulso de 0,2 ms apenas por encima
# del umbral motor, intervalo entre estímulos 763 ± 50 ms (~1,3 Hz), 4 bloques de 500
# estímulos por nervio. Se analiza el primer bloque del mediano de sub-001 (run-03).
# [IFCN] 500 barridos alcanzan para los componentes corticales tempranos.
SUJETO = "004"
RUN = "02"
DIR_DATOS = RAIZ / f"EEG-Paciente{int(SUJETO)}" # datos, fuera de git

BASE = f"sub-{SUJETO}_task-median_run-{RUN}"       # prefijo BIDS del run
ARCHIVO_EEG = DIR_DATOS / f"{BASE}_eeg.set"        # el .fdt debe estar al lado
ARCHIVO_EVENTOS = DIR_DATOS / f"{BASE}_events.tsv"

# ---- Canal ----
# [IFCN] el N20 se registra en la región parietal contralateral al brazo estimulado
# (Pc, 2 cm detrás de C3/C4, ≈ CP3/CP4 del sistema 10-10). [P] el estímulo fue en el
# brazo IZQUIERDO -> canal contralateral CP4. CP3 (ipsilateral) solo se usa para
# verificar la lateralidad (figura 05).
CANAL = "CP4"
CANALES = [CANAL]
CANALES_LATERALIDAD = ["CP3", "CP4"]

# ---- Referencia ----
# [IFCN] montaje cortical del mediano Pc-Fz: el P20 frontal tiene polaridad opuesta al
# N20 parietal, así que la derivación CP4-Fz los suma. [P] el EEG se adquirió contra la
# mastoides derecha (RM) y Fz se agregó a propósito para poder re-referenciar.
# La lateralidad se evalúa con una referencia simétrica (mastoides enlazadas), porque
# con Fz el P20 frontal invertido aparece en ambos hemisferios (falso "N20" en CP3).
# Opciones: "RM", "Fz", "FPz", lista de canales, "mastoides_enlazadas", "promedio".
REFERENCIA = "Fz"
REFERENCIA_LATERALIDAD = "mastoides_enlazadas"

# ---- Artefacto de estimulación (se interpola ANTES de filtrar) ----
# [P] interpolan con PCHIP en ventanas individuales (~-1,8 a +4,4 ms). Acá se usa una
# recta de -1 a +3 ms: el artefacto dura ~1,5 ms (chequeo_artefacto.py) y la ventana
# queda fuera de la del PEP, así que la forma de la interpolación no lo afecta.
INTERPOLAR_ARTEFACTO = True
T_ARTEFACTO = (-0.001, 0.003)    # s respecto del estímulo

# ---- Filtrado (Butterworth pasabanda orden 4 + notch, fase cero) ----
# [P] EEG cortical: Butterworth de orden 4, fase cero, pasabanda 30-400 Hz y notch de
# 48-53 Hz. Se adopta la misma banda para que los resultados sean comparables con el
# paper. El pasaaltos de 30 Hz elimina la actividad de fondo lenta (alfa, deriva), que
# es la mayor parte del ruido; el N20-P25 es un componente rápido y se conserva
# (comparar_filtros.py). [IFCN] recomienda bandas más anchas para el registro clínico
# (pasaaltos < 3 Hz, pasabajos > 2000 Hz) y el notch apagado: el filtro de fase cero
# no corre latencias y el notch es angosto (Q = 30), así que se mantiene; ver
# comparar_filtros.py para el efecto de cada banda.
F_BAJO = 30.0     # Hz
F_ALTO = 400.0    # Hz
ORDEN = 4
F_NOTCH = 50.0    # Hz (None desactiva el notch)
Q_NOTCH = 30.0

# ---- Segmentación ----
# La época empieza en -30 ms para que la línea de base contenga la ventana de ruido de
# la SNR del paper (misma duración que la de señal, antes del estímulo).
TMIN = -0.030     # s
TMAX = 0.080      # s

# ---- Promedios y SNR ----
# Ventana del PEP donde se miden la SNR y las amplitudes de bloque: complejo N20-P25,
# la respuesta cortical primaria que la IFCN usa para latencia y amplitud. Con Fz, los
# componentes posteriores a ~25 ms se mezclan con el N30 frontal invertido.
VENTANA_SENAL = (0.015, 0.030)   # s
TAM_BLOQUE = 50                  # épocas por bloque para estimar amplitudes (modos s, sn)
# N para la curva SNR vs. N (M se agrega solo). Bloques DISJUNTOS de N épocas
# consecutivas; con N <= M/4 hay >= 4 bloques independientes.
N_VALORES = [25, 50, 100, 125, 250]
N_BLOQUES_JK = 10                # bloques del jackknife para el error estándar de la SNR
# SNR del paper [P]: RMS en ±1 ms alrededor del pico del N20 / RMS en una ventana de
# igual duración antes del estímulo (métrica complementaria).
SEMIANCHO_SNR_PAPER = 0.001      # s
