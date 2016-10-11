import os
import csv, re, numpy, json, ast, re
import shutil, datetime, logging
import ctk, vtk, qt, slicer
from collections import OrderedDict



from slicer.ScriptedLoadableModule import *
from SlicerProstateUtils.helpers import WatchBoxAttribute, BasicInformationWatchBox, DICOMBasedInformationWatchBox, IncomingDataWindow
from SlicerProstateUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin, ParameterNodeObservationMixin
from SlicerProstateUtils.constants import DICOMTAGS, COLOR, STYLE, FileExtension
from SlicerProstateUtils.events import SlicerProstateEvents

class SlicerCaseManager(ScriptedLoadableModule):
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SlicerCaseManager"
    self.parent.categories = ["Radiology"]
    self.parent.dependencies = ["SlicerProstate"]
    self.parent.contributors = ["Christian Herz (SPL)","Longquan Chen(SPL)"]
    self.parent.helpText = """A common module for case management in Slicer"""
    self.parent.acknowledgementText = """Surgical Planning Laboratory, Brigham and Women's Hospital, Harvard
                                        Medical School, Boston, USA This work was supported in part by the National
                                        Institutes of Health through grants R01 EB020667, U24 CA180918,
                                        R01 CA111288 and P41 EB015898. The code is originated from the module SliceTracker"""

