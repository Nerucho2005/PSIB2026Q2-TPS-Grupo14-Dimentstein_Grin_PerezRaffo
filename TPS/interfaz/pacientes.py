# pacientes.py
# Sujetos del dataset ds004388 para la interfaz: qué run del mediano usar, dónde están
# sus archivos, cómo descargarlos y cuándo borrarlos.
#
# - Cada sujeto se guarda en EEG-Paciente{n}/ en la raíz del repo, igual que las
#   descargas hechas a mano (config.rutas_sujeto).
# - La descarga usa curl contra el espejo público de OpenNeuro en Amazon S3, archivo
#   por archivo, el mismo comando que se usa desde CMD:
#       curl -L -O https://s3.amazonaws.com/openneuro.org/ds004388/sub-007/eeg/sub-007_task-median_run-03_eeg.set
#   Si una descarga se corta, se retoma desde donde quedó (curl -C -).
# - Un run se considera completo cuando el .set y el .fdt tienen EXACTAMENTE el
#   tamaño publicado en el dataset (tabla SUJETOS) y están los archivos chicos.
# - Solo se borran las carpetas que creó la interfaz (marca .descargado_por_interfaz):
#   lo que se descargó a mano, como EEG-Paciente1 para el informe, nunca se toca.
import os
import shutil
import subprocess
import time

import config as cfg

URL_BASE = os.environ.get("PSIB_URL_BASE", "https://s3.amazonaws.com/openneuro.org/ds004388")
EXTENSIONES = ("eeg.set", "eeg.fdt", "eeg.json", "channels.tsv", "events.tsv", "events.json")
MARCA = ".descargado_por_interfaz"
MARGEN_DISCO = 1.0e9          # bytes libres que se dejan de margen al descargar

# Primer run del mediano de cada sujeto y tamaño exacto (bytes) de su .set y su .fdt,
# tomados del árbol del dataset en OpenNeuro (v1.0.0). El orden de las tareas está
# contrabalanceado: según el sujeto, el primer bloque del mediano es el run-02 o el 03.
SUJETOS = {
    "001": ("03", 31784496, 1795049016), "002": ("03", 31826480, 1797442104),
    "003": ("02", 31603472, 1784730648), "004": ("02", 31749584, 1793059032),
    "005": ("03", 31495696, 1778588328), "006": ("02", 31886032, 1800837480),
    "007": ("03", 31844864, 1814244600), "008": ("02", 31708256, 1806389640),
    "009": ("03", 32400752, 1846208160), "010": ("03", 32415296, 1847044440),
    "011": ("02", 31351184, 1785858000), "012": ("03", 31610576, 1800773040),
    "013": ("02", 31565360, 1798173120), "014": ("03", 31642344, 1802599700),
    "015": ("02", 31596312, 1799952860), "016": ("02", 31465224, 1727937139),
    "017": ("02", 31801040, 1811724720), "018": ("03", 31459520, 1792087320),
    "019": ("02", 31787264, 1810932600), "020": ("03", 31497720, 1794283820),
    "021": ("02", 31457544, 1791973700), "022": ("03", 31485728, 1793594280),
    "023": ("03", 31886768, 1816654080), "024": ("03", 31438232, 1790863260),
    "025": ("02", 31514184, 1795230500), "026": ("02", 31618112, 1801206360),
    "027": ("03", 31550624, 1797325800), "028": ("02", 31558976, 1797806040),
    "029": ("03", 31691464, 1805424100), "030": ("02", 31358048, 1786252680),
    "031": ("03", 31437248, 1667099971), "032": ("03", 31654536, 1803300740),
    "033": ("02", 31615032, 1801029260), "034": ("02", 31443152, 1791146160),
    "035": ("02", 31513856, 1795238780), "036": ("03", 31322864, 1784229600),
    "037": ("02", 31825032, 1797359568), "038": ("02", 31912368, 1802337720),
    "039": ("02", 31613544, 1800943700), "040": ("03", 31337504, 1785071400),
}


class DescargaCancelada(Exception):
    pass


def run_de(sujeto):
    return SUJETOS[sujeto][0]


def rutas(sujeto):
    """(carpeta, prefijo BIDS, .set, _events.tsv) del primer run del mediano."""
    return cfg.rutas_sujeto(sujeto, run_de(sujeto))


def tamano_esperado(sujeto):
    """Bytes del .set + .fdt según el dataset."""
    _, tam_set, tam_fdt = SUJETOS[sujeto]
    return tam_set + tam_fdt


