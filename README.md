# PSIB2026Q2-TPS-Grupo14-Dimentstein_Grin_PerezRaffo/
## Etapas 3 y 4: promedio homogéneo e inhomogéneo (`promedio.py`)

### Modelo

Cada época $m$ ($m = 1, \dots, M$), en cada canal:

$$x_m(n) = a_m \, s(n) + v_m(n)$$

- $s(n)$: PEP, igual en todas las épocas.
- $a_m$: amplitud del PEP en la época $m$.
- $v_m(n)$: ruido de media 0 y varianza $\sigma_m^2$, independiente entre épocas.

### Promedio homogéneo

$$\hat{s}(n) = \frac{1}{M} \sum_{m=1}^{M} x_m(n)$$

Es óptimo si todas las épocas son iguales ($a_m = 1$, $\sigma_m = \sigma$). La varianza del ruido residual es $\sigma^2 / M$.

### Promedio inhomogéneo

$$\hat{s}(n) = \sum_{m=1}^{M} w_m \, x_m(n)$$

Los pesos minimizan la varianza del ruido residual, $\sum_m w_m^2 \sigma_m^2$, con la condición de no sesgo $\sum_m w_m a_m = 1$. Resolviendo con multiplicadores de Lagrange:

$$w_m = \frac{a_m / \sigma_m^2}{\sum_k a_k^2 / \sigma_k^2}$$

| Modo | Supuesto | Pesos |
|---|---|---|
| `"n"` | amplitud constante, ruido variable | $w_m \propto 1/\sigma_m^2$ |
| `"s"` | amplitud variable, ruido constante | $w_m \propto a_m$ |
| `"sn"` | ambos variables | $w_m \propto a_m/\sigma_m^2$ |

Con $a_m = 1$ y $\sigma_m$ constante se recupera el promedio homogéneo ($w_m = 1/M$).

### Estimación de $\sigma_m^2$ y $a_m$

- **$\sigma_m^2$**: varianza del residuo $x_m(n) - a_m \bar{x}(n)$ sobre toda la época, con $\bar{x}$ el promedio homogéneo. No se usa solo el pre-estímulo porque, tras el pasabanda de 5–100 Hz, 20 ms equivalen a unos 4 grados de libertad, demasiado pocos para estimar una varianza.
- **$a_m$**: por bloques de $B = 50$ épocas consecutivas. Para cada bloque $b$, dentro de la ventana del PEP (15–80 ms):

$$a_b = \frac{\langle \bar{x}_b, r_b \rangle}{\langle r_b, r_b \rangle}$$

  donde $\bar{x}_b$ es el promedio del bloque y $r_b$ el promedio de las épocas de los otros bloques. Todas las épocas del bloque comparten $a_b$, y se normaliza para que la media de $a$ sea 1. No se estima época por época porque con una sola época la SNR es demasiado baja: la estimación sale casi puro ruido y da pesos negativos.

### Interfaz

- `promedio_homogeneo(epocas)` → `pe` de forma `(n_canales, n_muestras)`.
- `promedio_inhomogeneo(epocas, modo, tiempos, ventana_senal=(0.015, 0.080), tam_bloque=50)` → `(pe, pesos)`, con `pesos` de forma `(n_epocas, n_canales)`.
- Las entradas son la salida de `segmentar_epocas`: épocas en V y en orden temporal; tiempos y ventanas en segundos.
- Los pesos se calculan por separado para cada canal.
