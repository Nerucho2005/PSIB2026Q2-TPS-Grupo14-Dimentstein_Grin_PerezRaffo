# main_window.py
# Interfaz gráfica del TPS: elegir uno de los 40 sujetos del dataset, descargar su
# primer run del mediano si no está (pacientes.py, con curl), correr el pipeline
# completo (figuras/graficos.calcular) y mostrar las 10 figuras y las tablas de métricas.
#
# Organización:
#   - Trabajo (QThread): descarga + cálculo en un hilo aparte, para que la ventana no
#     se congele. No crea figuras: matplotlib no es seguro entre hilos.
#   - VentanaPrincipal: arma las figuras en el hilo principal (construir_figuras), las
#     embebe en las pestañas y llena las tablas.
#   - Caché: los resultados de cada sujeto se guardan en results/cache_interfaz/, con
#     una clave que incluye los parámetros de config.py (si cambian, se recalcula).
#
# Ejecutar desde la raíz del repo:   python TPS/interfaz/main_window.py
import hashlib
import json
import pickle
import sys
import threading
import time
import traceback
from pathlib import Path

_TPS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_TPS / "main"), str(_TPS / "pruebas"), str(_TPS / "figuras")]

import matplotlib

matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QApplication, QFileDialog, QMainWindow, QMessageBox,
                               QTableWidgetItem)

import config as cfg
import graficos as gr
import pacientes
from ui_ventana import Ui_MainWindow

POLITICAS = ("terminar", "cambiar", "conservar")       # mismo orden que comboBorrado
# pestaña -> figura de graficos.construir_figuras
PESTANAS = {"PSD": "01_psd", "Artefacto": "02_artefacto", "Filtros": "03_filtros",
            "Referencias": "04_referencias", "Lateralidad": "05_lateralidad",
            "PEP": "06_pep_metodos", "Curvas": "07_curvas_snr",
            "Diferencias": "08_diferencias_metodos", "Pesos": "09_pesos",
            "Reproducibilidad": "10_reproducibilidad"}
VERSION_CACHE = 2
DIR_CACHE = cfg.DIR_RESULTADOS / "cache_interfaz"


# --------------------------------------------------------------------------
# Caché de resultados: un pickle por sujeto y conjunto de parámetros
# --------------------------------------------------------------------------
def ruta_cache(sujeto, incluir_promedio):
    clave = dict(v=VERSION_CACHE, filtro=(cfg.F_BAJO, cfg.F_ALTO, cfg.ORDEN, cfg.F_NOTCH, cfg.Q_NOTCH),
                 artefacto=(cfg.INTERPOLAR_ARTEFACTO, cfg.T_ARTEFACTO), epoca=(cfg.TMIN, cfg.TMAX),
                 snr=(cfg.VENTANA_SENAL, cfg.TAM_BLOQUE, cfg.N_VALORES, cfg.N_BLOQUES_JK),
                 canal=cfg.CANAL, ref=str(cfg.REFERENCIA), prom=incluir_promedio)
    h = hashlib.md5(json.dumps(clave, default=str).encode()).hexdigest()[:10]
    return DIR_CACHE / f"sub-{sujeto}_run-{pacientes.run_de(sujeto)}_{h}.pkl"


# --------------------------------------------------------------------------
# Hilo de trabajo: descarga + pipeline
# --------------------------------------------------------------------------
class Cancelado(Exception):
    pass


