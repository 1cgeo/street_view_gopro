import time
from qgis.core import *
from qgis.utils import iface
from PyQt5.QtCore import *

class TrackGyroscope:
    
    def __init__(self):
        self.M_PI = 3.14159
        self.myNewCenter = QgsPointXY()
        self.mLastGpsPosition = QgsPointXY()
        self.mSecondLastGpsPosition = QgsPointXY()
        self.mWgs84CRS = QgsCoordinateReferenceSystem.fromOgcWmsCrs( "EPSG:4326")
        self.wgs84ToCanvas = QgsCoordinateTransform( 
            self.mWgs84CRS, 
            iface.mapCanvas().mapSettings().destinationCrs(), 
            QgsProject.instance().transformContext() 
        )
        self.outputPath = None
        self.conn = None
        self.lastRecordTimstamp = time.time()

    def getOutputPath(self):
        return self.outputPath

    def setOutputPath(self, outputPath):
        self.outputPath = outputPath
        
    def showDirection(self, info):
        rotation = self.getRotation(info)
        iface.mapCanvas().setRotation(rotation)
        self.saveGPSInfo(rotation, info.longitude, info.latitude)
        
    def saveGPSInfo(self, rot, lng, lat):
        with open(self.getOutputPath(), "a") as csv:
            csv.write("{},{},{},{}\n".format(rot, lng, lat, str(time.time())))
            self.lastRecordTimstamp = time.time()
        
    def getRotation(self, info):
        self.myNewCenter = QgsPointXY( info.longitude, info.latitude )
        if(self.myNewCenter != self.mLastGpsPosition):
            self.mSecondLastGpsPosition = self.mLastGpsPosition
            self.mLastGpsPosition = self.myNewCenter 
        trueNorth = 0
        trueNorth = QgsBearingUtils.bearingTrueNorth( iface.mapCanvas().mapSettings().destinationCrs(), QgsProject.instance().transformContext(), iface.mapCanvas().mapSettings().visibleExtent().center() )
        bearing = info.direction
        
        bearingLine = QLineF()
        bearingLine.setP1( self.wgs84ToCanvas.transform( self.myNewCenter ).toQPointF() )
        da1 = QgsDistanceArea()
        da1.setSourceCrs( iface.mapCanvas().mapSettings().destinationCrs(), QgsProject.instance().transformContext() )
        totalLength = da1.measureLine( iface.mapCanvas().mapSettings().extent().center(), QgsPointXY( iface.mapCanvas().mapSettings().extent().xMaximum(),
                                   iface.mapCanvas().mapSettings().extent().yMaximum() ) )
                                   
        da = QgsDistanceArea()
        da.setSourceCrs( self.mWgs84CRS, QgsProject.instance().transformContext() )
        da.setEllipsoid( QgsProject.instance().ellipsoid() )
        res = da.computeSpheroidProject( self.myNewCenter, totalLength, ( bearing - trueNorth ) * self.M_PI / 180.0 )
        bearingLine.setP2( self.wgs84ToCanvas.transform( res ).toQPointF() )
        return 270 - bearingLine.angle()

    def validateSettings(self, connectionList, outputPath):
        if len(connectionList) == 0:
            raise Exception('Conecte o GPS!')
        if outputPath is None or outputPath == '':
            raise Exception('Defina um arquivo de saída!')

    def setCurrentConnection(self, conn):
        self.conn = conn

    def getCurrentConnection(self):
        return self.conn

    def start(self):
        connectionList = QgsApplication.gpsConnectionRegistry().connectionList()
        
        self.validateSettings(connectionList, self.getOutputPath())

        conn = connectionList[0]
        try:
            conn.stateChanged.disconnect(self.showDirection)
        except:
            pass
        conn.stateChanged.connect(self.showDirection)
        self.setCurrentConnection(conn)

    def stop(self):
        conn = self.getCurrentConnection()
        try:
            conn.stateChanged.disconnect(self.showDirection)
        except:
            pass
