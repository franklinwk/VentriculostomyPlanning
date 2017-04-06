import os
import csv, re, numpy, json, ast, re
import shutil, datetime, logging
import ctk, vtk, qt, slicer, inspect
from collections import OrderedDict
from functools import wraps
from VentriculostomyPlanningUtils.UserEvents import VentriculostomyUserEvents

from slicer.ScriptedLoadableModule import *
from SlicerProstateUtils.helpers import WatchBoxAttribute, BasicInformationWatchBox, DICOMBasedInformationWatchBox, IncomingDataWindow
from SlicerProstateUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin, ParameterNodeObservationMixin
from SlicerProstateUtils.constants import DICOMTAGS, COLOR, STYLE, FileExtension
from SlicerProstateUtils.events import SlicerProstateEvents



class WindowLevelEffectsButton(qt.QPushButton):
  """
  The code here is regenerated from SlicerProstateUtil.buttons, from Andrey Fedorov,
  This button might be in
  Will be removed or rewritten later.
  """
  FILE_NAME = 'icon-WindowLevelEffect.png'

  @property
  def sliceWidgets(self):
    return self._sliceWidgets

  @sliceWidgets.setter
  def sliceWidgets(self, value):
    self._sliceWidgets = value
    self.setup()

  def __init__(self, title="", sliceWidgets=None, parent=None, **kwargs):
    super(WindowLevelEffectsButton, self).__init__(title, parent, **kwargs)
    self.checkable = True
    self.toolTip = "Change W/L with respect to FG and BG opacity"
    self.wlEffects = {}
    self.sliceWidgets = sliceWidgets
    self._connectSignals()
    iconPath = os.path.join(os.path.dirname(inspect.getfile(self.__class__)), 'Resources/Icons', self.FILE_NAME)
    pixmap = qt.QPixmap(iconPath)
    self.setIcon(qt.QIcon(pixmap))

  def refreshForAllAvailableSliceWidgets(self):
    self.sliceWidgets = None

  def _connectSignals(self):
    self.destroyed.connect(self.onAboutToBeDestroyed)
    self.toggled.connect(self.onToggled)

  def onAboutToBeDestroyed(self, obj):
    obj.destroyed.disconnect(self.onAboutToBeDestroyed)

  def setup(self):
    lm = slicer.app.layoutManager()
    if not self.sliceWidgets:
      self._sliceWidgets = []
      sliceLogics = lm.mrmlSliceLogics()
      for n in range(sliceLogics.GetNumberOfItems()):
        sliceLogic = sliceLogics.GetItemAsObject(n)
        self._sliceWidgets.append(lm.sliceWidget(sliceLogic.GetName()))
    for sliceWidget in self._sliceWidgets :
      self.addSliceWidget(sliceWidget)

  def cleanupSliceWidgets(self):
    for sliceWidget in self.wlEffects.keys():
      if sliceWidget not in self._sliceWidgets:
        self.removeSliceWidget(sliceWidget)

  def addSliceWidget(self, sliceWidget):
    if not self.wlEffects.has_key(sliceWidget):
      self.wlEffects[sliceWidget] = WindowLevelEffect(sliceWidget)

  def removeSliceWidget(self, sliceWidget):
    if self.wlEffects.has_key(sliceWidget):
      self.wlEffects[sliceWidget].disable()
      del self.wlEffects[sliceWidget]

  def onToggled(self, toggled):
    if toggled:
      self._enableWindowLevelEffects()
    else:
      self._disableWindowLevelEffects()

  def _enableWindowLevelEffects(self):
    for wlEffect in self.wlEffects.values():
      wlEffect.enable()

  def _disableWindowLevelEffects(self):
    for wlEffect in self.wlEffects.values():
      wlEffect.disable()


