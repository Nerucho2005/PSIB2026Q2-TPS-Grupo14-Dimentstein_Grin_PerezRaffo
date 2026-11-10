# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ventana.ui'
##
## Created by: Qt User Interface Compiler version 6.12.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QMainWindow, QMenu, QMenuBar,
    QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy,
    QSpacerItem, QSplitter, QStatusBar, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1280, 820)
        self.actionProcesar = QAction(MainWindow)
        self.actionProcesar.setObjectName(u"actionProcesar")
        self.actionGuardarFiguras = QAction(MainWindow)
        self.actionGuardarFiguras.setObjectName(u"actionGuardarFiguras")
        self.actionExportar = QAction(MainWindow)
        self.actionExportar.setObjectName(u"actionExportar")
        self.actionSalir = QAction(MainWindow)
        self.actionSalir.setObjectName(u"actionSalir")
        self.actionAcercaDe = QAction(MainWindow)
        self.actionAcercaDe.setObjectName(u"actionAcercaDe")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.layoutCentral = QVBoxLayout(self.centralwidget)
        self.layoutCentral.setObjectName(u"layoutCentral")
        self.layoutSuperior = QHBoxLayout()
        self.layoutSuperior.setObjectName(u"layoutSuperior")
        self.panelControles = QWidget(self.centralwidget)
        self.panelControles.setObjectName(u"panelControles")
        self.panelControles.setMinimumSize(QSize(290, 0))
        self.panelControles.setMaximumSize(QSize(330, 16777215))
        self.layoutPanel = QVBoxLayout(self.panelControles)
        self.layoutPanel.setObjectName(u"layoutPanel")
        self.layoutPanel.setContentsMargins(0, 0, 0, 0)
        self.grupoPaciente = QGroupBox(self.panelControles)
        self.grupoPaciente.setObjectName(u"grupoPaciente")
        self.formPaciente = QFormLayout(self.grupoPaciente)
        self.formPaciente.setObjectName(u"formPaciente")
        self.labelPaciente = QLabel(self.grupoPaciente)
        self.labelPaciente.setObjectName(u"labelPaciente")

        self.formPaciente.setWidget(0, QFormLayout.ItemRole.LabelRole, self.labelPaciente)

        self.comboPaciente = QComboBox(self.grupoPaciente)
        self.comboPaciente.setObjectName(u"comboPaciente")

        self.formPaciente.setWidget(0, QFormLayout.ItemRole.FieldRole, self.comboPaciente)

        self.labelRun = QLabel(self.grupoPaciente)
        self.labelRun.setObjectName(u"labelRun")

        self.formPaciente.setWidget(1, QFormLayout.ItemRole.LabelRole, self.labelRun)

        self.lblRun = QLabel(self.grupoPaciente)
        self.lblRun.setObjectName(u"lblRun")
        self.lblRun.setWordWrap(True)

        self.formPaciente.setWidget(1, QFormLayout.ItemRole.FieldRole, self.lblRun)

        self.labelDatos = QLabel(self.grupoPaciente)
        self.labelDatos.setObjectName(u"labelDatos")

        self.formPaciente.setWidget(2, QFormLayout.ItemRole.LabelRole, self.labelDatos)

        self.lblDatos = QLabel(self.grupoPaciente)
        self.lblDatos.setObjectName(u"lblDatos")
        self.lblDatos.setWordWrap(True)

        self.formPaciente.setWidget(2, QFormLayout.ItemRole.FieldRole, self.lblDatos)


        self.layoutPanel.addWidget(self.grupoPaciente)

        self.grupoOpciones = QGroupBox(self.panelControles)
        self.grupoOpciones.setObjectName(u"grupoOpciones")
        self.layoutOpciones = QVBoxLayout(self.grupoOpciones)
        self.layoutOpciones.setObjectName(u"layoutOpciones")
        self.chkPromedio = QCheckBox(self.grupoOpciones)
        self.chkPromedio.setObjectName(u"chkPromedio")
        self.chkPromedio.setChecked(False)

        self.layoutOpciones.addWidget(self.chkPromedio)

        self.chkCache = QCheckBox(self.grupoOpciones)
        self.chkCache.setObjectName(u"chkCache")
        self.chkCache.setChecked(True)

        self.layoutOpciones.addWidget(self.chkCache)

        self.labelBorrado = QLabel(self.grupoOpciones)
        self.labelBorrado.setObjectName(u"labelBorrado")
        self.labelBorrado.setWordWrap(True)

        self.layoutOpciones.addWidget(self.labelBorrado)

        self.comboBorrado = QComboBox(self.grupoOpciones)
        self.comboBorrado.addItem("")
        self.comboBorrado.addItem("")
        self.comboBorrado.addItem("")
        self.comboBorrado.setObjectName(u"comboBorrado")

        self.layoutOpciones.addWidget(self.comboBorrado)


        self.layoutPanel.addWidget(self.grupoOpciones)

        self.grupoAnalisis = QGroupBox(self.panelControles)
        self.grupoAnalisis.setObjectName(u"grupoAnalisis")
        self.layoutAnalisis = QVBoxLayout(self.grupoAnalisis)
        self.layoutAnalisis.setObjectName(u"layoutAnalisis")
        self.btnProcesar = QPushButton(self.grupoAnalisis)
        self.btnProcesar.setObjectName(u"btnProcesar")

        self.layoutAnalisis.addWidget(self.btnProcesar)

        self.btnCancelar = QPushButton(self.grupoAnalisis)
        self.btnCancelar.setObjectName(u"btnCancelar")
        self.btnCancelar.setEnabled(False)

        self.layoutAnalisis.addWidget(self.btnCancelar)

        self.btnBorrarDatos = QPushButton(self.grupoAnalisis)
        self.btnBorrarDatos.setObjectName(u"btnBorrarDatos")

        self.layoutAnalisis.addWidget(self.btnBorrarDatos)


        self.layoutPanel.addWidget(self.grupoAnalisis)

        self.grupoResultados = QGroupBox(self.panelControles)
        self.grupoResultados.setObjectName(u"grupoResultados")
        self.layoutResultados = QVBoxLayout(self.grupoResultados)
        self.layoutResultados.setObjectName(u"layoutResultados")
        self.lblResumen = QLabel(self.grupoResultados)
        self.lblResumen.setObjectName(u"lblResumen")
        self.lblResumen.setWordWrap(True)

        self.layoutResultados.addWidget(self.lblResumen)

        self.btnGuardarFiguras = QPushButton(self.grupoResultados)
        self.btnGuardarFiguras.setObjectName(u"btnGuardarFiguras")
        self.btnGuardarFiguras.setEnabled(False)

        self.layoutResultados.addWidget(self.btnGuardarFiguras)

        self.btnExportar = QPushButton(self.grupoResultados)
        self.btnExportar.setObjectName(u"btnExportar")
        self.btnExportar.setEnabled(False)

        self.layoutResultados.addWidget(self.btnExportar)


        self.layoutPanel.addWidget(self.grupoResultados)

        self.spacerPanel = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.layoutPanel.addItem(self.spacerPanel)


        self.layoutSuperior.addWidget(self.panelControles)

        self.tabsGraficos = QTabWidget(self.centralwidget)
        self.tabsGraficos.setObjectName(u"tabsGraficos")
        self.tabPSD = QWidget()
        self.tabPSD.setObjectName(u"tabPSD")
        self.layoutPSD = QVBoxLayout(self.tabPSD)
        self.layoutPSD.setObjectName(u"layoutPSD")
        self.lblVacioPSD = QLabel(self.tabPSD)
        self.lblVacioPSD.setObjectName(u"lblVacioPSD")
        self.lblVacioPSD.setWordWrap(True)

        self.layoutPSD.addWidget(self.lblVacioPSD)

        self.tabsGraficos.addTab(self.tabPSD, "")
        self.tabArtefacto = QWidget()
        self.tabArtefacto.setObjectName(u"tabArtefacto")
        self.layoutArtefacto = QVBoxLayout(self.tabArtefacto)
        self.layoutArtefacto.setObjectName(u"layoutArtefacto")
        self.lblVacioArtefacto = QLabel(self.tabArtefacto)
        self.lblVacioArtefacto.setObjectName(u"lblVacioArtefacto")
        self.lblVacioArtefacto.setWordWrap(True)

        self.layoutArtefacto.addWidget(self.lblVacioArtefacto)

        self.tabsGraficos.addTab(self.tabArtefacto, "")
        self.tabFiltros = QWidget()
        self.tabFiltros.setObjectName(u"tabFiltros")
        self.layoutFiltros = QVBoxLayout(self.tabFiltros)
        self.layoutFiltros.setObjectName(u"layoutFiltros")
        self.lblVacioFiltros = QLabel(self.tabFiltros)
        self.lblVacioFiltros.setObjectName(u"lblVacioFiltros")
        self.lblVacioFiltros.setWordWrap(True)

        self.layoutFiltros.addWidget(self.lblVacioFiltros)

        self.tabsGraficos.addTab(self.tabFiltros, "")
        self.tabReferencias = QWidget()
        self.tabReferencias.setObjectName(u"tabReferencias")
        self.layoutReferencias = QVBoxLayout(self.tabReferencias)
        self.layoutReferencias.setObjectName(u"layoutReferencias")
        self.lblVacioReferencias = QLabel(self.tabReferencias)
        self.lblVacioReferencias.setObjectName(u"lblVacioReferencias")
        self.lblVacioReferencias.setWordWrap(True)

        self.layoutReferencias.addWidget(self.lblVacioReferencias)

        self.tabsGraficos.addTab(self.tabReferencias, "")
        self.tabLateralidad = QWidget()
        self.tabLateralidad.setObjectName(u"tabLateralidad")
        self.layoutLateralidad = QVBoxLayout(self.tabLateralidad)
        self.layoutLateralidad.setObjectName(u"layoutLateralidad")
        self.lblVacioLateralidad = QLabel(self.tabLateralidad)
        self.lblVacioLateralidad.setObjectName(u"lblVacioLateralidad")
        self.lblVacioLateralidad.setWordWrap(True)

        self.layoutLateralidad.addWidget(self.lblVacioLateralidad)

        self.tabsGraficos.addTab(self.tabLateralidad, "")
        self.tabPEP = QWidget()
        self.tabPEP.setObjectName(u"tabPEP")
        self.layoutPEP = QVBoxLayout(self.tabPEP)
        self.layoutPEP.setObjectName(u"layoutPEP")
        self.lblVacioPEP = QLabel(self.tabPEP)
        self.lblVacioPEP.setObjectName(u"lblVacioPEP")
        self.lblVacioPEP.setWordWrap(True)

        self.layoutPEP.addWidget(self.lblVacioPEP)

        self.tabsGraficos.addTab(self.tabPEP, "")
        self.tabCurvas = QWidget()
        self.tabCurvas.setObjectName(u"tabCurvas")
        self.layoutCurvas = QVBoxLayout(self.tabCurvas)
        self.layoutCurvas.setObjectName(u"layoutCurvas")
        self.lblVacioCurvas = QLabel(self.tabCurvas)
        self.lblVacioCurvas.setObjectName(u"lblVacioCurvas")
        self.lblVacioCurvas.setWordWrap(True)

        self.layoutCurvas.addWidget(self.lblVacioCurvas)

        self.tabsGraficos.addTab(self.tabCurvas, "")
        self.tabDiferencias = QWidget()
        self.tabDiferencias.setObjectName(u"tabDiferencias")
        self.layoutDiferencias = QVBoxLayout(self.tabDiferencias)
        self.layoutDiferencias.setObjectName(u"layoutDiferencias")
        self.lblVacioDiferencias = QLabel(self.tabDiferencias)
        self.lblVacioDiferencias.setObjectName(u"lblVacioDiferencias")
        self.lblVacioDiferencias.setWordWrap(True)

        self.layoutDiferencias.addWidget(self.lblVacioDiferencias)

        self.tabsGraficos.addTab(self.tabDiferencias, "")
        self.tabPesos = QWidget()
        self.tabPesos.setObjectName(u"tabPesos")
        self.layoutPesos = QVBoxLayout(self.tabPesos)
        self.layoutPesos.setObjectName(u"layoutPesos")
        self.lblVacioPesos = QLabel(self.tabPesos)
        self.lblVacioPesos.setObjectName(u"lblVacioPesos")
        self.lblVacioPesos.setWordWrap(True)

        self.layoutPesos.addWidget(self.lblVacioPesos)

        self.tabsGraficos.addTab(self.tabPesos, "")
        self.tabReproducibilidad = QWidget()
        self.tabReproducibilidad.setObjectName(u"tabReproducibilidad")
        self.layoutReproducibilidad = QVBoxLayout(self.tabReproducibilidad)
        self.layoutReproducibilidad.setObjectName(u"layoutReproducibilidad")
        self.lblVacioReproducibilidad = QLabel(self.tabReproducibilidad)
        self.lblVacioReproducibilidad.setObjectName(u"lblVacioReproducibilidad")
        self.lblVacioReproducibilidad.setWordWrap(True)

        self.layoutReproducibilidad.addWidget(self.lblVacioReproducibilidad)

        self.tabsGraficos.addTab(self.tabReproducibilidad, "")
        self.tabMetricas = QWidget()
        self.tabMetricas.setObjectName(u"tabMetricas")
        self.layoutTabMetricas = QVBoxLayout(self.tabMetricas)
        self.layoutTabMetricas.setObjectName(u"layoutTabMetricas")
        self.splitterMetricas = QSplitter(self.tabMetricas)
        self.splitterMetricas.setObjectName(u"splitterMetricas")
        self.splitterMetricas.setOrientation(Qt.Vertical)
        self.grupoComponentes = QGroupBox(self.splitterMetricas)
        self.grupoComponentes.setObjectName(u"grupoComponentes")
        self.layoutComponentes = QVBoxLayout(self.grupoComponentes)
        self.layoutComponentes.setObjectName(u"layoutComponentes")
        self.tablaComponentes = QTableWidget(self.grupoComponentes)
        self.tablaComponentes.setObjectName(u"tablaComponentes")
        self.tablaComponentes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablaComponentes.setAlternatingRowColors(True)
        self.tablaComponentes.horizontalHeader().setStretchLastSection(True)
        self.tablaComponentes.verticalHeader().setVisible(False)

        self.layoutComponentes.addWidget(self.tablaComponentes)

        self.splitterMetricas.addWidget(self.grupoComponentes)
        self.grupoSNR = QGroupBox(self.splitterMetricas)
        self.grupoSNR.setObjectName(u"grupoSNR")
        self.layoutSNR = QVBoxLayout(self.grupoSNR)
        self.layoutSNR.setObjectName(u"layoutSNR")
        self.tablaSNR = QTableWidget(self.grupoSNR)
        self.tablaSNR.setObjectName(u"tablaSNR")
        self.tablaSNR.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablaSNR.setAlternatingRowColors(True)
        self.tablaSNR.horizontalHeader().setStretchLastSection(True)
        self.tablaSNR.verticalHeader().setVisible(False)

        self.layoutSNR.addWidget(self.tablaSNR)

        self.splitterMetricas.addWidget(self.grupoSNR)
        self.grupoReproducibilidad = QGroupBox(self.splitterMetricas)
        self.grupoReproducibilidad.setObjectName(u"grupoReproducibilidad")
        self.layoutTablaRep = QVBoxLayout(self.grupoReproducibilidad)
        self.layoutTablaRep.setObjectName(u"layoutTablaRep")
        self.tablaReproducibilidad = QTableWidget(self.grupoReproducibilidad)
        self.tablaReproducibilidad.setObjectName(u"tablaReproducibilidad")
        self.tablaReproducibilidad.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tablaReproducibilidad.setAlternatingRowColors(True)
        self.tablaReproducibilidad.horizontalHeader().setStretchLastSection(True)
        self.tablaReproducibilidad.verticalHeader().setVisible(False)

        self.layoutTablaRep.addWidget(self.tablaReproducibilidad)

        self.splitterMetricas.addWidget(self.grupoReproducibilidad)

        self.layoutTabMetricas.addWidget(self.splitterMetricas)

        self.tabsGraficos.addTab(self.tabMetricas, "")

        self.layoutSuperior.addWidget(self.tabsGraficos)


        self.layoutCentral.addLayout(self.layoutSuperior)

        self.txtLog = QPlainTextEdit(self.centralwidget)
        self.txtLog.setObjectName(u"txtLog")
        self.txtLog.setMaximumSize(QSize(16777215, 110))
        self.txtLog.setReadOnly(True)

        self.layoutCentral.addWidget(self.txtLog)

        self.barraProgreso = QProgressBar(self.centralwidget)
        self.barraProgreso.setObjectName(u"barraProgreso")
        self.barraProgreso.setValue(0)

        self.layoutCentral.addWidget(self.barraProgreso)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1280, 21))
        self.menuArchivo = QMenu(self.menubar)
        self.menuArchivo.setObjectName(u"menuArchivo")
        self.menuAyuda = QMenu(self.menubar)
        self.menuAyuda.setObjectName(u"menuAyuda")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuArchivo.menuAction())
        self.menubar.addAction(self.menuAyuda.menuAction())
        self.menuArchivo.addAction(self.actionProcesar)
        self.menuArchivo.addAction(self.actionGuardarFiguras)
        self.menuArchivo.addAction(self.actionExportar)
        self.menuArchivo.addSeparator()
        self.menuArchivo.addAction(self.actionSalir)
        self.menuAyuda.addAction(self.actionAcercaDe)

        self.retranslateUi(MainWindow)

        self.tabsGraficos.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"PES del nervio mediano \u2014 SNR seg\u00fan el promediado", None))
        self.actionProcesar.setText(QCoreApplication.translate("MainWindow", u"Descargar y analizar", None))
