from qgis.gui import QgsMapLayerComboBox

class ComboBoxMapLayer(QgsMapLayerComboBox):
    
    def __init__(self, transformGeometryCrsFunction):
        super(ComboBoxMapLayer, self).__init__()
        self.transformGeometryCrsFunction = transformGeometryCrsFunction

    def getCurrentLayerFields(self):
        if not self.currentLayer():
            return []
        return self.currentLayer().fields().names()