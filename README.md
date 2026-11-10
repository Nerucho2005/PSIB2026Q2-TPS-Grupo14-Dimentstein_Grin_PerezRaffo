# PSIB2026Q2 · TPS Grupo 14 · Dimentstein, Grin, Pérez Raffo

**Potenciales evocados somatosensoriales (PES) del nervio mediano: mejora de la relación señal/ruido según el tipo de promediado y la cantidad de épocas.**

> **Nota para una IA que lea este archivo.** Este README es el contexto completo del proyecto: objetivo, datos, decisiones de diseño con su bibliografía, estructura, módulos y pendientes. Antes de proponer cambios, respetá las convenciones de la sección 8 y revisá la sección 9 (pendientes). Desde noviembre de 2026 el trabajo usa **solo el nervio mediano**. El análisis anterior con los dos nervios y la interfaz gráfica quedó en la rama `feature/interfaz`.

---

## 1. Objetivo

Trabajo Práctico de Señales (TPS) de 16.63 *Procesamiento de Señales e Imágenes Biomédicas* (ITBA).

**Objetivo:** cuantificar cómo mejora la **SNR** del PES del nervio mediano
- según el **tipo de promediado**: homogéneo e inhomogéneo en sus modos `n`, `s` y `sn`;
- según la **cantidad de épocas promediadas** (N).

Las decisiones de diseño previas son el filtrado, el canal, la referencia y el tratamiento del artefacto. Cada una se justifica con la bibliografía y con la evidencia de los scripts de verificación. Requisito de la cátedra: el filtrado **no debe distorsionar la latencia de los picos**.

## 2. Datos y bibliografía

- **Dataset:** OpenNeuro **ds004388** v1.0.0 (BIDS, EEGLAB). Es el Experimento 1 de **[P] Nierula et al. (2024)**, *PLOS Biology* 22(10): e3002828, "A multichannel electrophysiological approach to noninvasively and precisely record human spinal cord activity".
- **El estudio:**
  - Es un trabajo **metodológico**: valida el registro no invasivo de la médula espinal (ESG multicanal más filtrado espacial por CCA), junto con el nervio periférico y la corteza.
  - Participaron 42 voluntarios **sanos** y diestros; se analizaron 36.
  - Hubo estimulación eléctrica del **mediano izquierdo** en la muñeca, con pulsos de 0,2 ms apenas por encima del umbral motor (el dataset también tiene bloques de estimulación tibial, que no se usan en este trabajo).
  - El intervalo entre estímulos fue de 763 ± 50 ms (≈ 1,3 Hz), en 4 bloques de 500 estímulos por nervio, alternados entre nervios y contrabalanceados.
- **Registro:**
  - EEG de 64 canales a 10 kHz, contra la **mastoides derecha (RM)**; Fz se agregó para poder re-referenciar.
  - Filtro de hardware de 0,16 a 2500 Hz.
- **Datos usados:** `sub-001`, `task-median_run-03` (500 estímulos), en `EEG-Paciente1/`, fuera de git. El `.fdt` pesa ~1,8 GB.
- **Procesamiento cortical del paper**, como referencia:
  - interpolación PCHIP del artefacto;
  - remuestreo a 1 kHz e ICA;
  - **Butterworth de orden 4 de fase cero, 30–400 Hz**, más notch de 48–53 Hz;
  - referencia promedio;
  - CCA.
  - Su N20 medio es de **19,81 ± 0,20 ms** (media ± EE, N = 36).
  - Su **SNR** es el RMS en ±1 ms alrededor del pico dividido por el RMS en la misma ventana antes del estímulo.
