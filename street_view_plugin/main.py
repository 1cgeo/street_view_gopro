import os, sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from .modules.qgis.controllers.qgisCtrl import QgisCtrl
from .controllers.streetviewCtrl import StreetViewCtrl
from .config import Config
from qgis.utils import iface

class Main:

    def __init__(self, iface):    
        super(Main, self).__init__()
        self.plugin_dir = os.path.dirname(__file__)
        self.qgisCtrl = QgisCtrl()
        self.action = None
        self.streetViewCtrl = StreetViewCtrl(qgis=self.qgisCtrl)

    def initGui(self):
        self.action = self.qgisCtrl.createAction(
            Config.NAME,
            self.getPluginIconPath(),
            self.startPlugin
            
        )
        self.qgisCtrl.addActionDigitizeToolBar(self.action)
        
    def unload(self):
        self.qgisCtrl.removeActionDigitizeToolBar(
            self.action
        )
        
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
