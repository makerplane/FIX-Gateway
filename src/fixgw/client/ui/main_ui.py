# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'main.ui'
#
# Created by: PyQt6 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt6 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tabStatus = QtWidgets.QWidget()
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tabStatus.sizePolicy().hasHeightForWidth())
        self.tabStatus.setSizePolicy(sizePolicy)
        self.tabStatus.setObjectName("tabStatus")
        self.layoutStatus = QtWidgets.QHBoxLayout(self.tabStatus)
        self.layoutStatus.setObjectName("layoutStatus")
        self.tabWidget.addTab(self.tabStatus, "")
        self.tabData = QtWidgets.QWidget()
        self.tabData.setObjectName("tabData")
        self.layoutData = QtWidgets.QHBoxLayout(self.tabData)
        self.layoutData.setObjectName("layoutData")
        self.tabWidget.addTab(self.tabData, "")
        self.tabSimulate = QtWidgets.QWidget()
        self.tabSimulate.setObjectName("tabSimulate")
        self.layoutSimulate = QtWidgets.QHBoxLayout(self.tabSimulate)
        self.layoutSimulate.setObjectName("layoutSimulate")
        self.tabWidget.addTab(self.tabSimulate, "")
        self.horizontalLayout.addWidget(self.tabWidget)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 30))
        self.menubar.setObjectName("menubar")
        self.menu_File = QtWidgets.QMenu(self.menubar)
        self.menu_File.setObjectName("menu_File")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menubar.addAction(self.menu_File.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "FIX-Gateway Client"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabStatus), _translate("MainWindow", "Status"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabData), _translate("MainWindow", "Data"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabSimulate), _translate("MainWindow", "Simulate"))
        self.menu_File.setTitle(_translate("MainWindow", "&File"))