#if QT_CONFIG(shortcut)
        self.actionProcesar.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+R", None))
#endif // QT_CONFIG(shortcut)
        self.actionGuardarFiguras.setText(QCoreApplication.translate("MainWindow", u"Guardar figuras...", None))
#if QT_CONFIG(shortcut)
        self.actionGuardarFiguras.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+S", None))
#endif // QT_CONFIG(shortcut)
        self.actionExportar.setText(QCoreApplication.translate("MainWindow", u"Exportar CSV...", None))
#if QT_CONFIG(shortcut)
        self.actionExportar.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+E", None))
#endif // QT_CONFIG(shortcut)
        self.actionSalir.setText(QCoreApplication.translate("MainWindow", u"Salir", None))
#if QT_CONFIG(shortcut)
        self.actionSalir.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+Q", None))
#endif // QT_CONFIG(shortcut)
        self.actionAcercaDe.setText(QCoreApplication.translate("MainWindow", u"Acerca de", None))
        self.grupoPaciente.setTitle(QCoreApplication.translate("MainWindow", u"1. Paciente", None))
        self.labelPaciente.setText(QCoreApplication.translate("MainWindow", u"Paciente", None))
#if QT_CONFIG(tooltip)
        self.comboPaciente.setToolTip(QCoreApplication.translate("MainWindow", u"Sujetos del dataset ds004388 (OpenNeuro)", None))
