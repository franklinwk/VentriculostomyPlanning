import os
import csv, re, numpy, json, ast, re
import shutil, datetime, logging
import ctk, vtk, qt, slicer, inspect
from functools import wraps

from slicer.ScriptedLoadableModule import *
from SlicerDevelopmentToolboxUtils.widgets import BasicInformationWatchBox, DICOMBasedInformationWatchBox
from SlicerDevelopmentToolboxUtils.helpers import WatchBoxAttribute
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.constants import DICOMTAGS

def onReturnProcessEvents(func):
  @wraps(func)
  def wrapper(*args, **kwargs):
    func(*args, **kwargs)
    slicer.app.processEvents()
  return wrapper


def beforeRunProcessEvents(func):
  @wraps(func)
  def wrapper(*args, **kwargs):
    slicer.app.processEvents()
    func(*args, **kwargs)
  return wrapper


class SlicerCaseManager(ScriptedLoadableModule):
  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SlicerCaseManager"
    self.parent.categories = ["Radiology"]
    self.parent.dependencies = [""]
    self.parent.contributors = ["Longquan Chen(SPL)","Christian Herz (SPL)"]
    self.parent.helpText = """A common module for case management in Slicer"""
    self.parent.acknowledgementText = """Surgical Planning Laboratory, Brigham and Women's Hospital, Harvard
                                        Medical School, Boston, USA This work was supported in part by the National
                                        Institutes of Health through grants R01 EB020667, U24 CA180918,
                                        R01 CA111288 and P41 EB015898. The code is originated from the module SliceTracker"""

