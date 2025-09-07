#!/usr/bin/python3
#############################################################
## NeewerLite-Python ver. [2025-02-01-BETA]
## by Zach Glenwright
############################################################
## > https://github.com/taburineagle/NeewerLite-Python/ <
############################################################
## A cross-platform Python script using the bleak and
## PySide2 libraries to control Neewer brand lights via
## Bluetooth on multiple platforms -
##          Windows, Linux/Ubuntu, MacOS and RPi
############################################################
## Originally based on the NeewerLight project by @keefo
##      > https://github.com/keefo/NeewerLite <
############################################################

import os
import sys
import time
import math
import tempfile
import argparse
import asyncio
import threading
import platform # used to determine which OS we're using for MAC address/GUID listing
import logging

from datetime import datetime
from subprocess import run, PIPE # used to get MacOS Mac address

from importlib import util as ilu # determining which PySide installation is in place 
from importlib import metadata as ilm # determining which version of packages are installed

# Display the version of NeewerLite-Python we're using
print("---------------------------------------------------------")
print("             NeewerLite-Python ver. [2025-02-01-BETA]")
print("                 by Zach Glenwright")
print("  > https://github.com/taburineagle/NeewerLite-Python <")
print("---------------------------------------------------------")
print("Checking for bleak and PySide packages...")

if (ilu.find_spec("bleak")) != None: # we have Bleak installed
    # IMPORT BLEAK (this is the library that allows the program to communicate with the lights) - THIS IS NECESSARY!
    try:
        from bleak import BleakScanner, BleakClient

        print(f'bleak is installed!  Version: {ilm.version("bleak")}')
    except ModuleNotFoundError as e:
        print("Bleak is installed, but we can't import it!  This... should not happen!")
        sys.exit(1)
else: # bleak is not installed, so we need to do that...
    print(" ===== CAN NOT FIND BLEAK LIBRARY =====")
    print(" You need the bleak Python package installed to use NeewerLite-Python.")
    print(" Bleak is the library that connects the program to Bluetooth devices.")
    print(" Please install the Bleak package first before running NeewerLite-Python.")
    print()
    print(" To install Bleak, run either pip or pip3 from the command line:")
    print("    pip install bleak")
    print("    pip3 install bleak")
    print()
    print(" Or visit this website for more information:")
    print("    https://pypi.org/project/bleak/")
    sys.exit(1) # you can't use the program itself without Bleak, so kill the program if we don't have it

PySideGUI = None # which frontend we're using for the GUI (PySide6 or PySide2)
importError = 0 # whether or not there's an issue loading PySide2 or the GUI file

if (ilu.find_spec("PySide6")) != None: # if PySide6 is available, try to import PySide6
    try:
        from PySide6.QtCore import QItemSelectionModel
        from PySide6.QtGui import QKeySequence, QShortcut
        from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QMessageBox

        from PySide6.QtCore import QRect, Signal, Qt
        from PySide6.QtGui import QFont, QGradient, QLinearGradient, QColor
        from PySide6.QtWidgets import QFormLayout, QGridLayout, QKeySequenceEdit, QWidget, QPushButton, QTableWidget, \
             QTableWidgetItem, QAbstractScrollArea, QAbstractItemView, QTabWidget, QGraphicsScene, QGraphicsView, QFrame, \
             QSlider, QLabel, QLineEdit, QCheckBox, QStatusBar, QScrollArea, QTextEdit, QComboBox

        print(f'PySide6 is installed (skipping the PySide2 check!)  Version: {ilm.version("PySide6")}')
        PySideGUI = "PySide6"
    except Exception as e:
        print("PySide6 is installed, but couldn't be imported - trying PySide2, if available...")
        importError = 1 # log that we can't find PySide6
else:
    print("PySide6 isn't installed!  Trying PySide2, if available...")
    importError = 1 # if PySide6 is installed, but there's an issue importing it, then report an error

if importError == 1:
    if ilu.find_spec("PySide2") != None: # if PySide6 couldn't be imported (or there was an issue with it), try PySide2
        try:
            from PySide2.QtCore import QItemSelectionModel
            from PySide2.QtGui import QKeySequence
            from PySide2.QtWidgets import QApplication, QMainWindow, QShortcut, QMessageBox

            from PySide2.QtCore import QRect, Signal, Qt
            from PySide2.QtGui import QFont, QLinearGradient, QColor
            from PySide2.QtWidgets import QFormLayout, QGridLayout, QKeySequenceEdit, QWidget, QPushButton, QTableWidget, \
                 QTableWidgetItem, QAbstractScrollArea, QAbstractItemView, QTabWidget, QGraphicsScene, QGraphicsView, QFrame, \
                 QSlider, QLabel, QLineEdit, QCheckBox, QStatusBar, QScrollArea, QTextEdit, QComboBox

            print(f'PySide2 is installed!  Version: {ilm.version("PySide2")}')
            importError = 0
            PySideGUI = "PySide2"
        except Exception as e:
            print("PySide2 is installed, but couldn't be imported...")
            importError = 1 # log that we can't import PySide2
    else:
        print(" ===== CAN NOT FIND PYSIDE6 or PYSIDE2 LIBRARIES =====")
        print(" You don't have the PySide2 or PySide6 Python libraries installed.  If you're only running NeewerLite-Python from")
        print(" a command-line (from a Raspberry Pi CLI for instance), or using the HTTP server, you don't need this package.")
        print(" If you want to launch NeewerLite-Python with the GUI, you need to install either the PySide2 or PySide6 package.")
        print()
        print(" To install PySide2, run either pip or pip3 from the command line:")
        print("    pip install PySide2")
        print("    pip3 install PySide2")
        print()
        print(" To install PySide6, run either pip or pip3 from the command line:")
        print("    pip install PySide6")
        print("    pip3 install PySide6")
        print()
        print(" Visit these websites for more information:")
        print("    https://pypi.org/project/PySide2/")
        print("    https://pypi.org/project/PySide6/")

        importError = 1 # log that we had an issue with importing PySide2

print("---------------------------------------------------------")

# IMPORT THE HTTP SERVER
try:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import urllib.parse # parsing custom light names in the HTTP server
except Exception as e:
    pass # if there are any HTTP errors, don't do anything yet

CCTSlider = -1 # the current slider moved in the CCT window - 1 - Brightness / 2 - Hue / -1 - Both Brightness and Hue
sendValue = [120, 135, 2, 50, 56, 50] # an array to hold the values to be sent to the light
lastSelection = [] # the current light selection (this is for snapshot preset entering/leaving buttons)
lastSortingField = -1 # the last field used for sorting purposes

availableLights = [] # the list of Neewer lights currently available to control
# List Subitems (for ^^^^^^):
# [0] - UpdatedBLEInformation object (replaces Bleak object, but retains information) Object (can use .name / .realname / .address / .rssi / .HWMACaddr to get specifics)
# [1] - Bleak Connection (the actual Bluetooth connection to the light itself)
# [2] - Custom Name for Light (string)
# [3] - Last Used Parameters (list)
# [4] - The range of color temperatures to use in CCT mode (list, min, max) <- changed in 0.12
# [5] - Whether or not to send Brightness and Hue independently for old lights (boolean)
# [6] - Whether or not this light has been manually turned ON/OFF (boolean)
# [7] - The Power and Channel data returned for this light (list)
# [8] - Whether or not this light uses the new Infinity light protocol (int - 0: no, 1: yes, 2: protocol, but not Infinity light)

# Light Preset ***Default*** Settings (for sections below):
# NOTE: The list is 0-based, so the preset itself is +1 from the subitem
# [0] - [CCT mode] - 5600K / 20%
# [1] - [CCT mode] - 3200K / 20%
# [2] - [CCT mode] - 5600K / 0% (lights are on, but set to 0% brightness)
# [3] - [HSI mode] - 0° hue / 100% saturation / 20% intensity (RED)
# [4] - [HSI mode] - 240° hue / 100% saturation / 20% intensity (BLUE)
# [5] - [HSI mode] - 120° hue / 100% saturation / 20% intensity (GREEN)
# [6] - [HSI mode] - 300° hue / 100% saturation / 20% intensity (PURPLE)
# [7] - [HSI mode] - 160° hue / 100% saturation / 20% intensity (CYAN)

# The list of **default** light presets for restoring and checking against
defaultLightPresets = [
    [[-1, [120, 135, 2, 20, 56, 50]]],
    [[-1, [120, 135, 2, 20, 32, 50]]],
    [[-1, [120, 135, 2, 0, 56, 50]]],
    [[-1, [120, 134, 4, 0, 0, 100, 20]]],
    [[-1, [120, 134, 4, 240, 0, 100, 20]]],
    [[-1, [120, 134, 4, 120, 0, 100, 20]]],
    [[-1, [120, 134, 4, 44, 1, 100, 20]]],
    [[-1, [120, 134, 4, 160, 0, 100, 20]]]
    ]

customLightPresets = defaultLightPresets[:] # copy the default presets to the list for the current session's presets

threadAction = "" # the current action to take from the thread
serverBusy = [False, ""] # whether or not the HTTP server is busy
asyncioEventLoop = None # the current asyncio loop

setLightUUID = "69400002-B5A3-F393-E0A9-E50E24DCCA99" # the UUID to send information to the light
notifyLightUUID = "69400003-B5A3-F393-E0A9-E50E24DCCA99" # the UUID for notify callbacks from the light

receivedData = "" # the data received from the Notify characteristic

# SET FROM THE PREFERENCES FILE ON LAUNCH
findLightsOnStartup = True # whether or not to look for lights when the program starts
autoConnectToLights = True # whether or not to auto-connect to lights after finding them
printDebug = True # show debug messages in the console for all of the program's events
maxNumOfAttempts = 6 # the maximum attempts the program will attempt an action before erroring out
rememberLightsOnExit = False # whether or not to save the currently set light settings (mode/hue/brightness/etc.) when quitting out
rememberPresetsOnExit = True # whether or not to save the custom preset list when quitting out
acceptable_HTTP_IPs = [] # the acceptable IPs for the HTTP server, set on launch by prefs file
customKeys = [] # custom keymappings for keyboard shortcuts, set on launch by the prefs file
whiteListedMACs = [] # whitelisted list of MAC addresses to add to NeewerLite-Python
enableTabsOnLaunch = False # whether or not to enable tabs on startup (even with no lights connected)

lockFile = tempfile.gettempdir() + os.sep + "NeewerLite-Python.lock"
anotherInstance = False # whether or not we're using a new instance (for the Singleton check)
globalPrefsFile = os.path.dirname(os.path.abspath(sys.argv[0])) + os.sep + "light_prefs" + os.sep + "NeewerLite-Python.prefs" # the global preferences file for saving/loading
customLightPresetsFile = os.path.dirname(os.path.abspath(sys.argv[0])) + os.sep + "light_prefs" + os.sep + "customLights.prefs"

# FILE LOCKING FOR SINGLE INSTANCE
def singleInstanceLock():
    global anotherInstance

    if os.path.exists(lockFile): # the lockfile exists, so we have another instance running
        anotherInstance = True
    else: # if it doesn't, try to create it
        try:
            lf = os.open(lockFile, os.O_WRONLY | os.O_CREAT | os.O_EXCL) # try to get a file spec to lock the "running" instance

            with os.fdopen(lf, 'w') as lockfile:
                lockfile.write(str(os.getpid())) # write the PID of the current running process to the temporary lockfile
        except IOError: # if we had an error acquiring the file descriptor, the file most likely already exists.
            anotherInstance = True
    
def singleInstanceUnlockandQuit(exitCode):
    try:
        os.remove(lockFile) # try to delete the lockfile on exit
    except FileNotFoundError: # if another process deleted it, then just error out
        printDebugString("Lockfile not found in temp directory, so we're going to skip deleting it!")

    sys.exit(exitCode) # quit out, with the specified exitCode

def doAnotherInstanceCheck():
    if anotherInstance == True: # if we're running a 2nd instance, but we shouldn't be
        print("You're already running another instance of NeewerLite-Python.")
        print("Please close that copy first before opening a new one.")
        print()
        print("To force opening a new instance, add --force_instance to the command line.")
        sys.exit(1)