class SlicerCaseManagerWidget(ModuleWidgetMixin, ScriptedLoadableModuleWidget):
  @property
  def caseRootDir(self):
    return self.casesRootDirectoryButton.directory

  @caseRootDir.setter
  def caseRootDir(self, path):
    try:
      exists = os.path.exists(path)
    except TypeError:
      exists = False
    self.setSetting('CasesRootLocation', path if exists else None)
    self.casesRootDirectoryButton.text = self.truncatePath(path) if exists else "Choose output directory"
    self.casesRootDirectoryButton.toolTip = path
    self.openCaseButton.enabled = exists
    self.createNewCaseButton.enabled = exists
  
  @property
  def caseDirectoryList(self):
    return self._caseDirectoryList

  @caseDirectoryList.setter
  def caseDirectoryList(self,list):
    self._caseDirectoryList = list      
  
  @property
  def preopDataDir(self):
    return self._preopDataDir

  @preopDataDir.setter
  def preopDataDir(self, path):
    self._preopDataDir = path
    if path is None:
      return
    if os.path.exists(path):
      self.loadPreopData()
  
  @property
  def mpReviewPreprocessedOutput(self):
    return os.path.join(self.currentCaseDirectory, "mpReviewPreprocessed") if self.currentCaseDirectory else None

  @property
  def preopDICOMDataDirectory(self):
    return os.path.join(self.currentCaseDirectory, "DICOM", "Preop") if self.currentCaseDirectory else None

  @property
  def intraopDICOMDataDirectory(self):
    return os.path.join(self.currentCaseDirectory, "DICOM", "Intraop") if self.currentCaseDirectory else None

  @property
  def outputDir(self):
    return os.path.join(self.currentCaseDirectory, "SliceTrackerOutputs")

  @property
  def currentCaseDirectory(self):
    return self._currentCaseDirectory

  @property
  def currentTargets(self):
    return self._currentTargets

  @currentTargets.setter
  def currentTargets(self, targets):
    self._currentTargets = targets
    self.targetTableModel.targetList = targets
    if not targets:
      self.targetTableModel.coverProstateTargetList = None
    else:
      coverProstate = self.registrationResults.getMostRecentApprovedCoverProstateRegistration()
      if coverProstate:
        self.targetTableModel.coverProstateTargetList = coverProstate.approvedTargets
    self.targetTable.enabled = targets is not None

  @currentCaseDirectory.setter
  def currentCaseDirectory(self, path):
    self._currentCaseDirectory = path
    valid = path is not None
    self.closeCaseButton.enabled = valid
    if not valid:
      self.caseWatchBox.reset()

  @property
  def generatedOutputDirectory(self):
    return self._generatedOutputDirectory

  @generatedOutputDirectory.setter
  def generatedOutputDirectory(self, path):
    if not os.path.exists(path):
      self.logic.createDirectory(path)
    exists = os.path.exists(path)
    self._generatedOutputDirectory = path if exists else ""
    self.completeCaseButton.enabled = exists and not self.logic.caseCompleted
  
  @property
  def mainGUIGroupBox(self):
    return self._mainGUIGroupBox

  @property
  def collapsibleDirectoryConfigurationArea(self):
    return self._collapsibleDirectoryConfigurationArea
  
  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.logic = SlicerCaseManagerLogic()
    self.modulePath = os.path.dirname(slicer.util.modulePath(self.moduleName))
    self._currentCaseDirectory = None
    self._caseDirectoryList = {}
    self.caseDirectoryList = {"DICOM/Preop", "Results"}

  def setup(self):
    #ScriptedLoadableModuleWidget.setup(self)

    self._mainGUIGroupBox = qt.QGroupBox()
    self._collapsibleDirectoryConfigurationArea = ctk.ctkCollapsibleButton()
    self.mainGUIGroupBoxLayout = qt.QGridLayout()
    self._mainGUIGroupBox.setLayout(self.mainGUIGroupBoxLayout)
    self.createNewCaseButton = self.createButton("New case")
    self.openCaseButton = self.createButton("Open case")
    self.closeCaseButton = self.createButton("Close case", toolTip="Close case without completing it", enabled=False)
    self.completeCaseButton = self.createButton('Case completed', enabled=True)
    self.mainGUIGroupBoxLayout.addWidget(self.createNewCaseButton, 1, 0)
    self.mainGUIGroupBoxLayout.addWidget(self.openCaseButton, 1, 1)
    self.mainGUIGroupBoxLayout.addWidget(self.completeCaseButton, 1, 2)
    
    self.createPatientWatchBox()
    #self.createIntraopWatchBox()
    self.createCaseInformationArea()
    self.setupConnections()
    self.layout.addWidget(self._mainGUIGroupBox)

  
  def updateOutputFolder(self):
    if os.path.exists(self.generatedOutputDirectory):
      return
    if self.patientWatchBox.getInformation("PatientID") != '' \
            and self.intraopWatchBox.getInformation("StudyDate") != '':
      if self.outputDir and not os.path.exists(self.outputDir):
        self.logic.createDirectory(self.outputDir)
      finalDirectory = self.patientWatchBox.getInformation("PatientID") + "-biopsy-" + \
                       str(qt.QDate().currentDate()) + "-" + qt.QTime().currentTime().toString().replace(":", "")
      self.generatedOutputDirectory = os.path.join(self.outputDir, finalDirectory, "MRgBiopsy")
    else:
      self.generatedOutputDirectory = ""

  def createPatientWatchBox(self):
    self.patientWatchBoxInformation = [WatchBoxAttribute('PatientID', 'Patient ID: ', DICOMTAGS.PATIENT_ID),
                                       WatchBoxAttribute('PatientName', 'Patient Name: ', DICOMTAGS.PATIENT_NAME),
                                       WatchBoxAttribute('DOB', 'Date of Birth: ', DICOMTAGS.PATIENT_BIRTH_DATE),
                                       WatchBoxAttribute('StudyDate', 'Preop Study Date: ', DICOMTAGS.STUDY_DATE)]
    self.patientWatchBox = DICOMBasedInformationWatchBox(self.patientWatchBoxInformation)
    self.layout.addWidget(self.patientWatchBox)
  
  def createIntraopWatchBox(self):
    intraopWatchBoxInformation = [WatchBoxAttribute('StudyDate', 'Intraop Study Date: ', DICOMTAGS.STUDY_DATE),
                                  WatchBoxAttribute('CurrentSeries', 'Current Series: ', [DICOMTAGS.SERIES_NUMBER,
                                                                                          DICOMTAGS.SERIES_DESCRIPTION])]
    self.intraopWatchBox = DICOMBasedInformationWatchBox(intraopWatchBoxInformation)
    self.registrationDetailsButton = self.createButton("", styleSheet="border:none;",
                                                       maximumWidth=16)
    self.layout.addWidget(self.intraopWatchBox)
  
  def createCaseInformationArea(self):
    self.casesRootDirectoryButton = self.createDirectoryButton(text="Choose cases root location",
                                                               caption="Choose cases root location",
                                                               directory=self.getSetting('CasesRootLocation'))
    self.createCaseWatchBox()
    self._collapsibleDirectoryConfigurationArea.collapsed = True
    self._collapsibleDirectoryConfigurationArea.text = "Case Directory Settings"
    self.directoryConfigurationLayout = qt.QGridLayout(self._collapsibleDirectoryConfigurationArea)
    self.directoryConfigurationLayout.addWidget(qt.QLabel("Cases Root Directory"), 1, 0, 1, 1)
    self.directoryConfigurationLayout.addWidget(self.casesRootDirectoryButton, 1, 1, 1, 1)
    self.directoryConfigurationLayout.addWidget(self.caseWatchBox, 2, 0, 1, qt.QSizePolicy.ExpandFlag)
    self.layout.addWidget(self._collapsibleDirectoryConfigurationArea)

  def createCaseWatchBox(self):
    watchBoxInformation = [WatchBoxAttribute('CurrentCaseDirectory', 'Directory')]
    self.caseWatchBox = BasicInformationWatchBox(watchBoxInformation, title="Current Case")


  def setupConnections(self):
    self.createNewCaseButton.clicked.connect(self.onCreateNewCaseButtonClicked)
    self.openCaseButton.clicked.connect(self.onOpenCaseButtonClicked)
    self.casesRootDirectoryButton.directoryChanged.connect(lambda: setattr(self, "caseRootDir",
                                                                           self.casesRootDirectoryButton.directory))
    self.completeCaseButton.clicked.connect(self.onCompleteCaseButtonClicked)
    self.closeCaseButton.clicked.connect(self.clearData)

  def onCreateNewCaseButtonClicked(self):
    if not self.checkAndWarnUserIfCaseInProgress():
      return
    self.clearData()
    self.caseDialog = NewCaseSelectionNameWidget(self.caseRootDir)
    selectedButton = self.caseDialog.exec_()
    if selectedButton == qt.QMessageBox.Ok:
      newCaseDirectory = self.caseDialog.newCaseDirectory
      os.mkdir(newCaseDirectory)
      for direcory in self.caseDirectoryList:
        subDirectory = direcory.split("/")
        for iIndex in range(len(subDirectory)+1):
          fullPath = ""
          for jIndex in range(iIndex):
            fullPath = os.path.join(fullPath,subDirectory[jIndex])
          if not os.path.exists(os.path.join(newCaseDirectory,fullPath)): 
            os.mkdir(os.path.join(newCaseDirectory,fullPath))      
      self.currentCaseDirectory = newCaseDirectory      
      self.startPreopDICOMReceiver()
  
  def onCompleteCaseButtonClicked(self):
    self.logic.caseCompleted = True
    shutil.rmtree(os.path.join(self.currentCaseDirectory, "Results"))
    slicer.util.saveScene(os.path.join(self.currentCaseDirectory, "Results"))
    self.clearData()
  
  def onOpenCaseButtonClicked(self):
    if not self.checkAndWarnUserIfCaseInProgress():
      return
    slicer.mrmlScene.Clear(0)
    path = qt.QFileDialog.getExistingDirectory(self.parent.window(), "Select Case Directory", self.caseRootDir)
    if not path:
      return
    self.currentCaseDirectory = path
    if (not os.path.exists(os.path.join(path, "DICOM", "Preop")) ) or (not os.path.exists(os.path.join(path, "Results")) ):
      slicer.util.warningDisplay("The selected case directory seems not to be valid", windowTitle="")
      self.clearData()
    else:
      #slicer.util.loadVolume(self.preopImagePath, returnNode=True)
      slicer.util.loadScene(os.path.join(path, "Results","Results.mrml"))

  def checkAndWarnUserIfCaseInProgress(self):
    proceed = True
    if self.currentCaseDirectory is not None:
      if not slicer.util.confirmYesNoDisplay("Current case will be closed. Do you want to proceed?"):
        proceed = False
    return proceed

  def startPreopDICOMReceiver(self):
    self.preopTransferWindow = IncomingDataWindow(incomingDataDirectory=self.preopDICOMDataDirectory,
                                                  skipText="No Preop available")
    self.preopTransferWindow.addObserver(SlicerProstateEvents.IncomingDataSkippedEvent,
                                         self.continueWithoutPreopData)
    self.preopTransferWindow.addObserver(SlicerProstateEvents.IncomingDataCanceledEvent,
                                         self.onPreopTransferMessageBoxCanceled)
    self.preopTransferWindow.addObserver(SlicerProstateEvents.IncomingDataReceiveFinishedEvent,
                                         self.startPreProcessingPreopData)
    self.preopTransferWindow.show()
  
  def continueWithoutPreopData(self, caller, event):
    self.cleanupPreopDICOMReceiver()
    self.simulatePreopPhaseButton.enabled = False
    self.simulateIntraopPhaseButton.enabled = True
  
  def cleanupPreopDICOMReceiver(self):
    if self.preopTransferWindow:
      self.preopTransferWindow.hide()
      self.preopTransferWindow.removeObservers()
      self.preopTransferWindow = None
  
  def onPreopTransferMessageBoxCanceled(self,caller, event):
    self.clearData()
    pass

  def startPreProcessingPreopData(self, caller=None, event=None):
    self.cleanupPreopDICOMReceiver()
    ## to do, use mpreview to process the dicom series
    ## here it only load the volumes in the directory
    for subdir, dirs, files in os.walk(self.preopDICOMDataDirectory):
      for file in files:
        if not file[0] == ".":
          slicer.util.loadVolume(os.path.join(self.preopDICOMDataDirectory, file))
    
    pass


  def loadCaseData(self):

    pass
  
  def clearData(self):
    pass