- **[IFCN] Mauguière et al. (1999)**, *Recommendations for the Practice of Clinical Neurophysiology*, EEG Suppl. 52, cap. 2.4. Es una guía clínica con estas pautas:
  - estímulo a menos de 5 Hz;
  - 500 barridos alcanzan;
  - filtros de registro: pasaaltos < 3 Hz y pasabajos > 2000 Hz, con notch apagado; el filtrado digital posterior permite "seleccionar off-line las frecuencias de interés";
  - montaje **Pc–Fz**;
  - normas: N20 19,8 ms (límite 23,0 ms), N20–P25 3,2 µV (mínimo 0,8 µV);
  - reproducibilidad: 0,25 ms y 20 %.
- **Teoría de promediado:** apuntes de la cátedra (modelo x_m = a_m·s + v_m, pesos óptimos, método par/impar).

## 3. Decisiones de diseño

| Decisión | Elección | Justificación | Evidencia |
|---|---|---|---|
| Canal | **CP4** | [IFCN] N20 en la región parietal contralateral (Pc ≈ CP3/CP4). [P] estímulo en el brazo izquierdo | `05_lateralidad`: N20 solo en CP4 con referencia simétrica |
| Referencia | **Fz** | [IFCN] montaje Pc–Fz: el P20 frontal tiene polaridad opuesta al N20 y la derivación los suma. [P] Fz agregado para re-referenciar | `04_referencias` (RM, Fz, mastoides enlazadas, promedio) |
| Lateralidad | mastoides enlazadas | Con Fz, el P20 invertido produce un falso "N20" también en CP3 | `05_lateralidad` |
| Artefacto | **recta de −1 a +3 ms, antes de filtrar** | [P] interpola con PCHIP (variante). El artefacto dura ~1,5 ms y queda fuera de la ventana del PEP | `02_artefacto`, `chequeo_artefacto.py` |
| Filtro | **Butterworth de orden 4, fase cero, 30–400 Hz** | [P] misma banda y mismo tipo de filtro. La fase cero no corre latencias. [IFCN] el filtrado digital offline de la banda de interés es aceptable | `03_filtros` (IFCN 1–2000, anterior 5–100, paper 30–400) |
| Notch | 50 Hz, Q = 30 | [P] usa notch de 48–53 Hz. [IFCN] recomienda apagarlo en el registro clínico: se mantiene porque es angosto y de fase cero, y se discute | `01_psd` |
| Ventana del PEP | 15–30 ms (N20–P25) | [IFCN] latencia del N20 y amplitud N20–P25. Con Fz, lo posterior a ~25 ms se mezcla con el N30 frontal | — |
| N de épocas | M = 500 | [IFCN] 500 barridos alcanzan. [P] bloques de 500 | `07_curvas_snr` |

**Advertencias para el informe:**
- **Armónicos de la red:** con el pasabajos en 400 Hz, los armónicos de 150, 250 y 350 Hz quedan dentro de la banda; antes, el pasabajos de 100 Hz los eliminaba. El notch solo quita los 50 Hz. El promediado los atenúa porque no están sincronizados con el estímulo, gracias al jitter de ±50 ms. Revisar en `01_psd`.
- **Componentes tardíos:** el pasaaltos de 30 Hz atenúa el N35 y el P45. Para el objetivo de SNR no importa, porque la ventana es 15–30 ms.
- **Amplitudes:** las normas IFCN de amplitud se definen con filtros clínicos. Con 30–400 Hz son solo orientativas; las latencias sí son comparables.

## 4. Estructura del repositorio

