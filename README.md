# PSIB2026Q2 · TPS Grupo 14 · Dimentstein, Grin, Pérez Raffo

**Potenciales evocados somatosensoriales (PES) del nervio tibial y del nervio mediano: filtrado, segmentación, promediado homogéneo e inhomogéneo y evaluación de la SNR.**

> **Nota para una IA que lea este archivo.** Este README es el contexto completo del proyecto. Describe el objetivo, los datos, la estructura del repositorio, cada módulo y función, las decisiones metodológicas ya tomadas (con su justificación y resultados) y las tareas pendientes. Antes de proponer cambios, respetá las convenciones de la sección 9 y revisá la sección 10 (pendientes). Los resultados numéricos de la sección 8 son del sujeto `sub-001`.

---

## 1. Objetivo del trabajo

Trabajo Práctico de Señales (TPS) de la materia 16.63 *Procesamiento de Señales e Imágenes Biomédicas* (ITBA). Objetivos de la cátedra:

1. Filtrar el EEG (ruido de línea de 50 Hz, actividad de fondo y artefactos) **sin distorsionar la latencia de los picos**.
2. Segmentar en épocas alineadas al estímulo (t = 0) y promediar (*ensemble averaging*).
3. Evaluar cuantitativamente cómo mejora la **relación señal/ruido (SNR)** al agregar realizaciones, comparando el promedio **homogéneo** con el **inhomogéneo**.
4. Analizar por separado la estimulación del **nervio tibial** y la del **nervio mediano**.

Componentes buscados:

| Nervio | Componentes corticales | Canales | Primer componente |
|---|---|---|---|
| Tibial (pierna) | P40 (=P37), N50 (=N45), P60, N75 | Cz, **CPz** (≈ Cz') | P40, ~37–41 ms |
| Mediano (brazo) | N20, P25, N35, P45 | CP3 / **CP4** (≈ C3'/C4'), **contralateral** al brazo | N20, ~18–20 ms |

---

## 2. Datos

- **Dataset:** OpenNeuro **ds004388** (Nierula et al., 2024), versión 1.0.0, formato BIDS.
- **Sujeto analizado:** `sub-001`. Runs usados: `task-tibial_run-02` y `task-median_run-03` (500 estímulos cada uno, ~395 s).
- **Formato:** EEGLAB. El `.set` es el encabezado y el `.fdt` contiene la señal (`float32`, ~1,8 GB por run). Ambos deben estar en la misma carpeta.
- **Archivos por run:** `_eeg.set`, `_eeg.fdt`, `_eeg.json` (metadatos de adquisición), `_channels.tsv`, `_events.tsv` (un estímulo por fila: `onset` en s, `sample`, `trial_type == "stimulus"`) y `_events.json`.
- **Frecuencia de muestreo:** 10 kHz. **114 canales:** 64 de EEG de cuero cabelludo, electrodos espinales (`S..`, `SC..`, `L1`, `L4`, `AC`, `AL`; referenciados a TH6), ECG, EMG/ENG, etc.
- **Referencia de adquisición del EEG: mastoides derecha (RM).** No figura como canal. `LM` (mastoides izquierda) sí está disponible.
- **Lateralidad del mediano:** se estimuló el **brazo izquierdo**. El N20 aparece en **CP4** y no en CP3 (ver sección 8).

**Descarga** (CMD de Windows, desde la raíz del repo). `openneuro-py` respeta la estructura BIDS, así que se descarga a una carpeta temporal y después se mueve:

```
openneuro-py download --dataset=ds004388 --tag=1.0.0 --target-dir="tmp_descarga" --include="sub-001/eeg/sub-001_task-median_run-03_*"
move tmp_descarga\sub-001\eeg\sub-001_task-median_run-03_* EEG-Paciente1\
rmdir /s /q tmp_descarga
```

Cada run ocupa ~1,8 GB: conviene descargar de a uno y verificar el tamaño del `.fdt`. Una descarga anterior falló por disco lleno y dejó `.fdt` truncados.

---

## 3. Estructura del repositorio

Todo plano, sin subcarpetas en `TPS/`. Cada archivo tiene un dueño, para minimizar conflictos.

```
PSIB2026Q2-TPS-Grupo14-Dimentstein_Grin_PerezRaffo/
├── EEG-Paciente1/          # datos .set/.fdt/.tsv/.json (FUERA de git)
├── TPS/
│   ├── config.py               # parámetros compartidos (único archivo común)
│   ├── filtrado.py             # etapa 1: carga, canales, interpolación del artefacto, filtrado
│   ├── segmentacion.py         # etapa 2: eventos y épocas
│   ├── promedio.py             # etapas 3–4: promedio homogéneo e inhomogéneo
│   ├── snr.py                  # etapa 6: SNR por promedio alternado y curva SNR vs. N
│   ├── teoria.py               # etapa 7: latencias y amplitudes vs. referencia
│   ├── main.py                 # corre todo de punta a punta
│   ├── chequeo_artefacto.py    # verificación: artefacto de estímulo e interpolación
│   └── comparar_pasaaltos.py   # verificación: justificación del pasaaltos
├── results/                # salidas de los scripts (FUERA de git, se regenera)
├── informe/                # figuras y tablas finales copiadas desde results/
├── .gitignore              # results/, __pycache__/, EEG-Paciente1/
├── requirements.txt        # mne, mne-bids, numpy, scipy, pandas, matplotlib, seaborn, openneuro-py, jupyter
└── README.md
```

**Dueños según el flujo pactado:** Nico → `filtrado.py`, `segmentacion.py`, `promedio.py`. Rama → `snr.py`, `teoria.py`, gráficos. `config.py` y `main.py` son compartidos.

**Pendiente de integración:** en otra rama se está desarrollando una interfaz gráfica. Regla para integrarla: **la GUI solo llama a las funciones de los `.py`**, sin reimplementar cálculos.

---

## 4. Cómo ejecutar

```
pip install -r requirements.txt
python TPS/main.py                  # pipeline completo
python TPS/chequeo_artefacto.py     # verificación del artefacto
python TPS/comparar_pasaaltos.py    # comparación de cortes del pasaaltos
```

Para cambiar de nervio, editar en `config.py`: `NERVIO = "tibial"` o `"mediano"`. Todo lo demás (archivo, canales, ventanas) se ajusta solo.

---

## 5. Orden del pipeline

```
_events.tsv ──► cargar_eventos ──► muestras de estímulo
                                        │
.set/.fdt ──► cargar_eeg ──► seleccionar_canales ──► interpolar_artefacto ──► filtro 5–100 Hz + notch 50 Hz (fase cero)
                                                                                       │
                                                         segmentar_epocas (−20 a 120 ms; línea de base −20 a 0 ms)
                                                                                       │
                                     promedio_homogeneo / promedio_inhomogeneo ("n", "s", "sn")
                                                                                       │
                                     calcular_snr / curva_snr  ──►  comparar_con_teoria / tabla_metodos  ──►  figuras y CSV
```

El orden importa: **el artefacto se interpola sobre el registro crudo, antes de filtrar.** Si se filtrara primero, el filtro de fase cero (no causal) dispersaría el pulso hacia ambos lados de t = 0.

---

## 6. Módulos y funciones

Convenciones de datos en todo el pipeline:
- `epocas`: array `(n_epocas, n_canales, n_muestras)` en **V**, **en orden temporal** (requisito del promedio por bloques y del promedio alternado).
- `tiempos` / `t`: `(n_muestras,)` en **s**, con 0 = estímulo.
- `pe`: promedio `(n_canales, n_muestras)` en V.
- `pesos`: `(n_epocas, n_canales)`.
- Ventanas temporales siempre en segundos.

### 6.1 `config.py`: parámetros

| Parámetro | Valor | Descripción |
|---|---|---|
| `NERVIO` | `"tibial"` / `"mediano"` | Selecciona todo lo que depende del nervio. |
| `SUJETO`, `RUN`, `TAREA`, `BASE` | `001`, `02`/`03` | Arman el nombre BIDS del archivo. |
| `ARCHIVO_EEG`, `ARCHIVO_EVENTOS` | rutas | Construidas con `Path(__file__)`, independientes del directorio de ejecución. |
| `CANALES` | tibial `["Cz","CPz"]`, mediano `["CP3","CP4"]` | En el mediano se dejan los dos para identificar el lado contralateral. |
| `INTERPOLAR_ARTEFACTO`, `T_ARTEFACTO` | `True`, `(-0.001, 0.003)` | Ventana de interpolación respecto de cada estímulo. |
| `F_BAJO`, `F_ALTO`, `ORDEN` | 5 Hz, 100 Hz, 4 | Butterworth pasabanda, aplicado con `sosfiltfilt` (fase cero). |
| `F_NOTCH`, `Q_NOTCH` | 50 Hz, 30 | Notch IIR; `None` lo desactiva. |
| `TMIN`, `TMAX` | −0,020 s; 0,120 (tibial) / 0,080 (mediano) | Límites de la época. |
| `VENTANA_SENAL` | tibial (0,015–0,080), mediano (0,012–0,060) | Dónde está el PEP; se usa para amplitudes `a_b` y para la SNR. |
| `TAM_BLOQUE` | 50 | Épocas por bloque para estimar amplitudes. |
| `N_VALORES`, `N_REP` | [10, 25, …, 400], 20 | Curva SNR vs. N (M se agrega solo). |

### 6.2 `filtrado.py`: etapa 1

| Función | Qué hace |
|---|---|
| `cargar_eeg(ruta, archivo)` | Abre el `.set` con `mne.io.read_raw_eeglab(preload=False)`, sin cargar los datos en memoria. Avisa si falta el `.fdt`. |
| `seleccionar_canales(raw, canales)` | Copia del registro solo con los canales pedidos (sin distinguir mayúsculas). Avisa si falta alguno. **Limitación actual: descarta los demás canales, lo que impide re-referenciar después** (ver pendiente 1). |
| `interpolar_artefacto(datos, muestras_estimulo, fs, t_ini, t_fin)` | Para cada estímulo, reemplaza las muestras entre `t_ini` y `t_fin` por una **recta** que une la muestra en `t_ini` con la muestra en `t_fin`. Opera sobre un array `(n_canales, n_muestras)` y devuelve una copia. |
| `_disenar_filtros(...)` | Diseña el Butterworth pasabanda y el notch en formato SOS. Valida los cortes contra Nyquist. |
| `_filtrar(datos, filtros, padlen)` | Aplica cada filtro con `sosfiltfilt` (fase cero, extensión impar en los bordes). |
| `graficar_comparacion(crudo, filtrado, ...)` | Auxiliar: crudo vs. filtrado en un intervalo. |
| `preprocesar_eeg(registro, canales, f_bajo, f_alto, orden, f_notch, q_notch, ..., muestras_estimulo, t_artefacto)` | Función principal: carga → selecciona canales → **interpola el artefacto** (si `muestras_estimulo` no es `None`) → filtra. Devuelve un `ResultadoPreprocesamiento(raw, sfreq, canales, eventos, event_id, parametros)`. |

### 6.3 `segmentacion.py`: etapa 2

| Función | Qué hace |
|---|---|
| `cargar_eventos(ruta_tsv)` | Lee el `_events.tsv`, filtra `trial_type == "stimulus"` y ordena por `onset`. Devuelve un DataFrame (con la columna `sample`). |
| `segmentar_epocas(eeg_filtrado, eventos, sfreq, tmin, tmax, baseline=True)` | Recorta las épocas de forma vectorizada (acepta un Raw de MNE o un array con `sfreq`). Descarta los estímulos cuya ventana se sale del registro. Resta la media del pre-estímulo (`tmin` a 0). Devuelve `(epocas, tiempos)`. |

### 6.4 `promedio.py`: etapas 3 y 4

**Modelo** de cada época m, por canal:  x_m(n) = a_m · s(n) + v_m(n), con ruido v_m de media 0 y varianza σ²_m, independiente entre épocas.

**Estimador:** ŝ(n) = Σ w_m x_m(n), con la condición de no sesgo Σ w_m a_m = 1. Minimizando la varianza residual Σ w_m² σ²_m (multiplicadores de Lagrange):

  **w_m = (a_m / σ²_m) / Σ_k (a_k² / σ²_k)**

| Modo | Supuesto | Pesos |
|---|---|---|
| homogéneo | a_m = 1, σ_m constante | w_m = 1/M |
| `"n"` | amplitud constante, ruido variable | w_m ∝ 1/σ²_m |
| `"s"` | amplitud variable, ruido constante | w_m ∝ a_m |
| `"sn"` | ambos variables | w_m ∝ a_m/σ²_m |

| Función | Qué hace |
|---|---|
| `promedio_homogeneo(epocas)` | Media simple sobre las épocas. |
| `varianza_ruido(epocas, a)` | σ²_m = varianza del residuo x_m − a_m·ŝ sobre **toda la época** (con el pre-estímulo solo habría ~4 grados de libertad tras el pasabanda). |
| `amplitudes(epocas, tiempos, ventana_senal, tam_bloque)` | a_m **por bloques** de épocas consecutivas (con una época sola, la SNR es demasiado baja). Para el bloque b: a_b = ⟨x̄_b, r_b⟩ / ⟨r_b, r_b⟩, con x̄_b el promedio del bloque y r_b el de los **otros** bloques. Los a_b negativos (solo posibles por ruido) se recortan a 0 con `np.clip`. Se normaliza a media 1. |
| `pesos_inhomogeneos(a, sigma2)` | Aplica la fórmula de w_m por canal. |
| `promedio_inhomogeneo(epocas, modo, tiempos, ventana_senal, tam_bloque)` | Devuelve `(pe, pesos)`. |

### 6.5 `snr.py`: etapa 6

**Estimación del ruido residual: promedio alternado (*plus-minus averaging*).** Es equivalente al método de la cátedra (separar realizaciones pares e impares, promediar cada subensamble y restarlos): (s_par − s_impar)/2 = (1/M) Σ (−1)^m x_m. El PEP se cancela y el ruido conserva la varianza del promedio completo. **El factor 1/2 es necesario**: sin él, el ruido queda sobreestimado 4 veces (6 dB). Generalizaciones implementadas: se usan los **pesos** del promedio que se evalúa (sirve para los inhomogéneos) y **varias particiones** (`n_perm`) para reducir la varianza de la estimación. Con `n_perm=1` es exactamente el método de clase.

**SNR por canal** (en la ventana del PEP, ambas potencias en la misma ventana):
P_ruido = media de ruido(n)² · P_señal = media de pe(n)² − P_ruido · **SNR = 10·log10(P_señal / P_ruido)** [dB]. NaN si P_señal ≤ 0.

| Función | Qué hace |
|---|---|
| `pesos_homogeneos(epocas)` | Pesos 1/M con la misma forma que los inhomogéneos. |
| `_signos(M, n_perm, rng)` | Patrones de signo ±1 opuestos dentro de cada par de épocas consecutivas. |
| `ruido_residual(epocas, pesos, n_perm, semilla)` | Promedio alternado para `n_perm` particiones. |
| `calcular_snr(epocas, pe, pesos, tiempos, ventana_senal, n_perm=50)` | Devuelve un dict con arrays por canal: `snr_db`, `p_senal`, `p_ruido`, `rms_ruido`. |
| `_promediar(...)` | Interfaz común para los 4 métodos. Con N chico reduce `tam_bloque` a N//2. Devuelve `None` si no se pueden estimar amplitudes. |
| `snr_todos_los_metodos(epocas, tiempos, ventana_senal, tam_bloque)` | Los 4 promedios y su SNR con todas las épocas: `{metodo: {pe, pesos, snr_db, ...}}`. |
| `curva_snr(epocas, tiempos, n_valores, metodo, n_rep, ...)` | SNR en función de N, con bloques de N épocas **consecutivas** e inicio aleatorio. Las potencias se promedian entre repeticiones **antes** del logaritmo (descartar las negativas sesgaría la curva hacia arriba). |
| `snr_teorica_homogeneo(n_valores, snr_ref_db, n_ref)` | Recta de referencia: +10·log10(N), es decir +3 dB por duplicación. |

**Limitación conocida:** en los modos `"s"` y `"sn"`, las amplitudes se estiman con las mismas épocas que se promedian. En simulación, su SNR salió **optimista en ~3–6 dB**. Para el homogéneo y `"n"`, la estimación es aproximadamente insesgada (±0,5 dB). Validado con datos sintéticos (PEP conocido + ruido de varianza variable).

### 6.6 `teoria.py`: etapa 7

| Función / objeto | Qué hace |
|---|---|
| `COMPONENTES_POR_NERVIO` | Por componente: polaridad, ventana de búsqueda y latencia de referencia (típica, límite superior). **Valores orientativos, a confirmar con la bibliografía de la materia** (pendiente 3). |
| `componentes_de(nervio)` | Devuelve el diccionario del nervio. |
| `medir_componentes(t, pe, componentes)` | Por canal: extremo con la polaridad esperada dentro de la ventana. Cada búsqueda empieza ≥ 2 ms después del pico anterior. Si el extremo cae en el borde de la ventana, se marca `borde=True` (no es un pico real). |
| `comparar_con_teoria(t, pe, canales, nervio)` | DataFrame: latencia, referencia, diferencia, `dentro_rango` (no se evalúa si `borde`), amplitud base-pico y **amplitud pico a pico** de los dos primeros componentes (P40–N50 o N20–P25). |
| `tabla_metodos(t, pes, canales, nervio)` | Compara latencias y amplitudes entre los 4 métodos. |

### 6.7 `main.py`

Ejecuta: eventos → `preprocesar_eeg` (con interpolación) → `segmentar_epocas` → `snr_todos_los_metodos` (imprime la tabla de SNR) → `comparar_con_teoria` y `tabla_metodos` (imprime y guarda CSV) → `curva_snr` para los 4 métodos → figura por canal (PEP de los 4 métodos + curva SNR vs. N con recta teórica). Salidas en `results/`: `pep_snr_<nervio>_<canal>.png`, `componentes_<nervio>_homogeneo.csv`, `componentes_<nervio>_por_metodo.csv`. Las figuras son provisorias hasta que exista `graficos.py`.

### 6.8 Scripts de verificación (no los ejecuta `main.py`; se conservan como evidencia)

- **`chequeo_artefacto.py`:** promedio **sin filtrar** alrededor del estímulo (zoom de −5 a 15 ms, con 30 épocas individuales), amplitud y duración del artefacto, y comparación crudo / filtrado / filtrado con interpolación. Salida: `artefacto_<canal>.png`.
- **`comparar_pasaaltos.py`:** carga e interpola una vez, filtra con cortes de 0,5, 1, 2 y 5 Hz y reporta SNR, ruido, latencias y amplitudes. Salida: `comparacion_pasaaltos_<nervio>.csv/.png`.

---

## 7. Decisiones metodológicas y su justificación

| Decisión | Justificación (con evidencia de los scripts) |
|---|---|
| **Filtro de fase cero** (`sosfiltfilt`) | No desplaza latencias. Verificado: los picos del crudo y del filtrado coinciden, y las latencias son idénticas con los 4 cortes de pasaaltos. |
| **Pasaaltos 5 Hz** | Comparado con 0,5/1/2 Hz: latencias y amplitud pico a pico invariantes (CPz 8,18–8,26 µV), SNR máxima (con 1 Hz se pierden ~2,2 dB) y ventaja del inhomogéneo constante (~2 dB). Costo: elimina la onda lenta posterior a 80 ms y altera las amplitudes base-pico → **reportar amplitudes pico a pico**. |
| **Pasabajos 100 Hz** | El P40 dura 10–20 ms (energía por debajo de 100 Hz). Al ser de fase cero, no altera latencias. No se comparó. |
| **Interpolación lineal −1 a +3 ms, antes de filtrar** | Artefacto de 50–85 µV y ~1,5 ms en ambos nervios. Con o sin interpolación, el PEP filtrado es idéntico en la ventana de señal. Afecta ~3 % de la época en la estimación de σ², con un sesgo casi igual en todas las épocas, por lo que no cambia los pesos. Sin interpolar, la variabilidad del artefacto entre épocas sesgaría σ². |
| **Bloques de 50 épocas para a_m** | Una época sola tiene SNR muy baja (a_m casi puro ruido, pesos negativos). |
| **σ² sobre toda la época** | El pre-estímulo solo tiene muy pocos grados de libertad. |
| **SNR por promedio alternado** | Equivale al método par/impar de la cátedra, generalizado a pesos y a varias particiones. |
| **Canal principal del tibial: CPz** | P40–N50 = 8,2 µV en CPz vs. 4,4 µV en Cz (Cz' de la literatura está ~2 cm por detrás de Cz). |
| **Canal del mediano: CP4** | Contralateral al brazo izquierdo estimulado. CP3 no muestra N20 (componentes marcados como `borde`). |

---

## 8. Resultados actuales (`sub-001`, referencia RM, 5–100 Hz, M = 500)

**SNR con todas las épocas (dB):**

| Método | Tibial Cz | Tibial CPz | Mediano CP3 | Mediano CP4 |
|---|---|---|---|---|
| homogéneo | 11,39 | 15,37 | 9,84 | 12,04 |
| `n` | 13,42 | 17,28 | 12,11 | 15,07 |
| `s` | 11,97 | 15,55 | 11,76 | 12,35 |
| `sn` | 13,70 | 17,27 | 13,76 | 15,22 |

**Interpretación:** `n` mejora ~2 dB (tibial) y ~3 dB (mediano, CP4) sobre el homogéneo, y `s` casi no aporta. La ganancia viene de la **variabilidad del ruido entre épocas**, no de la amplitud del PEP, que es estable (sin habituación apreciable). El homogéneo sigue aproximadamente la recta de +3 dB por duplicación.

**Componentes (homogéneo):**

| Nervio / canal | Latencias (ms) | Amplitud pico a pico |
|---|---|---|
| Tibial CPz | P40 40,9 · N50 51,0 · P60 60,8 · N75 75,2 | P40–N50 = 8,23 µV |
| Tibial Cz | P40 41,0 · N50 50,8 · P60 59,8 · N75 78,5 | P40–N50 = 4,44 µV |
| Mediano CP4 | N20 17,6 · P25 23,0 · N35 30,9 · P45 45,1 | N20–P25 = 1,92 µV |
| Mediano CP3 | sin N20 (ipsilateral; componentes en `borde`) | no aplica |

- Las latencias son robustas frente al método (±0,3 ms). Las diferencias de amplitud entre métodos son del orden del ruido residual.
- El N75 tibial tiene la latencia menos precisa (valle ancho).
- **El N20 del mediano es pequeño (~1 µV):** probablemente lo atenúa la referencia RM, que está del mismo lado que CP4 (ver pendiente 1).
- En el mediano aparece una negatividad a ~6 ms en ambos canales, ya presente en el crudo y fuera de la ventana de análisis. Su origen no está claro (residuo lento del artefacto o campo lejano temprano).
- Con N = 10, la SNR es inestable: un punto de −32 dB en CP4 homogéneo, y NaN en CP3. El logaritmo diverge cuando P_señal ≈ 0.

---

## 9. Convenciones para modificar el código

- **Funciones puras:** reciben y devuelven arrays. Sin leer archivos ni usar variables globales dentro de las funciones de cálculo.
- **Parámetros en `config.py`**, no hardcodeados. Los valores por defecto internos de cada módulo (`TMIN`, `RUTA_EVENTOS`, `VENTANA_SENAL` de `snr.py`, etc.) son heredados: desde `main.py` siempre se pasan los de `config.py`.
- **Git:** una rama corta por tarea (`feat/...`), nadie pushea directo a `main`, PR con revisión de un compañero. `config.py` se cambia solo con un PR visible para todo el grupo.
- **Validar con datos sintéticos** (PEP conocido + ruido) antes de usar datos reales.
- Terminal de Windows: **CMD** (los comandos multilínea con `\` o `` ` `` no sirven; escribir en una sola línea).

---

## 10. Pendientes (próxima sesión, en este orden)

### 1. Parámetro de referencia (prioritario, sobre todo para el mediano)

**Problema:** el EEG está referido a la mastoides derecha (RM). Cada canal es V_canal − V_RM, así que la actividad que capte RM se resta. RM está del mismo lado que CP4, lo que probablemente atenúa el N20 (~1 µV). Además, `seleccionar_canales` descarta los demás canales **antes** de cualquier re-referencia, así que hoy no se puede cambiar.

**A implementar:**
- Parámetro `referencia` en `preprocesar_eeg` y `REFERENCIA` en `config.py` (idealmente por nervio). Incluir el o los canales de referencia en la selección, aplicar `raw.set_eeg_reference(...)` y después descartarlos. Como todas las operaciones son lineales, el orden respecto de la interpolación y el filtrado no altera el resultado.
- Opciones a comparar:
  - **RM** (adquisición, actual): sin cambios.
  - **Fz** para el mediano (montaje IFCN CP3/CP4–Fz: el P20 frontal, de polaridad opuesta, refuerza el N20) y **FPz** para el tibial (montaje IFCN CPz–FPz).
  - **Mastoides enlazadas** (LM+RM)/2, simétrica: equivale a restar LM/2 a cada canal.
  - (Si se usa referencia promedio, **excluir los canales no EEG**: `S..`, `SC..`, `L1`, `L4`, `AC`, `AL`, ECG, EMG, etc.)
- Comparar el PEP y la tabla de componentes con cada referencia, para ambos nervios. Se espera que las latencias no cambien y que la amplitud sí.

### 2. Robustez de la curva SNR vs. N

- **Sacar N = 10** de `N_VALORES` (empezar en 25 o 50). Con N chico, el logaritmo diverge (punto de −32 dB) y los bloques de amplitud de `"s"`/`"sn"` quedan de ~5 épocas.
- **Intervalos de confianza por *bootstrap*** sobre épocas, para la SNR de cada método y, sobre todo, para la **diferencia `n` − homogéneo** (remuestreo pareado), de modo que la conclusión "`n` mejora ~2–3 dB" tenga incertidumbre.
- Barras de error en la curva y **recta teórica anclada por ajuste** sobre todos los puntos (hoy se ancla en N = M, el punto más ruidoso; de ahí el salto final).
- Opcional: gráfico de **pesos y σ² en función del número de época** (modo `"n"`), que explica por qué gana el inhomogéneo.

### 3. Valores de referencia de `teoria.py`

- Reemplazar las latencias orientativas de `COMPONENTES_POR_NERVIO` (P40 típica 38 ms / límite superior 44 ms; N20 19,5 / 23 ms; el resto nominales) por los de la **bibliografía de la materia** (p. ej. guía 9D de la ACNS, Cruccu et al. 2008, *Clin Neurophysiol*).
- Revisar en `participants.tsv` si figura la **altura** del sujeto: la latencia depende de la longitud de la vía (P40 medido = 40,9 ms; N20 medido = 17,6 ms).
- Confirmar con la bibliografía la interpretación de la positividad de ~13 ms del mediano (¿P14 de campo lejano?).

### Otros pendientes menores

- Actualizar el encabezado de `config.py` (todavía dice "pipeline del PEP tibial").
- Crear `graficos.py` (figuras finales para el informe) e integrar la GUI.
- Extensión: otros runs del mismo sujeto (tibial 04/06/08) concatenados, para extender la curva SNR a ~2000 épocas, y eventualmente otros sujetos (2–3).