class SlicerCaseManagerLogic(ScriptedLoadableModuleLogic):
  
  @property
  def caseCompleted(self):
    return self._caseCompleted

  @caseCompleted.setter
  def caseCompleted(self, value):
    self._caseCompleted = value
    if value is True:
      self.stopSmartDICOMReceiver()
  
  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    self.caseCompleted = True
    self.DEFAULT_JSON_FILE_NAME = "results.json"
  
  def stopSmartDICOMReceiver(self):
    self.smartDicomReceiver = getattr(self, "smartDicomReceiver", None)
    if self.smartDicomReceiver:
      self.smartDicomReceiver.stop()
      self.smartDicomReceiver.removeObservers()
  
  def closeCase(self, directory):
    self.stopSmartDICOMReceiver()
    if os.path.exists(directory):
      self.caseCompleted = False
      if self.getDirectorySize(directory) == 0:
        shutil.rmtree(directory)
        
  def hasCaseBeenCompleted(self, directory):
    self.caseCompleted = False
    filename = os.path.join(directory, self.DEFAULT_JSON_FILE_NAME)
    if not os.path.exists(filename):
      return
    with open(filename) as data_file:
      data = json.load(data_file)
      self.caseCompleted = data["completed"]
    return self.caseCompleted
    
class NewCaseSelectionNameWidget(qt.QMessageBox, ModuleWidgetMixin):

  PREFIX = "Case"
  SUFFIX = "-" + datetime.date.today().strftime("%Y%m%d")
  SUFFIX_PATTERN = "-[0-9]{8}"
  CASE_NUMBER_DIGITS = 3
  PATTERN = PREFIX+"[0-9]{"+str(CASE_NUMBER_DIGITS-1)+"}[0-9]{1}"+SUFFIX_PATTERN

  def __init__(self, destination, parent=None):
    super(NewCaseSelectionNameWidget, self).__init__(parent)
    if not os.path.exists(destination):
      raise
    self.destinationRoot = destination
    self.newCaseDirectory = None
    self.minimum = self.getNextCaseNumber()
    self.setupUI()
    self.setupConnections()
    self.onCaseNumberChanged(self.minimum)

  def getNextCaseNumber(self):
    import re
    caseNumber = 0
    for dirName in [dirName for dirName in os.listdir(self.destinationRoot)
                     if os.path.isdir(os.path.join(self.destinationRoot, dirName)) and re.match(self.PATTERN, dirName)]:
      number = int(re.split(self.SUFFIX_PATTERN, dirName)[0].split(self.PREFIX)[1])
      caseNumber = caseNumber if caseNumber > number else number
    return caseNumber+1

  def setupUI(self):
    self.setWindowTitle("Case Number Selection")
    self.setText("Please select a case number for the new case.")
    self.setIcon(qt.QMessageBox.Question)
    self.spinbox = qt.QSpinBox()
    self.spinbox.setRange(self.minimum, int("9"*self.CASE_NUMBER_DIGITS))
    self.preview = qt.QLabel()
    self.notice = qt.QLabel()
    self.layout().addWidget(self.createVLayout([self.createHLayout([qt.QLabel("Proposed Case Number"), self.spinbox]),
                                                self.preview, self.notice]), 2, 1)
    self.okButton = self.addButton(self.Ok)
    self.okButton.enabled = False
    self.cancelButton = self.addButton(self.Cancel)
    self.setDefaultButton(self.okButton)

  def setupConnections(self):
    self.spinbox.valueChanged.connect(self.onCaseNumberChanged)

  def onCaseNumberChanged(self, caseNumber):
    formatString = '%0'+str(self.CASE_NUMBER_DIGITS)+'d'
    caseNumber = formatString % caseNumber
    directory = self.PREFIX+caseNumber+self.SUFFIX
    self.newCaseDirectory = os.path.join(self.destinationRoot, directory)
    self.preview.setText("New case directory: " + self.newCaseDirectory)
    self.okButton.enabled = not os.path.exists(self.newCaseDirectory)
    self.notice.text = "" if not os.path.exists(self.newCaseDirectory) else "Note: Directory already exists."