```
PSIB2026Q2-TPS-Grupo14-Dimentstein_Grin_PerezRaffo/
├── EEG-Paciente1/ … EEG-Paciente10/   # datos .set/.fdt/.tsv/.json de cada sujeto (FUERA de git)
├── TPS/
│   ├── main/                   # PIPELINE: lo que necesita main.py
│   │   ├── config.py           # parámetros (decisiones de diseño con su bibliografía; SUJETO y RUN)
│   │   ├── filtrado.py         # etapas 1-2: carga, re-referencia, artefacto, filtrado
│   │   ├── segmentacion.py     # etapa 3: eventos y épocas
│   │   ├── promedio.py         # etapa 4: promedio homogéneo e inhomogéneo (n, s, sn)
│   │   ├── snr.py              # etapa 5: SNR par/impar, jackknife, curva SNR vs. N, SNR del paper
│   │   ├── teoria.py           # etapa 6: componentes vs. IFCN y paper; reproducibilidad
│   │   └── main.py             # corre las 6 etapas para un sujeto, tablas en results/
│   ├── pruebas/                # VERIFICACIÓN de las decisiones de diseño (no las usa main.py)
│   │   ├── chequeo_artefacto.py    # artefacto de estímulo e interpolación
│   │   ├── comparar_filtros.py     # bandas IFCN / anterior / paper
│   │   └── comparar_referencias.py # RM, Fz, mastoides enlazadas, promedio
│   └── figuras/                # FIGURAS DEL INFORME
│       ├── graficos.py         # figuras 01-10 (sub-001) + CSV
│       └── grupal.py           # figuras 11-13: análisis de los 10 sujetos (lee results/)
├── results/                    # CSV de cada sujeto (FUERA de git)
├── informe/figuras/            # figuras finales (PNG + PDF) y tablas
├── requirements.txt
└── README.md
```

## 5. Cómo ejecutar

Desde la raíz del repo, en CMD:

```
python TPS/main/main.py                     # pipeline de un sujeto (SUJETO y RUN en config.py)
python TPS/pruebas/chequeo_artefacto.py     # justificación de la interpolación
python TPS/pruebas/comparar_filtros.py      # justificación de la banda
python TPS/pruebas/comparar_referencias.py  # justificación de la referencia
python TPS/figuras/graficos.py              # figuras 01-10 (agregar --sin-promedio para omitir la ref. promedio, la más lenta)
python TPS/figuras/grupal.py                # figuras 11-13 (antes correr main.py con cada sujeto)
```

## 6. Pipeline y módulos

```
_events.tsv ─► cargar_eventos ─► muestras de estímulo
.set/.fdt ─► cargar_y_referenciar (CP4 − Fz) ─► interpolar_artefacto (−1 a +3 ms)
          ─► Butterworth 30–400 Hz + notch 50 Hz (sosfiltfilt) ─► segmentar_epocas (−30 a 80 ms, base −30 a 0)
          ─► promedios (homogéneo, n, s, sn) ─► SNR par/impar ± jackknife ─► curva SNR vs. N
          ─► SNR del paper ─► componentes vs. IFCN/paper ─► reproducibilidad
```

**El artefacto se interpola sobre el registro crudo, antes de filtrar.** Si se filtrara primero, el filtro de fase cero lo dispersaría hacia ambos lados de t = 0.

**Convenciones de datos:**
- `epocas`: `(M, C, N)` en V, **en orden temporal**;
- `tiempos`: en s, con 0 en el estímulo;
- `pe`: `(C, N)`;
- `pesos`: `(M, C)`.

### `promedio.py`

Modelo: x_m(n) = a_m·s(n) + v_m(n). Pesos óptimos sin sesgo: **w_m = (a_m/σ²_m) / Σ(a_k²/σ²_k)**. Hay cuatro modos:
- homogéneo: w = 1/M;
- `n`: w ∝ 1/σ²_m;
- `s`: w ∝ a_m;
- `sn`: w ∝ a_m/σ²_m.

Cómo se estiman los parámetros:
- **σ²_m:** sobre toda la época.
- **a_m:** por bloques de 50 épocas, comparando cada bloque contra el promedio de los otros. Los valores negativos se recortan a 0 y se normaliza a media 1.

### `snr.py`

- **SNR principal: promedio alternado** (*plus-minus*). Es equivalente al método par/impar de la cátedra, (s_par − s_impar)/2, con los pesos del método evaluado y 50 particiones. Se calcula así:
  - P_ruido = media de ruido² en la ventana;
  - P_señal = media de pe² − P_ruido;
  - SNR = 10·log10(P_señal/P_ruido).
