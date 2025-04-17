from qgis.core import QgsProcessingProvider
from .processings.compactar.compactar import ComprimirImagensExifTool  # Plota pontos das imagens
from .processings.pre_processar.Pontos_imagens import ImageToGeometry  # Plota pontos das imagens
from .processings.pre_processar.Remove_pontos_parada import RemovePontosDeParada  # Copia imagens
from .processings.pre_processar.Copia_imagens import CopiaImagens  # Copia imagens
from .processings.recuperar.Adiciona_coordenadas_EXIF import AdicionaCoordenadasExiftool  # Adiciona metadados GPS
from qgis.PyQt.QtGui import QIcon
import os

class StreetviewProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(ComprimirImagensExifTool())
        self.addAlgorithm(ImageToGeometry())
        self.addAlgorithm(RemovePontosDeParada())
        self.addAlgorithm(CopiaImagens())
        self.addAlgorithm(AdicionaCoordenadasExiftool())

    def id(self):
        return "streetview"

    def name(self):
        return "Street View - Processamentos Auxiliares"

    def longName(self):
        return self.name()

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icons', 'streetview.png'))
