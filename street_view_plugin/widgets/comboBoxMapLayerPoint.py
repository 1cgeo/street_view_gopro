from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsMapLayerProxyModel

class ComboBoxMapLayerPoint(QgsMapLayerComboBox):
    
    def __init__(self, transformGeometryCrsFunction):
        super(ComboBoxMapLayerPoint, self).__init__()
        self.transformGeometryCrsFunction = transformGeometryCrsFunction
        self.setFilters(QgsMapLayerProxyModel.PointLayer)