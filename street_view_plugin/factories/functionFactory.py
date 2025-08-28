
from street_view_plugin.models.trackGyroscope import TrackGyroscope
from street_view_plugin.models.storageConfig import StorageConfig
from street_view_plugin.models.alarm import Alarm
from street_view_plugin.models.timer import Timer
from street_view_plugin.models.buildStruct import BuildStruct
from street_view_plugin.models.buildSiteMetadata import BuildSiteMetadata
from street_view_plugin.models.processPointsAndLines import ProcessPointsAndLines
from street_view_plugin.models.applyMask import ApplyMask
from street_view_plugin.models.applyBlurMask import ApplyBlurMask

class FunctionFactory:

    def create(self, functionName, *args):
        functions = {
            'BuildSiteMetadata': lambda *args: BuildSiteMetadata(*args),
            'TrackGyroscope': lambda *args: TrackGyroscope(*args),
            'StorageConfig': lambda *args: StorageConfig(*args),
            'Alarm': lambda *args: Alarm(*args),
            'Timer': lambda *args: Timer(*args),
            'BuildStruct': lambda *args: BuildStruct(*args),
            'ProcessPointsAndLines': lambda *args: ProcessPointsAndLines(*args),
            'ApplyMask': lambda *args: ApplyMask(*args),
            'ApplyBlurMask': lambda *args: ApplyBlurMask(*args),
        }
        return functions[functionName](*args) if functionName in functions else None