import os, sys, copy
from PyQt5 import QtCore, uic, QtWidgets, QtGui
from street_view_plugin.factories.iconPathFactory import IconPathFactory
from datetime import datetime

class IconLabelWidget(QtWidgets.QWidget):

    def __init__(
            self,
            parent=None,
            iconPathFactory=IconPathFactory()
        ):
        super(IconLabelWidget, self).__init__(parent)
        uic.loadUi(self.getUIPath(), self)
        self.iconPathFactory = iconPathFactory

    def setupIcon(self, iconType):
        self.iconLb.setPixmap(
            QtGui.QIcon(
                self.iconPathFactory.get(iconType)
            ).pixmap(QtCore.QSize(20, 20))
        )

    def getUIPath(self):
        return os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 
            '..',
            'uis',
            'iconLabelWidget.ui'
        )

    def showMessage(self, text, messageType='info'):
        self.setupIcon(messageType)
        self.infoLb.setText(text)