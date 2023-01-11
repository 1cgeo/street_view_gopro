from PyQt5 import QtCore, QtWidgets, QtGui 

class Timer:

    def __init__(self):
        super(Timer, self).__init__()
        self.time = QtCore.QTimer()
        self.time.timeout.connect(self.triggerCallbacks)
        self.callbacks = []
        self.millisecond = None

    def addCallback(self, callback):
        self.callbacks.append(callback)
    
    def removeCallback(self, callback):
        self.callbacks = list(filter(lambda a: a != callback, self.callbacks))

    def triggerCallbacks(self):
        [ cb() for cb in self.callbacks ]

    def start(self, millisecond):
        self.millisecond = millisecond
        self.time.start(self.millisecond)

    def reset(self):
        self.stop()
        self.time.start(self.millisecond)

    def stop(self):
        self.time.stop()

""" t = Timer()
t.addCallback(lambda: print('check'))
t.start(2000) """