#endif // QT_CONFIG(tooltip)
        self.labelRun.setText(QCoreApplication.translate("MainWindow", u"Run", None))
        self.lblRun.setText(QCoreApplication.translate("MainWindow", u"-", None))
        self.labelDatos.setText(QCoreApplication.translate("MainWindow", u"Datos", None))
        self.lblDatos.setText(QCoreApplication.translate("MainWindow", u"(sin verificar)", None))
        self.grupoOpciones.setTitle(QCoreApplication.translate("MainWindow", u"2. Opciones", None))
        self.chkPromedio.setText(QCoreApplication.translate("MainWindow", u"Incluir referencia promedio (lento)", None))
#if QT_CONFIG(tooltip)
        self.chkPromedio.setToolTip(QCoreApplication.translate("MainWindow", u"Agrega la referencia promedio a la figura de referencias", None))
#endif // QT_CONFIG(tooltip)
        self.chkCache.setText(QCoreApplication.translate("MainWindow", u"Usar resultados guardados si existen", None))
#if QT_CONFIG(tooltip)
        self.chkCache.setToolTip(QCoreApplication.translate("MainWindow", u"Si el paciente ya se analiz\u00f3 con los mismos par\u00e1metros, no se descarga ni se recalcula", None))
#endif // QT_CONFIG(tooltip)
        self.labelBorrado.setText(QCoreApplication.translate("MainWindow", u"Datos descargados:", None))
        self.comboBorrado.setItemText(0, QCoreApplication.translate("MainWindow", u"Eliminar al terminar el an\u00e1lisis", None))
        self.comboBorrado.setItemText(1, QCoreApplication.translate("MainWindow", u"Eliminar al cambiar de paciente", None))
        self.comboBorrado.setItemText(2, QCoreApplication.translate("MainWindow", u"Conservar", None))

        self.grupoAnalisis.setTitle(QCoreApplication.translate("MainWindow", u"3. An\u00e1lisis", None))
        self.btnProcesar.setText(QCoreApplication.translate("MainWindow", u"Descargar y analizar", None))
