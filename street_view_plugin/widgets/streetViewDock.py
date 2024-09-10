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

    def showInfoMessage(self, title, text):
        QtWidgets.QMessageBox.information(
            self,
            title, 
            text
        )
    
    def showYesNoMessage(self, title, text):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setWindowTitle(title)
        msgBox.setText(text)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msgBox.setDefaultButton(QtWidgets.QMessageBox.No)
        result = msgBox.exec_()
        if result == QtWidgets.QMessageBox.Yes:
            return True
        return False
    
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
    def on_buildStructBtn_clicked(self):
        if not self.imageFolderPathLe.text() :
            self.showErrorMessage('Erro', 'Selecione a Pasta de Imagens')
            return
        self.getController().buildStruct(
            self.imageFolderPathLe.text()
        )

    @QtCore.pyqtSlot(bool)
    def on_selectMetadataFolderPathBtn_clicked(self):
        filePath = QtWidgets.QFileDialog.getExistingDirectory(
            self, 
            "Selecionar Pasta de Metadados",
            ""
        )
        if not filePath:
            return
        self.metadataFolderPathLe.setText(filePath)
        # self.showInfoMessage('Aviso', 'Estrutura de imagens criada com sucesso!')

    @QtCore.pyqtSlot(bool)
    def on_buildSiteMetadataBtn_clicked(self):
        imageLayer = self.imageLayer.currentLayer()
        connectionLayer = self.connectionLayer.currentLayer()
        metadataFolderPath = self.metadataFolderPathLe.text()
        if not( imageLayer and connectionLayer and metadataFolderPath):
            self.showErrorMessage('Erro', 'Preencha todos os campos!')
            return
        self.getController().buildSiteMetadata(
            imageLayer,
            connectionLayer,
            metadataFolderPath
        )
        self.showInfoMessage('Aviso', 'Metadados criado com sucesso!')

    @QtCore.pyqtSlot(bool)
    def on_processPointsAndLinesBtn_clicked(self):
        pointLayer = self.prePointLayer.currentLayer()
        lineLayer = self.preLineLayer.currentLayer()
        distance = self.distance.value()
        if not( pointLayer and lineLayer):
            self.showErrorMessage('Erro', 'Preencha todas as camadas!')
            return
        if distance<=0:
            self.showErrorMessage('Erro', 'Distancia não pode ser menor ou igual a 0!')
            return
        self.getController().processPointsAndLines(
            pointLayer,
            lineLayer,
            distance
        )
        self.showInfoMessage('Aviso', 'Camadas processadas com sucesso!')

    @QtCore.pyqtSlot(bool)
    def on_applyMaskBtn_clicked(self):
        inputFolder = self.inputFolder.filePath()
        outputFolder = self.outputFolder.filePath()
        carMask = self.carMaskBtn.isChecked()
        customMask = self.customMaskBtn.isChecked()
        pointLayer = self.imageLayer_3.currentLayer()
        if carMask:
            mask = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'resources', 'masks', 'mascara_branca_viatura_eb_dsg.png'))
        elif customMask:
            mask = self.mask.filePath()
            if not os.path.isfile(mask):
                self.showErrorMessage('Erro', 'Máscara invalida!')
                return
        else:
            self.showErrorMessage('Erro', 'Nenhuma máscara selecionada!')
            return
        if not( inputFolder and outputFolder and mask and pointLayer):
            self.showErrorMessage('Erro', 'Preencha todos os campos!')
            return
        if inputFolder==outputFolder:
            continuar = self.showYesNoMessage('Aviso', 'As pastas de entrada e saída são iguais. Deseja continuar?\n Caso sejam iguais as imagens serão sobrescritas!')
            if not continuar:
                return
        self.getController().applyMask(
            inputFolder,
            outputFolder,
            mask,
            pointLayer
        )
        self.showInfoMessage('Aviso', 'Máscaras aplicadas com sucesso!')


    @QtCore.pyqtSlot(bool)
    def on_customMaskBtn_toggled(self):
        if self.customMaskBtn.isChecked():
            self.mask.setEnabled(True)
        else:
            self.mask.setEnabled(False)

