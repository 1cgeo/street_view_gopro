from .main import Main
from qgis.core import QgsApplication
from .provider import StreetviewProvider

def classFactory(iface):
    return Main(iface)

def registerProcessingProvider():
    global streetview_provider
    streetview_provider = StreetviewProvider()
    QgsApplication.processingRegistry().addProvider(streetview_provider)

def unloadProcessingProvider():
    global streetview_provider
    if streetview_provider is not None:
        QgsApplication.processingRegistry().removeProvider(streetview_provider)
        streetview_provider = None