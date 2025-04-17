import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from .modules.qgis.controllers.qgisCtrl import QgisCtrl
from .controllers.streetviewCtrl import StreetViewCtrl
from .config import Config
from qgis.utils import iface

# Importação do provider
from qgis.core import QgsApplication
from .provider import StreetviewProvider

class Main:

    def __init__(self, iface):
        super(Main, self).__init__()
        self.plugin_dir = os.path.dirname(__file__)
        self.qgisCtrl = QgisCtrl()
        self.action = None
        self.streetViewCtrl = StreetViewCtrl(qgis=self.qgisCtrl)

        # Inicializa a referência ao provider
        self.provider = None

    def initGui(self):
        self.action = self.qgisCtrl.createAction(
            Config.NAME,
            self.getPluginIconPath(),
            self.startPlugin
        )
        self.qgisCtrl.addActionDigitizeToolBar(self.action)

        # ➕ Registrar o StreetviewProvider
        self.provider = StreetviewProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        self.qgisCtrl.removeActionDigitizeToolBar(self.action)

        # ➖ Desregistrar o StreetviewProvider
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

    def startPlugin(self, b):
        self.streetViewCtrl.loadDock()

    def getPluginIconPath(self):
        return os.path.join(
            os.path.abspath(os.path.join(
                os.path.dirname(__file__)
            )),
            'icons',
            'streetview.png'
        )