# =======================================================
# = GUI CREATION AND FUNCTIONS AHEAD!
# =======================================================
if PySideGUI != None: # create the GUI if the PySide GUI classes are imported
    mainFont = QFont()
    mainFont.setBold(True)

    if PySideGUI == "PySide2":
        mainFont.setWeight(75)
    else: # if we're using PySide6, the old "font weight" method is deprecated
        mainFont.setWeight(QFont.ExtraBold)

    def combinePySideValues(theValues):
        # ADDED THIS TO FIX PySide2 VERSIONS < 5.15 
        # AND THE "can not interpret as integer" 
        # ERROR WHEN COMBINING ALIGNMENT FLAGS
        returnValue = int(theValues[0])

        for a in range(1, len(theValues)):
            returnValue = returnValue + int(theValues[a])

        return returnValue

    class Ui_MainWindow(object):
        def setupUi(self, MainWindow):
            # ============ FONTS, GRADIENTS AND OTHER WINDOW SPECIFICS ============
            MainWindow.setFixedSize(590, 670) # the main window should be this size at launch, and no bigger
            MainWindow.setWindowTitle("NeewerLite-Python [2025-02-01-BETA] by Zach Glenwright")

            self.centralwidget = QWidget(MainWindow)
            self.centralwidget.setObjectName(u"centralwidget")

            # ============ THE TOP-MOST BUTTONS ============
            self.turnOffButton = QPushButton(self.centralwidget)
            self.turnOffButton.setGeometry(QRect(10, 4, 150, 22))
            self.turnOffButton.setText("Turn Light(s) Off")

            self.turnOnButton = QPushButton(self.centralwidget)
            self.turnOnButton.setGeometry(QRect(165, 4, 150, 22))
            self.turnOnButton.setText("Turn Light(s) On")

            self.scanCommandButton = QPushButton(self.centralwidget)
            self.scanCommandButton.setGeometry(QRect(416, 4, 81, 22))
            self.scanCommandButton.setText("Scan")

            self.tryConnectButton = QPushButton(self.centralwidget)
            self.tryConnectButton.setGeometry(QRect(500, 4, 81, 22))
            self.tryConnectButton.setText("Connect")

            self.turnOffButton.setEnabled(False)
            self.turnOnButton.setEnabled(False)
            self.tryConnectButton.setEnabled(False)

            # ============ THE LIGHT TABLE ============
            self.lightTable = QTableWidget(self.centralwidget)

            self.lightTable.setColumnCount(4)
            self.lightTable.setColumnWidth(0, 120)
            self.lightTable.setColumnWidth(1, 150)
            self.lightTable.setColumnWidth(2, 94)
            self.lightTable.setColumnWidth(3, 190)

            __QT0 = QTableWidgetItem()
            __QT0.setText("Light Name")
            self.lightTable.setHorizontalHeaderItem(0, __QT0)

            __QT1 = QTableWidgetItem()
            __QT1.setText("MAC Address")
            self.lightTable.setHorizontalHeaderItem(1, __QT1)

            __QT2 = QTableWidgetItem()
            __QT2.setText("Linked")
            self.lightTable.setHorizontalHeaderItem(2, __QT2)

            __QT3 = QTableWidgetItem()
            __QT3.setText("Status")
            self.lightTable.setHorizontalHeaderItem(3, __QT3)

            self.lightTable.setGeometry(QRect(10, 32, 571, 261))
            self.lightTable.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
            self.lightTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.lightTable.setAlternatingRowColors(True)
            self.lightTable.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.lightTable.verticalHeader().setStretchLastSection(False)

            # ============ THE CUSTOM PRESET BUTTONS ============

            self.customPresetButtonsCW = QWidget(self.centralwidget)
            self.customPresetButtonsCW.setGeometry(QRect(10, 300, 571, 68))
            self.customPresetButtonsLay = QGridLayout(self.customPresetButtonsCW)
            self.customPresetButtonsLay.setContentsMargins(0, 0, 0, 0) # ensure this widget spans from the left to the right edge of the light table

            self.customPreset_0_Button = customPresetButton(self.centralwidget, text="<strong><font size=+2>1</font></strong><br>PRESET<br>GLOBAL")
            self.customPresetButtonsLay.addWidget(self.customPreset_0_Button, 1, 1)
            self.customPreset_1_Button = customPresetButton(self.centralwidget, text="<strong><font size=+2>2</font></strong><br>PRESET<br>GLOBAL")
            self.customPresetButtonsLay.addWidget(self.customPreset_1_Button, 1, 2)
            self.customPreset_2_Button = customPresetButton(self.centralwidget, text="<strong><font size=+2>3</font></strong><br>PRESET<br>GLOBAL")
            self.customPresetButtonsLay.addWidget(self.customPreset_2_Button, 1, 3)
            self.customPreset_3_Button = customPresetButton(self.centralwidget, text="<strong><font size=+2>4</font></strong><br>PRESET<br>GLOBAL")
            self.customPresetButtonsLay.addWidget(self.customPreset_3_Button, 1, 4)
            self.customPreset_4_Button = customPresetButton(self.centralwidget, text="<strong><font size=+2>5</font></strong><br>PRESET<br>GLOBAL")
            self.customPresetButtonsLay.addWidget(self.customPreset_4_Button, 1, 5)
            self.customPreset_5_Button = customPresetButton(self.centralwidget, text="<strong><font size=+2>6</font></strong><br>PRESET<br>GLOBAL")
            self.customPresetButtonsLay.addWidget(self.customPreset_5_Button, 1, 6)
            self.customPreset_6_Button = customPresetButton(self.centralwidget, text="<strong><font size=+2>7</font></strong><br>PRESET<br>GLOBAL")
            self.customPresetButtonsLay.addWidget(self.customPreset_6_Button, 1, 7)
            self.customPreset_7_Button = customPresetButton(self.centralwidget, text="<strong><font size=+2>8</font></strong><br>PRESET<br>GLOBAL")
            self.customPresetButtonsLay.addWidget(self.customPreset_7_Button, 1, 8)

            # ============ THE MODE TABS ============
            self.ColorModeTabWidget = QTabWidget(self.centralwidget)
            self.ColorModeTabWidget.setGeometry(QRect(10, 385, 571, 254))

            # === >> MAIN TAB WIDGETS << ===
            self.CCT = QWidget()
            self.HSI = QWidget()
            self.ANM = QWidget()
            
            # ============ SINGLE SLIDER WIDGET DEFINITIONS ============

            self.colorTempSlider = parameterWidget(title="Color Temperature", gradient="TEMP", 
                                                sliderMin=32, sliderMax=72, sliderVal=56, prefix="00K")
            self.brightSlider = parameterWidget(title="Brightness", gradient="BRI")
            self.GMSlider = parameterWidget(title="GM Compensation", gradient="GM", sliderOffset=-50, sliderVal=50, prefix="")
            
            self.RGBSlider = parameterWidget(title="Hue", gradient="RGB", sliderMin=0, sliderMax=360, sliderVal=180, prefix="º")
            self.colorSatSlider = parameterWidget(title="Saturation", gradient="SAT", sliderVal=100)

            # change the saturation gradient when the RGB slider changes
            self.RGBSlider.valueChanged.connect(self.colorSatSlider.adjustSatGradient)
            
            self.speedSlider = parameterWidget(title="Speed", gradient="SPEED", sliderMin=0, sliderMax=10, sliderVal=5, prefix="")
            self.sparksSlider = parameterWidget(title="Sparks", gradient="SPARKS", sliderMin=0, sliderMax=10, sliderVal=5, prefix="")

            # ============ DOUBLE SLIDER WIDGET DEFINITIONS ============

            self.brightDoubleSlider = doubleSlider(sliderType="BRI")
            self.RGBDoubleSlider = doubleSlider(sliderType="RGB")
            self.colorTempDoubleSlider = doubleSlider(sliderType="TEMP")
            
            # ============ FX CHOOSER DEFINITIONS ============

            self.effectChooser_Title = QLabel(self.ANM, text="Choose an effect:")
            self.effectChooser_Title.setGeometry(QRect(8, 6, 120, 20))
            self.effectChooser_Title.setFont(mainFont)

            self.effectChooser = QComboBox(self.ANM)
            self.effectChooser.setGeometry(QRect(125, 6, 430, 22))

            # ============ FX CHOOSER DEFINITIONS ============

            self.specialOptionsSection = QWidget(self.ANM)

            self.specialOptions_Title = QLabel(self.specialOptionsSection, text="Choose a color option:")
            self.specialOptions_Title.setFont(mainFont)
            self.specialOptions_Title.setGeometry(0, 0, 250, 20)

            self.specialOptionsChooser = QComboBox(self.specialOptionsSection)
            self.specialOptionsChooser.setGeometry(QRect(0, 20, self.ColorModeTabWidget.width() - 16, 22))

            self.specialOptionsSection.hide()

            # =============================================================================

            # === >> THE LIGHT PREFS TAB << ===
            self.lightPrefs = QWidget()

            # CUSTOM NAME FIELD FOR THIS LIGHT
            self.customName = QCheckBox(self.lightPrefs)
            self.customName.setGeometry(QRect(10, 14, 541, 16))
            self.customName.setText("Custom Name for this light:")
            self.customName.setFont(mainFont)

            self.customNameTF = QLineEdit(self.lightPrefs)
            self.customNameTF.setGeometry(QRect(10, 34, 541, 20))
            self.customNameTF.setMaxLength(80)

            # CUSTOM HSI COLOR TEMPERATURE RANGES FOR THIS LIGHT
            self.colorTempRange = QCheckBox(self.lightPrefs)
            self.colorTempRange.setGeometry(QRect(10, 82, 541, 16))
            self.colorTempRange.setText("Use Custom Color Temperature Range for CCT mode:")
            self.colorTempRange.setFont(mainFont)

            self.colorTempRange_Min_TF = QLineEdit(self.lightPrefs)
            self.colorTempRange_Min_TF.setGeometry(QRect(10, 102, 120, 20))
            self.colorTempRange_Min_TF.setMaxLength(80)

            self.colorTempRange_Max_TF = QLineEdit(self.lightPrefs)
            self.colorTempRange_Max_TF.setGeometry(QRect(160, 102, 120, 20))
            self.colorTempRange_Max_TF.setMaxLength(80)
            
            self.colorTempRange_Min_Description = QLabel(self.lightPrefs)
            self.colorTempRange_Min_Description.setGeometry(QRect(10, 124, 120, 16))
            self.colorTempRange_Min_Description.setAlignment(Qt.AlignCenter)
            self.colorTempRange_Min_Description.setText("Minimum")
            self.colorTempRange_Min_Description.setFont(mainFont)
            
            self.colorTempRange_Max_Description = QLabel(self.lightPrefs)
            self.colorTempRange_Max_Description.setGeometry(QRect(160, 124, 120, 16))
            self.colorTempRange_Max_Description.setAlignment(Qt.AlignCenter)
            self.colorTempRange_Max_Description.setText("Maximum")
            self.colorTempRange_Max_Description.setFont(mainFont)
            
            # WHETHER OR NOT TO ONLY ALLOW CCT MODE FOR THIS LIGHT
            self.onlyCCTModeCheck = QCheckBox(self.lightPrefs)
            self.onlyCCTModeCheck.setGeometry(QRect(10, 160, 401, 31))
            self.onlyCCTModeCheck.setText("This light can only use CCT mode\n(for Neewer lights without HSI mode)")
            self.onlyCCTModeCheck.setFont(mainFont)

            # SAVE IIITTTTTT!
            self.saveLightPrefsButton = QPushButton(self.lightPrefs)
            self.saveLightPrefsButton.setGeometry(QRect(416, 170, 141, 23))
            self.saveLightPrefsButton.setText("Save Preferences")

            # === >> THE GLOBAL PREFS TAB << ===
            self.globalPrefs = QScrollArea()
            self.globalPrefsCW = QWidget()

            self.globalPrefsCW.setMaximumWidth(550) # make sure to resize all contents to fit in the horizontal space of the scrollbar widget

            self.globalPrefsLay = QFormLayout(self.globalPrefsCW)
            self.globalPrefsLay.setLabelAlignment(Qt.AlignLeft)

            self.globalPrefs.setWidget(self.globalPrefsCW)
            self.globalPrefs.setWidgetResizable(True)

            # MAIN PROGRAM PREFERENCES
            self.findLightsOnStartup_check = QCheckBox("Scan for Neewer lights on program launch")
            self.autoConnectToLights_check = QCheckBox("Automatically try to link to newly found lights")
            self.printDebug_check = QCheckBox("Print debug information to the console")
            self.rememberLightsOnExit_check = QCheckBox("Remember the last mode parameters set for lights on exit")
            self.rememberPresetsOnExit_check = QCheckBox("Save configuration of custom presets on exit")
            self.maxNumOfAttempts_field = QLineEdit()
            self.maxNumOfAttempts_field.setFixedWidth(35)
            self.acceptable_HTTP_IPs_field = QTextEdit()
            self.acceptable_HTTP_IPs_field.setFixedHeight(70)
            self.whiteListedMACs_field = QTextEdit()
            self.whiteListedMACs_field.setFixedHeight(70)

            self.resetGlobalPrefsButton = QPushButton("Reset Preferences to Defaults")
            self.saveGlobalPrefsButton = QPushButton("Save Global Preferences")

            # THE FIRST SECTION OF KEYBOARD MAPPING SECTION
            self.windowButtonsCW = QWidget()
            self.windowButtonsLay = QGridLayout(self.windowButtonsCW)

            self.SC_turnOffButton_field = singleKeySequenceEditCancel("Ctrl+PgDown")
            self.windowButtonsLay.addWidget(QLabel("<strong>Window Top</strong><br>Turn Light(s) Off", alignment=Qt.AlignCenter), 1, 1)
            self.windowButtonsLay.addWidget(self.SC_turnOffButton_field, 2, 1)
            self.SC_turnOnButton_field = singleKeySequenceEditCancel("Ctrl+PgUp")
            self.windowButtonsLay.addWidget(QLabel("<strong>Window Top</strong><br>Turn Light(s) On", alignment=Qt.AlignCenter), 1, 2)
            self.windowButtonsLay.addWidget(self.SC_turnOnButton_field, 2, 2)
            self.SC_scanCommandButton_field = singleKeySequenceEditCancel("Ctrl+Shift+S")
            self.windowButtonsLay.addWidget(QLabel("<strong>Window Top</strong><br>Scan/Re-Scan", alignment=Qt.AlignCenter), 1, 3)
            self.windowButtonsLay.addWidget(self.SC_scanCommandButton_field, 2, 3)
            self.SC_tryConnectButton_field = singleKeySequenceEditCancel("Ctrl+Shift+C")
            self.windowButtonsLay.addWidget(QLabel("<strong>Window Top</strong><br>Connect", alignment=Qt.AlignCenter), 1, 4)
            self.windowButtonsLay.addWidget(self.SC_tryConnectButton_field, 2, 4)

            # SWITCHING BETWEEN TABS KEYBOARD MAPPING SECTION
            self.tabSwitchCW = QWidget()
            self.tabSwitchLay = QGridLayout(self.tabSwitchCW)

            self.SC_Tab_CCT_field = singleKeySequenceEditCancel("Alt+1")
            self.tabSwitchLay.addWidget(QLabel("<strong>Switching Tabs</strong><br>To CCT", alignment=Qt.AlignCenter), 1, 1)
            self.tabSwitchLay.addWidget(self.SC_Tab_CCT_field, 2, 1)
            self.SC_Tab_HSI_field = singleKeySequenceEditCancel("Alt+2")
            self.tabSwitchLay.addWidget(QLabel("<strong>Switching Tabs</strong><br>To HSI", alignment=Qt.AlignCenter), 1, 2)
            self.tabSwitchLay.addWidget(self.SC_Tab_HSI_field, 2, 2)
            self.SC_Tab_SCENE_field = singleKeySequenceEditCancel("Alt+3")
            self.tabSwitchLay.addWidget(QLabel("<strong>Switching Tabs</strong><br>To SCENE", alignment=Qt.AlignCenter), 1, 3)
            self.tabSwitchLay.addWidget(self.SC_Tab_SCENE_field, 2, 3)
            self.SC_Tab_PREFS_field = singleKeySequenceEditCancel("Alt+4")
            self.tabSwitchLay.addWidget(QLabel("<strong>Switching Tabs</strong><br>To Light Prefs", alignment=Qt.AlignCenter), 1, 4)
            self.tabSwitchLay.addWidget(self.SC_Tab_PREFS_field, 2, 4)

            # BRIGHTNESS ADJUSTMENT KEYBOARD MAPPING SECTION
            self.brightnessCW = QWidget()
            self.brightnessLay = QGridLayout(self.brightnessCW)

            self.SC_Dec_Bri_Small_field = singleKeySequenceEditCancel("/")
            self.brightnessLay.addWidget(QLabel("<strong>Brightness</strong><br>Small Decrease", alignment=Qt.AlignCenter), 1, 1)
            self.brightnessLay.addWidget(self.SC_Dec_Bri_Small_field, 2, 1)
            self.SC_Dec_Bri_Large_field = singleKeySequenceEditCancel("Ctrl+/")
            self.brightnessLay.addWidget(QLabel("<strong>Brightness</strong><br>Large Decrease", alignment=Qt.AlignCenter), 1, 2)
            self.brightnessLay.addWidget(self.SC_Dec_Bri_Large_field, 2, 2)
            self.SC_Inc_Bri_Small_field = singleKeySequenceEditCancel("*")
            self.brightnessLay.addWidget(QLabel("<strong>Brightness</strong><br>Small Increase", alignment=Qt.AlignCenter), 1, 3)
            self.brightnessLay.addWidget(self.SC_Inc_Bri_Small_field, 2, 3)
            self.SC_Inc_Bri_Large_field = singleKeySequenceEditCancel("Ctrl+*")
            self.brightnessLay.addWidget(QLabel("<strong>Brightness</strong><br>Large Increase", alignment=Qt.AlignCenter), 1, 4)
            self.brightnessLay.addWidget(self.SC_Inc_Bri_Large_field, 2, 4)

            # SLIDER ADJUSTMENT KEYBOARD MAPPING SECTIONS
            self.sliderAdjustmentCW = QWidget()
            self.sliderAdjustmentLay = QGridLayout(self.sliderAdjustmentCW)

            self.SC_Dec_1_Small_field = singleKeySequenceEditCancel("7")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 1</strong><br>Small Decrease", alignment=Qt.AlignCenter), 1, 1)
            self.sliderAdjustmentLay.addWidget(self.SC_Dec_1_Small_field, 2, 1)
            self.SC_Dec_1_Large_field = singleKeySequenceEditCancel("Ctrl+7")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 1</strong><br>Large Decrease", alignment=Qt.AlignCenter), 1, 2)
            self.sliderAdjustmentLay.addWidget(self.SC_Dec_1_Large_field, 2, 2)
            self.SC_Inc_1_Small_field = singleKeySequenceEditCancel("9")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 1</strong><br>Small Increase", alignment=Qt.AlignCenter), 1, 3)
            self.sliderAdjustmentLay.addWidget(self.SC_Inc_1_Small_field, 2, 3)
            self.SC_Inc_1_Large_field = singleKeySequenceEditCancel("Ctrl+9")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 1</strong><br>Large Increase", alignment=Qt.AlignCenter), 1, 4)
            self.sliderAdjustmentLay.addWidget(self.SC_Inc_1_Large_field, 2, 4)

            self.SC_Dec_2_Small_field = singleKeySequenceEditCancel("4")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 2</strong><br>Small Decrease", alignment=Qt.AlignCenter), 3, 1)
            self.sliderAdjustmentLay.addWidget(self.SC_Dec_2_Small_field, 4, 1)
            self.SC_Dec_2_Large_field = singleKeySequenceEditCancel("Ctrl+4")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 2</strong><br>Large Decrease", alignment=Qt.AlignCenter), 3, 2)
            self.sliderAdjustmentLay.addWidget(self.SC_Dec_2_Large_field, 4, 2)
            self.SC_Inc_2_Small_field = singleKeySequenceEditCancel("6")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 2</strong><br>Small Increase", alignment=Qt.AlignCenter), 3, 3)
            self.sliderAdjustmentLay.addWidget(self.SC_Inc_2_Small_field, 4, 3)
            self.SC_Inc_2_Large_field = singleKeySequenceEditCancel("Ctrl+6")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 2</strong><br>Large Increase", alignment=Qt.AlignCenter), 3, 4)
            self.sliderAdjustmentLay.addWidget(self.SC_Inc_2_Large_field, 4, 4)

            self.SC_Dec_3_Small_field = singleKeySequenceEditCancel("1")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 3</strong><br>Small Decrease", alignment=Qt.AlignCenter), 5, 1)
            self.sliderAdjustmentLay.addWidget(self.SC_Dec_3_Small_field, 6, 1)
            self.SC_Dec_3_Large_field = singleKeySequenceEditCancel("Ctrl+1")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 3</strong><br>Large Decrease", alignment=Qt.AlignCenter), 5, 2)
            self.sliderAdjustmentLay.addWidget(self.SC_Dec_3_Large_field, 6, 2)
            self.SC_Inc_3_Small_field = singleKeySequenceEditCancel("3")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 3</strong><br>Small Increase", alignment=Qt.AlignCenter), 5, 3)
            self.sliderAdjustmentLay.addWidget(self.SC_Inc_3_Small_field, 6, 3)
            self.SC_Inc_3_Large_field = singleKeySequenceEditCancel("Ctrl+3")
            self.sliderAdjustmentLay.addWidget(QLabel("<strong>Slider 3</strong><br>Large Increase", alignment=Qt.AlignCenter), 5, 4)
            self.sliderAdjustmentLay.addWidget(self.SC_Inc_3_Large_field, 6, 4)

            # BOTTOM BUTTONS
            self.bottomButtonsCW = QWidget()
            self.bottomButtonsLay = QGridLayout(self.bottomButtonsCW)

            self.bottomButtonsLay.addWidget(self.resetGlobalPrefsButton, 1, 1)
            self.bottomButtonsLay.addWidget(self.saveGlobalPrefsButton, 1, 2)

            # FINALLY, IT'S TIME TO BUILD THE PREFERENCES PANE ITSELF
            self.globalPrefsLay.addRow(QLabel("<strong><u>Main Program Options</strong></u>", alignment=Qt.AlignCenter))
            self.globalPrefsLay.addRow(self.findLightsOnStartup_check)
            self.globalPrefsLay.addRow(self.autoConnectToLights_check)
            self.globalPrefsLay.addRow(self.printDebug_check)
            self.globalPrefsLay.addRow(self.rememberLightsOnExit_check)
            self.globalPrefsLay.addRow(self.rememberPresetsOnExit_check)
            self.globalPrefsLay.addRow("Maximum Number of retries:", self.maxNumOfAttempts_field)
            self.globalPrefsLay.addRow(QLabel("<hr><strong><u>Acceptable IPs to use for the HTTP Server:</strong></u><br><em>Each line below is an IP allows access to NeewerLite-Python's HTTP server.<br>Wildcards for IP addresses can be entered by just leaving that section blank.<br><u>For example:</u><br><strong>192.168.*.*</strong> would be entered as just <strong>192.168.</strong><br><strong>10.0.1.*</strong> is <strong>10.0.1.</strong>", alignment=Qt.AlignCenter))
            self.globalPrefsLay.addRow(self.acceptable_HTTP_IPs_field)
            self.globalPrefsLay.addRow(QLabel("<hr><strong><u>Whitelisted MAC Addresses/GUIDs</u></strong><br><em>Devices with whitelisted MAC Addresses/GUIDs are added to the<br>list of lights even if their name doesn't contain <strong>Neewer</strong> in it.<br><br>This preference is really only useful if you have compatible lights<br>that don't show up properly due to name mismatches.</em>", alignment=Qt.AlignCenter))
            self.globalPrefsLay.addRow(self.whiteListedMACs_field)
            self.globalPrefsLay.addRow(QLabel("<hr><strong><u>Custom GUI Keyboard Shortcut Mapping - GUI Buttons</strong></u><br><em>To switch a keyboard shortcut, click on the old shortcut and type a new one in.<br>To reset a shortcut to default, click the X button next to it.</em><br><br>These 4 keyboard shortcuts control the buttons on the top of the window.", alignment=Qt.AlignCenter))
            self.globalPrefsLay.addRow(self.windowButtonsCW)
            self.globalPrefsLay.addRow(QLabel("<hr><strong><u>Custom GUI Keyboard Shortcut Mapping - Switching Mode Tabs</strong></u><br><em>To switch a keyboard shortcut, click on the old shortcut and type a new one in.<br>To reset a shortcut to default, click the X button next to it.</em><br><br>These 4 keyboard shortcuts switch between<br>the CCT, HSI, SCENE and LIGHT PREFS tabs.", alignment=Qt.AlignCenter))
            self.globalPrefsLay.addRow(self.tabSwitchCW)
            self.globalPrefsLay.addRow(QLabel("<hr><strong><u>Custom GUI Keyboard Shortcut Mapping - Increase/Decrease Brightness</strong></u><br><em>To switch a keyboard shortcut, click on the old shortcut and type a new one in.<br>To reset a shortcut to default, click the X button next to it.</em><br><br>These 4 keyboard shortcuts adjust the brightness of the selected light(s).", alignment=Qt.AlignCenter))
            self.globalPrefsLay.addRow(self.brightnessCW)
            self.globalPrefsLay.addRow(QLabel("<hr><strong><u>Custom GUI Keyboard Shortcut Mapping - Slider Adjustments</strong></u><br><em>To switch a keyboard shortcut, click on the old shortcut and type a new one in.<br>To reset a shortcut to default, click the X button next to it.</em><br><br>These 12 keyboard shortcuts adjust <em>up to 3 sliders</em> on the currently active tab.", alignment=Qt.AlignCenter))
            self.globalPrefsLay.addRow(self.sliderAdjustmentCW)
            self.globalPrefsLay.addRow(QLabel("<hr>"))
            self.globalPrefsLay.addRow(self.bottomButtonsCW)

            # === >> ADD THE TABS TO THE TAB WIDGET << ===
            self.ColorModeTabWidget.addTab(self.CCT, "CCT Mode")
            self.ColorModeTabWidget.addTab(self.HSI, "HSI Mode")
            self.ColorModeTabWidget.addTab(self.ANM, "Scene Mode")
            self.ColorModeTabWidget.addTab(self.lightPrefs, "Light Preferences")
            self.ColorModeTabWidget.addTab(self.globalPrefs, "Global Preferences")

            self.ColorModeTabWidget.setCurrentIndex(0) # make the CCT tab the main tab shown on launch

            # ============ THE STATUS BAR AND WINDOW ASSIGNS ============
            MainWindow.setCentralWidget(self.centralwidget)
            self.statusBar = QStatusBar(MainWindow)
            MainWindow.setStatusBar(self.statusBar)

    # =======================================================
    # = CUSTOM GUI CLASSES
    # =======================================================

    class parameterWidget(QWidget):
        valueChanged = Signal(int) # return the value that's been changed

        def __init__(self, **kwargs):
            super(parameterWidget, self).__init__()

            if 'prefix' in kwargs:
                self.thePrefix = kwargs['prefix']
            else:
                self.thePrefix = "%"
            
            self.widgetTitle = QLabel(self)
            self.widgetTitle.setFont(mainFont)
            self.widgetTitle.setGeometry(0, 0, 440, 17)

            if 'title' in kwargs:
                self.widgetTitle.setText(kwargs['title'])    
            
            self.bgGradient = QGraphicsView(QGraphicsScene(self), self)
            self.bgGradient.setGeometry(0, 20, 552, 24)
            self.bgGradient.setFrameShape(QFrame.NoFrame)
            self.bgGradient.setFrameShadow(QFrame.Sunken)
            self.bgGradient.setAlignment(Qt.Alignment(combinePySideValues([Qt.AlignLeft, Qt.AlignTop])))

            self.slider = QSlider(self)
            self.slider.setGeometry(0, 25, 552, 16)
            self.slider.setStyleSheet("QSlider::groove:horizontal" 
                                    "{"
                                    "border: 2px solid transparent;"
                                    "height: 12px;"
                                    "background: transparent;"
                                    "margin: 2px 0;"
                                    "}"
                                    "QSlider::handle:horizontal {"
                                    "background-color: rgba(255, 255, 255, 0.75);"
                                    "opacity:0.3;"
                                    "border: 2px solid #5c5c5c;"
                                    "width: 12px;"
                                    "margin: -2px 0;"
                                    "border-radius: 3px;"
                                    "}")
            
            if 'sliderOffset' in kwargs:
                self.sliderOffset = kwargs['sliderOffset']
            else:
                self.sliderOffset = 0

            if 'sliderMin' in kwargs:
                self.slider.setMinimum(kwargs['sliderMin'])
            else:
                self.slider.setMinimum(0)

            if 'sliderMax' in kwargs:
                self.slider.setMaximum(kwargs['sliderMax'])
            else:
                self.slider.setMaximum(100)

            if 'sliderVal' in kwargs:
                self.slider.setValue(kwargs['sliderVal'])
            else:
                self.slider.setValue(50)

            if 'gradient' in kwargs:
                self.gradient = kwargs['gradient']
                self.bgGradient.setBackgroundBrush(self.renderGradient(self.gradient)) 

            self.slider.setOrientation(Qt.Horizontal)
            self.slider.valueChanged.connect(self.sliderValueChanged)

            self.minTF = QLabel(self, text=str(self.slider.minimum() + self.sliderOffset) + self.thePrefix)
            self.minTF.setGeometry(0, 46, 184, 20)
            self.minTF.setAlignment(Qt.AlignLeft)

            self.valueTF = QLabel(self, text=str(self.slider.value() + self.sliderOffset) + self.thePrefix)
            self.valueTF.setFont(mainFont)
            self.valueTF.setGeometry(185, 42, 184, 20)
            self.valueTF.setAlignment(Qt.AlignCenter)

            self.maxTF = QLabel(self, text=str(self.slider.maximum() + self.sliderOffset) + self.thePrefix)
            self.maxTF.setGeometry(370, 46, 184, 20)
            self.maxTF.setAlignment(Qt.AlignRight)
        
        def value(self):
            return self.slider.value()

        def setValue(self, theValue):
            self.slider.setValue(int(theValue))

        def setRangeText(self, min, max):
            self.widgetTitle.setText("Range: " + str(min) + self.thePrefix + "-" + str(max) + self.thePrefix)

        def changeSliderRange(self, newRange):
            self.slider.setMinimum(newRange[0])
            self.slider.setMaximum(newRange[1])
            self.minTF.setText(str(newRange[0]) + self.thePrefix)
            self.maxTF.setText(str(newRange[1]) + self.thePrefix)

            if self.gradient == "TEMP":
                self.bgGradient.setBackgroundBrush(self.renderGradient(self.gradient))

        def sliderValueChanged(self, changeValue):
            self.valueTF.setText(str(changeValue  + self.sliderOffset) + self.thePrefix)
            self.valueChanged.emit(changeValue)

        def adjustSatGradient(self, hue):
            self.bgGradient.setBackgroundBrush(self.renderGradient("SAT", hue))

        def presentMe(self, parent, posX, posY, halfSize = False):
            self.setParent(parent) # move the control to a different tab parent

            if halfSize == False: # check all the sizes to make sure they're correct
                if self.widgetTitle.geometry() != QRect(0, 0, 440, 17):
                    self.widgetTitle.setGeometry(0, 0, 440, 17)
                if self.bgGradient.geometry() != QRect(0, 20, 552, 24):
                    self.bgGradient.setGeometry(0, 20, 552, 24)
                if self.slider.geometry() != QRect(0, 25, 552, 16):
                    self.slider.setGeometry(0, 25, 552, 16)
                if self.minTF.geometry() != QRect(0, 46, 184, 20):
                    self.minTF.setGeometry(0, 46, 184, 20)
                if self.valueTF.geometry() != QRect(185, 42, 184, 20):
                    self.valueTF.setGeometry(185, 42, 184, 20)
                if self.maxTF.geometry() != QRect(370, 46, 184, 20):
                    self.maxTF.setGeometry(370, 46, 184, 20)
            else:
                if self.widgetTitle.geometry() != QRect(0, 0, 216, 17):
                    self.widgetTitle.setGeometry(0, 0, 216, 17)
                if self.bgGradient.geometry() != QRect(0, 20, 272, 24):
                    self.bgGradient.setGeometry(0, 20, 272, 24)
                if self.slider.geometry() != QRect(0, 25, 272, 16):
                    self.slider.setGeometry(0, 25, 272, 16)
                if self.minTF.geometry() != QRect(0, 46, 90, 20):
                    self.minTF.setGeometry(0, 46, 90, 20)
                if self.valueTF.geometry() != QRect(90, 42, 90, 20):
                    self.valueTF.setGeometry(90, 42, 90, 20)
                if self.maxTF.geometry() != QRect(180, 46, 90, 20):
                    self.maxTF.setGeometry(180, 46, 90, 20)

            # finally move the entire control to a position and display it
            self.move(posX, posY)
            self.show()

        def renderGradient(self, gradientType, hue=180):
            returnGradient = QLinearGradient(0, 0, 1, 0)
            
            if PySideGUI == "PySide2":
                returnGradient.setCoordinateMode(returnGradient.ObjectMode)
            else:
                returnGradient.setCoordinateMode(QGradient.ObjectMode)

            if gradientType == "TEMP": # color temperature gradient (calculate new gradient with new bounds)
                min = self.slider.minimum() * 100
                max = self.slider.maximum() * 100

                rangeStep = (max - min) / 4 # figure out how much in between steps of the gradient

                for i in range(5): # fill the gradient with a new set of colors
                    rgbValues = self.convert_K_to_RGB(min + (rangeStep * i))                
                    returnGradient.setColorAt((0.25 * i), QColor(rgbValues[0], rgbValues[1], rgbValues[2]))
            elif gradientType == "BRI": # brightness gradient
                returnGradient.setColorAt(0.0, QColor(0, 0, 0, 255)) # Dark
                returnGradient.setColorAt(1.0, QColor(255, 255, 255, 255)) # Light
            elif gradientType == "GM": # GM adjustment gradient
                returnGradient.setColorAt(0.0, QColor(255, 0, 255, 255)) # Full Magenta
                returnGradient.setColorAt(0.5, QColor(255, 255, 255, 255)) # White
                returnGradient.setColorAt(1.0, QColor(0, 255, 0, 255)) # Full Green
            elif gradientType == "RGB": # RGB 360º gradient
                returnGradient.setColorAt(0.0, QColor(255, 0, 0, 255))
                returnGradient.setColorAt(0.16, QColor(255, 255, 0, 255))
                returnGradient.setColorAt(0.33, QColor(0, 255, 0, 255))
                returnGradient.setColorAt(0.49, QColor(0, 255, 255, 255))
                returnGradient.setColorAt(0.66, QColor(0, 0, 255, 255))
                returnGradient.setColorAt(0.83, QColor(255, 0, 255, 255))
                returnGradient.setColorAt(1.0, QColor(255, 0, 0, 255))
            elif gradientType == "SAT": # color saturation gradient (calculate new gradient with base hue)
                returnGradient.setColorAt(0, QColor(255, 255, 255))
                newColor = self.convert_HSI_to_RGB(hue / 360)
                returnGradient.setColorAt(1, QColor(newColor[0], newColor[1], newColor[2]))
            elif gradientType == "SPEED": # speed setting gradient
                returnGradient.setColorAt(0.0, QColor(255, 255, 255, 255))
                returnGradient.setColorAt(1.0, QColor(0, 0, 255, 255))
            elif gradientType == "SPARKS": # sparks setting gradient
                returnGradient.setColorAt(0.0, QColor(255, 255, 255, 255))
                returnGradient.setColorAt(1.0, QColor(255, 0, 0, 255))

            return returnGradient
        
        # CALCULATE THE RGB VALUE OF COLOR TEMPERATURE
        def convert_K_to_RGB(self, Ktemp):
            # Based on this script: https://gist.github.com/petrklus/b1f427accdf7438606a6
            # from @petrklus on GitHub (his source was from http://www.tannerhelland.com/4435/convert-temperature-rgb-algorithm-code/)

            tmp_internal = Ktemp / 100.0
            
            # red 
            if tmp_internal <= 66:
                red = 255
            else:
                tmp_red = 329.698727446 * math.pow(tmp_internal - 60, -0.1332047592)

                if tmp_red < 0:
                    red = 0
                elif tmp_red > 255:
                    red = 255
                else:
                    red = tmp_red
            
            # green
            if tmp_internal <= 66:
                tmp_green = 99.4708025861 * math.log(tmp_internal) - 161.1195681661

                if tmp_green < 0:
                    green = 0
                elif tmp_green > 255:
                    green = 255
                else:
                    green = tmp_green
            else:
                tmp_green = 288.1221695283 * math.pow(tmp_internal - 60, -0.0755148492)

                if tmp_green < 0:
                    green = 0
                elif tmp_green > 255:
                    green = 255
                else:
                    green = tmp_green
            
            # blue
            if tmp_internal >= 66:
                blue = 255
            elif tmp_internal <= 19:
                blue = 0
            else:
                tmp_blue = 138.5177312231 * math.log(tmp_internal - 10) - 305.0447927307
                if tmp_blue < 0:
                    blue = 0
                elif tmp_blue > 255:
                    blue = 255
                else:
                    blue = tmp_blue
            
            return int(red), int(green), int(blue) # return the integer value for each part of the RGB values for this step

        def convert_HSI_to_RGB(self, h, s = 1, v = 1):
            # Taken from this StackOverflow page, which is an articulation of the colorsys code to
            # convert HSV values (not HSI, but close, as I'm keeping S and V locked to 1) to RGB:
            # https://stackoverflow.com/posts/26856771/revisions

            if s == 0.0: v*=255; return (v, v, v)
            i = int(h*6.) # XXX assume int() truncates!
            f = (h*6.)-i; p,q,t = int(255*(v*(1.-s))), int(255*(v*(1.-s*f))), int(255*(v*(1.-s*(1.-f)))); v*=255; i%=6
            if i == 0: return (v, t, p)
            if i == 1: return (q, v, p)
            if i == 2: return (p, v, t)
            if i == 3: return (p, q, v)
            if i == 4: return (t, p, v)
            if i == 5: return (v, p, q)

    class doubleSlider(QWidget):
        valueChanged = Signal(int, int) # return left value, right value

        def __init__(self, **kwargs):
            super(doubleSlider, self).__init__()

            if 'sliderType' in kwargs:
                self.sliderType = kwargs['sliderType']
            else:
                self.sliderType = "RGB"

            if self.sliderType == "RGB":
                self.leftSlider = parameterWidget(title="Hue Limits", gradient="RGB", sliderMin=0, sliderVal=0, sliderMax=360, prefix="º")
                self.rightSlider = parameterWidget(title="Range: 0º-360º", gradient="RGB", sliderMin=0, sliderVal=360, sliderMax=360, prefix="º")
            elif self.sliderType == "BRI":
                self.leftSlider = parameterWidget(title="Brightness Limits", gradient="BRI", sliderMin=0, sliderVal=0, sliderMax=100, prefix="%")
                self.rightSlider = parameterWidget(title="Range: 0%-100%", gradient="BRI", sliderMin=0, sliderVal=100, sliderMax=100, prefix="%")
            elif self.sliderType == "TEMP":
                self.leftSlider = parameterWidget(title="Color Temperature Limits", gradient="TEMP", sliderMin=32, sliderVal=32, sliderMax=72, prefix="00K")
                self.rightSlider = parameterWidget(title="Range: 3200K-5600K", gradient="TEMP", sliderMin=32, sliderVal=72, sliderMax=72, prefix="00K")
        
            self.leftSlider.valueChanged.connect(self.doubleSliderValueChanged)
            self.rightSlider.valueChanged.connect(self.doubleSliderValueChanged)

            self.leftSlider.presentMe(self, 0, 0, True)
            self.rightSlider.presentMe(self, 282, 0, True)

        def doubleSliderValueChanged(self):
            leftSliderValue = self.leftSlider.value()
            rightSliderValue = self.rightSlider.value()

            if leftSliderValue > rightSliderValue:
                self.rightSlider.setValue(leftSliderValue)
            if rightSliderValue < leftSliderValue:
                self.leftSlider.setValue(rightSliderValue)

            self.rightSlider.setRangeText(leftSliderValue, rightSliderValue)
            self.valueChanged.emit(leftSliderValue, rightSliderValue)

        def changeSliderRange(self, newRange):
            self.leftSlider.changeSliderRange(newRange)
            self.rightSlider.changeSliderRange(newRange)

        def value(self):
            return([self.leftSlider.value(), self.rightSlider.value()])
        
        def setValue(self, theSlider, theValue):
            if theSlider == "left":
                self.leftSlider.setValue(theValue)
            elif theSlider == "right":
                self.rightSlider.setValue(theValue)

        def presentMe(self, parent, posX, posY):
            self.setParent(parent)
            self.move(posX, posY)
            self.show()

    class customPresetButton(QLabel):
        clicked = Signal() # signal sent when you click on the button
        rightclicked = Signal() # signal sent when you right-click on the button
        enteredWidget = Signal() # signal sent when the mouse enters the button
        leftWidget = Signal() # signal sent when the mouse leaves the button

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            if platform.system() == "Windows": # Windows font
                customPresetFont = QFont("Calibri")
                customPresetFont.setPointSize(10.5)
                self.setFont(customPresetFont)
            elif platform.system() == "Linux": # Linux (Ubuntu) font
                customPresetFont = QFont()
                customPresetFont.setPointSize(10.5)
                self.setFont(customPresetFont)
            else: # fallback font
                customPresetFont = QFont()
                customPresetFont.setPointSize(12)
                self.setFont(customPresetFont)

            self.setAlignment(Qt.AlignCenter)
            self.setTextFormat(Qt.TextFormat.RichText)
            self.setText(kwargs['text'])

            self.setStyleSheet("customPresetButton"
                            "{"
                            "border: 1px solid grey; background-color: #a5cbf7;"
                            "}"
                            "customPresetButton::hover"
                            "{"
                            "background-color: #a5e3f7;"
                            "}")

        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.clicked.emit()
            elif event.button() == Qt.RightButton:
                self.rightclicked.emit()

        def enterEvent(self, event):
            self.enteredWidget.emit()

        def leaveEvent(self, event):
            self.leftWidget.emit()

        def markCustom(self, presetNum, isSnap = 0):
            if isSnap == 0: # we're using a global preset
                self.setText("<strong><font size=+2>" + str(presetNum + 1) + "</font></strong><br>CUSTOM<br>GLOBAL")

                self.setStyleSheet("customPresetButton"
                            "{"
                            "border: 1px solid grey; background-color: #7188ff;"
                            "}"
                            "customPresetButton::hover"
                            "{"
                            "background-color: #70b0ff;"
                            "}")
            elif isSnap >= 1: # we're using a snapshot preset
                self.setText("<strong><font size=+2>" + str(presetNum + 1) + "</font></strong><br>CUSTOM<br>SNAP")

                self.setStyleSheet("customPresetButton"
                            "{"
                            "border: 1px solid grey; background-color: #71e993;"
                            "}"
                            "customPresetButton::hover"
                            "{"
                            "background-color: #abe9ab;"
                            "}")
            else: # we're resetting back to a default preset
                self.setText("<strong><font size=+2>" + str(presetNum + 1) + "</font></strong><br>PRESET<br>GLOBAL")

                self.setStyleSheet("customPresetButton"
                            "{"
                            "border: 1px solid grey; background-color: #a5cbf7;"
                            "}"
                            "customPresetButton::hover"
                            "{"
                            "background-color: #a5e3f7;"
                            "}")

    class singleKeySequenceEditCancel(QWidget):
        def __init__(self, defaultValue):
            super(singleKeySequenceEditCancel, self).__init__()
            self.defaultValue = defaultValue # the default keyboard shortcut for this field

            customLayout = QGridLayout()
            customLayout.setContentsMargins(0, 0, 0, 0) # don't use any extra padding for this control

            # THE KEYBOARD SHORTCUT FIELD
            self.keyPressField = singleKeySequenceEdit()
            # self.keyPressField.setToolTip("Click on this field and type in a new keyboard shortcut to register it")

            # THE RESET BUTTON
            self.resetButton = QLabel("X", alignment=Qt.AlignCenter)
            self.resetButton.setFixedWidth(24)
            self.resetButton.setStyleSheet("QLabel" 
                                        "{"
                                        "border: 1px solid black; background-color: light grey;"
                                        "}"
                                        "QLabel::hover"
                                        "{"
                                        "background-color: salmon;"
                                        "}")
            # self.resetButton.setToolTip("Click on this button to reset the current keyboard shortcut to it's default value")
            self.resetButton.mousePressEvent = self.resetValue

            customLayout.addWidget(self.keyPressField, 1, 1)
            customLayout.addWidget(self.resetButton, 1, 2)

            self.setMaximumWidth(135) # make sure the entire control is no longer than 135 pixels wide
            self.setLayout(customLayout)

        def keySequence(self):
            return self.keyPressField.keySequence()

        def setKeySequence(self, keySequence):
            self.keyPressField.setKeySequence(keySequence)

        def resetValue(self, event):
            self.keyPressField.setKeySequence(self.defaultValue)

    class singleKeySequenceEdit(QKeySequenceEdit):
        # CUSTOM VERSION OF QKeySequenceEdit THAT ONLY ACCEPTS ONE COMBINATION BEFORE RETURNING
        def keyPressEvent(self, event):
            super(singleKeySequenceEdit, self).keyPressEvent(event)

            theString = self.keySequence().toString(QKeySequence.NativeText)

            if theString:
                lastSequence = theString.split(",")[-1].strip()
                self.setKeySequence(lastSequence)

    try: # try to load the GUI
        class MainWindow(QMainWindow, Ui_MainWindow):
            def __init__(self):
                QMainWindow.__init__(self)
                self.setupUi(self) # set up the main UI
                self.connectMe() # connect the function handlers to the widgets

                if enableTabsOnLaunch == False: # if we're not supposed to enable tabs on launch, then disable them all
                    self.ColorModeTabWidget.setTabEnabled(0, False) # disable the CCT tab on launch
                    self.ColorModeTabWidget.setTabEnabled(1, False) # disable the HSI tab on launch
                    self.ColorModeTabWidget.setTabEnabled(2, False) # disable the SCENE tab on launch
                    self.ColorModeTabWidget.setTabEnabled(3, False) # disable the LIGHT PREFS tab on launch
                    self.ColorModeTabWidget.setCurrentIndex(0)

                if findLightsOnStartup == True: # if we're set up to find lights on startup, then indicate that
                    self.statusBar.showMessage("Please wait - searching for Neewer lights...")
                else:
                    self.statusBar.showMessage("Welcome to NeewerLite-Python!  Hit the Scan button above to scan for lights.")

                if platform.system() == "Darwin": # if we're on MacOS, then change the column text for the 2nd column in the light table
                    self.lightTable.horizontalHeaderItem(1).setText("Light UUID")

                # IF ANY OF THE CUSTOM PRESETS ARE ACTUALLY CUSTOM, THEN MARK THOSE BUTTONS AS CUSTOM
                if customLightPresets[0] != defaultLightPresets[0]:
                    if customLightPresets[0][0][0] == -1: # if the current preset is custom, but a global, mark it that way
                        self.customPreset_0_Button.markCustom(0)
                    else: # the current preset is a snapshot preset
                        self.customPreset_0_Button.markCustom(0, 1)
                if customLightPresets[1] != defaultLightPresets[1]:
                    if customLightPresets[1][0][0] == -1:
                        self.customPreset_1_Button.markCustom(1)
                    else:
                        self.customPreset_1_Button.markCustom(1, 1)
                if customLightPresets[2] != defaultLightPresets[2]:
                    if customLightPresets[2][0][0] == -1:
                        self.customPreset_2_Button.markCustom(2)
                    else:
                        self.customPreset_2_Button.markCustom(2, 1)
                if customLightPresets[3] != defaultLightPresets[3]:
                    if customLightPresets[3][0][0] == -1:
                        self.customPreset_3_Button.markCustom(3)
                    else:
                        self.customPreset_3_Button.markCustom(3, 1)
                if customLightPresets[4] != defaultLightPresets[4]:
                    if customLightPresets[4][0][0] == -1:
                        self.customPreset_4_Button.markCustom(4)
                    else:
                        self.customPreset_4_Button.markCustom(4, 1)
                if customLightPresets[5] != defaultLightPresets[5]:
                    if customLightPresets[5][0][0] == -1:
                        self.customPreset_5_Button.markCustom(5)
                    else:
                        self.customPreset_5_Button.markCustom(5, 1)
                if customLightPresets[6] != defaultLightPresets[6]:
                    if customLightPresets[6][0][0] == -1:
                        self.customPreset_6_Button.markCustom(6)
                    else:
                        self.customPreset_6_Button.markCustom(6, 1)
                if customLightPresets[7] != defaultLightPresets[7]:
                    if customLightPresets[7][0][0] == -1:
                        self.customPreset_7_Button.markCustom(7)
                    else:
                        self.customPreset_7_Button.markCustom(7, 1)
                    
                self.show()

            def connectMe(self):
                self.turnOffButton.clicked.connect(self.turnLightOff)
                self.turnOnButton.clicked.connect(self.turnLightOn)

                self.scanCommandButton.clicked.connect(self.startSelfSearch)
                self.tryConnectButton.clicked.connect(self.startConnect)

                self.ColorModeTabWidget.currentChanged.connect(self.tabChanged)
                self.lightTable.itemSelectionChanged.connect(self.selectionChanged)
                self.effectChooser.currentIndexChanged.connect(self.effectChanged)

                # Allow clicking on the headers for sorting purposes
                horizHeaders = self.lightTable.horizontalHeader()
                horizHeaders.setSectionsClickable(True)
                horizHeaders.sectionClicked.connect(self.sortByHeader)

                # COMMENTS ARE THE SAME THE ENTIRE WAY DOWN THIS CHAIN
                self.customPreset_0_Button.clicked.connect(lambda: recallCustomPreset(0)) # when you click a preset
                self.customPreset_0_Button.rightclicked.connect(lambda: self.saveCustomPresetDialog(0)) # when you right-click a preset
                self.customPreset_0_Button.enteredWidget.connect(lambda: self.highlightLightsForSnapshotPreset(0)) # when the mouse enters the widget
                self.customPreset_0_Button.leftWidget.connect(lambda: self.highlightLightsForSnapshotPreset(0, True)) # when the mouse leaves the widget
                self.customPreset_1_Button.clicked.connect(lambda: recallCustomPreset(1))
                self.customPreset_1_Button.rightclicked.connect(lambda: self.saveCustomPresetDialog(1))
                self.customPreset_1_Button.enteredWidget.connect(lambda: self.highlightLightsForSnapshotPreset(1))
                self.customPreset_1_Button.leftWidget.connect(lambda: self.highlightLightsForSnapshotPreset(1, True))
                self.customPreset_2_Button.clicked.connect(lambda: recallCustomPreset(2))
                self.customPreset_2_Button.rightclicked.connect(lambda: self.saveCustomPresetDialog(2))
                self.customPreset_2_Button.enteredWidget.connect(lambda: self.highlightLightsForSnapshotPreset(2))
                self.customPreset_2_Button.leftWidget.connect(lambda: self.highlightLightsForSnapshotPreset(2, True))
                self.customPreset_3_Button.clicked.connect(lambda: recallCustomPreset(3))
                self.customPreset_3_Button.rightclicked.connect(lambda: self.saveCustomPresetDialog(3))
                self.customPreset_3_Button.enteredWidget.connect(lambda: self.highlightLightsForSnapshotPreset(3))
                self.customPreset_3_Button.leftWidget.connect(lambda: self.highlightLightsForSnapshotPreset(3, True))
                self.customPreset_4_Button.clicked.connect(lambda: recallCustomPreset(4))
                self.customPreset_4_Button.rightclicked.connect(lambda: self.saveCustomPresetDialog(4))
                self.customPreset_4_Button.enteredWidget.connect(lambda: self.highlightLightsForSnapshotPreset(4))
                self.customPreset_4_Button.leftWidget.connect(lambda: self.highlightLightsForSnapshotPreset(4, True))
                self.customPreset_5_Button.clicked.connect(lambda: recallCustomPreset(5))
                self.customPreset_5_Button.rightclicked.connect(lambda: self.saveCustomPresetDialog(5))
                self.customPreset_5_Button.enteredWidget.connect(lambda: self.highlightLightsForSnapshotPreset(5))
                self.customPreset_5_Button.leftWidget.connect(lambda: self.highlightLightsForSnapshotPreset(5, True))
                self.customPreset_6_Button.clicked.connect(lambda: recallCustomPreset(6))
                self.customPreset_6_Button.rightclicked.connect(lambda: self.saveCustomPresetDialog(6))
                self.customPreset_6_Button.enteredWidget.connect(lambda: self.highlightLightsForSnapshotPreset(6))
                self.customPreset_6_Button.leftWidget.connect(lambda: self.highlightLightsForSnapshotPreset(6, True))
                self.customPreset_7_Button.clicked.connect(lambda: recallCustomPreset(7))
                self.customPreset_7_Button.rightclicked.connect(lambda: self.saveCustomPresetDialog(7))
                self.customPreset_7_Button.enteredWidget.connect(lambda: self.highlightLightsForSnapshotPreset(7))
                self.customPreset_7_Button.leftWidget.connect(lambda: self.highlightLightsForSnapshotPreset(7, True))

                # Connect the sliders to the computation function
                self.colorTempSlider.valueChanged.connect(lambda: self.computeValues())
                self.brightSlider.valueChanged.connect(lambda: self.computeValues())
                self.GMSlider.valueChanged.connect(lambda: self.computeValues())
                self.RGBSlider.valueChanged.connect(lambda: self.computeValues())
                self.colorSatSlider.valueChanged.connect(lambda: self.computeValues())
                self.brightDoubleSlider.valueChanged.connect(lambda: self.computeValues())
                self.RGBDoubleSlider.valueChanged.connect(lambda: self.computeValues())
                self.colorTempDoubleSlider.valueChanged.connect(lambda: self.computeValues())
                self.speedSlider.valueChanged.connect(lambda: self.computeValues())
                self.sparksSlider.valueChanged.connect(lambda: self.computeValues())
                self.specialOptionsChooser.currentIndexChanged.connect(lambda: self.computeValues())

                # CHECKS TO SEE IF SPECIFIC FIELDS (and the save button) SHOULD BE ENABLED OR DISABLED
                self.customName.clicked.connect(self.checkLightPrefsEnables)
                self.colorTempRange.clicked.connect(self.checkLightPrefsEnables)
                self.saveLightPrefsButton.clicked.connect(self.checkLightPrefs)

                self.resetGlobalPrefsButton.clicked.connect(lambda: self.setupGlobalLightPrefsTab(True))
                self.saveGlobalPrefsButton.clicked.connect(self.saveGlobalPrefs)

                # SHORTCUT KEYS - MAKE THEM HERE, SET THEIR ASSIGNMENTS BELOW WITH self.setupShortcutKeys()
                # IN CASE WE NEED TO CHANGE THEM AFTER CHANGING PREFERENCES
                self.SC_turnOffButton = QShortcut(self)
                self.SC_turnOnButton = QShortcut(self)
                self.SC_scanCommandButton = QShortcut(self)
                self.SC_tryConnectButton = QShortcut(self)
                self.SC_Tab_CCT = QShortcut(self)
                self.SC_Tab_HSI = QShortcut(self)
                self.SC_Tab_SCENE = QShortcut(self)
                self.SC_Tab_PREFS = QShortcut(self)

                # DECREASE/INCREASE BRIGHTNESS REGARDLESS OF WHICH TAB WE'RE ON
                self.SC_Dec_Bri_Small = QShortcut(self)
                self.SC_Inc_Bri_Small = QShortcut(self)
                self.SC_Dec_Bri_Large = QShortcut(self)
                self.SC_Inc_Bri_Large = QShortcut(self)

                # THE SMALL INCREMENTS *DO* NEED A CUSTOM FUNCTION, BUT ONLY IF WE CHANGE THE
                # SHORTCUT ASSIGNMENT TO SOMETHING OTHER THAN THE NORMAL NUMBERS
                # THE LARGE INCREMENTS DON'T NEED A CUSTOM FUNCTION
                self.SC_Dec_1_Small = QShortcut(self)
                self.SC_Inc_1_Small = QShortcut(self)
                self.SC_Dec_2_Small = QShortcut(self)
                self.SC_Inc_2_Small = QShortcut(self)
                self.SC_Dec_3_Small = QShortcut(self)
                self.SC_Inc_3_Small = QShortcut(self)
                self.SC_Dec_1_Large = QShortcut(self)
                self.SC_Inc_1_Large = QShortcut(self)
                self.SC_Dec_2_Large = QShortcut(self)
                self.SC_Inc_2_Large = QShortcut(self)
                self.SC_Dec_3_Large = QShortcut(self)
                self.SC_Inc_3_Large = QShortcut(self)

                self.setupShortcutKeys() # set up the shortcut keys for the first time

                # CONNECT THE KEYS TO THEIR FUNCTIONS
                self.SC_turnOffButton.activated.connect(self.turnLightOff)
                self.SC_turnOnButton.activated.connect(self.turnLightOn)
                self.SC_scanCommandButton.activated.connect(self.startSelfSearch)
                self.SC_tryConnectButton.activated.connect(self.startConnect)
                self.SC_Tab_CCT.activated.connect(lambda: self.switchToTab(0))
                self.SC_Tab_HSI.activated.connect(lambda: self.switchToTab(1))
                self.SC_Tab_SCENE.activated.connect(lambda: self.switchToTab(2))
                self.SC_Tab_PREFS.activated.connect(lambda: self.switchToTab(3))

                # DECREASE/INCREASE BRIGHTNESS REGARDLESS OF WHICH TAB WE'RE ON
                self.SC_Dec_Bri_Small.activated.connect(lambda: self.changeSliderValue(0, -1))
                self.SC_Inc_Bri_Small.activated.connect(lambda: self.changeSliderValue(0, 1))
                self.SC_Dec_Bri_Large.activated.connect(lambda: self.changeSliderValue(0, -5))
                self.SC_Inc_Bri_Large.activated.connect(lambda: self.changeSliderValue(0, 5))

                # THE SMALL INCREMENTS DO NEED A SPECIAL FUNCTION-
                # (see above) - BASICALLY, IF THEY'RE JUST ASSIGNED THE DEFAULT NUMPAD/NUMBER VALUES
                # THESE FUNCTIONS DON'T TRIGGER (THE SAME FUNCTIONS ARE HANDLED BY numberShortcuts(n))
                # BUT IF THEY ARE CUSTOM, *THEN* THESE TRIGGER INSTEAD, AND THIS FUNCTION ^^^^ JUST DOES
                # SCENE SELECTIONS IN SCENE MODE
                self.SC_Dec_1_Small.activated.connect(lambda: self.changeSliderValue(1, -1))
                self.SC_Inc_1_Small.activated.connect(lambda: self.changeSliderValue(1, 1))
                self.SC_Dec_2_Small.activated.connect(lambda: self.changeSliderValue(2, -1))
                self.SC_Inc_2_Small.activated.connect(lambda: self.changeSliderValue(2, 1))
                self.SC_Dec_3_Small.activated.connect(lambda: self.changeSliderValue(3, -1))
                self.SC_Inc_3_Small.activated.connect(lambda: self.changeSliderValue(3, 1))

                # THE LARGE INCREMENTS DON'T NEED A CUSTOM FUNCTION
                self.SC_Dec_1_Large.activated.connect(lambda: self.changeSliderValue(1, -5))
                self.SC_Inc_1_Large.activated.connect(lambda: self.changeSliderValue(1, 5))
                self.SC_Dec_2_Large.activated.connect(lambda: self.changeSliderValue(2, -5))
                self.SC_Inc_2_Large.activated.connect(lambda: self.changeSliderValue(2, 5))
                self.SC_Dec_3_Large.activated.connect(lambda: self.changeSliderValue(3, -5))
                self.SC_Inc_3_Large.activated.connect(lambda: self.changeSliderValue(3, 5))

                # THE NUMPAD SHORTCUTS ARE SET UP REGARDLESS OF WHAT THE CUSTOM INC/DEC SHORTCUTS ARE
                self.SC_Num1 = QShortcut(QKeySequence("1"), self)
                self.SC_Num1.activated.connect(lambda: self.numberShortcuts(1))
                self.SC_Num2 = QShortcut(QKeySequence("2"), self)
                self.SC_Num2.activated.connect(lambda: self.numberShortcuts(2))
                self.SC_Num3 = QShortcut(QKeySequence("3"), self)
                self.SC_Num3.activated.connect(lambda: self.numberShortcuts(3))
                self.SC_Num4 = QShortcut(QKeySequence("4"), self)
                self.SC_Num4.activated.connect(lambda: self.numberShortcuts(4))
                self.SC_Num5 = QShortcut(QKeySequence("5"), self)
                self.SC_Num5.activated.connect(lambda: self.numberShortcuts(5))
                self.SC_Num6 = QShortcut(QKeySequence("6"), self)
                self.SC_Num6.activated.connect(lambda: self.numberShortcuts(6))
                self.SC_Num7 = QShortcut(QKeySequence("7"), self)
                self.SC_Num7.activated.connect(lambda: self.numberShortcuts(7))
                self.SC_Num8 = QShortcut(QKeySequence("8"), self)
                self.SC_Num8.activated.connect(lambda: self.numberShortcuts(8))
                self.SC_Num9 = QShortcut(QKeySequence("9"), self)
                self.SC_Num9.activated.connect(lambda: self.numberShortcuts(9))

            def sortByHeader(self, theHeader):
                global availableLights
                global lastSortingField

                if theHeader < 2: # if we didn't click on the "Linked" or "Status" headers, start processing the sort
                    sortingList = [] # a copy of the availableLights array
                    checkForCustomNames = False # whether or not to ask to sort by custom names (if there aren't any custom names, then don't allow)

                    for a in range(len(availableLights)): # copy the entire availableLights array into a temporary array to process it
                        if theHeader == 0 and availableLights[a][2] != "": # if the current light has a custom name (and we clicked on Name)
                            checkForCustomNames = True # then we need to ask what kind of sorting when we sort

                        sortingList.append([availableLights[a][0], availableLights[a][1], availableLights[a][2], availableLights[a][3], \
                                            availableLights[a][4], availableLights[a][5], availableLights[a][6], availableLights[a][7], \
                                            availableLights[a][0].name, availableLights[a][0].address, availableLights[a][0].rssi, \
                                            availableLights[a][8]])
                else: # we clicked on the "Linked" or "Status" headers, which do not allow sorting
                    sortingField = -1

                if theHeader == 0:
                    sortDlg = QMessageBox(self)
                    sortDlg.setIcon(QMessageBox.Question)
                    sortDlg.setWindowTitle("Sort by...")
                    sortDlg.setText("Which do you want to sort by?")
                    
                    sortDlg.addButton(" RSSI (Signal Level) ", QMessageBox.ButtonRole.AcceptRole)
                    sortDlg.addButton(" Type of Light ", QMessageBox.ButtonRole.AcceptRole)

                    if checkForCustomNames == True: # if we have custom names available, then add that as an option
                        sortDlg.addButton("Custom Name", QMessageBox.ButtonRole.AcceptRole)    
                        
                    sortDlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                    sortDlg.setIcon(QMessageBox.Warning)

                    if PySideGUI == "PySide2": # PySide2 does exec_(), PySide 6 does plain exec()
                        clickedButton = sortDlg.exec_()
                    else:
                        clickedButton = sortDlg.exec()

                    if clickedButton == 0:
                        sortingField = 10 # sort by RSSI
                    elif clickedButton == 1:
                        sortingField = 8 # sort by type of light
                    elif clickedButton == 2:
                        if checkForCustomNames == True: # if the option was available for custom names, this is "custom name"
                            sortingField = 2 
                        else: # if the option wasn't available, then this is "cancel"
                            sortingField = -1 # cancel out of sorting - write this!
                    elif clickedButton == 3: # this option is only available if custom names is accessible - if so, this is "cancel"
                            sortingField = -1 # cancel out of sorting - write this!
                elif theHeader == 1: # sort by MAC Address/GUID
                    sortingField = 9

                if sortingField != -1: # we want to sort
                    self.lightTable.horizontalHeader().setSortIndicatorShown(True) # show the sorting indicator

                    if lastSortingField != sortingField: # if we're doing a different kind of sort than the last one
                        self.lightTable.horizontalHeader().setSortIndicator(theHeader, Qt.SortOrder.AscendingOrder) # force the header to "Ascending" order
                        if sortingField != 10: # if we're not looking at RSSI
                            doReverseSort = False # we need an ascending order search
                        else: # we ARE looking at RSSI
                            doReverseSort = True # if we're looking at RSSI, then the search order is reversed (as the smaller # is actually the higher value)
                    else: # if it's the same as before, then take the cue from the last order
                        if self.lightTable.horizontalHeader().sortIndicatorOrder() == Qt.SortOrder.DescendingOrder:
                            if sortingField != 10:
                                doReverseSort = True
                            else:
                                doReverseSort = False
                        elif self.lightTable.horizontalHeader().sortIndicatorOrder() == Qt.SortOrder.AscendingOrder:
                            if sortingField != 10:
                                doReverseSort = False
                            else:
                                doReverseSort = True

                    sortedList = sorted(sortingList, key = lambda x: x[sortingField], reverse = doReverseSort) # sort the list
                    availableLights.clear() # clear the list of available lights

                    for a in range(len(sortedList)): # rebuild the available lights list from the sorted list
                        availableLights.append([sortedList[a][0], sortedList[a][1], sortedList[a][2], sortedList[a][3], \
                                                sortedList[a][4], sortedList[a][5], sortedList[a][6], sortedList[a][7], \
                                                sortedList[a][11]])
                                            
                    self.updateLights(False) # redraw the table with the new light list
                    lastSortingField = sortingField # keep track of the last field used for sorting, so we know whether or not to switch to ascending
                else:
                    self.lightTable.horizontalHeader().setSortIndicatorShown(False) # hide the sorting indicator

            def switchToTab(self, theTab): # SWITCH TO THE REQUESTED TAB **IF IT IS AVAILABLE**
                if self.ColorModeTabWidget.isTabEnabled(theTab) == True:
                    self.ColorModeTabWidget.setCurrentIndex(theTab)

            def numberShortcuts(self, theNumber):
                # THE KEYS (IF THERE AREN'T CUSTOM ONES SET UP):
                # 7 AND 9 ADJUST THE FIRST SLIDER ON A TAB
                # 4 AND 6 ADJUST THE SECOND SLIDER ON A TAB
                # 1 AND 3 ADJUST THE THIRD SLIDER ON A TAB
                if theNumber == 1:
                    if customKeys[16] == "1":
                        self.changeSliderValue(3, -1) # decrement slider 3
                elif theNumber == 2:
                    pass
                elif theNumber == 3:
                    if customKeys[17] == "3":
                            self.changeSliderValue(3, 1) # increment slider 3
                elif theNumber == 4:
                    if customKeys[14] == "4":
                            self.changeSliderValue(2, -1) # decrement slider 2
                elif theNumber == 5:
                    pass
                elif theNumber == 6:
                    if customKeys[15] == "6":
                            self.changeSliderValue(2, 1) # increment slider 2
                elif theNumber == 7:
                    if customKeys[12] == "7":
                            self.changeSliderValue(1, -1) # decrement slider 1
                elif theNumber == 8:
                    pass
                elif theNumber == 9:
                    if customKeys[13] == "9":
                            self.changeSliderValue(1, 1) # increment slider 1

            def changeSliderValue(self, sliderToChange, changeAmt):
                if self.ColorModeTabWidget.currentIndex() == 0:
                    if sliderToChange == 1:
                        self.colorTempSlider.setValue(self.colorTempSlider.value() + changeAmt)
                    elif sliderToChange == 2 or sliderToChange == 0:
                        self.brightSlider.setValue(self.brightSlider.value() + changeAmt)
                    elif sliderToChange == 3:
                        self.GMSlider.setValue(self.GMSlider.value() + changeAmt)
                elif self.ColorModeTabWidget.currentIndex() == 1:
                    if sliderToChange == 1:
                        self.RGBSlider.setValue(self.RGBSlider.value() + changeAmt)
                    elif sliderToChange == 2:
                        self.colorSatSlider.setValue(self.colorSatSlider.value() + changeAmt)
                    elif sliderToChange == 3 or sliderToChange == 0:
                        self.brightSlider.setValue(self.brightSlider.value() + changeAmt)
                elif self.ColorModeTabWidget.currentIndex() == 2:
                    if sliderToChange == 0:
                        self.Slider_ANM_Brightness.setValue(self.Slider_ANM_Brightness.value() + changeAmt)

            def checkLightTab(self, selectedLight = -1):
                currentIdx = self.ColorModeTabWidget.currentIndex()

                if currentIdx == 0: # if we're on the CCT tab, do the check
                    if selectedLight == -1: # if we don't have a light selected
                        self.setupCCTBounds(3200, 5600) # restore the bounds to their default of 56(00)K
                    else: # set up the gradient to show the range of color temperatures available to the currently selected light
                        self.setupCCTBounds(availableLights[selectedLight][4][0], availableLights[selectedLight][4][1])
                elif currentIdx == 3: # if we're on the Preferences tab instead
                    if selectedLight != -1: # if there is a specific selected light
                        self.setupLightPrefsTab(selectedLight) # update the Prefs tab with the information for that selected light

            def setupCCTBounds(self, startRange, endRange):
                startRange = int(startRange / 100)
                endRange = int(endRange / 100)

                self.colorTempSlider.changeSliderRange([startRange, endRange])
                self.colorTempDoubleSlider.changeSliderRange([startRange, endRange])

            def setupLightPrefsTab(self, selectedLight):
                # SET UP THE CUSTOM NAME TEXT BOX
                if availableLights[selectedLight][2] == "":
                    self.customName.setChecked(False)
                    self.customNameTF.setEnabled(False)
                    self.customNameTF.setText("") # set the "custom name" to nothing
                else:
                    self.customName.setChecked(True)
                    self.customNameTF.setEnabled(True)
                    self.customNameTF.setText(availableLights[selectedLight][2]) # set the "custom name" field to the custom name of this light

                # SET UP THE MINIMUM AND MAXIMUM TEXT BOXES
                defaultRange = getLightSpecs(availableLights[selectedLight][0].name, "temp")

                if availableLights[selectedLight][4] == defaultRange:
                    self.colorTempRange.setChecked(False)
                    self.colorTempRange_Min_TF.setEnabled(False)
                    self.colorTempRange_Max_TF.setEnabled(False)

                    self.colorTempRange_Min_TF.setText(str(defaultRange[0]))
                    self.colorTempRange_Max_TF.setText(str(defaultRange[1]))
                else:
                    self.colorTempRange.setChecked(True)
                    self.colorTempRange_Min_TF.setEnabled(True)
                    self.colorTempRange_Max_TF.setEnabled(True)
                    
                    self.colorTempRange_Min_TF.setText(str(availableLights[selectedLight][4][0]))
                    self.colorTempRange_Max_TF.setText(str(availableLights[selectedLight][4][1]))
                
                # IF THE OPTION TO SEND ONLY CCT MODE IS ENABLED, THEN ENABLE THAT CHECKBOX
                if availableLights[selectedLight][5] == True:
                    self.onlyCCTModeCheck.setChecked(True)
                else:
                    self.onlyCCTModeCheck.setChecked(False)

                self.checkLightPrefsEnables() # set up which fields on the panel are enabled

            def checkLightPrefsEnables(self): # enable/disable fields when clicking on checkboxes
                # allow/deny typing in the "custom name" field if the option is clicked
                if self.customName.isChecked():
                    self.customNameTF.setEnabled(True)
                else:
                    self.customNameTF.setEnabled(False)
                    self.customNameTF.setText("")

                # allow/deny typing in the "minmum" and "maximum" fields if the option is clicked
                if self.colorTempRange.isChecked():
                    self.colorTempRange_Min_TF.setEnabled(True)
                    self.colorTempRange_Max_TF.setEnabled(True)
                else:
                    selectedRows = self.selectedLights() # get the list of currently selected lights
                    defaultSettings = getLightSpecs(availableLights[selectedRows[0]][0].name, "temp")

                    self.colorTempRange_Min_TF.setText(str(defaultSettings[0]))
                    self.colorTempRange_Max_TF.setText(str(defaultSettings[1]))

                    self.colorTempRange_Min_TF.setEnabled(False)
                    self.colorTempRange_Max_TF.setEnabled(False)
                
            def checkLightPrefs(self): # check the new settings and save the custom file
                selectedRows = self.selectedLights() # get the list of currently selected lights

                # CHECK DEFAULT SETTINGS AGAINST THE CURRENT SETTINGS
                defaultSettings = getLightSpecs(availableLights[selectedRows[0]][0].name)

                if self.colorTempRange.isChecked():
                    newRange = [testValid("range_min", self.colorTempRange_Min_TF.text(), defaultSettings[1][0], 1000, 5600, True),
                                testValid("range_max", self.colorTempRange_Max_TF.text(), defaultSettings[1][1], 1000, 10000, True)]
                else:
                    newRange = defaultSettings[1]

                changedPrefs = 0 # number of how many preferences have changed

                if len(selectedRows) == 1: # if we have 1 selected light - which should never be false, as we can't use Prefs with more than 1
                    if self.customName.isChecked(): # if we're set to allow a custom name
                        if availableLights[selectedRows[0]][2] != self.customNameTF.text():
                            availableLights[selectedRows[0]][2] = self.customNameTF.text() # set this light's custom name to the text box
                            changedPrefs += 1 # add one to the preferences changed counter
                    else: # we're not supposed to set a custom name (so delete it)
                        if availableLights[selectedRows[0]][2] != "":
                            availableLights[selectedRows[0]][2] = "" # clear the old custom name if we've turned this off
                            changedPrefs += 1 # add one to the preferences changed counter

                    # IF A CUSTOM NAME IS SET UP FOR THIS LIGHT, THEN CHANGE THE TABLE TO REFLECT THAT
                    if availableLights[selectedRows[0]][2] != "":
                        self.setTheTable([availableLights[selectedRows[0]][2] + " (" + availableLights[selectedRows[0]][0].name + ")" "\n  [ʀssɪ: " + str(availableLights[selectedRows[0]][0].rssi) + " dBm]",
                                        "", "", ""], selectedRows[0])
                    else: # if there is no custom name, then reset the table to show that
                        self.setTheTable([availableLights[selectedRows[0]][0].name + "\n  [ʀssɪ: " + str(availableLights[selectedRows[0]][0].rssi) + " dBm]",
                                        "", "", ""], selectedRows[0])

                    if self.colorTempRange.isChecked(): # if we've asked to save a custom temperature range for this light
                        if availableLights[selectedRows[0]][4] != newRange: # change the range in the available lights table if they are different
                            if defaultSettings[1] != newRange:
                                availableLights[selectedRows[0]][4][0] = newRange[0]
                                availableLights[selectedRows[0]][4][1] = newRange[1]
                                changedPrefs += 1 # add one to the preferences changed counter
                            else: # the ranges are the same as the default range, so we're not modifying those values
                                printDebugString("You asked for a custom range of color temperatures, but didn't specify a custom range, so not changing!")
                    else: # if the custom temp checkbox is not clicked
                        if availableLights[selectedRows[0]][4] != defaultSettings[1]: # and the settings are not the defaults
                            availableLights[selectedRows[0]][4] = defaultSettings[1] # restore them to the defaults
                            changedPrefs += 1 # add one to the preferences changed counter

                    if availableLights[selectedRows[0]][5] != self.onlyCCTModeCheck.isChecked():
                        availableLights[selectedRows[0]][5] = self.onlyCCTModeCheck.isChecked() # if the option to send BRI and HUE separately is checked, then turn that on
                        changedPrefs += 1

                    if changedPrefs > 0:
                        # IF ALL THE SETTINGS ARE THE SAME AS THE DEFAULT, THEN DELETE THE PREFS FILE (IF IT EXISTS)
                        if defaultSettings[0] == self.customNameTF.text() and \
                        defaultSettings[1] == newRange and \
                        defaultSettings[2] == self.onlyCCTModeCheck.isChecked():
                            printDebugString("All the options that are currently set are the defaults for this light, so the preferences file will be deleted.")
                            saveLightPrefs(selectedRows[0], True) # delete the old prefs file
                        else:
                            saveLightPrefs(selectedRows[0]) # save the light settings to a special file
                    else:
                        printDebugString("You don't have any new preferences to save, so we aren't saving any!")

            def setupGlobalLightPrefsTab(self, setDefault=False):
                if setDefault == False:
                    self.findLightsOnStartup_check.setChecked(findLightsOnStartup)
                    self.autoConnectToLights_check.setChecked(autoConnectToLights)
                    self.printDebug_check.setChecked(printDebug)
                    self.rememberLightsOnExit_check.setChecked(rememberLightsOnExit)
                    self.rememberPresetsOnExit_check.setChecked(rememberPresetsOnExit)
                    self.maxNumOfAttempts_field.setText(str(maxNumOfAttempts))
                    self.acceptable_HTTP_IPs_field.setText("\n".join(acceptable_HTTP_IPs))
                    self.whiteListedMACs_field.setText("\n".join(whiteListedMACs))
                    self.SC_turnOffButton_field.setKeySequence(customKeys[0])
                    self.SC_turnOnButton_field.setKeySequence(customKeys[1])
                    self.SC_scanCommandButton_field.setKeySequence(customKeys[2])
                    self.SC_tryConnectButton_field.setKeySequence(customKeys[3])
                    self.SC_Tab_CCT_field.setKeySequence(customKeys[4])
                    self.SC_Tab_HSI_field.setKeySequence(customKeys[5])
                    self.SC_Tab_SCENE_field.setKeySequence(customKeys[6])
                    self.SC_Tab_PREFS_field.setKeySequence(customKeys[7])
                    self.SC_Dec_Bri_Small_field.setKeySequence(customKeys[8])
                    self.SC_Inc_Bri_Small_field.setKeySequence(customKeys[9])
                    self.SC_Dec_Bri_Large_field.setKeySequence(customKeys[10])
                    self.SC_Inc_Bri_Large_field.setKeySequence(customKeys[11])
                    self.SC_Dec_1_Small_field.setKeySequence(customKeys[12])
                    self.SC_Inc_1_Small_field.setKeySequence(customKeys[13])
                    self.SC_Dec_2_Small_field.setKeySequence(customKeys[14])
                    self.SC_Inc_2_Small_field.setKeySequence(customKeys[15])
                    self.SC_Dec_3_Small_field.setKeySequence(customKeys[16])
                    self.SC_Inc_3_Small_field.setKeySequence(customKeys[17])
                    self.SC_Dec_1_Large_field.setKeySequence(customKeys[18])
                    self.SC_Inc_1_Large_field.setKeySequence(customKeys[19])
                    self.SC_Dec_2_Large_field.setKeySequence(customKeys[20])
                    self.SC_Inc_2_Large_field.setKeySequence(customKeys[21])
                    self.SC_Dec_3_Large_field.setKeySequence(customKeys[22])
                    self.SC_Inc_3_Large_field.setKeySequence(customKeys[23])
                else: # if you clicked the RESET button, reset all preference values to their defaults
                    self.findLightsOnStartup_check.setChecked(True)
                    self.autoConnectToLights_check.setChecked(True)
                    self.printDebug_check.setChecked(True)
                    self.rememberLightsOnExit_check.setChecked(False)
                    self.rememberPresetsOnExit_check.setChecked(True)
                    self.maxNumOfAttempts_field.setText("6")
                    self.acceptable_HTTP_IPs_field.setText("\n".join(["127.0.0.1", "192.168.", "10."]))
                    self.whiteListedMACs_field.setText("")
                    self.SC_turnOffButton_field.setKeySequence("Ctrl+PgDown")
                    self.SC_turnOnButton_field.setKeySequence("Ctrl+PgUp")
                    self.SC_scanCommandButton_field.setKeySequence("Ctrl+Shift+S")
                    self.SC_tryConnectButton_field.setKeySequence("Ctrl+Shift+C")
                    self.SC_Tab_CCT_field.setKeySequence("Alt+1")
                    self.SC_Tab_HSI_field.setKeySequence("Alt+2")
                    self.SC_Tab_SCENE_field.setKeySequence("Alt+3")
                    self.SC_Tab_PREFS_field.setKeySequence("Alt+4")
                    self.SC_Dec_Bri_Small_field.setKeySequence("/")
                    self.SC_Inc_Bri_Small_field.setKeySequence("*")
                    self.SC_Dec_Bri_Large_field.setKeySequence("Ctrl+/")
                    self.SC_Inc_Bri_Large_field.setKeySequence("Ctrl+*")
                    self.SC_Dec_1_Small_field.setKeySequence("7")
                    self.SC_Inc_1_Small_field.setKeySequence("9")
                    self.SC_Dec_2_Small_field.setKeySequence("4")
                    self.SC_Inc_2_Small_field.setKeySequence("6")
                    self.SC_Dec_3_Small_field.setKeySequence("1")
                    self.SC_Inc_3_Small_field.setKeySequence("3")
                    self.SC_Dec_1_Large_field.setKeySequence("Ctrl+7")
                    self.SC_Inc_1_Large_field.setKeySequence("Ctrl+9")
                    self.SC_Dec_2_Large_field.setKeySequence("Ctrl+4")
                    self.SC_Inc_2_Large_field.setKeySequence("Ctrl+6")
                    self.SC_Dec_3_Large_field.setKeySequence("Ctrl+1")
                    self.SC_Inc_3_Large_field.setKeySequence("Ctrl+3")

            def saveGlobalPrefs(self):
                # change these global values to the new values in Prefs
                global customKeys, autoConnectToLights, printDebug, rememberLightsOnExit, \
                    rememberPresetsOnExit, maxNumOfAttempts, acceptable_HTTP_IPs, whiteListedMACs

                finalPrefs = [] # list of final prefs to merge together at the end

                if not self.findLightsOnStartup_check.isChecked(): # this option is usually on, so only add on false
                    finalPrefs.append("findLightsOnStartup=0")
                
                if not self.autoConnectToLights_check.isChecked(): # this option is usually on, so only add on false
                    autoConnectToLights = False
                    finalPrefs.append("autoConnectToLights=0")
                else:
                    autoConnectToLights = True
                
                if not self.printDebug_check.isChecked(): # this option is usually on, so only add on false
                    printDebug = False
                    finalPrefs.append("printDebug=0")
                else:
                    printDebug = True
                
                if self.rememberLightsOnExit_check.isChecked(): # this option is usually off, so only add on true
                    rememberLightsOnExit = True
                    finalPrefs.append("rememberLightsOnExit=1")
                else:
                    rememberLightsOnExit = False

                if not self.rememberPresetsOnExit_check.isChecked(): # this option is usually on, so only add if false
                    rememberPresetsOnExit = False
                    finalPrefs.append("rememberPresetsOnExit=0")
                else:
                    rememberPresetsOnExit = True
                
                if self.maxNumOfAttempts_field.text() != "6": # the default for this option is 6 attempts
                    maxNumOfAttempts = int(self.maxNumOfAttempts_field.text())
                    finalPrefs.append("maxNumOfAttempts=" + self.maxNumOfAttempts_field.text())
                else:
                    maxNumOfAttempts = 6

                # FIGURE OUT IF THE HTTP IP ADDRESSES HAVE CHANGED
                returnedList_HTTP_IPs = self.acceptable_HTTP_IPs_field.toPlainText().split("\n")
                
                if returnedList_HTTP_IPs != ["127.0.0.1", "192.168.", "10."]: # if the list of HTTP IPs have changed
                    acceptable_HTTP_IPs = returnedList_HTTP_IPs # change the global HTTP IPs available
                    finalPrefs.append("acceptable_HTTP_IPs=" + ";".join(acceptable_HTTP_IPs)) # add the new ones to the preferences
                else:
                    acceptable_HTTP_IPs = ["127.0.0.1", "192.168.", "10."] # if we reset the IPs, then re-reset the parameter

                # ADD WHITELISTED LIGHTS TO PREFERENCES IF THEY EXIST
                returnedList_whiteListedMACs = self.whiteListedMACs_field.toPlainText().replace(" ", "").split("\n") # remove spaces and split on newlines

                if returnedList_whiteListedMACs[0] != "": # if we have any MAC addresses specified
                    whiteListedMACs = returnedList_whiteListedMACs # then set the list to the addresses specified
                    finalPrefs.append("whiteListedMACs=" + ";".join(whiteListedMACs)) # add the new addresses to the preferences
                else:
                    whiteListedMACs = [] # or clear the list
                
                # SET THE NEW KEYBOARD SHORTCUTS TO THE VALUES IN PREFERENCES
                customKeys[0] = self.SC_turnOffButton_field.keySequence().toString()
                customKeys[1] = self.SC_turnOnButton_field.keySequence().toString()
                customKeys[2] = self.SC_scanCommandButton_field.keySequence().toString()
                customKeys[3] = self.SC_tryConnectButton_field.keySequence().toString()
                customKeys[4] = self.SC_Tab_CCT_field.keySequence().toString()
                customKeys[5] = self.SC_Tab_HSI_field.keySequence().toString()
                customKeys[6] = self.SC_Tab_SCENE_field.keySequence().toString()
                customKeys[7] = self.SC_Tab_PREFS_field.keySequence().toString()
                customKeys[8] = self.SC_Dec_Bri_Small_field.keySequence().toString()
                customKeys[9] = self.SC_Inc_Bri_Small_field.keySequence().toString()
                customKeys[10] = self.SC_Dec_Bri_Large_field.keySequence().toString()
                customKeys[11] = self.SC_Inc_Bri_Large_field.keySequence().toString()
                customKeys[12] = self.SC_Dec_1_Small_field.keySequence().toString()
                customKeys[13] = self.SC_Inc_1_Small_field.keySequence().toString()
                customKeys[14] = self.SC_Dec_2_Small_field.keySequence().toString()
                customKeys[15] = self.SC_Inc_2_Small_field.keySequence().toString()
                customKeys[16] = self.SC_Dec_3_Small_field.keySequence().toString()
                customKeys[17] = self.SC_Inc_3_Small_field.keySequence().toString()
                customKeys[18] = self.SC_Dec_1_Large_field.keySequence().toString()
                customKeys[19] = self.SC_Inc_1_Large_field.keySequence().toString()
                customKeys[20] = self.SC_Dec_2_Large_field.keySequence().toString()
                customKeys[21] = self.SC_Inc_2_Large_field.keySequence().toString()
                customKeys[22] = self.SC_Dec_3_Large_field.keySequence().toString()
                customKeys[23] = self.SC_Inc_3_Large_field.keySequence().toString()

                self.setupShortcutKeys() # change shortcut key assignments to the new values in prefs

                if customKeys[0] != "Ctrl+PgDown": 
                    finalPrefs.append("SC_turnOffButton=" + customKeys[0])
                
                if customKeys[1] != "Ctrl+PgUp":
                    finalPrefs.append("SC_turnOnButton=" + customKeys[1])
                
                if customKeys[2] != "Ctrl+Shift+S":
                    finalPrefs.append("SC_scanCommandButton=" + customKeys[2])
                
                if customKeys[3] != "Ctrl+Shift+C":
                    finalPrefs.append("SC_tryConnectButton=" + customKeys[3])
                
                if customKeys[4] != "Alt+1":
                    finalPrefs.append("SC_Tab_CCT=" + customKeys[4])
                
                if customKeys[5] != "Alt+2":
                    finalPrefs.append("SC_Tab_HSI=" + customKeys[5])
                
                if customKeys[6] != "Alt+3":
                    finalPrefs.append("SC_Tab_SCENE=" + customKeys[6])
                
                if customKeys[7] != "Alt+4":
                    finalPrefs.append("SC_Tab_PREFS=" + customKeys[7])
                
                if customKeys[8] != "/":
                    finalPrefs.append("SC_Dec_Bri_Small=" + customKeys[8])
                
                if customKeys[9] != "*":
                    finalPrefs.append("SC_Inc_Bri_Small=" + customKeys[9])
                
                if customKeys[10] != "Ctrl+/":
                    finalPrefs.append("SC_Dec_Bri_Large=" + customKeys[10])
                
                if customKeys[11] != "Ctrl+*":
                    finalPrefs.append("SC_Inc_Bri_Large=" + customKeys[11])
                
                if customKeys[12] != "7":
                    finalPrefs.append("SC_Dec_1_Small=" + customKeys[12])
                
                if customKeys[13] != "9":
                    finalPrefs.append("SC_Inc_1_Small=" + customKeys[13])
                
                if customKeys[14] != "4":
                    finalPrefs.append("SC_Dec_2_Small=" + customKeys[14])
                
                if customKeys[15] != "6":
                    finalPrefs.append("SC_Inc_2_Small=" + customKeys[15])
                
                if customKeys[16] != "1":
                    finalPrefs.append("SC_Dec_3_Small=" + customKeys[16])
                
                if customKeys[17] != "3":
                    finalPrefs.append("SC_Inc_3_Small=" + customKeys[17])
                
                if customKeys[18] != "Ctrl+7":
                    finalPrefs.append("SC_Dec_1_Large=" + customKeys[18])
                
                if customKeys[19] != "Ctrl+9":
                    finalPrefs.append("SC_Inc_1_Large=" + customKeys[19])
                
                if customKeys[20] != "Ctrl+4":
                    finalPrefs.append("SC_Dec_2_Large=" + customKeys[20])
                
                if customKeys[21] != "Ctrl+6":
                    finalPrefs.append("SC_Inc_2_Large=" + customKeys[21])
                
                if customKeys[22] != "Ctrl+1":
                    finalPrefs.append("SC_Dec_3_Large=" + customKeys[22])
                
                if customKeys[23] != "Ctrl+3":
                    finalPrefs.append("SC_Inc_3_Large=" + customKeys[23])

                # CARRY "HIDDEN" DEBUGGING OPTIONS TO PREFERENCES FILE
                if enableTabsOnLaunch == True:
                    finalPrefs.append("enableTabsOnLaunch=1")
                
                if len(finalPrefs) > 0: # if we actually have preferences to save...
                    with open(globalPrefsFile, mode="w", encoding="utf-8") as prefsFileToWrite:
                        prefsFileToWrite.write(("\n").join(finalPrefs)) # then write them to the prefs file

                    # PRINT THIS INFORMATION WHETHER DEBUG OUTPUT IS TURNED ON OR NOT
                    print(f"New global preferences saved in {globalPrefsFile} - here is the list:")

                    for a in range(len(finalPrefs)):
                        print(f" > {finalPrefs[a]}")  # iterate through the list of preferences and show the new value(s) you set
                else: # there are no preferences to save, so clean up the file (if it exists)
                    print("There are no preferences to save (all preferences are currently set to their default values).")
                    
                    if os.path.exists(globalPrefsFile): # if a previous preferences file exists
                        print("Since all preferences are set to their defaults, we are deleting the NeewerLite-Python.prefs file.")
                        os.remove(globalPrefsFile) # ...delete it!

            def setupShortcutKeys(self):
                self.SC_turnOffButton.setKey(QKeySequence(customKeys[0]))
                self.SC_turnOnButton.setKey(QKeySequence(customKeys[1]))
                self.SC_scanCommandButton.setKey(QKeySequence(customKeys[2]))
                self.SC_tryConnectButton.setKey(QKeySequence(customKeys[3]))
                self.SC_Tab_CCT.setKey(QKeySequence(customKeys[4]))
                self.SC_Tab_HSI.setKey(QKeySequence(customKeys[5]))
                self.SC_Tab_SCENE.setKey(QKeySequence(customKeys[6]))
                self.SC_Tab_PREFS.setKey(QKeySequence(customKeys[7]))
                self.SC_Dec_Bri_Small.setKey(QKeySequence(customKeys[8]))
                self.SC_Inc_Bri_Small.setKey(QKeySequence(customKeys[9]))
                self.SC_Dec_Bri_Large.setKey(QKeySequence(customKeys[10]))
                self.SC_Inc_Bri_Large.setKey(QKeySequence(customKeys[11]))

                # IF THERE ARE CUSTOM KEYS SET UP FOR THE SMALL INCREMENTS, SET THEM HERE (AS THE NUMPAD KEYS WILL BE TAKEN AWAY IN THAT INSTANCE):
                if customKeys[12] != "7":
                    self.SC_Dec_1_Small.setKey(QKeySequence(customKeys[12]))
                else: # if we changed back to default, clear the key assignment if there was one before
                    self.SC_Dec_1_Small.setKey(QKeySequence())

                if customKeys[13] != "9":
                    self.SC_Inc_1_Small.setKey(QKeySequence(customKeys[13]))
                else:
                    self.SC_Inc_1_Small.setKey(QKeySequence())

                if customKeys[14] != "4":
                    self.SC_Dec_2_Small.setKey(QKeySequence(customKeys[14]))
                else:
                    self.SC_Dec_2_Small.setKey(QKeySequence())
                
                if customKeys[15] != "6":
                    self.SC_Inc_2_Small.setKey(QKeySequence(customKeys[15]))
                else:
                    self.SC_Inc_2_Small.setKey(QKeySequence())

                if customKeys[16] != "1":
                    self.SC_Dec_3_Small.setKey(QKeySequence(customKeys[16]))
                else:
                    self.SC_Dec_3_Small.setKey(QKeySequence())

                if customKeys[17] != "3":
                    self.SC_Inc_3_Small.setKey(QKeySequence(customKeys[17]))
                else:
                    self.SC_Inc_3_Small.setKey(QKeySequence())
                    
                self.SC_Dec_1_Large.setKey(QKeySequence(customKeys[18]))
                self.SC_Inc_1_Large.setKey(QKeySequence(customKeys[19]))
                self.SC_Dec_2_Large.setKey(QKeySequence(customKeys[20]))
                self.SC_Inc_2_Large.setKey(QKeySequence(customKeys[21]))
                self.SC_Dec_3_Large.setKey(QKeySequence(customKeys[22]))
                self.SC_Inc_3_Large.setKey(QKeySequence(customKeys[23]))

            # CHECK TO SEE WHETHER OR NOT TO ENABLE/DISABLE THE "Connect" BUTTON OR CHANGE THE PREFS TAB
            def selectionChanged(self):
                selectedRows = self.selectedLights(True) # get the list of currently selected lights

                if len(selectedRows[0]) > 0: # if we have a selection
                    self.tryConnectButton.setEnabled(True) # if we have light(s) selected in the table, then enable the "Connect" button

                    if len(selectedRows[0]) == 1: # we have exactly one light selected
                        self.ColorModeTabWidget.setTabEnabled(3, True) # enable the "Preferences" tab for this light

                        # SWITCH THE TURN ON/OFF BUTTONS ON, AND CHANGE TEXT TO SINGLE BUTTON TEXT
                        self.turnOffButton.setText("Turn Light Off")
                        self.turnOffButton.setEnabled(True)
                        self.turnOnButton.setText("Turn Light On")
                        self.turnOnButton.setEnabled(True)

                        self.ColorModeTabWidget.setTabEnabled(0, True)

                        if availableLights[selectedRows[0][0]][5] == True: # if this light is CCT only, then disable the HSI and ANM tabs
                            self.ColorModeTabWidget.setTabEnabled(1, False) # disable the HSI mode tab
                            self.ColorModeTabWidget.setTabEnabled(2, False) # disable the ANM/SCENE tab
                        else: # we can use HSI and ANM/SCENE modes, so enable those tabs
                            self.ColorModeTabWidget.setTabEnabled(1, True) # enable the HSI mode tab
                            self.ColorModeTabWidget.setTabEnabled(2, True) # enable the ANM/SCENE tab

                        if selectedRows[1] > 0: # if we have an Infinity or Infinity-style light
                            self.GMSlider.setVisible(True)
                        else:
                            self.GMSlider.setVisible(False)

                        currentlySelectedRow = selectedRows[0][0] # get the row index of the 1 selected item
                        self.checkLightTab(currentlySelectedRow) # if we're on CCT, check to see if this light can use extended values + on Prefs, update Prefs

                        # RECALL LAST SENT SETTING FOR THIS PARTICULAR LIGHT, IF A SETTING EXISTS
                        if availableLights[currentlySelectedRow][3] != []: # if the last set parameters aren't empty
                            if availableLights[currentlySelectedRow][6] != False: # if the light is listed as being turned ON
                                sendValue = translateByteString(availableLights[currentlySelectedRow][3]) # make the current "sendValue" the last set parameter so it doesn't re-send it on re-load
                                sendValue["infinityMode"] = selectedRows[1]
                                self.setUpGUI(**sendValue)
                            else:
                                self.ColorModeTabWidget.setCurrentIndex(0) # switch to the CCT tab if the light is off and there ARE prior parameters
                        else:
                            self.ColorModeTabWidget.setCurrentIndex(0) # switch to the CCT tab if there are no prior parameters
                    else: # we have multiple lights selected
                        # SWITCH THE TURN ON/OFF BUTTONS ON, AND CHANGE TEXT TO MULTIPLE LIGHTS TEXT
                        self.turnOffButton.setText("Turn Light(s) Off")
                        self.turnOffButton.setEnabled(True)
                        self.turnOnButton.setText("Turn Light(s) On")
                        self.turnOnButton.setEnabled(True)

                        # ENABLE ALL OF THE TABS BELOW
                        self.ColorModeTabWidget.setTabEnabled(0, True)
                        self.ColorModeTabWidget.setTabEnabled(1, True) # enable the "HSI" mode tab
                        self.ColorModeTabWidget.setTabEnabled(2, True) # enable the "ANM/SCENE" mode tab
                        self.ColorModeTabWidget.setTabEnabled(3, False) # disable the "Preferences" tab, as we have multiple lights selected

                        if selectedRows[1] == True:
                            self.GMSlider.setVisible(True)
                        else:
                            self.GMSlider.setVisible(False)
                else: # the selection has been cleared or there are no lights to select
                    currentTab = self.ColorModeTabWidget.currentIndex() # get the currently selected tab (so when we disable the tabs, we stick on the current one)
                    self.tryConnectButton.setEnabled(False) # if we have no lights selected, disable the Connect button

                    # SWITCH THE TURN ON/OFF BUTTONS OFF, AND CHANGE TEXT TO GENERIC TEXT
                    self.turnOffButton.setText("Turn Light(s) Off")
                    self.turnOffButton.setEnabled(False)
                    self.turnOnButton.setText("Turn Light(s) On")
                    self.turnOnButton.setEnabled(False)

                    self.ColorModeTabWidget.setTabEnabled(0, False) # disable the "CCT" mode tab
                    self.ColorModeTabWidget.setTabEnabled(1, False) # disable the "HSI" mode tab
                    self.ColorModeTabWidget.setTabEnabled(2, False) # disable the "ANM/SCENE" mode tab
                    self.ColorModeTabWidget.setTabEnabled(3, False) # disable the "Light Preferences" tab, as we have no lights selected

                    if currentTab < 2:
                        self.ColorModeTabWidget.setCurrentIndex(currentTab) # disable the tabs, but don't switch (unless ANM or Preferences)
                    else:
                        self.ColorModeTabWidget.setCurrentIndex(0) # if we're on Prefs, then switch to the CCT tab

                    self.checkLightTab() # check to see if we're on the CCT tab - if we are, then restore order

            # SET UP THE GUI FOR USING INFINITY MODE/SWITCHING EFFECTS LIST
            def setInfinityMode(self, infinityMode = 0):
                countOfCurrentEffects = self.effectChooser.count()

                if infinityMode == 0:
                    if countOfCurrentEffects == 0 or countOfCurrentEffects == 18:
                        self.effectChooser.clear()
                        self.effectChooser.addItems(["1 - Cop Car", "2 - Ambulance", "3 - Fire Engine",
                                                "4 - Fireworks", "5 - Party", "6 - Candlelight",
                                                "7 - Lightning", "8 - Paparazzi", "9 - TV Screen"])
                else:
                    if countOfCurrentEffects == 0 or countOfCurrentEffects == 9:
                        self.effectChooser.clear()
                        self.effectChooser.addItems(["1 - Lightning", "2 - Paparazzi", "3 - Defective Bulb",
                                                "4 - Explosion", "5 - Welding", "6 - CCT Flash",
                                                "7 - Hue Flash", "8 - CCT Pulse", "9 - Hue Pulse",
                                                "10 - Cop Car", "11 - Candlelight", "12 - Hue Loop",
                                                "13 - CCT Loop", "14 - INT Loop (CCT)", "14 - INT Loop (HSI)",
                                                "15 - TV Screen", "16 - Fireworks", "17 - Party"])

            # ADD A LIGHT TO THE TABLE VIEW
            def setTheTable(self, infoArray, rowToChange = -1):
                if rowToChange == -1:
                    currentRow = self.lightTable.rowCount()
                    self.lightTable.insertRow(currentRow) # if rowToChange is not specified, then we'll make a new row at the end
                    self.lightTable.setItem(currentRow, 0, QTableWidgetItem())
                    self.lightTable.setItem(currentRow, 1, QTableWidgetItem())
                    self.lightTable.setItem(currentRow, 2, QTableWidgetItem())
                    self.lightTable.setItem(currentRow, 3, QTableWidgetItem())
                else:
                    currentRow = rowToChange # change data for the specified row

                # THIS SECTION BELOW LIMITS UPDATING THE TABLE **ONLY** IF THE DATA SUPPLIED IS DIFFERENT THAN IT WAS ORIGINALLY
                if infoArray[0] != "": # the name of the light
                    if rowToChange == -1 or (rowToChange != -1 and infoArray[0] != self.returnTableInfo(rowToChange, 0)):
                        self.lightTable.item(currentRow, 0).setText(infoArray[0])
                if infoArray[1] != "": # the MAC address of the light
                    if rowToChange == -1 or (rowToChange != -1 and infoArray[1] != self.returnTableInfo(rowToChange, 1)):
                        self.lightTable.item(currentRow, 1).setText(infoArray[1])
                if infoArray[2] != "": # the Linked status of the light
                    if rowToChange == -1 or (rowToChange != -1 and infoArray[2] != self.returnTableInfo(rowToChange, 2)):
                        self.lightTable.item(currentRow, 2).setText(infoArray[2])
                if infoArray[3] != "": # the current status message of the light
                    if rowToChange == -1 or (rowToChange != -1 and infoArray[2] != self.returnTableInfo(rowToChange, 3)):
                        self.lightTable.item(currentRow, 3).setText(infoArray[3])
                self.lightTable.resizeRowsToContents()

    except Exception as e:
        logging.exception(e)