#if QT_CONFIG(tooltip)
        self.btnProcesar.setToolTip(QCoreApplication.translate("MainWindow", u"Descarga los runs que falten, filtra, promedia y calcula la SNR", None))
#endif // QT_CONFIG(tooltip)
        self.btnCancelar.setText(QCoreApplication.translate("MainWindow", u"Cancelar", None))
        self.btnBorrarDatos.setText(QCoreApplication.translate("MainWindow", u"Eliminar datos descargados", None))
#if QT_CONFIG(tooltip)
        self.btnBorrarDatos.setToolTip(QCoreApplication.translate("MainWindow", u"Borra solo las carpetas que descarg\u00f3 la interfaz", None))
#endif // QT_CONFIG(tooltip)
        self.grupoResultados.setTitle(QCoreApplication.translate("MainWindow", u"4. Resultados", None))
        self.lblResumen.setText(QCoreApplication.translate("MainWindow", u"(sin resultados)", None))
        self.btnGuardarFiguras.setText(QCoreApplication.translate("MainWindow", u"Guardar figuras...", None))
        self.btnExportar.setText(QCoreApplication.translate("MainWindow", u"Exportar CSV...", None))
        self.lblVacioPSD.setText(QCoreApplication.translate("MainWindow", u"Todav\u00eda no hay resultados.", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabPSD), QCoreApplication.translate("MainWindow", u"1. Espectro", None))
        self.lblVacioArtefacto.setText(QCoreApplication.translate("MainWindow", u"Todav\u00eda no hay resultados.", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabArtefacto), QCoreApplication.translate("MainWindow", u"2. Artefacto", None))
        self.lblVacioFiltros.setText(QCoreApplication.translate("MainWindow", u"Todav\u00eda no hay resultados.", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabFiltros), QCoreApplication.translate("MainWindow", u"3. Filtros", None))
        self.lblVacioReferencias.setText(QCoreApplication.translate("MainWindow", u"Todav\u00eda no hay resultados.", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabReferencias), QCoreApplication.translate("MainWindow", u"4. Referencias", None))
        self.lblVacioLateralidad.setText(QCoreApplication.translate("MainWindow", u"Todav\u00eda no hay resultados.", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabLateralidad), QCoreApplication.translate("MainWindow", u"5. Lateralidad", None))
        self.lblVacioPEP.setText(QCoreApplication.translate("MainWindow", u"Todav\u00eda no hay resultados.", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabPEP), QCoreApplication.translate("MainWindow", u"6. PEP por m\u00e9todo", None))
        self.lblVacioCurvas.setText(QCoreApplication.translate("MainWindow", u"Todav\u00eda no hay resultados.", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabCurvas), QCoreApplication.translate("MainWindow", u"7. SNR vs. N", None))
        self.lblVacioDiferencias.setText(QCoreApplication.translate("MainWindow", u"Todav\u00eda no hay resultados.", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabDiferencias), QCoreApplication.translate("MainWindow", u"8. Dif. de SNR", None))
        self.lblVacioPesos.setText(QCoreApplication.translate("MainWindow", u"Todav\u00eda no hay resultados.", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabPesos), QCoreApplication.translate("MainWindow", u"9. Pesos", None))
        self.lblVacioReproducibilidad.setText(QCoreApplication.translate("MainWindow", u"Todav\u00eda no hay resultados.", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabReproducibilidad), QCoreApplication.translate("MainWindow", u"10. Reproducib.", None))
        self.grupoComponentes.setTitle(QCoreApplication.translate("MainWindow", u"Componentes del PEP (promedio homog\u00e9neo, CP4\u2013Fz)", None))
        self.grupoSNR.setTitle(QCoreApplication.translate("MainWindow", u"SNR por m\u00e9todo (\u00b1 error est\u00e1ndar jackknife) y diferencia con el homog\u00e9neo", None))
        self.grupoReproducibilidad.setTitle(QCoreApplication.translate("MainWindow", u"Reproducibilidad (primera vs. segunda mitad, criterio IFCN)", None))
        self.tabsGraficos.setTabText(self.tabsGraficos.indexOf(self.tabMetricas), QCoreApplication.translate("MainWindow", u"M\u00e9tricas", None))
        self.txtLog.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Registro de eventos...", None))
        self.menuArchivo.setTitle(QCoreApplication.translate("MainWindow", u"Archivo", None))
        self.menuAyuda.setTitle(QCoreApplication.translate("MainWindow", u"Ayuda", None))
    # retranslateUi