- `jackknife_snr`: error estándar por jackknife de 10 bloques de épocas consecutivas. **No se usa bootstrap con reemplazo**: repite épocas, que se cancelan en el promedio alternado, y rompe el orden temporal.
- `diferencia_metodos`: IC 95 % por jackknife pareado.
- `curva_snr`: SNR vs. N con bloques disjuntos de N épocas consecutivas (al menos 4; si no, jackknife dentro de las N épocas).
- `ajustar_pendiente`: pendiente contra log10(N); la teórica es 10 dB/década.
- `snr_teorica_ajustada`: recta +10·log10(N) ajustada.
- **`snr_paper` y `curva_snr_paper`**: métrica complementaria de [P]. Es el RMS en ±1 ms alrededor del N20 dividido por el RMS en la ventana espejada antes del estímulo, pasado a dB con 20·log10. Como el numerador incluye ruido, con N chico tiende a 0 dB.

### `teoria.py`

- `COMPONENTES`: N20, P25, N35 y P45, con polaridad y ventana de búsqueda.
- `comparar_con_teoria`: latencias, amplitudes y N20–P25 pico a pico contra la IFCN y el paper. Marca `borde`, `polaridad_ok` y `valido`.
- `tabla_metodos`: componentes según el método de promediado.
- `reproducibilidad`: primera contra segunda mitad del registro (criterio IFCN).

### `graficos.py`: figuras del informe

| Figura | Contenido |
|---|---|
| 01_psd | PSD del crudo interpolado contra el filtrado (banda y notch) |
| 02_artefacto | Zoom sin filtrar y promedio filtrado, sin y con interpolación |
| 03_filtros | PEP con las bandas IFCN, anterior y del paper, y su SNR (homogéneo y `n`) |
| 04_referencias | PEP y ruido residual con RM, Fz, mastoides enlazadas y promedio |
| 05_lateralidad | CP3 contra CP4 con mastoides enlazadas |
| 06_pep_metodos | PEP de los 4 métodos, banda ±2·RMS y componentes; detalle de la ventana |
| 07_curvas_snr | SNR vs. N de los 4 métodos con la recta teórica, y SNR del paper vs. N |
| 08_diferencias_metodos | `n`, `s` y `sn` menos el homogéneo, con IC 95 % |
| 09_pesos | σ² por época y peso relativo de cada método inhomogéneo |
| 10_reproducibilidad | Primera contra segunda mitad (IFCN) |

Además guarda los CSV `03_filtros`, `04_referencias`, `06_componentes`, `07_snr_metodos` y `08_diferencias_metodos`.

## 7. Resultados

### Grupo: sub-001 a sub-010 (primer run del mediano de cada uno, M = 500)

Se analizan 10 de los 40 sujetos por tiempo de descarga y espacio en disco (~1,8 GB por run). Para cada sujeto se cambian `SUJETO` y `RUN` en `config.py`; `DIR_DATOS` es `EEG-Paciente{n}`. Las descargas se hacen desde el espejo S3 de OpenNeuro con `curl`, porque la API de openneuro-py daba timeout.

| Medida | Media [IC 95 % entre sujetos] | Prueba |
|---|---|---|
| Ganancia de `n` sobre el homogéneo | **+1,40 dB [0,43; 2,36]**, 9/10 positivos | Wilcoxon p = 0,004 |
| Ídem sin sub-009 | +1,04 dB [0,42; 1,67] | p = 0,008 |
| Ganancia de `s` | −0,07 dB [−0,52; 0,38] | p = 0,70 |
| Ganancia de `sn` | +1,37 dB [0,41; 2,33] | p = 0,004 |
| Pendiente del homogéneo | 10,2 dB/década (no difiere de 10) | p = 0,77 |
| SNR del homogéneo | 22,5 dB [19,3; 25,6] | — |
| N20 (9 sujetos confiables) | 19,4 ± 1,1 ms; paper 19,81 ± 1,2 ms | diferencia no significativa (p = 0,24) |