def estado(sujeto):
    """'completo', 'incompleto' (hay archivos pero falta algo o hay uno truncado) o
    'ausente'."""
    carpeta, base, _, _ = rutas(sujeto)
    _, tam_set, tam_fdt = SUJETOS[sujeto]
    esperado = {"eeg.set": tam_set, "eeg.fdt": tam_fdt}
    archivos = {e: carpeta / f"{base}_{e}" for e in EXTENSIONES}
    if not any(f.exists() for f in archivos.values()):
        return "ausente"
    for ext, f in archivos.items():
        if not f.is_file() or (ext in esperado and f.stat().st_size != esperado[ext]):
            return "incompleto"
    return "completo"


def descargado_por_interfaz(sujeto):
    return (rutas(sujeto)[0] / MARCA).is_file()


def espacio_libre(carpeta):
    while not carpeta.exists():
        carpeta = carpeta.parent
    return shutil.disk_usage(carpeta).free


def bytes_en_disco(sujeto):
    carpeta, base, _, _ = rutas(sujeto)
    return sum(f.stat().st_size for f in carpeta.glob(f"{base}_*") if f.is_file())


def descargar(sujeto, log=print, cancelar=lambda: False, proceso=None):
    """Descarga con curl los 6 archivos del primer run del mediano que falten o estén
    incompletos. cancelar(): devuelve True para interrumpir; proceso: lista donde se
    guarda el subproceso en curso (para poder terminarlo)."""
    curl = shutil.which("curl")
    if curl is None:
        raise RuntimeError("No se encontró curl. En Windows 10/11 viene instalado; "
                           "si no, instalarlo y agregarlo al PATH.")
    carpeta, base, _, _ = rutas(sujeto)
    _, tam_set, tam_fdt = SUJETOS[sujeto]
    esperado = {"eeg.set": tam_set, "eeg.fdt": tam_fdt}

    faltan = tamano_esperado(sujeto) - bytes_en_disco(sujeto)
    if espacio_libre(carpeta) < faltan + MARGEN_DISCO:
        raise OSError(f"Espacio insuficiente: hacen falta ~{(faltan + MARGEN_DISCO) / 1e9:.1f} GB "
                      f"y hay {espacio_libre(carpeta) / 1e9:.1f} GB libres. Borrá datos de otros "
                      "pacientes.")
    if not carpeta.exists():
        carpeta.mkdir(parents=True)
        (carpeta / MARCA).touch()               # esta carpeta la creó la interfaz

    for ext in EXTENSIONES:
        destino = carpeta / f"{base}_{ext}"
        if destino.is_file() and (ext not in esperado or destino.stat().st_size == esperado[ext]):
            continue                            # ya está completo
        url = f"{URL_BASE}/sub-{sujeto}/eeg/{base}_{ext}"
        parcial = destino.is_file() and destino.stat().st_size > 0
        log(f"{'Retomando' if parcial else 'Descargando'} {destino.name}")
        codigo, error = _curl(curl, url, destino, parcial, cancelar, proceso)
        if codigo == 33:                        # el servidor no permite retomar: de cero
            destino.unlink()
            codigo, error = _curl(curl, url, destino, False, cancelar, proceso)
        if codigo != 0:
            raise RuntimeError(f"curl falló al descargar {destino.name} (código {codigo}): {error}")
        if ext in esperado and destino.stat().st_size != esperado[ext]:
            raise RuntimeError(f"{destino.name} quedó con {destino.stat().st_size} bytes "
                               f"(se esperaban {esperado[ext]}). Volvé a intentar: la descarga "
                               "se retoma desde donde quedó.")
    log(f"Descarga de sub-{sujeto} completa.")


def _curl(curl, url, destino, reanudar, cancelar, proceso):
    """Corre curl -L -o destino url (con -C - para retomar). Devuelve (código, error)."""
    args = [curl, "-L", "--fail", "-sS", *(["-C", "-"] if reanudar else []), "-o", str(destino), url]
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proceso is not None:
        proceso[:] = [p]
    while p.poll() is None:                     # espera, atenta a una cancelación
        if cancelar():
            p.terminate()
            p.wait()
            raise DescargaCancelada()
        time.sleep(0.3)
    return p.returncode, p.stderr.read().strip()


def borrar(sujeto, log=print):
    """Borra la carpeta del sujeto SOLO si la creó la interfaz."""
    carpeta = rutas(sujeto)[0]
    if carpeta.exists() and descargado_por_interfaz(sujeto):
        gb = sum(f.stat().st_size for f in carpeta.rglob("*") if f.is_file()) / 1e9
        shutil.rmtree(carpeta)
        log(f"Datos de sub-{sujeto} eliminados ({gb:.1f} GB liberados).")


def descargados_por_interfaz():
    return [s for s in SUJETOS if descargado_por_interfaz(s)]


def borrar_otros(sujeto, log=print):
    for s in descargados_por_interfaz():
        if s != sujeto:
            borrar(s, log)
