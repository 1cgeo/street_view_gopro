from qgis.PyQt.QtXml import QDomDocument
from PyQt5 import QtCore, QtWidgets, QtGui 
from qgis import gui, core
import base64, os, processing
from qgis.utils import plugins, iface
from configparser import ConfigParser
from PyQt5.QtWidgets import QAction, QMenu
from PyQt5.QtGui import QIcon
import math, uuid
from configparser import ConfigParser
import subprocess
import platform
import shutil

class QgisCtrl:

    def addActionDigitizeToolBar(self, action):
        iface.digitizeToolBar().addAction(action)

    def removeActionDigitizeToolBar(self, action):
        iface.digitizeToolBar().removeAction(action)

    def createAction(self, name, iconPath, callback):
        a = QAction(
            QIcon(iconPath),
            name,
            iface.mainWindow()
        )
        a.triggered.connect(callback)
        return a

    def addDockWidget(self, dockWidget):
        iface.addDockWidget(QtCore.Qt.RightDockWidgetArea, dockWidget)
    
    def removeDockWidget(self, dockWidget):
        if not dockWidget.isVisible():
            return
        iface.removeDockWidget(dockWidget)
