from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsMapLayerProxyModel

class ComboBoxMapLayerLine(QgsMapLayerComboBox):
    
    def __init__(self, transformGeometryCrsFunction):
        super(ComboBoxMapLayerLine, self).__init__()
        self.transformGeometryCrsFunction = transformGeometryCrsFunction
        self.setFilters(QgsMapLayerProxyModel.LineLayer)