class SlicerCaseManagerWidget(ScriptedLoadableModuleWidget, ModuleWidgetMixin):
  @property
  def caseRootDir(self):
    return self._caseRootDir

  @caseRootDir.setter
  def caseRootDir(self, path):
    try:
      exists = os.path.exists(path)
    except TypeError:
      exists = False
    self._caseRootDir = path
    self.setSetting('CasesRootLocation', path if exists else None)
    self.casesRootDirectoryButton.toolTip = path
    self.rootDirectoryLabel.setText(str(self._caseRootDir))
    self.openCaseButton.enabled = exists
    self.createNewCaseButton.enabled = exists

  
  @property
  def caseDirectoryList(self):
    return self._caseDirectoryList

  @caseDirectoryList.setter
  def caseDirectoryList(self,list):
    self._caseDirectoryList = list      
  
  @property
  def planningDataDir(self):
    return self._planningDataDir

  @planningDataDir.setter
  def planningDataDir(self, path):
    self._planningDataDir = path
    if path is None:
      return
    if os.path.exists(path):
      self.loadPlanningData()

  @property
  def planningDICOMDataDirectory(self):
    return os.path.join(self.currentCaseDirectory, "DICOM", "Planning") if self.currentCaseDirectory else ""

  @property
  def outputDir(self):
    return os.path.join(self.currentCaseDirectory, "VentriclostomyOutputs")

  @property
  def currentCaseDirectory(self):
    return self._currentCaseDirectory

  @currentCaseDirectory.setter
  def currentCaseDirectory(self, path):
    self._currentCaseDirectory = path
    valid = path is not None
    if valid:
      self.updateCaseWatchBox()
    else:
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
  
  @property
  def mainGUIGroupBox(self):
    return self._mainGUIGroupBox

  @property
  def collapsibleDirectoryConfigurationArea(self):
    return self._collapsibleDirectoryConfigurationArea
  
  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.logic = SlicerCaseManagerLogic()
    self.moduleName = "slicerCaseManager"
    #self.modulePath = os.path.dirname(slicer.util.modulePath(self.moduleName))
    self._caseRootDir = self.getSetting('CasesRootLocation')
    self._currentCaseDirectory = None
    self._caseDirectoryList = {}
    self.caseDirectoryList = {"DICOM/Planning", "Results"}
    self.warningBox = qt.QMessageBox()
    self.CloseCaseEvent = vtk.vtkCommand.UserEvent + 201
    self.LoadCaseCompletedEvent = vtk.vtkCommand.UserEvent + 202
    self.StartCaseImportEvent = vtk.vtkCommand.UserEvent + 203
    self.CreatedNewCaseEvent = vtk.vtkCommand.UserEvent + 204
    self.setup()

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self._mainGUIGroupBox = qt.QGroupBox()
    self._collapsibleDirectoryConfigurationArea = ctk.ctkCollapsibleButton()
    self.mainGUIGroupBoxLayout = qt.QGridLayout()
    self._mainGUIGroupBox.setLayout(self.mainGUIGroupBoxLayout)
    self.createNewCaseButton = self.createButton("New case")
    self.openCaseButton = self.createButton("Open case")
    self.mainGUIGroupBoxLayout.addWidget(self.createNewCaseButton, 1, 0)
    self.mainGUIGroupBoxLayout.addWidget(self.openCaseButton, 1, 1)
    self.casesRootDirectoryButton = self.createDirectoryButton(text="Choose cases root location",
                                                               caption="Choose cases root location",
                                                               directory=self.getSetting('CasesRootLocation'))
    self.rootDirectoryLabel = qt.QLabel('')
    if self.getSetting('CasesRootLocation'):
      self.rootDirectoryLabel = qt.QLabel(self.getSetting('CasesRootLocation'))
    self.createPatientWatchBox()
    #self.createIntraopWatchBox()
    self.createCaseWatchBox()
    #self.createCaseInformationArea()
    self.setupConnections()
    self.layout.addWidget(self._mainGUIGroupBox)
    slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.StartImportEvent, self.StartCaseImportCallback)
    slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.EndImportEvent, self.LoadCaseCompletedCallback)

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def StartCaseImportCallback(self, caller, eventId, callData):
    print("loading case")
    self.logic.update_observers(self.StartCaseImportEvent)

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def LoadCaseCompletedCallback(self, caller, eventId, callData):
    print("case loaded")
    self.logic.update_observers(self.LoadCaseCompletedEvent)

  def updateOutputFolder(self):
    if os.path.exists(self.generatedOutputDirectory):
      return
    if self.patientWatchBox.getInformation("PatientID") != '' :
      if self.outputDir and not os.path.exists(self.outputDir):
        self.logic.createDirectory(self.outputDir)
      finalDirectory = self.patientWatchBox.getInformation("PatientID") + \
                       str(qt.QDate().currentDate()) + "-" + qt.QTime().currentTime().toString().replace(":", "")
      self.generatedOutputDirectory = os.path.join(self.outputDir, finalDirectory, "Planning")
    else:
      self.generatedOutputDirectory = ""

  def createPatientWatchBox(self):
    self.patientWatchBoxInformation = [WatchBoxAttribute('PatientID', 'Patient ID: ', DICOMTAGS.PATIENT_ID),
                                       WatchBoxAttribute('PatientName', 'Patient Name: ', DICOMTAGS.PATIENT_NAME),
                                       WatchBoxAttribute('DOB', 'Date of Birth: ', DICOMTAGS.PATIENT_BIRTH_DATE),
                                       WatchBoxAttribute('StudyDate', 'Planning Study Date: ', DICOMTAGS.STUDY_DATE),
                                       WatchBoxAttribute('CurrentCaseDirectory', 'Case Directory')]
    self.patientWatchBox = DICOMBasedInformationWatchBox(self.patientWatchBoxInformation)
    self.layout.addWidget(self.patientWatchBox)

  def createCaseWatchBox(self):
    watchBoxInformation = [WatchBoxAttribute('CurrentCaseDirectory', 'Directory')]
    self.caseWatchBox = BasicInformationWatchBox(watchBoxInformation, title="Current Case")


  def setupConnections(self):
    self.createNewCaseButton.clicked.connect(self.onCreateNewCaseButtonClicked)
    self.openCaseButton.clicked.connect(self.onOpenCaseButtonClicked)
    self.casesRootDirectoryButton.directorySelected.connect(lambda: setattr(self, "caseRootDir",
                                                                           self.casesRootDirectoryButton.directory))

  def updateCaseWatchBox(self):
    value = self.currentCaseDirectory
    self.patientWatchBox.setInformation("CurrentCaseDirectory", os.path.relpath(value, self.caseRootDir), toolTip=value)

  def onCreateNewCaseButtonClicked(self):
    if not self.checkAndWarnUserIfCaseInProgress():
      return
    if not self.caseRootDir:
      self.warningBox.setText("The root directory for cases is not set up yet.")
      self.warningBox.exec_()
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
      self.logic.update_observers(self.CreatedNewCaseEvent)
  
  def onOpenCaseButtonClicked(self):
    if not self.checkAndWarnUserIfCaseInProgress():
      return
    if not self.caseRootDir:
      self.warningBox.setText("The root directory for cases is not set up yet.")
      self.warningBox.exec_()
      return
    path = qt.QFileDialog.getExistingDirectory(self.parent.window(), "Select Case Directory", self.caseRootDir)
    if not path:
      return
    slicer.mrmlScene.Clear(0)
    self.logic.update_observers(self.CloseCaseEvent)
    self.currentCaseDirectory = path
    if (not os.path.exists(os.path.join(path, "DICOM", "Planning")) ) or (not os.path.exists(os.path.join(path, "Results")) ):
      slicer.util.warningDisplay("The selected case directory seems not to be valid", windowTitle="")
      self.clearData()
    else:
      # Here the both the slicer.vtkMRMLScene.StartImportEvent and slicer.vtkMRMLScene.EndImportEvent will be triggered
      sucess = slicer.util.loadScene(os.path.join(path, "Results","Results.mrml"))

  def checkAndWarnUserIfCaseInProgress(self):
    proceed = True
    if self.currentCaseDirectory is not None:
      if not slicer.util.confirmYesNoDisplay("Current case will be closed. Do you want to proceed?"):
        proceed = False
    return proceed

  def loadCaseData(self):
    # To do: load data from Json file
    pass

  def clearData(self):
    # To do: clear the flags
    if self.currentCaseDirectory:
      #self.logic.closeCase(self.currentCaseDirectory) #this function remove the whole case directory.
      self.currentCaseDirectory = None
    slicer.mrmlScene.Clear(0)
    self.logic.update_observers(self.CloseCaseEvent)
    self.patientWatchBox.sourceFile = None
    self.caseWatchBox.sourceFile = None
    pass


class SlicerCaseManagerLogic(ModuleLogicMixin, ScriptedLoadableModuleLogic):
  @property
  def caseCompleted(self):
    return self._caseCompleted

  @caseCompleted.setter
  def caseCompleted(self, value):
    self._caseCompleted = value
  
  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    self.caseCompleted = True
    self.DEFAULT_JSON_FILE_NAME = "results.json"
    self.observers = []

  def register(self, observer):
    if not observer in self.observers:
      self.observers.append(observer)


  def unregister(self, observer):
    if observer in self.observers:
      self.observers.remove(observer)

  def unregister_all(self):
    if self.observers:
      del self.observers[:]

  @beforeRunProcessEvents
  def update_observers(self, EventID):
    for observer in self.observers:
      observer.updateFromCaseManager(EventID)
  
  def closeCase(self, directory):
    if os.path.exists(directory):
      self.caseCompleted = False
      if self.getDirectorySize(directory) == 0:
        shutil.rmtree(directory)
      #self.update_observers(self.CloseCaseEvent)
        
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
      slicer.util.warningDisplay("Root directory is not set, please set the root in the 'Case Directory Settings' panel ", windowTitle="")
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