class WindowLevelEffect(object):
  """
    The code here is regenerated from SlicerProstateUtil.buttons, from Andrey Fedorov
    Will be removed or rewritten later.
    """
  EVENTS = [vtk.vtkCommand.LeftButtonPressEvent,
            vtk.vtkCommand.LeftButtonReleaseEvent,
            vtk.vtkCommand.MouseMoveEvent]

  def __init__(self, sliceWidget):
    self.actionState = None
    iconPath = os.path.join(os.path.dirname(inspect.getfile(self.__class__)), 'Resources/Icons/icon-WindowLevelEffect.png' )
    pixmap = qt.QPixmap(iconPath)
    self.cursor = qt.QCursor(qt.QIcon(pixmap).pixmap(32, 32), 0, 0)
    self.sliceWidget = sliceWidget
    self.sliceLogic = sliceWidget.sliceLogic()
    self.compositeNode = sliceWidget.mrmlSliceCompositeNode()
    self.sliceView = self.sliceWidget.sliceView()
    self.interactor = self.sliceView.interactorStyle().GetInteractor()

    self.actionState = None

    self.interactorObserverTags = []

    self.bgStartWindowLevel = [0,0]
    self.fgStartWindowLevel = [0,0]

  def enable(self):
    for e in self.EVENTS:
      tag = self.interactor.AddObserver(e, self.processEvent, 1.0)
      self.interactorObserverTags.append(tag)

  def disable(self):
    for tag in self.interactorObserverTags:
      self.interactor.RemoveObserver(tag)
    self.interactorObserverTags = []

  def processEvent(self, caller=None, event=None):
    """
    handle events from the render window interactor
    """
    bgLayer = self.sliceLogic.GetBackgroundLayer()
    fgLayer = self.sliceLogic.GetForegroundLayer()

    bgNode = bgLayer.GetVolumeNode()
    fgNode = fgLayer.GetVolumeNode()

    changeFg = 1 if fgNode and self.compositeNode.GetForegroundOpacity() > 0.5 else 0
    changeBg = not changeFg

    if event == "LeftButtonPressEvent":
      self.actionState = "dragging"
      self.sliceWidget.setCursor(self.cursor)

      xy = self.interactor.GetEventPosition()
      self.startXYPosition = xy
      self.currentXYPosition = xy

      if bgNode:
        bgDisplay = bgNode.GetDisplayNode()
        self.bgStartWindowLevel = [bgDisplay.GetWindow(), bgDisplay.GetLevel()]
      if fgNode:
        fgDisplay = fgNode.GetDisplayNode()
        self.fgStartWindowLevel = [fgDisplay.GetWindow(), fgDisplay.GetLevel()]
      self.abortEvent(event)

    elif event == "MouseMoveEvent":
      if self.actionState == "dragging":
        if bgNode and changeBg:
          self.updateNodeWL(bgNode, self.bgStartWindowLevel, self.startXYPosition)
        if fgNode and changeFg:
          self.updateNodeWL(fgNode, self.fgStartWindowLevel, self.startXYPosition)
        self.abortEvent(event)

    elif event == "LeftButtonReleaseEvent":
      self.sliceWidget.unsetCursor()
      self.actionState = ""
      self.abortEvent(event)

  def updateNodeWL(self, node, startWindowLevel, startXY):

    currentXY = self.interactor.GetEventPosition()

    vDisplay = node.GetDisplayNode()
    vImage = node.GetImageData()
    vRange = vImage.GetScalarRange()

    deltaX = currentXY[0] - startXY[0]
    deltaY = currentXY[1] - startXY[1]
    gain = (vRange[1] - vRange[0]) / 500.
    newWindow = startWindowLevel[0] + (gain * deltaX)
    newLevel = startWindowLevel[1] + (gain * deltaY)

    vDisplay.SetAutoWindowLevel(0)
    vDisplay.SetWindowLevel(newWindow, newLevel)
    vDisplay.Modified()

  def abortEvent(self, event):
    """Set the AbortFlag on the vtkCommand associated
    with the event - causes other things listening to the
    interactor not to receive the events"""
    # TODO: make interactorObserverTags a map to we can
    # explicitly abort just the event we handled - it will
    # be slightly more efficient
    for tag in self.interactorObserverTags:
      cmd = self.interactor.GetCommand(tag)
      cmd.SetAbortFlag(1)

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
    self.parent.dependencies = ["SlicerProstate"]
    self.parent.contributors = ["Longquan Chen(SPL)","Christian Herz (SPL)"]
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
    self.rootDirectoryLabel.setText(str(self.caseRootDir))
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
    return os.path.join(self.currentCaseDirectory, "DICOM", "Planning") if self.currentCaseDirectory else None

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
    self.modulePath = os.path.dirname(slicer.util.modulePath(self.moduleName))
    self._currentCaseDirectory = None
    self._caseDirectoryList = {}
    self.caseDirectoryList = {"DICOM/Planning", "Results"}

  def setup(self):
    #ScriptedLoadableModuleWidget.setup(self)

    self._mainGUIGroupBox = qt.QGroupBox()
    self._collapsibleDirectoryConfigurationArea = ctk.ctkCollapsibleButton()
    self.mainGUIGroupBoxLayout = qt.QGridLayout()
    self._mainGUIGroupBox.setLayout(self.mainGUIGroupBoxLayout)
    self.createNewCaseButton = self.createButton("New case")
    self.openCaseButton = self.createButton("Open case")
    self.mainGUIGroupBoxLayout.addWidget(self.createNewCaseButton, 1, 0)
    self.mainGUIGroupBoxLayout.addWidget(self.openCaseButton, 1, 1)
    
    self.createPatientWatchBox()
    #self.createIntraopWatchBox()
    self.createCaseInformationArea()
    self.setupConnections()
    self.layout.addWidget(self._mainGUIGroupBox)

  
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
                                       WatchBoxAttribute('StudyDate', 'Planning Study Date: ', DICOMTAGS.STUDY_DATE)]
    self.patientWatchBox = DICOMBasedInformationWatchBox(self.patientWatchBoxInformation)
    self.layout.addWidget(self.patientWatchBox)
  
  def createCaseInformationArea(self):
    self.casesRootDirectoryButton = self.createDirectoryButton(text="Choose cases root location",
                                                               caption="Choose cases root location",
                                                               directory=self.getSetting('CasesRootLocation'))
    self.createCaseWatchBox()
    self._collapsibleDirectoryConfigurationArea.collapsed = True
    self._collapsibleDirectoryConfigurationArea.text = "Case Directory Settings"
    self.directoryConfigurationLayout = qt.QGridLayout(self._collapsibleDirectoryConfigurationArea)
    self.directoryConfigurationLayout.addWidget(qt.QLabel("Cases Root Directory:"), 1, 0, 1, 1)
    self.rootDirectoryLabel = qt.QLabel('')
    self.directoryConfigurationLayout.addWidget(self.rootDirectoryLabel, 1, 1, 1, 1)
    self.directoryConfigurationLayout.addWidget(self.casesRootDirectoryButton, 1, 2, 1, 1)
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

  def updateCaseWatchBox(self):
    value = self.currentCaseDirectory
    self.caseWatchBox.setInformation("CurrentCaseDirectory", os.path.relpath(value, self.caseRootDir), toolTip=value)

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
  
  def onOpenCaseButtonClicked(self):
    if not self.checkAndWarnUserIfCaseInProgress():
      return
    path = qt.QFileDialog.getExistingDirectory(self.parent.window(), "Select Case Directory", self.caseRootDir)
    if not path:
      return
    slicer.mrmlScene.Clear(0)
    self.logic.update_observers(VentriculostomyUserEvents.CloseCaseEvent)
    self.currentCaseDirectory = path
    if (not os.path.exists(os.path.join(path, "DICOM", "Planning")) ) or (not os.path.exists(os.path.join(path, "Results")) ):
      slicer.util.warningDisplay("The selected case directory seems not to be valid", windowTitle="")
      self.clearData()
    else:
      #slicer.util.loadVolume(self.planningImagePath, returnNode=True)
      sucess = slicer.util.loadScene(os.path.join(path, "Results","Results.mrml"))
      self.logic.update_observers(VentriculostomyUserEvents.LoadParametersToScene, self.currentCaseDirectory)


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
      self.logic.closeCase(self.currentCaseDirectory)
      self.currentCaseDirectory = None
    slicer.mrmlScene.Clear(0)
    self.logic.update_observers(VentriculostomyUserEvents.CloseCaseEvent)
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

  @onReturnProcessEvents
  def update_observers(self, *args, **kwargs):
    for observer in self.observers:
      observer.updateFromCaseManager(*args, **kwargs)
  
  def closeCase(self, directory):
    if os.path.exists(directory):
      self.caseCompleted = False
      if self.getDirectorySize(directory) == 0:
        shutil.rmtree(directory)
      #self.update_observers(VentriculostomyUserEvents.CloseCaseEvent)
        
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