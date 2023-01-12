from street_view_plugin.factories.widgetFactory import WidgetFactory
from street_view_plugin.factories.functionFactory import FunctionFactory
from datetime import datetime

class StreetViewCtrl:

    def __init__(self, 
            qgis,
            widgetFactory=WidgetFactory(),
            functionFactory=FunctionFactory()
        ):
        super(StreetViewCtrl, self).__init__()
        self.qgis = qgis
        self.widgetFactory = widgetFactory
        self.functionFactory = functionFactory
        self.streetViewDock = None
        self.batteryTimer = None
        self.storageTimer = None
        self.gyroTimer = None
        self.trackGyroscope = None
        self.lastGyroTimestamp = None

    def loadDock(self):
        self.streetViewDock = self.widgetFactory.create('StreetViewDock', self)
        self.qgis.addDockWidget(self.streetViewDock)

    def startTrackGyroscope(self):
        allConfig = self.getAllConfig()
        if not('gyroPath' in allConfig and allConfig['gyroPath'] != ''):
            raise Exception('Defina um arquivo de saída!')
        if self.trackGyroscope:
            self.trackGyroscope.stop()
        self.trackGyroscope = self.functionFactory.create('TrackGyroscope')
        self.trackGyroscope.setOutputPath(allConfig['gyroPath'])
        self.trackGyroscope.start()
        self.startGyroAlarm()

    def stopTrackGyroscope(self):
        if not self.trackGyroscope:
            return
        self.trackGyroscope.stop()

    def getAllConfig(self):
        storageConfig = self.functionFactory.create('StorageConfig')
        return storageConfig.getAllValues()

    def setConfig(self, key, value):
        storageConfig = self.functionFactory.create('StorageConfig')
        storageConfig.setValue(key, value)

    def calcStorageDuration(self, sizeGB, numberPhotos):
        return ((sizeGB * 1000 - (numberPhotos * 3)) / 241) * 60

    def calcBatteryDuration(self, percent):
        return (percent - 10) * 90

    def startBatteryAlarm(self):
        if self.batteryTimer:
            self.stopBatteryAlarm()
        self.batteryTimer = self.functionFactory.create('Timer')
        self.batteryTimer.addCallback(self.checkBattery)
        self.batteryTimer.start(5000)

    def stopBatteryAlarm(self):
        self.batteryTimer.stop()

    def checkBattery(self):
        allConfig = self.getAllConfig()
        startTimeEpoch = allConfig['datetime']
        durationSeconds = self.calcBatteryDuration(allConfig['battery'])
        if (startTimeEpoch + durationSeconds) > datetime.now().timestamp():
            return
        self.streetViewDock.updateBatteryStatus('warning')
        self.beep()

    def startStorageAlarm(self):
        if self.storageTimer:
            self.stopStorageAlarm()
        self.storageTimer = self.functionFactory.create('Timer')
        self.storageTimer.addCallback(self.checkStorage)
        self.storageTimer.start(5000)

    def stopStorageAlarm(self):
        self.storageTimer.stop()

    def checkStorage(self):
        allConfig = self.getAllConfig()
        startTimeEpoch = allConfig['datetime']
        numberPhotos = 0 if not 'numberPhotos' in allConfig else allConfig['numberPhotos']
        durationSeconds = self.calcStorageDuration(
            allConfig['storage'],
            numberPhotos
        )
        if (startTimeEpoch + durationSeconds) > datetime.now().timestamp():
            return
        
        self.streetViewDock.updateStorageStatus('warning')
        self.beep()

    def startGyroAlarm(self):
        if self.gyroTimer:
            self.stopGyroAlarm()
        self.gyroTimer = self.functionFactory.create('Timer')
        self.gyroTimer.addCallback(self.checkGyro)
        self.gyroTimer.start(2000)

    def stopGyroAlarm(self):
        self.gyroTimer.stop()

    def checkGyro(self):
        self.streetViewDock.updateGyroStatus()
        if not(self.lastGyroTimestamp):
            self.lastGyroTimestamp = self.trackGyroscope.lastRecordTimstamp
            return
        if self.isRecordingGyro():
            self.lastGyroTimestamp = self.trackGyroscope.lastRecordTimstamp
            return
        self.streetViewDock.updateGyroStatus('warning')
        self.beep()

    def isRecordingGyro(self):
        if self.trackGyroscope and self.lastGyroTimestamp and self.lastGyroTimestamp < self.trackGyroscope.lastRecordTimstamp:
            return True
        return False

    def beep(self, qty=1):
        if not self.isRecordingGyro():
            return
        alarm = self.functionFactory.create('Alarm')
        alarm.beep(qty)

    def buildStruct(self, imagesFolderPath, csvGyroPath):
        buildStruct = self.functionFactory.create('BuildStruct')
        buildStruct.build(
            imagesFolderPath, 
            csvGyroPath
        )

    def buildSiteMetadata(self, imageLayer, connectionLayer, metadataFolderPath):
        buildSiteMetadata = self.functionFactory.create('BuildSiteMetadata')
        buildSiteMetadata.build(
            imageLayer, 
            connectionLayer, 
            metadataFolderPath
        )
    
            