class Trabajo(QThread):
    mensaje = Signal(str)
    progreso = Signal(int)
    terminado = Signal(object)
    fallo = Signal(str)

    def __init__(self, sujeto, incluir_promedio, usar_cache, politica):
        super().__init__()
        self.sujeto, self.incluir_promedio = sujeto, incluir_promedio
        self.usar_cache, self.politica = usar_cache, politica
        self._cancelar = False
        self._proceso = []

    def cancelar(self):
        self._cancelar = True
        for p in self._proceso:
            if p.poll() is None:
                p.terminate()

    def _revisar(self):
        if self._cancelar:
            raise Cancelado()

    def run(self):
        try:
            self.terminado.emit(self._correr())
        except (Cancelado, pacientes.DescargaCancelada):
            self.fallo.emit("Análisis cancelado.")
        except Exception as e:                       # se muestra en la ventana
            self.fallo.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

    def _correr(self):
        s = self.sujeto
        ruta = ruta_cache(s, self.incluir_promedio)
        if self.usar_cache and ruta.is_file():
            self.mensaje.emit(f"sub-{s}: resultados guardados (caché), no hace falta descargar.")
            with open(ruta, "rb") as f:
                R = pickle.load(f)
            self.progreso.emit(100)
            return R

        # 1. Descarga (si falta o quedó incompleta)
        hubo_descarga = pacientes.estado(s) != "completo"
        if hubo_descarga:
            if self.politica == "cambiar":
                pacientes.borrar_otros(s, self.mensaje.emit)
            self._descargar()

        # 2. Pipeline completo (graficos.calcular), con el avance de cada etapa
        p0 = 40 if hubo_descarga else 0

        def avance(frac, texto):
            self._revisar()
            self.progreso.emit(int(p0 + (100 - p0) * frac))
            self.mensaje.emit(f"   {texto}")

        R = gr.calcular(incluir_promedio=self.incluir_promedio, avance=avance)
        R["sujeto"], R["run"] = s, pacientes.run_de(s)
        DIR_CACHE.mkdir(parents=True, exist_ok=True)
        with open(ruta, "wb") as f:
            pickle.dump(R, f)

        # 3. Política de borrado (solo carpetas creadas por la interfaz)
        if self.politica == "terminar":
            pacientes.borrar(s, self.mensaje.emit)
        return R

    def _descargar(self):
        esperado = pacientes.tamano_esperado(self.sujeto)
        fin = threading.Event()

        def vigilar():                           # progreso según los bytes ya en disco
            while not fin.wait(1.0):
                hecho = pacientes.bytes_en_disco(self.sujeto)
                self.progreso.emit(int(40 * min(hecho / esperado, 1.0)))

        threading.Thread(target=vigilar, daemon=True).start()
        try:
            pacientes.descargar(self.sujeto, self.mensaje.emit, lambda: self._cancelar,
                                self._proceso)
        finally:
            fin.set()