**Interpretación:**
- **Ganancia de `n`:** es chica pero sistemática. Solo es significativa individualmente en sub-009, porque el jackknife dentro de un registro tiene poca potencia para ~1 dB.
- **`s`:** no aporta, porque no hay habituación.
- **Curva SNR vs. N:** sigue la teoría.

**Sujetos atípicos:**
- **sub-009:** las primeras ~100 épocas son muy ruidosas (σ² de hasta ~430 µV²); ahí `n` gana +4,6 dB. Su N20 es débil (−0,7 µV) y no pasa la reproducibilidad, así que se excluye de la comparación de latencias (`SUJETOS_SENSIBILIDAD` en `grupal.py`).
- **sub-008:** una sola época con σ² ≈ 550 µV² distorsiona la curva del homogéneo (pendiente 13,4).
- **sub-004:** no cumple la reproducibilidad de latencia (0,6 ms).
- **sub-003 y sub-004:** el P25 cae en el borde de su ventana.

### sub-001 (figuras 01–10)

**Hay que volver a correr todo con la configuración nueva** (30–400 Hz, ventana de 15–30 ms, épocas desde −30 ms). Los resultados anteriores, con 5–100 Hz y una ventana de 12–60 ms, son **obsoletos**. Como referencia, con Fz daban:
- ganancia de `n` de +3,0 dB [0,15; 5,85];
- `s` nunca significativo;
- pendiente del homogéneo de 10,5 ± 0,3 dB/década;
- N20 de 18,7 ms.

Se espera que el filtro de 30 Hz cambie la SNR absoluta y, posiblemente, la ganancia de `n`, porque parte de la variabilidad del ruido entre épocas está en las bajas frecuencias. Esto es un punto de discusión.

Validación con datos sintéticos (PEP conocido, ruido con tramos de varianza alta, 500 épocas):
- `n` y `sn` ganan ~4 dB;
- `s`, 0 dB;
- las pendientes dan 9,7–10,3 dB/década;
- N20 a 19,1 ms, con 18,7 ms simulados.

## 8. Convenciones

- **Funciones puras** en los módulos de cálculo. Los parámetros están en `config.py` y se pasan desde los scripts.
- **Git:** se trabaja directamente en `main` (`git pull` al empezar, commits chicos, `git push`). La rama `feature/interfaz` guarda la GUI y el análisis con los dos nervios.
- **Validar con datos sintéticos** antes de usar datos reales.
- Terminal de Windows: **CMD**, con comandos en una sola línea.

## 9. Pendientes

1. Correr `main.py`, los tres scripts de verificación y `graficos.py` con los datos reales, y revisar:
   - que la ventana de 15–30 ms contenga el N20 y el P25;
   - los armónicos en `01_psd`;
   - si la ganancia de `n` se mantiene con 30–400 Hz.
2. Redactar el informe:
   - **métodos**: decisiones de la sección 3 con citas;
   - **resultados**: figuras 06–09;
   - **discusión**: comparación con el paper (solo latencias, porque el paper usa CCA sobre 64 canales y amplitudes en unidades arbitrarias), las dos métricas de SNR y la IFCN.
3. Opcional: extender la curva SNR vs. N con los otros runs del mediano (05, 07 y 09) para llegar a ~2000 épocas.

## Nota sobre los imports

Los scripts de `pruebas/` y `figuras/` agregan `TPS/main` al `sys.path` en sus primeras líneas, para poder importar los módulos del pipeline con `import config`, `from filtrado import ...`, etc. No hay que convertir esos imports a la forma `TPS.main.config`: VS Code a veces lo propone, y rompe la ejecución desde la raíz del repo. Si Pylance marca los imports como no resueltos, se puede agregar `"python.analysis.extraPaths": ["TPS/main", "TPS/pruebas"]` a la configuración de VS Code; es solo cosmético.
