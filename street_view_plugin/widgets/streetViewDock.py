import os, sys, copy
from PyQt5 import QtCore, uic, QtWidgets, QtGui
from street_view_plugin.factories.iconPathFactory import IconPathFactory
from datetime import datetime
import time

class StreetViewDock(QtWidgets.QDockWidget):

    def __init__(
            self, 
            controller,
            iconPathFactory=IconPathFactory()
        ):
        super(StreetViewDock, self).__init__()
        uic.loadUi(self.getUIPath(), self)
        self.controller = controller
        self.iconPathFactory = iconPathFactory
        self.dateTimeEdit.setDisplayFormat(
            self.getDateTimeFormat()
        )
        self.setupInputs()
        self.setupConfig()

    def getDateTimeFormat(self):
        return "yyyy-MM-dd HH:mm:ss"

    def setController(self, controller):
        self.controller = controller

    def getController(self):
        return self.controller

    def getInputs(self):
        return {
            'battery': self.batteryPerSb,
            'storage': self.storageGBSb,
            'gyroPath': self.gyroFilePathLe,
            'numberPhotos': self.numPhotosSb,
            'datetime': self.dateTimeEdit
        }

    def getInput(self, name):
        return self.getInputs()[name]

    def getButton(self, name):
        return self.getButtons()[name]

    def getButtons(self):
        return {
            'battery': self.saveBatteryPercBtn,
            'storage': self.saveStorageGBBtn,
            'gyroPath': self.saveGyroFilePathBtn,
            'numberPhotos': self.saveNumPhotosBtn,
            'datetime': self.saveDateTimeBtn
        }

    def setupConfig(self):
        self.dateTimeEdit.setDateTime(QtCore.QDateTime.currentDateTime())
        allConfig = self.getController().getAllConfig()
        for key in allConfig:
            widget = self.getInput(key)
            if type(widget) == QtWidgets.QLineEdit:
                widget.setText(allConfig[key])
                continue
            if type(widget) == QtWidgets.QSpinBox:
                widget.setValue(allConfig[key])
                continue
            widget.setDateTime(QtCore.QDateTime.fromSecsSinceEpoch(allConfig[key]))
        self.updateBatteryStatus()
        self.updateStorageStatus()
        self.updateGyroStatus()

    def hasStartDateTime(self):
        allConfig = self.getController().getAllConfig()
        return 'datetime' in allConfig

    def updateBatteryStatus(self, status='info'):
        self.stopBatteryAlarmBtn.setVisible(False if status == 'info' else True)
        if status == 'warning':
            self.batteryStatus.showMessage(
                '''
                    <b style='color: red'>Troque a bateria!</b>
                ''',
                'warning'
            )
            return
        percent = self.batteryPerSb.value()
        if percent == 0 or not self.hasStartDateTime():
            self.batteryStatus.setVisible(False)
            return
        self.batteryStatus.setVisible(True)
        currentEpoch = self.dateTimeEdit.dateTime().toSecsSinceEpoch()
        durationSeconds = self.getController().calcBatteryDuration(percent)
        self.batteryStatus.showMessage(
            '''
                <b>Previsão de troca: {}</b>
            '''.format(datetime.fromtimestamp(currentEpoch + durationSeconds))
        )
        self.getController().startBatteryAlarm()
        
    def updateStorageStatus(self, status='info'):
        self.stopStorageAlarmBtn.setVisible(False if status == 'info' else True)
        if status == 'warning':
            self.storageStatus.showMessage(
                '''
                    <b style='color: red'>Troque o cartão de memória!</b>
                ''',
                'warning'
            )
            return
        sizeGB = self.storageGBSb.value()
        if sizeGB == 0 or not self.hasStartDateTime():
            self.storageStatus.setVisible(False)
            return
        self.storageStatus.setVisible(True)
        numberPhotos = self.numPhotosSb.value()
        currentEpoch = self.dateTimeEdit.dateTime().toSecsSinceEpoch()
        durationSeconds = self.getController().calcStorageDuration(sizeGB, numberPhotos)
        self.storageStatus.showMessage(
            '''
                <b>Previsão de troca: {}</b>
            '''.format(datetime.fromtimestamp(currentEpoch + durationSeconds))
        )
        self.getController().startStorageAlarm()

    def updateGyroStatus(self, status='info'):
        self.stopGyroAlarmBtn.setVisible(False if status == 'info' else True)
        if status == 'warning':
            self.gyroStatus.showMessage(
                '''
                    <b style='color:red'>Giroscópio não está sendo gravado!</b>
                ''',
                'warning'
            )
            return
        gyroFilePath = self.gyroFilePathLe.text()
        if gyroFilePath == '':
            self.gyroStatus.setVisible(False)
            return
        self.gyroStatus.setVisible(True)
        self.gyroStatus.showMessage(
            '''
                <b>Gravando ...</b>
            '''
            if self.getController().isRecordingGyro()
            else '<b>Não está gravando!</b>'
        )

    def getIconPathSaveButton(self, key):
        allConfig = self.getController().getAllConfig()
        return 'saved' if allConfig and key in allConfig else 'not-saved'

    def setupInputs(self):
        for setup in [
                {
                    'spinbox': self.batteryPerSb,
                    'min': 0,
                    'max': 100
                },
                {
                    'spinbox': self.storageGBSb,
                    'min': 0,
                    'max': 1000
                },
                {
                    'spinbox': self.numPhotosSb,
                    'min': 0,
                    'max': 200000
                }
            ]:
            setup['spinbox'].setMinimum(setup['min'])
            setup['spinbox'].setMaximum(setup['max'])
        for setup in [
                {
                    'button': self.stopBatteryAlarmBtn,
                    'iconPath': self.iconPathFactory.get('ok')
                },
                {
                    'button': self.stopStorageAlarmBtn,
                    'iconPath': self.iconPathFactory.get('ok')
                },
                {
                    'button': self.stopGyroAlarmBtn,
                    'iconPath': self.iconPathFactory.get('ok')
                }
            ]:
            setup['button'].setIcon(QtGui.QIcon(setup['iconPath']))
            setup['button'].setIconSize(QtCore.QSize(20, 20))
        self.setupSaveButton()
        self.connectSignals()

    def setupSaveButton(self):
        for setup in [
                {
                    'button': self.saveBatteryPercBtn,
                    'iconPath': self.iconPathFactory.get(self.getIconPathSaveButton('battery'))
                },
                {
                    'button': self.saveStorageGBBtn,
                    'iconPath': self.iconPathFactory.get(self.getIconPathSaveButton('storage'))
                },
                {
                    'button': self.saveGyroFilePathBtn,
                    'iconPath': self.iconPathFactory.get(self.getIconPathSaveButton('gyroPath'))
                },
                {
                    'button': self.saveNumPhotosBtn,
                    'iconPath': self.iconPathFactory.get(self.getIconPathSaveButton('numberPhotos'))
                },
                {
                    'button': self.saveDateTimeBtn,
                    'iconPath': self.iconPathFactory.get(self.getIconPathSaveButton('datetime'))
                }
            ]:
            setup['button'].setIcon(QtGui.QIcon(setup['iconPath']))
            setup['button'].setIconSize(QtCore.QSize(20, 20))
            #setup['button'].setToolTip(toolTip)

    def connectSignals(self):
        self.batteryPerSb.valueChanged.connect(lambda *args: self.updateStatus('battery'))
        self.storageGBSb.valueChanged.connect(lambda *args: self.updateStatus('storage'))
        self.gyroFilePathLe.textChanged.connect(lambda *args: self.updateStatus('gyroPath'))
        self.numPhotosSb.valueChanged.connect(lambda *args: self.updateStatus('numberPhotos'))

    def updateStatus(self, key):
        allConfig = self.getController().getAllConfig()
        if not(key in allConfig):
            return
        inputW = self.getInput(key)
        if type(inputW) == QtWidgets.QLineEdit:
            currentValue = inputW.text()
        else:
            currentValue = inputW.value()
        isEqual = currentValue == allConfig[key]
        button = self.getButton(key)
        button.setIcon(
            QtGui.QIcon(
                self.iconPathFactory.get(
                    'saved' if isEqual else 'not-saved'
                )
            )
        )
        button.setIconSize(QtCore.QSize(20, 20))
                
    def getUIPath(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 
            '..',
            'uis',
            'streetViewDock.ui'
        )

    def showErrorMessage(self, title, text):
        QtWidgets.QMessageBox.critical(
            self,
            title, 
            text
        )
    
    @QtCore.pyqtSlot(bool)
    def on_selectGyroFilePathBtn_clicked(self):
        filePath = QtWidgets.QFileDialog.getSaveFileName(
            self, 
            "",
            "trak-giro-{}.csv".format(
                datetime.now().strftime("%d-%m-%Y")

            ),
            '*.csv'
        )
        if not filePath[0]:
            return
        self.gyroFilePathLe.setText(filePath[0])

    @QtCore.pyqtSlot(bool)
    def on_saveGyroFilePathBtn_clicked(self):
        self.getController().setConfig('gyroPath', self.gyroFilePathLe.text())
        self.setupSaveButton()

    @QtCore.pyqtSlot(bool)
    def on_startTrackGyroBtn_clicked(self):
        try:
            self.getController().startTrackGyroscope()
        except Exception as e:
            self.showErrorMessage('Erro', str(e))

    @QtCore.pyqtSlot(bool)
    def on_stopTrackGyroBtn_clicked(self):
        self.getController().stopTrackGyroscope()

    @QtCore.pyqtSlot(bool)
    def on_saveBatteryPercBtn_clicked(self):
        percent = self.batteryPerSb.value()
        self.getController().setConfig('battery', percent)
        self.setupSaveButton()
        self.updateBatteryStatus()

    @QtCore.pyqtSlot(bool)
    def on_saveStorageGBBtn_clicked(self):
        sizeGB = self.storageGBSb.value()
        self.getController().setConfig('storage', sizeGB)
        self.setupSaveButton()
        self.updateStorageStatus()

    @QtCore.pyqtSlot(bool)
    def on_saveNumPhotosBtn_clicked(self):
        numberPhotos = self.numPhotosSb.value()
        self.getController().setConfig('numberPhotos', numberPhotos)
        self.setupSaveButton()
        self.updateStorageStatus()

    @QtCore.pyqtSlot(bool)
    def on_saveDateTimeBtn_clicked(self):
        dateTime = self.dateTimeEdit.dateTime().toSecsSinceEpoch()
        self.getController().setConfig('datetime', dateTime)
        self.setupSaveButton()
        self.updateStorageStatus()
        self.updateBatteryStatus()

    @QtCore.pyqtSlot(bool)
    def on_stopBatteryAlarmBtn_clicked(self):
        self.getController().stopBatteryAlarm()
        self.stopBatteryAlarmBtn.setVisible(False)

    @QtCore.pyqtSlot(bool)
    def on_stopStorageAlarmBtn_clicked(self):
        self.getController().stopStorageAlarm()
        self.stopStorageAlarmBtn.setVisible(False)

    @QtCore.pyqtSlot(bool)
    def on_stopGyroAlarmBtn_clicked(self):
        self.getController().stopGyroAlarm()
        self.stopGyroAlarmBtn.setVisible(False)

    @QtCore.pyqtSlot(bool)
    def on_selectImageFolderPathBtn_clicked(self):
        filePath = QtWidgets.QFileDialog.getExistingDirectory(
            self, 
            "Selecionar Pasta de Imagens",
            ""
        )
        if not filePath:
            return
        self.imageFolderPathLe.setText(filePath)

    @QtCore.pyqtSlot(bool)
    def on_selecCSVGyroPathBtn_clicked(self):
        filePath = QtWidgets.QFileDialog.getOpenFileName(
            self, 
            "Selecionar CSV track giroscópio",
            "",
            '*.csv'
        )
        if not filePath[0]:
            return
        self.gyroCSVFilePathLe.setText(filePath[0])

    @QtCore.pyqtSlot(bool)
    def on_buildStructBtn_clicked(self):
        if not( self.imageFolderPathLe.text() and self.gyroCSVFilePathLe.text()):
            self.showErrorMessage('Erro', 'Selecione os Arquivos')
            return
        self.getController().buildStruct(
            self.imageFolderPathLe.text(),
            self.gyroCSVFilePathLe.text()
        )