# --------------------------------------------------------------------------
# Ventana
# --------------------------------------------------------------------------
class VentanaPrincipal(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.trabajo = None
        self.R, self.figs, self.tablas, self.lienzos = None, {}, {}, []

        for s in pacientes.SUJETOS:
            self.comboPaciente.addItem(f"sub-{s}", s)
        self.comboPaciente.currentIndexChanged.connect(self._actualizar_estado)
        self.chkPromedio.toggled.connect(self._actualizar_estado)
        self.chkCache.toggled.connect(self._actualizar_estado)

        self.btnProcesar.clicked.connect(self.procesar)
        self.actionProcesar.triggered.connect(self.procesar)
        self.btnCancelar.clicked.connect(self.cancelar)
        self.btnBorrarDatos.clicked.connect(self.borrar_datos)
        self.btnGuardarFiguras.clicked.connect(self.guardar_figuras)
        self.actionGuardarFiguras.triggered.connect(self.guardar_figuras)
        self.btnExportar.clicked.connect(self.exportar_csv)
        self.actionExportar.triggered.connect(self.exportar_csv)
        self.actionSalir.triggered.connect(self.close)
        self.actionAcercaDe.triggered.connect(self.acerca_de)
        self.actionGuardarFiguras.setEnabled(False)
        self.actionExportar.setEnabled(False)
        self.splitterMetricas.setSizes([330, 240, 120])

        gr.estilo()
        self._actualizar_estado()
        self.log(f"Los datos de cada paciente se guardan en {cfg.RAIZ / 'EEG-Paciente<n>'}")

    # ---- utilidades ----
    def log(self, texto):
        texto = str(texto).strip("\n")
        for linea in texto.splitlines():
            self.txtLog.appendPlainText(linea)
        if texto.strip():
            self.statusbar.showMessage(texto.strip().splitlines()[-1])

    @property
    def sujeto(self):
        return self.comboPaciente.currentData()

    # ---- estado del paciente elegido ----
    def _actualizar_estado(self):
        s = self.sujeto
        carpeta, base, _, _ = pacientes.rutas(s)
        self.lblRun.setText(f"run-{pacientes.run_de(s)} (primer bloque del mediano)")
        if self.chkCache.isChecked() and ruta_cache(s, self.chkPromedio.isChecked()).is_file():
            texto, boton = "Ya analizado (resultados guardados).", "Ver resultados"
        else:
            est = pacientes.estado(s)
            if est == "completo":
                texto, boton = f"Descargado en {carpeta.name}.", "Analizar"
            else:
                falta = (pacientes.tamano_esperado(s) - pacientes.bytes_en_disco(s)) / 1e9
                libre = pacientes.espacio_libre(carpeta) / 1e9
                previo = "Descarga incompleta: se retoma. " if est == "incompleto" else ""
                texto = f"{previo}A descargar: ~{falta:.1f} GB ({libre:.0f} GB libres)."
                boton = "Descargar y analizar"
        self.lblDatos.setText(texto)
        self.btnProcesar.setText(boton)

    # ---- análisis ----
    def procesar(self):
        if self.trabajo is not None:
            return
        s = self.sujeto
        cfg.usar_sujeto(s, pacientes.run_de(s))      # todo el pipeline lee de config
        politica = POLITICAS[self.comboBorrado.currentIndex()]
        self.trabajo = Trabajo(s, self.chkPromedio.isChecked(), self.chkCache.isChecked(), politica)
        self.trabajo.mensaje.connect(self.log)
        self.trabajo.progreso.connect(self.barraProgreso.setValue)
        self.trabajo.terminado.connect(self._terminado)
        self.trabajo.fallo.connect(self._fallo)
        self.trabajo.finished.connect(self._fin_trabajo)
        self._ocupado(True)
        self.barraProgreso.setValue(0)
        self.log(f"\n=== sub-{s}, run-{pacientes.run_de(s)} ===")
        self._t0 = time.time()
        self.trabajo.start()

    def cancelar(self):
        if self.trabajo is not None:
            self.log("Cancelando (el cálculo se detiene al terminar la etapa en curso)...")
            self.btnCancelar.setEnabled(False)
            self.trabajo.cancelar()

    def _ocupado(self, si):
        for w in (self.btnProcesar, self.actionProcesar, self.btnBorrarDatos, self.comboPaciente,
                  self.chkPromedio, self.chkCache, self.comboBorrado):
            w.setEnabled(not si)
        self.btnCancelar.setEnabled(si)
        if not si:
            self._actualizar_estado()

    def _fin_trabajo(self):
        self.trabajo.deleteLater()      # Qt lo destruye cuando termina de emitir sus señales
        self.trabajo = None
        self._ocupado(False)

    def _fallo(self, texto):
        self.barraProgreso.setValue(0)
        self.log(texto.split("\n\n")[0])
        if texto != "Análisis cancelado.":
            caja = QMessageBox(QMessageBox.Critical, "Error", texto.split("\n\n")[0], parent=self)
            caja.setDetailedText(texto)
            caja.exec()

    def _terminado(self, R):
        self.log(f"Terminado en {time.time() - self._t0:.0f} s. Armando figuras...")
        try:
            self._mostrar(R)
        except Exception as e:
            self._fallo(f"{type(e).__name__} al armar las figuras: {e}\n\n{traceback.format_exc()}")
            return
        self.log("Listo.")

    # ---- resultados ----
    def _mostrar(self, R):
        for fig in self.figs.values():
            plt.close(fig)
        for w in self.lienzos:
            w.setParent(None)
            w.deleteLater()
        self.lienzos, self.R = [], R
        self.figs = gr.construir_figuras(R)
        for nombre_pestana, nombre_fig in PESTANAS.items():
            fig = self.figs[nombre_fig]
            plt.close(fig)              # se saca del gestor de pyplot: la dibuja su propio lienzo
            layout = getattr(self, f"layout{nombre_pestana}")
            getattr(self, f"lblVacio{nombre_pestana}").setVisible(False)
            lienzo = FigureCanvasQTAgg(fig)
            barra = NavigationToolbar2QT(lienzo, self)
            layout.addWidget(barra)
            layout.addWidget(lienzo, 1)
            self.lienzos += [barra, lienzo]

        self.tablas = self._tablas(R)
        self._llenar(self.tablaComponentes, self.tablas["componentes"])
        self._llenar(self.tablaSNR, self.tablas["snr"])
        self._llenar(self.tablaReproducibilidad, self.tablas["reproducibilidad"])

        X = R["resultados"]
        n20 = X["componentes"].set_index("componente").loc["N20"]
        lat = f"{gr.fmt(n20['lat_ms'])} ms" if n20["valido"] else "no confiable"
        self.lblResumen.setText(f"sub-{R['sujeto']} · run-{R['run']} · {X['M']} épocas\n"
                                f"N20: {lat} · SNR homogéneo: {gr.fmt(X['snr']['homogeneo'][0])} dB")
        for w in (self.btnGuardarFiguras, self.btnExportar, self.actionGuardarFiguras,
                  self.actionExportar):
            w.setEnabled(True)

    @staticmethod
    def _tablas(R):
        X = R["resultados"]
        comp = []
        for _, c in X["componentes"].iterrows():
            pp = "pico a pico" in c["componente"]
            comp.append({"Componente": c["componente"],
                         "Latencia (ms)": c["lat_ms"] if (not pp and c["valido"]) else np.nan,
                         "Límite IFCN (ms)": c["lat_lim_sup_ms"],
                         "z (paper)": c["z_paper"], "Amplitud (µV)": c["amp_uV"],
                         "Dentro de norma": c["dentro_rango"],
                         "Observación": "" if (pp or c["valido"]) else
                         "sin pico (borde o polaridad invertida)"})
        difs = X["difs"].set_index("metodo")
        snr = []
        for m in gr.METODOS:
            fila = {"Método": gr.NOMBRE_METODO[m], "SNR (dB)": X["snr"][m][0],
                    "± EE (dB)": X["snr"][m][1]}
            if m in difs.index:
                d = difs.loc[m]
                fila.update({"Dif. con homogéneo (dB)": d["dif_db"],
                             "IC 95 %": f"[{gr.fmt(d['ic95_inf'], 2)}; {gr.fmt(d['ic95_sup'], 2)}]",
                             "Significativa": bool(d["ic95_inf"] > 0 or d["ic95_sup"] < 0)})
            fila["Pendiente (dB/déc.)"] = X["pendientes"][m][0]
            snr.append(fila)
        rep = []
        for _, f in X["tabla_reproducibilidad"].iterrows():
            rep.append({"Componente": f["componente"], "Lat. 1.ª mitad (ms)": f["lat_1_ms"],
                        "Lat. 2.ª mitad (ms)": f["lat_2_ms"], "Δ lat. (ms)": f["dif_lat_ms"],
                        "Δ amp. (%)": 100 * f["dif_amp_rel"], "Cumple lat.": f["cumple_lat"],
                        "Cumple amp.": f["cumple_amp"]})
        columnas_snr = ["Método", "SNR (dB)", "± EE (dB)", "Dif. con homogéneo (dB)", "IC 95 %",
                        "Significativa", "Pendiente (dB/déc.)"]
        return dict(componentes=pd.DataFrame(comp), snr=pd.DataFrame(snr)[columnas_snr],
                    reproducibilidad=pd.DataFrame(rep), filtros=R["filtros"]["tabla"],
                    referencias=R["referencias"]["tabla"])

    @staticmethod
    def _llenar(tabla, df):
        tabla.clear()
        tabla.setRowCount(len(df))
        tabla.setColumnCount(len(df.columns))
        tabla.setHorizontalHeaderLabels(list(df.columns))
        for i, fila in enumerate(df.itertuples(index=False)):
            for j, v in enumerate(fila):
                if isinstance(v, (bool, np.bool_)):
                    texto = "Sí" if v else "No"
                elif v is None or (isinstance(v, float) and np.isnan(v)):
                    texto = "—"
                elif isinstance(v, (float, np.floating)):
                    texto = gr.fmt(v, 2)
                else:
                    texto = str(v)
                tabla.setItem(i, j, QTableWidgetItem(texto))
        tabla.resizeColumnsToContents()

    def guardar_figuras(self):
        if not self.figs:
            return
        defecto = cfg.DIR_RESULTADOS / f"figuras_sub-{self.R['sujeto']}"
        defecto.mkdir(parents=True, exist_ok=True)
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta para las figuras", str(defecto))
        if carpeta:
            for nombre, fig in self.figs.items():
                gr.guardar(fig, nombre, Path(carpeta))
            self.log(f"{len(self.figs)} figuras guardadas (PNG y PDF) en {carpeta}")

    def exportar_csv(self):
        if not self.tablas:
            return
        defecto = cfg.DIR_RESULTADOS / f"tablas_sub-{self.R['sujeto']}"
        defecto.mkdir(parents=True, exist_ok=True)
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta para los CSV", str(defecto))
        if carpeta:
            for nombre, df in self.tablas.items():
                # utf-8-sig: Excel muestra bien µ y las tildes
                df.to_csv(Path(carpeta) / f"{nombre}_sub-{self.R['sujeto']}.csv", index=False,
                          encoding="utf-8-sig")
            self.log(f"{len(self.tablas)} tablas exportadas en {carpeta}")

    def borrar_datos(self):
        sujetos = pacientes.descargados_por_interfaz()
        if not sujetos:
            self.log("No hay datos descargados por la interfaz (las carpetas descargadas a mano "
                     "no se borran desde acá).")
            return
        lista = ", ".join(f"sub-{s}" for s in sujetos)
        if QMessageBox.question(self, "Eliminar datos",
                                f"¿Eliminar los datos descargados por la interfaz ({lista})?\n"
                                "Los resultados guardados se conservan.") == QMessageBox.Yes:
            for s in sujetos:
                pacientes.borrar(s, self.log)
            self._actualizar_estado()

    def acerca_de(self):
        QMessageBox.about(self, "Acerca de",
                          "<b>PES del nervio mediano: SNR según el tipo de promediado</b><br>"
                          "16.63 PSIB — ITBA, 2026 Q2 — Grupo 14<br><br>"
                          "Datos: OpenNeuro ds004388 (Nierula et al., 2024).<br>"
                          f"{cfg.CANAL}–{cfg.REFERENCIA}, Butterworth {cfg.F_BAJO:g}–{cfg.F_ALTO:g} Hz "
                          f"(orden {cfg.ORDEN}, fase cero) + notch {cfg.F_NOTCH:g} Hz.<br>"
                          "Los parámetros se cambian en TPS/main/config.py.")

    def closeEvent(self, evento):
        if self.trabajo is not None:
            if QMessageBox.question(self, "Salir", "Hay un análisis en curso. ¿Cancelarlo y salir?") \
                    != QMessageBox.Yes:
                evento.ignore()
                return
            self.trabajo.cancelar()
            self.trabajo.wait(30000)
        evento.accept()


def main():
    app = QApplication(sys.argv)
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
