import os, inspect
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from ctk import ctkAxesWidget
import logging
import tempfile
import numpy
import SimpleITK as sitk
import sitkUtils
import DICOM
from DICOM import DICOMWidget
import PercutaneousApproachAnalysis
from PercutaneousApproachAnalysis import *
from numpy import linalg
from code import interact
#import SlicerCaseManager

#
# VentriculostomyPlanning
#

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

class VentriculostomyPlanning(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "VentriculostomyPlanning" # TODO make this more human readable by adding spaces
    self.parent.categories = ["IGT"]
    #self.parent.dependencies = [""]
    self.parent.contributors = ["Junichi Tokuda (BWH)", "Longquan Chen(BWH)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    It performs a simple thresholding on the input volume and optionally captures a screenshot.
    """
    self.parent.acknowledgementText = """
    This module was developed based on an example code provided by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# VentriculostomyPlanningWidget
#

class VentriculostomyPlanningWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = VentriculostomyPlanningLogic()
    self.dicomWidget = DICOMWidget()
    self.dicomWidget.parent.close()
    self.caseNum = 0
    self.cameraPos = [0.0]*3
    self.camera = None
    layoutManager = slicer.app.layoutManager()
    threeDView = layoutManager.threeDWidget(0).threeDView()
    displayManagers = vtk.vtkCollection()
    threeDView.getDisplayableManagers(displayManagers)
    for index in range(displayManagers.GetNumberOfItems()):
      if displayManagers.GetItemAsObject(index).GetClassName() == 'vtkMRMLCameraDisplayableManager':
        self.camera = displayManagers.GetItemAsObject(index).GetCameraNode().GetCamera()
        self.cameraPos = self.camera.GetPosition()
    # Instantiate and connect widgets ...
    #
    # Lines Area
    #

    configurationCollapsibleButton = ctk.ctkCollapsibleButton()
    configurationCollapsibleButton.text = "Configuration"
    self.layout.addWidget(configurationCollapsibleButton)
    configurationCollapsibleButton.setVisible(False)
    # Layout within the dummy collapsible button
    configurationFormLayout = qt.QFormLayout(configurationCollapsibleButton)
    #
    # Mid-sagittalReference line
    #
    """"""
    referenceConfigLayout = qt.QHBoxLayout()

    #-- Curve length
    lengthSagittalReferenceLineLabel = qt.QLabel('Sagittal Length:  ')
    referenceConfigLayout.addWidget(lengthSagittalReferenceLineLabel)
    self.lengthSagittalReferenceLineEdit = qt.QLineEdit()
    self.lengthSagittalReferenceLineEdit.text = '100.0'
    self.lengthSagittalReferenceLineEdit.readOnly = False
    self.lengthSagittalReferenceLineEdit.frame = True
    self.lengthSagittalReferenceLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthSagittalReferenceLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    referenceConfigLayout.addWidget(self.lengthSagittalReferenceLineEdit)
    lengthSagittalReferenceLineUnitLabel = qt.QLabel('mm  ')
    referenceConfigLayout.addWidget(lengthSagittalReferenceLineUnitLabel)

    lengthCoronalReferenceLineLabel = qt.QLabel('Coronal Length:  ')
    referenceConfigLayout.addWidget(lengthCoronalReferenceLineLabel)
    self.lengthCoronalReferenceLineEdit = qt.QLineEdit()
    self.lengthCoronalReferenceLineEdit.text = '30.0'
    self.lengthCoronalReferenceLineEdit.readOnly = False
    self.lengthCoronalReferenceLineEdit.frame = True
    self.lengthCoronalReferenceLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthCoronalReferenceLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    referenceConfigLayout.addWidget(self.lengthCoronalReferenceLineEdit)
    lengthCoronalReferenceLineUnitLabel = qt.QLabel('mm  ')
    referenceConfigLayout.addWidget(lengthCoronalReferenceLineUnitLabel)

    radiusPathPlanningLabel = qt.QLabel('Radius:  ')
    referenceConfigLayout.addWidget(radiusPathPlanningLabel)
    self.radiusPathPlanningEdit = qt.QLineEdit()
    self.radiusPathPlanningEdit.text = '30.0'
    self.radiusPathPlanningEdit.readOnly = False
    self.radiusPathPlanningEdit.frame = True
    self.radiusPathPlanningEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.radiusPathPlanningEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    referenceConfigLayout.addWidget(self.radiusPathPlanningEdit)
    radiusPathPlanningUnitLabel = qt.QLabel('mm  ')
    referenceConfigLayout.addWidget(radiusPathPlanningUnitLabel)
    configurationFormLayout.addRow(referenceConfigLayout)

    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "VentriculostomyPlanning Reload"
    referenceConfigLayout.addWidget(self.reloadButton)

    self.reloadButton.connect('clicked()', self.onReload)
    self.lengthSagittalReferenceLineEdit.connect('textEdited(QString)', self.onModifyMeasureLength)
    self.lengthCoronalReferenceLineEdit.connect('textEdited(QString)', self.onModifyMeasureLength)
    self.radiusPathPlanningEdit.connect('textEdited(QString)', self.onModifyPathPlanningRadius)

    self.allVolumeSelector = slicer.qMRMLNodeComboBox()
    self.allVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.allVolumeSelector.setMRMLScene(slicer.mrmlScene)
    self.allVolumeSelector.connect("nodeAdded(vtkMRMLNode*)", self.onAddedNode)
    #referenceConfigLayout.addWidget(self.allVolumeSelector)
    # PatientModel Area
    #
    #referenceCollapsibleButton = ctk.ctkCollapsibleButton()
    #referenceCollapsibleButton.text = "Reference Generating "
    #self.layout.addWidget(referenceCollapsibleButton)
    
    # Layout within the dummy collapsible button
    #referenceFormLayout = qt.QFormLayout(referenceCollapsibleButton)

    
    #CaseManagerConfigLayout = qt.QVBoxLayout()
    #slicerCaseWidgetParent = slicer.qMRMLWidget()
    #slicerCaseWidgetParent.setLayout(qt.QVBoxLayout())
    #slicerCaseWidgetParent.setMRMLScene(slicer.mrmlScene)
    #self.slicerCaseWidget = SlicerCaseManager.SlicerCaseManagerWidget(slicerCaseWidgetParent)
    #self.slicerCaseWidget.setup()
    #CaseManagerConfigLayout.addWidget(self.slicerCaseWidget.collapsibleDirectoryConfigurationArea)
    #CaseManagerConfigLayout.addWidget(self.slicerCaseWidget.mainGUIGroupBox)


    #referenceFormLayout.addRow(CaseManagerConfigLayout)
    #
    # input volume selector
    #

    self.mainGUIGroupBox = qt.QGroupBox()
    self.mainGUIGroupBoxLayout = qt.QGridLayout()
    self.mainGUIGroupBox.setLayout(self.mainGUIGroupBoxLayout)

    buttonWidth = 60
    buttonHeight = 60

    self.infoVolumeBox = qt.QGroupBox()
    inputVolumeLayout = qt.QHBoxLayout()
    inputVolumeLayout.setAlignment(qt.Qt.AlignLeft)
    self.infoVolumeBox.setLayout(inputVolumeLayout)
    self.layout.addWidget(self.infoVolumeBox)
    inputVolumeLabel = qt.QLabel('Select Case: ')
    inputVolumeLayout.addWidget(inputVolumeLabel)
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.selectNodeUponCreation = True
    self.inputVolumeSelector.addEnabled = False
    self.inputVolumeSelector.removeEnabled = False
    self.inputVolumeSelector.noneEnabled = True
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.showChildNodeTypes = False
    self.inputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.inputVolumeSelector.setToolTip( "Pick the input to the algorithm." )
    self.inputVolumeSelector.sortFilterProxyModel().setFilterRegExp("(Venous)")
    #self.inputVolumeSelector.sortFilterProxyModel().setFilterRegExp("^((?!NotShownEntity31415).)*$" )
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    inputVolumeLayout.addWidget(self.inputVolumeSelector)
    self.layout.addWidget(self.infoVolumeBox)
    self.layout.addWidget(self.mainGUIGroupBox)
    #
    # Create Model Button
    #
    #self.mainGUIGroupBoxLayout.addWidget(self.inputVolumeSelector,1,0)

    
    ROIConfigLayout = qt.QHBoxLayout()
    self.selectROIButton = qt.QPushButton("ROI definition")
    self.selectROIButton.toolTip = "Add two points in the 2D window"
    self.selectROIButton.enabled = True
    ROIConfigLayout.addWidget(self.selectROIButton)
    
    self.createROIButton = qt.QPushButton("Crop Volume")
    self.createROIButton.toolTip = "Created cropped volume"
    self.createROIButton.enabled = True
    ROIConfigLayout.addWidget(self.createROIButton)
    self.selectROIButton.connect('clicked(bool)',self.onDefineROI)
    self.createROIButton.connect('clicked(bool)',self.onCreateROI)
    
    #
    # Create Entry point Button
    #
    automaticEntryHorizontalLayout = qt.QHBoxLayout()
    
    self.createModelButton = qt.QPushButton("Create Model")
    self.createModelButton.toolTip = "Create a surface model."
    self.createModelButton.enabled = True
    self.createModelButton.connect('clicked(bool)', self.onCreateModel)

    self.scriptDirectory = os.path.join(os.path.dirname(os.path.realpath(__file__)),"Resources", "icons")



    self.loadCaseBox = qt.QGroupBox()
    loadCaseLayout = qt.QVBoxLayout()
    loadCaseLayout.setAlignment(qt.Qt.AlignCenter)
    self.loadCaseBox.setLayout(loadCaseLayout)
    self.LoadCaseButton = qt.QPushButton("")
    self.LoadCaseButton.toolTip = "Load a dicom dataset"
    self.LoadCaseButton.enabled = True
    loadCaseLabel = qt.QLabel('Load Dicom')
    #loadCaseLayout.addWidget(loadCaseLabel)
    loadCaseLayout.addWidget(self.LoadCaseButton)
    #self.LoadCaseButton.setFixedHeight(50)
    self.LoadCaseButton.setMaximumHeight(buttonHeight)
    self.LoadCaseButton.setMaximumWidth(buttonWidth)
    self.LoadCaseButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "load.png"))))
    self.LoadCaseButton.setIconSize(qt.QSize(self.LoadCaseButton.size))
    self.loadCaseBox.setStyleSheet('QGroupBox{border:0;}')
    self.mainGUIGroupBoxLayout.addWidget(self.LoadCaseButton, 2, 0)

    self.selectNasionBox = qt.QGroupBox()
    selectNasionLayout = qt.QVBoxLayout()
    selectNasionLayout.setAlignment(qt.Qt.AlignCenter)
    self.selectNasionBox.setLayout(selectNasionLayout)
    self.selectNasionBox.setStyleSheet('QGroupBox{border:0;}')
    self.selectNasionButton = qt.QPushButton("")
    self.selectNasionButton.toolTip = "Add a point in the 3D window"
    self.selectNasionButton.enabled = True
    self.selectNasionButton.setMaximumHeight(buttonHeight)
    self.selectNasionButton.setMaximumWidth(buttonWidth)
    self.selectNasionButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "nasion.png"))))
    self.selectNasionButton.setIconSize(qt.QSize(self.selectNasionButton.size))
    selectNasionLabel = qt.QLabel('Select Nasion')
    selectNasionLayout.addWidget(self.selectNasionButton)
    self.mainGUIGroupBoxLayout.addWidget(self.selectNasionButton, 2 , 1)

    self.selectSagittalBox = qt.QGroupBox()
    selectSagittalLayout = qt.QVBoxLayout()
    selectSagittalLayout.setAlignment(qt.Qt.AlignCenter)
    self.selectSagittalBox.setLayout(selectSagittalLayout)
    self.selectSagittalBox.setStyleSheet('QGroupBox{border:0;}')
    self.selectSagittalButton = qt.QPushButton("")
    self.selectSagittalButton.setMaximumHeight(buttonHeight)
    self.selectSagittalButton.setMaximumWidth(buttonWidth)
    self.selectSagittalButton.toolTip = "Add a point in the 3D window to identify the sagittal plane"
    self.selectSagittalButton.enabled = True
    self.selectSagittalButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "sagittalPoint.png"))))
    self.selectSagittalButton.setIconSize(qt.QSize(self.selectSagittalButton.size))
    selectSagittalLayout.addWidget(self.selectSagittalButton)
    self.mainGUIGroupBoxLayout.addWidget(self.selectSagittalButton, 2 , 2)

    self.createEntryPointButton = qt.QPushButton("Create Entry Point")
    self.createEntryPointButton.toolTip = "Create the initial entry point."
    self.createEntryPointButton.toolTip = "Create the initial entry point."
    self.createEntryPointButton.enabled = True

    self.LoadCaseButton.connect('clicked(bool)', self.onLoadCase)
    self.selectNasionButton.connect('clicked(bool)', self.onSelectNasionPoint)
    self.selectSagittalButton.connect('clicked(bool)', self.onSelectSagittalPoint)
    self.createEntryPointButton.connect('clicked(bool)', self.onCreateEntryPoint)

    
    #
    # Venous Segmentation/Rendering
    #
    
    # Layout within the dummy collapsible button
    createVesselHorizontalLayout = qt.QHBoxLayout()
    self.venousCalcStatus = qt.QLabel('VenousCalcStatus')

    self.detectVesselBox = qt.QGroupBox()
    detectVesselLayout = qt.QVBoxLayout()
    detectVesselLayout.setAlignment(qt.Qt.AlignCenter)
    self.detectVesselBox.setLayout(detectVesselLayout)
    self.grayScaleMakerButton = qt.QPushButton("")
    self.grayScaleMakerButton.enabled = True
    self.grayScaleMakerButton.toolTip = "Use the GrayScaleMaker module for vessel calculation "
    detectVesselLabel = qt.QLabel('Detect Vessel')
    #detectVesselLayout.addWidget(detectVesselLabel)
    detectVesselLayout.addWidget(self.grayScaleMakerButton)
    self.grayScaleMakerButton.setMaximumHeight(buttonHeight)
    self.grayScaleMakerButton.setMaximumWidth(buttonWidth)
    self.grayScaleMakerButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "vessel.png"))))
    self.grayScaleMakerButton.setIconSize(qt.QSize(self.grayScaleMakerButton.size))
    self.detectVesselBox.setStyleSheet('QGroupBox{border:0;}')
    #self.mainGUIGroupBoxLayout.addWidget(self.detectVesselBox, 2, 2)


    self.grayScaleMakerButton.connect('clicked(bool)', self.onVenousGrayScaleCalc)
    createVesselHorizontalLayout.addWidget(self.venousCalcStatus)
    self.vesselnessCalcButton = qt.QPushButton("VesselnessCalc")
    self.vesselnessCalcButton.toolTip = "Use Vesselness calculation "
    self.vesselnessCalcButton.enabled = True
    self.vesselnessCalcButton.connect('clicked(bool)', self.onVenousVesselnessCalc)
    
    #
    # Trajectory
    #


    #-- Add Point
    self.addCannulaBox = qt.QGroupBox()
    addCannulaLayout = qt.QVBoxLayout()
    addCannulaLayout.setAlignment(qt.Qt.AlignCenter)
    self.addCannulaBox.setLayout(addCannulaLayout)
    self.addCannulaTargetButton = qt.QPushButton("")
    self.addCannulaTargetButton.toolTip = ""
    self.addCannulaTargetButton.enabled = True
    addCannulaLabel = qt.QLabel('Add Cannula')
    #addCannulaLayout.addWidget(addCannulaLabel)
    addCannulaLayout.addWidget(self.addCannulaTargetButton)
    self.addCannulaTargetButton.setMaximumHeight(buttonHeight)
    self.addCannulaTargetButton.setMaximumWidth(buttonWidth)
    self.addCannulaTargetButton.setToolTip("Define the ventricle cylinder")
    self.addCannulaTargetButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "cannula.png"))))
    self.addCannulaTargetButton.setIconSize(qt.QSize(self.addCannulaTargetButton.size))
    '''
    self.addCannulaBox.setStyleSheet('QGroupBox{border:0;}')
    self.addCannulaDistalButton = qt.QPushButton("")
    self.addCannulaDistalButton.setMaximumHeight(buttonHeight)
    self.addCannulaDistalButton.setMaximumWidth(buttonWidth)
    self.addCannulaDistalButton.toolTip = "Define the distal cannula point"
    self.addCannulaDistalButton.enabled = True
    self.addCannulaDistalButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "cannula.png"))))
    self.addCannulaDistalButton.setIconSize(qt.QSize(self.addCannulaDistalButton.size))
    addCannulaLayout.addWidget(self.addCannulaDistalButton)
    '''
    self.mainGUIGroupBoxLayout.addWidget(self.addCannulaTargetButton,2,3)

    self.generatePathBox = qt.QGroupBox()
    generatePathLayout = qt.QVBoxLayout()
    generatePathLayout.setAlignment(qt.Qt.AlignCenter)
    self.generatePathBox.setLayout(generatePathLayout)
    self.generatePathButton = qt.QPushButton("")
    self.generatePathButton.toolTip = ""
    self.generatePathButton.enabled = True
    generatePathLabel = qt.QLabel('Generate Path')
    #generatePathLayout.addWidget(generatePathLabel)
    generatePathLayout.addWidget(self.generatePathButton)
    self.generatePathButton.setMaximumHeight(buttonHeight)
    self.generatePathButton.setMaximumWidth(buttonWidth)
    self.generatePathButton.setToolTip("Generate cannula paths")
    self.generatePathButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "pathPlanning.png"))))
    self.generatePathButton.setIconSize(qt.QSize(self.generatePathButton.size))
    self.generatePathBox.setStyleSheet('QGroupBox{border:0;}')
    self.mainGUIGroupBoxLayout.addWidget(self.generatePathButton, 2, 4)

    #-- Curve length
    self.infoGroupBox = qt.QGroupBox()
    self.infoGroupBoxLayout = qt.QVBoxLayout()
    self.infoGroupBox.setLayout(self.infoGroupBoxLayout)
    self.layout.addWidget(self.infoGroupBox)

    cannulaLengthInfoLayout = qt.QHBoxLayout()
    lengthTrajectoryLabel = qt.QLabel('Cannula Length:')
    cannulaLengthInfoLayout.addWidget(lengthTrajectoryLabel)
    self.lengthCannulaEdit = qt.QLineEdit()
    self.lengthCannulaEdit.text = '--'
    self.lengthCannulaEdit.setMaxLength(5)
    self.lengthCannulaEdit.readOnly = True
    self.lengthCannulaEdit.frame = True
    self.lengthCannulaEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthCannulaEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    cannulaLengthInfoLayout.addWidget(self.lengthCannulaEdit)
    lengthTrajectoryUnitLabel = qt.QLabel('mm  ')
    cannulaLengthInfoLayout.addWidget(lengthTrajectoryUnitLabel)
    self.infoGroupBoxLayout.addLayout(cannulaLengthInfoLayout)

    #-- Clear Point
    self.clearTrajectoryButton = qt.QPushButton("Clear")
    self.clearTrajectoryButton.toolTip = "Remove Trajectory"
    self.clearTrajectoryButton.enabled = True
    #trajectoryLayout.addWidget(self.clearTrajectoryButton)
    
    createPlanningLineHorizontalLayout = qt.QHBoxLayout()
    self.lockTrajectoryCheckBox = qt.QCheckBox()
    self.lockTrajectoryCheckBox.checked = 0
    self.lockTrajectoryCheckBox.setToolTip("If checked, the trajectory will be locked.")
    createPlanningLineHorizontalLayout.addWidget(self.lockTrajectoryCheckBox)

    self.confirmBox = qt.QGroupBox()
    confirmLayout = qt.QVBoxLayout()
    confirmLayout.setAlignment(qt.Qt.AlignCenter)
    self.confirmBox.setLayout(confirmLayout)
    self.createPlanningLineButton = qt.QPushButton("")
    self.createPlanningLineButton.toolTip = "Confirm the target and generate the planning line."
    self.createPlanningLineButton.enabled = True
    confirmLabel = qt.QLabel('   Confirm')
    #confirmLayout.addWidget(confirmLabel)
    confirmLayout.addWidget(self.createPlanningLineButton)

    self.createPlanningLineButton.setMaximumHeight(buttonHeight)
    self.createPlanningLineButton.setMaximumWidth(buttonWidth)
    self.createPlanningLineButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "confirm.png"))))
    self.createPlanningLineButton.setIconSize(qt.QSize(self.createPlanningLineButton.size))
    self.confirmBox.setStyleSheet('QGroupBox{border:0;}')
    self.mainGUIGroupBoxLayout.addWidget(self.createPlanningLineButton, 2, 5)

    self.saveBox = qt.QGroupBox()
    saveLayout = qt.QVBoxLayout()
    saveLayout.setAlignment(qt.Qt.AlignCenter)
    self.saveBox.setLayout(saveLayout)
    self.saveDataButton = qt.QPushButton("")
    self.saveDataButton.toolTip = "Save the scene and data"
    self.saveDataButton.enabled = True
    self.saveDataButton.connect('clicked(bool)', self.onSaveData)
    saveLabel = qt.QLabel('Save Result')
    #saveLayout.addWidget(saveLabel)
    saveLayout.addWidget(self.saveDataButton)

    self.saveDataButton.setMaximumHeight(buttonHeight)
    self.saveDataButton.setMaximumWidth(buttonWidth)
    self.saveDataButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "save.png"))))
    self.saveDataButton.setIconSize(qt.QSize(self.createPlanningLineButton.size))
    self.saveBox.setStyleSheet('QGroupBox{border:0;}')
    self.mainGUIGroupBoxLayout.addWidget(self.saveDataButton, 2, 6)

    self.setReverseViewButton = qt.QPushButton("Set Reverse 3D View")
    self.setReverseViewButton.setMinimumWidth(150)
    self.setReverseViewButton.toolTip = "Change the perspective view in 3D viewer."
    self.setReverseViewButton.enabled = True
    createPlanningLineHorizontalLayout.addWidget(self.setReverseViewButton)
    self.createPlanningLineButton.connect('clicked(bool)', self.onCreatePlanningLine)
    self.setReverseViewButton.connect('clicked(bool)', self.onSetReverseView)
    self.isReverseView = False

     # Needle trajectory
    self.addCannulaTargetButton.connect('clicked(bool)', self.onEditPlanningTarget)
    #self.addCannulaDistalButton.connect('clicked(bool)', self.onEditPlanningDistal)
    self.generatePathButton.connect('clicked(bool)', self.onGeneratePath)
    self.clearTrajectoryButton.connect('clicked(bool)', self.onClearTrajectory)
    self.lockTrajectoryCheckBox.connect('toggled(bool)', self.onLock)
    

    #
    # Mid-sagittalReference line
    #
    planningSagittalLineLayout = qt.QHBoxLayout()

    #-- Curve length
    lengthSagittalPlanningLineLabel = qt.QLabel('Sagittal Length:  ')
    planningSagittalLineLayout.addWidget(lengthSagittalPlanningLineLabel)
    self.lengthSagittalPlanningLineEdit = qt.QLineEdit()
    self.lengthSagittalPlanningLineEdit.text = '--'
    self.lengthSagittalPlanningLineEdit.setMaxLength(5)
    self.lengthSagittalPlanningLineEdit.readOnly = True
    self.lengthSagittalPlanningLineEdit.frame = True
    self.lengthSagittalPlanningLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthSagittalPlanningLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningSagittalLineLayout.addWidget(self.lengthSagittalPlanningLineEdit)
    lengthSagittalPlanningLineUnitLabel = qt.QLabel('mm  ')
    planningSagittalLineLayout.addWidget(lengthSagittalPlanningLineUnitLabel)

    planningCoronalLineLayout = qt.QHBoxLayout()
    lengthCoronalPlanningLineLabel = qt.QLabel('Coronal Length: ')
    planningCoronalLineLayout.addWidget(lengthCoronalPlanningLineLabel)
    self.lengthCoronalPlanningLineEdit = qt.QLineEdit()
    self.lengthCoronalPlanningLineEdit.text = '--'
    self.lengthCoronalPlanningLineEdit.setMaxLength(5)
    self.lengthCoronalPlanningLineEdit.readOnly = True
    self.lengthCoronalPlanningLineEdit.frame = True
    self.lengthCoronalPlanningLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthCoronalPlanningLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningCoronalLineLayout.addWidget(self.lengthCoronalPlanningLineEdit)
    lengthCoronalPlanningLineUnitLabel = qt.QLabel('mm  ')
    planningCoronalLineLayout.addWidget(lengthCoronalPlanningLineUnitLabel)

    planningPitchAngleLayout = qt.QHBoxLayout()
    #-- Curve length
    pitchAngleLabel = qt.QLabel('Pitch Angle:       ')
    planningPitchAngleLayout.addWidget(pitchAngleLabel)
    self.pitchAngleEdit = qt.QLineEdit()
    self.pitchAngleEdit.text = '--'
    self.pitchAngleEdit.setMaxLength(5)
    self.pitchAngleEdit.readOnly = True
    self.pitchAngleEdit.frame = True
    self.pitchAngleEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.pitchAngleEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningPitchAngleLayout.addWidget(self.pitchAngleEdit)
    pitchAngleUnitLabel = qt.QLabel('degree  ')
    planningPitchAngleLayout.addWidget(pitchAngleUnitLabel)

    planningYawAngleLayout = qt.QHBoxLayout()
    yawAngleLabel = qt.QLabel('Yaw Angle:        ')
    planningYawAngleLayout.addWidget(yawAngleLabel)
    self.yawAngleEdit = qt.QLineEdit()
    self.yawAngleEdit.text = '--'
    self.yawAngleEdit.setMaxLength(5)
    self.yawAngleEdit.readOnly = True
    self.yawAngleEdit.frame = True
    self.yawAngleEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.yawAngleEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningYawAngleLayout.addWidget(self.yawAngleEdit)
    yawAngleUnitLabel = qt.QLabel('degree  ')
    planningYawAngleLayout.addWidget(yawAngleUnitLabel)

    planningCannulaToNormAngleLayout = qt.QHBoxLayout()
    cannulaToNormAngleLabel = qt.QLabel('Cannula To Norm Angle:   ')
    planningCannulaToNormAngleLayout.addWidget(cannulaToNormAngleLabel)
    self.cannulaToNormAngleEdit = qt.QLineEdit()
    self.cannulaToNormAngleEdit.text = '--'
    self.cannulaToNormAngleEdit.setMaxLength(5)
    self.cannulaToNormAngleEdit.readOnly = True
    self.cannulaToNormAngleEdit.frame = True
    self.cannulaToNormAngleEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.cannulaToNormAngleEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningCannulaToNormAngleLayout.addWidget(self.cannulaToNormAngleEdit)
    cannulaToNormAngleUnitLabel = qt.QLabel('degree  ')
    planningCannulaToNormAngleLayout.addWidget(cannulaToNormAngleUnitLabel)


    planningCannulaToCoronalAngleLayout = qt.QHBoxLayout()
    cannulaToCoronalAngleLabel = qt.QLabel('Cannula To Coronal Angle:')
    planningCannulaToCoronalAngleLayout.addWidget(cannulaToCoronalAngleLabel)
    self.cannulaToCoronalAngleEdit = qt.QLineEdit()
    self.cannulaToCoronalAngleEdit.text = '--'
    self.cannulaToCoronalAngleEdit.setMaxLength(5)
    self.cannulaToCoronalAngleEdit.readOnly = True
    self.cannulaToCoronalAngleEdit.frame = True
    self.cannulaToCoronalAngleEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.cannulaToCoronalAngleEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningCannulaToCoronalAngleLayout.addWidget(self.cannulaToCoronalAngleEdit)
    cannulaToCoronalAngleUnitLabel = qt.QLabel('degree  ')
    planningCannulaToCoronalAngleLayout.addWidget(cannulaToCoronalAngleUnitLabel)

    planningSkullNormToSagittalAngleLayout = qt.QHBoxLayout()
    skullNormToSagittalAngleLabel = qt.QLabel('Skull Norm To Sagital Angle:')
    planningSkullNormToSagittalAngleLayout.addWidget(skullNormToSagittalAngleLabel)
    self.skullNormToSagittalAngleEdit = qt.QLineEdit()
    self.skullNormToSagittalAngleEdit.text = '--'
    self.skullNormToSagittalAngleEdit.setMaxLength(5)
    self.skullNormToSagittalAngleEdit.readOnly = True
    self.skullNormToSagittalAngleEdit.frame = True
    self.skullNormToSagittalAngleEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.skullNormToSagittalAngleEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningSkullNormToSagittalAngleLayout.addWidget(self.skullNormToSagittalAngleEdit)
    skullNormToSagittalAngleUnitLabel = qt.QLabel('degree  ')
    planningSkullNormToSagittalAngleLayout.addWidget(skullNormToSagittalAngleUnitLabel)

    planningSkullNormToCoronalAngleLayout = qt.QHBoxLayout()
    skullNormToCoronalAngleLabel = qt.QLabel('Skull Norm To Coronal Angle:')
    planningSkullNormToCoronalAngleLayout.addWidget(skullNormToCoronalAngleLabel)
    self.skullNormToCoronalAngleEdit = qt.QLineEdit()
    self.skullNormToCoronalAngleEdit.text = '--'
    self.skullNormToCoronalAngleEdit.setMaxLength(5)
    self.skullNormToCoronalAngleEdit.readOnly = True
    self.skullNormToCoronalAngleEdit.frame = True
    self.skullNormToCoronalAngleEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.skullNormToCoronalAngleEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningSkullNormToCoronalAngleLayout.addWidget(self.skullNormToCoronalAngleEdit)
    skullNormToCoronalAngleUnitLabel = qt.QLabel('degree  ')
    planningSkullNormToCoronalAngleLayout.addWidget(skullNormToCoronalAngleUnitLabel)




    self.infoGroupBoxLayout.addLayout(planningSagittalLineLayout)
    self.infoGroupBoxLayout.addLayout(planningCoronalLineLayout)
    self.infoGroupBoxLayout.addLayout(planningPitchAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningYawAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningSkullNormToSagittalAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningSkullNormToCoronalAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningCannulaToNormAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningCannulaToCoronalAngleLayout)

    #end of GUI section
    #####################################
    self.viewGroupBox = qt.QGroupBox()
    self.viewGroupBoxLayout = qt.QVBoxLayout()
    self.viewGroupBox.setLayout(self.viewGroupBoxLayout)
    self.layout.addWidget(self.viewGroupBox)

    viewGroupBoxLabel = qt.QLabel('Viewer Configuration')
    self.viewGroupBoxLayout.addWidget(viewGroupBoxLabel)

    self.viewSubGroupBox = qt.QGroupBox()
    self.viewSubGroupBoxLayout = qt.QHBoxLayout()
    self.viewSubGroupBox.setLayout(self.viewSubGroupBoxLayout)
    self.viewGroupBoxLayout.addWidget(self.viewSubGroupBox)
    #self.viewSubGroupBox.setStyleSheet("border:3")

    venousVolumeLabel = qt.QLabel('Venous Image')
    self.viewSubGroupBoxLayout.addWidget(venousVolumeLabel)
    self.imageSlider = qt.QSlider(qt.Qt.Horizontal)
    self.imageSlider.setMinimum(0)
    self.imageSlider.setMaximum(100)
    self.viewSubGroupBoxLayout.addWidget(self.imageSlider)
    ventricleVolumeLabel = qt.QLabel('Ventricle Image')
    self.setWindowLevelButton = WindowLevelEffectsButton()
    self.sliceWidgets = self.setWindowLevelButton.sliceWidgets
    self.viewSubGroupBoxLayout.addWidget(ventricleVolumeLabel)
    self.viewSubGroupBoxLayout.addWidget(self.setWindowLevelButton, 0, 3)
    self.viewGroupBoxLayout.addWidget(self.setReverseViewButton)

    self.imageSlider.connect('valueChanged(int)', self.onChangeSliceViewImage)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect(self.inputVolumeSelector.currentNode())
    self.logic.setSliceViewer()

  def cleanup(self):
    pass
  
  def initialFieldsValue(self):
    self.lengthSagittalPlanningLineEdit.text = '--'
    self.lengthCoronalPlanningLineEdit.text = '--'
    self.lengthCannulaEdit.text = '--'
    self.logic.clearSagittalPlanningLine()
    self.logic.clearCoronalPlanningLine()
    self.logic.clearSagittalReferenceLine()
    self.logic.clearCoronalReferenceLine()

  def onLoadCase(self):
    self.logic.baseVolumeNode = None
    self.logic.ventricleVolume = None
    self.inputVolumeSelector.setCurrentNode(None)
    self.dicomWidget.detailsPopup.open()
    pass

  def onAddedNode(self, addedNode):
    if addedNode.IsA("vtkMRMLVolumeNode"):
      volumeName = addedNode.GetName()
      validNode = False
      if ("Venous" in volumeName) or ("venous" in volumeName) :
        self.logic.baseVolumeNode = addedNode
        validNode = True
      elif ("Ventricle" in volumeName) or ("ventricle" in volumeName) :
        self.logic.ventricleVolume = addedNode
        validNode = True
      if self.logic.baseVolumeNode and self.logic.ventricleVolume and validNode:
        self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_ventricleVolume", self.logic.ventricleVolume.GetID())
        self.caseNum = self.caseNum + 1
        self.onSelect(self.logic.baseVolumeNode)
        self.inputVolumeSelector.setCurrentNode(self.logic.baseVolumeNode)
        # the setForegroundVolume will not work, because the slicerapp triggers the SetBackgroundVolume after the volume is loaded



  def onSelect(self, selectedNode=None):
    if selectedNode:        
      self.initialFieldsValue()
      self.logic.baseVolumeNode = selectedNode
      ventricleVolumeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_ventricleVolume")
      if not ventricleVolumeID:
        slicer.util.warningDisplay("This case doesn't have the venous image, please load the data into slicer", windowTitle="")
      else:
        self.logic.ventricleVolume = slicer.mrmlScene.GetNodeByID(ventricleVolumeID)
      caseName = ""
      #if self.caseNum>1:
      #  caseName = self.logic.baseVolumeNode.GetName()
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_model",caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_nasion",caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPoint", caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_target",caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_distal", caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_cylindarRadius",caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_cannula", caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_skullNorm", caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_cannulaModel",caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_sagittalReferenceModel",caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_coronalReferenceModel",caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPlanningModel",caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_coronalPlanningModel",caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel",caseName)
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessVolume",caseName)
      #Set the cropped image for processing
      if selectedNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume"):
        self.logic.currentVolumeNode = slicer.mrmlScene.GetNodeByID(selectedNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume"))
      else:
        self.logic.currentVolumeNode = selectedNode  
      self.logic.updateMeasureLength(float(self.lengthSagittalReferenceLineEdit.text), float(self.lengthCoronalReferenceLineEdit.text))
      self.logic.updatePathPlanningRadius(float(self.radiusPathPlanningEdit.text))
      self.lengthSagittalReferenceLineEdit.text = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength")
      self.lengthCoronalReferenceLineEdit.text = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength")
      self.radiusPathPlanningEdit.text = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_planningRadius")

      ReferenceModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalReferenceModel")
      self.logic.sagittalReferenceCurveManager._curveModel = slicer.mrmlScene.GetNodeByID(ReferenceModelID)
      ReferenceModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalReferenceModel")
      self.logic.coronalReferenceCurveManager._curveModel = slicer.mrmlScene.GetNodeByID(ReferenceModelID)
      ReferenceModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPlanningModel")
      self.logic.sagittalPlanningCurveManager._curveModel = slicer.mrmlScene.GetNodeByID(ReferenceModelID)
      ReferenceModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalPlanningModel")
      self.logic.coronalPlanningCurveManager._curveModel = slicer.mrmlScene.GetNodeByID(ReferenceModelID)
      self.logic.sagittalReferenceCurveManager.startEditLine()
      self.logic.coronalReferenceCurveManager.startEditLine()
      self.logic.sagittalPlanningCurveManager.startEditLine()
      self.logic.coronalPlanningCurveManager.startEditLine()
      self.logic.trajectoryManager.startEditLine()
      self.logic.createTrueSagittalPlane()
      self.logic.createEntryPoint()
      cannulaModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cannulaModel")
      cannulaFiducialsID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cannula")
      self.logic.pathNavigationModel.SetDisplayVisibility(0)
      self.logic.cannulaManager._curveModel = slicer.mrmlScene.GetNodeByID(cannulaModelID)
      self.logic.cannulaManager.curveFiducials = slicer.mrmlScene.GetNodeByID(cannulaFiducialsID)
      self.logic.cannulaManager.curveFiducials.AddObserver(slicer.vtkMRMLMarkupsNode().PointStartInteractionEvent, self.logic.updateSelectedMarker)
      self.logic.cannulaManager.curveFiducials.AddObserver(slicer.vtkMRMLMarkupsNode().PointModifiedEvent, self.logic.updateCannulaPosition)
      self.logic.cannulaManager.curveFiducials.AddObserver(slicer.vtkMRMLMarkupsNode().PointEndInteractionEvent, self.logic.endTrajectoryInteraction)
      self.logic.cannulaManager.setModifiedEventHandler(self.onCannulaModified)
      self.logic.cannulaManager.startEditLine()
      self.logic.createVentricleCylindar()
      #self.logic.generatePath()
      self.onCreatePlanningLine()
      self.isReverseView = False
      self.onCreateModel()
      self.onVenousGrayScaleCalc()
      self.logic.setSliceViewer()
      layoutManager = slicer.app.layoutManager()
      threeDView = layoutManager.threeDWidget(0).threeDView()
      threeDView.resetFocalPoint()
      threeDView.lookFromViewAxis(ctkAxesWidget.Anterior)
    pass

  def onCreatePlanningLine(self):
    self.logic.pitchAngle="--"
    self.logic.yawAngle = "--"
    self.logic.skullNormToSaggitalAngle = "--"
    self.logic.skullNormToCoronalAngle = "--"
    self.logic.cannulaToNormAngle = "--"
    self.logic.cannulaToCoronalAngle = "--"
    self.logic.pathCandidatesModel.SetDisplayVisibility(0)
    if self.logic.createPlanningLine():
      self.logic.calcPitchYawAngles()
      self.lengthSagittalPlanningLineEdit.text = '%.1f' % self.logic.getSagittalPlanningLineLength()
      self.lengthCoronalPlanningLineEdit.text = '%.1f' % self.logic.getCoronalPlanningLineLength()
      self.pitchAngleEdit.text = '%.1f' % self.logic.pitchAngle
      self.yawAngleEdit.text = '%.1f' % (-self.logic.yawAngle)
      if self.logic.calcCannulaAngles():
        self.cannulaToNormAngleEdit.text = '%.1f' % self.logic.cannulaToNormAngle
        self.cannulaToCoronalAngleEdit.text = '%.1f' % self.logic.cannulaToCoronalAngle
        self.skullNormToSagittalAngleEdit.text = '%.1f' % self.logic.skullNormToSaggitalAngle
        self.skullNormToCoronalAngleEdit.text = '%.1f' % self.logic.skullNormToCoronalAngle
    if self.logic.baseVolumeNode:
      cannulaNode = slicer.mrmlScene.GetNodeByID(self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cannula"))
      cannulaNode.AddObserver(cannulaNode.PointStartInteractionEvent, self.onResetPlanningOutput)
    pass

  @vtk.calldata_type(vtk.VTK_INT)
  def onResetPlanningOutput(self, node, eventID, callData):
    self.lengthCannulaEdit.text = '--'
    self.lengthSagittalPlanningLineEdit.text = '--'
    self.lengthCoronalPlanningLineEdit.text = '--'
    self.pitchAngleEdit.text = '--'
    self.yawAngleEdit.text = '--'
    self.cannulaToCoronalAngleEdit.text = '--'
    self.cannulaToNormAngleEdit.text = '--'
    self.skullNormToSagittalAngleEdit.text = '--'
    self.skullNormToCoronalAngleEdit.text = '--'

  def onSetReverseView(self):
    if self.logic.baseVolumeNode:
      layoutManager = slicer.app.layoutManager()
      threeDView = layoutManager.threeDWidget(0).threeDView()
      if self.isReverseView == False:
        displayManagers = vtk.vtkCollection()
        threeDView.getDisplayableManagers(displayManagers)
        for index in range(displayManagers.GetNumberOfItems()):
          if displayManagers.GetItemAsObject(index).GetClassName() == 'vtkMRMLCameraDisplayableManager':
            self.camera = displayManagers.GetItemAsObject(index).GetCameraNode().GetCamera()
            self.cameraPos = self.camera.GetPosition()
        threeDView.lookFromViewAxis(ctkAxesWidget.Posterior)
        threeDView.pitchDirection = threeDView.PitchUp
        threeDView.yawDirection = threeDView.YawRight
        threeDView.setPitchRollYawIncrement(self.logic.pitchAngle)
        threeDView.pitch()
        if self.logic.yawAngle < 0:
          threeDView.setPitchRollYawIncrement(self.logic.yawAngle)
        else:
          threeDView.setPitchRollYawIncrement(360-self.logic.yawAngle)
        threeDView.yaw()
        cannulaNode = slicer.mrmlScene.GetNodeByID(self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cannula"))
        if cannulaNode and cannulaNode.GetNumberOfFiducials()>=2:
          posSecond = [0.0]*3
          cannulaNode.GetNthFiducialPosition(1, posSecond)
          threeDView.setFocalPoint(posSecond[0],posSecond[1],posSecond[2])
        self.setReverseViewButton.setText("  Reset View     ")
        self.isReverseView = True
      else:
        self.camera.SetPosition(self.cameraPos)
        threeDView.zoomIn()# to refresh the 3D viewer, when the view position is inside the skull model, the model is not rendered,
        threeDView.zoomOut()# Zoom in and out will refresh the viewer
        self.setReverseViewButton.setText("Set Reverse View")
        self.isReverseView = False
    pass

  def onChangeSliceViewImage(self, sliderValue):
    red_widget = slicer.app.layoutManager().sliceWidget("Red")
    red_logic = red_widget.sliceLogic()
    red_cn = red_logic.GetSliceCompositeNode()
    yellow_widget = slicer.app.layoutManager().sliceWidget("Yellow")
    yellow_logic = yellow_widget.sliceLogic()
    yellow_cn = yellow_logic.GetSliceCompositeNode()
    green_widget = slicer.app.layoutManager().sliceWidget("Green")
    green_logic = green_widget.sliceLogic()
    green_cn = green_logic.GetSliceCompositeNode()
    red_cn.SetForegroundOpacity(sliderValue/100.0)
    yellow_cn.SetForegroundOpacity(sliderValue/100.0)
    green_cn.SetForegroundOpacity(sliderValue/100.0)
    pass
    
  def onCreateModel(self):
    if self.inputVolumeSelector.currentNode():
      outputModelNodeID = self.inputVolumeSelector.currentNode().GetAttribute("vtkMRMLScalarVolumeNode.rel_model") 
      if outputModelNodeID:
        outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
        outputModelNode.SetAttribute("vtkMRMLModelNode.modelCreated","False")
        self.logic.createModel(outputModelNode, self.logic.threshold)
  
  def onSelectNasionPoint(self):
    if not self.inputVolumeSelector.currentNode():
      slicer.util.warningDisplay("No case is selceted, please select the case in the combox", windowTitle="")
    else:
      outputModelNodeID = self.inputVolumeSelector.currentNode().GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
      if outputModelNodeID:
        outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
        if (not outputModelNode) or outputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False":
            self.logic.createModel(outputModelNode, self.logic.threshold)
        self.logic.selectNasionPointNode(outputModelNode) # when the model is not available, the model will be created, so nodeAdded signal should be disconnected
        self.logic.setSliceViewer()

  def onSelectSagittalPoint(self):
    if not self.inputVolumeSelector.currentNode():
      slicer.util.warningDisplay("No case is selceted, please select the case in the combox", windowTitle="")
    else:
      outputModelNodeID = self.inputVolumeSelector.currentNode().GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
      if outputModelNodeID:
        outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
        if (not outputModelNode) or outputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False":
            self.logic.createModel(outputModelNode, self.logic.threshold)
        self.logic.selectSagittalPointNode(outputModelNode) # when the model is not available, the model will be created, so nodeAdded signal should be disconnected
        self.logic.setSliceViewer()

  def onSaveData(self):
    #caseDirectory = qt.QFileDialog.getExistingDirectory(self.parent.window(), "Select Case Directory", self.scriptDirectory)
    ioManager = slicer.app.ioManager()

    if not ioManager.openSaveDataDialog():
      return
    #caseSubDirectoryName = "Results" + str(qt.QDate().currentDate()) + "-" + qt.QTime().currentTime().toString().replace(":", "")
    #slicer.util.saveScene(os.path.join(caseDirectory, caseSubDirectoryName))
    pass
  
  def onDefineROI(self):
    self.logic.currentVolumeNode = self.logic.baseVolumeNode
    self.logic.setSliceViewer()
    self.logic.defineROI()
  
  def onCreateROI(self):
    self.logic.createROI()
    self.logic.setSliceViewer()
      
  def onModifyMeasureLength(self):
    sagittalReferenceLength = float(self.lengthSagittalReferenceLineEdit.text)
    coronalReferenceLength = float(self.lengthCoronalReferenceLineEdit.text)
    if self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength"):
        self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength", '%.1f' % sagittalReferenceLength) 
    if self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength"):
        self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength", '%.1f' % coronalReferenceLength)    

  def onModifyPathPlanningRadius(self):
    radius = float(self.radiusPathPlanningEdit.text)
    if self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_planningRadius"):
      self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_planningRadius", '%.1f' % radius)


  def onCreateEntryPoint(self):
    self.onModifyMeasureLength()
    self.onModifyPathPlanningRadius()
    self.logic.createEntryPoint()

  # Event handlers for sagittalReference line
  def onEditSagittalReferenceLine(self, switch):

    if switch == True:
      self.addCannulaTargetButton.checked = False
      self.logic.startEditSagittalReferenceLine()
    else:
      self.logic.endEditSagittalReferenceLine()

  def onClearSagittalReferenceLine(self):
    self.logic.clearSagittalReferenceLine()

  def onSagittalReferenceLineModified(self, caller, event):
    self.lengthSagittalReferenceLineEdit.text = '%.2f' % self.logic.getSagittalReferenceLineLength()

  def onMoveSliceSagittalReferenceLine(self):
    self.logic.moveSliceSagittalReferenceLine()

  # Event handlers for coronalReference line
  def onEditCoronalReferenceLine(self, switch):

    if switch == True:
      self.addCannulaTargetButton.checked = False
      self.logic.startEditCoronalReferenceLine()
    else:
      self.logic.endEditCoronalReferenceLine()

  def onClearCoronalReferenceLine(self):
    self.logic.clearCoronalReferenceLine()

  def onCoronalReferenceLineModified(self, caller, event):
    self.lengthCoronalReferenceLineEdit.text = '%.2f' % self.logic.getCoronalReferenceLineLength()
    
  def onMoveSliceCoronalReferenceLine(self):
    self.logic.moveSliceCoronalReferenceLine()
  
  def onVenousGrayScaleCalc(self):
    if self.logic.baseVolumeNode:
      croppedVolumeNode = self.logic.baseVolumeNode
      croppedVolumeNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume")
      if croppedVolumeNodeID:
        croppedVolumeNode = slicer.mrmlScene.GetNodeByID(croppedVolumeNodeID)
      grayScaleModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel")
      if not grayScaleModelNodeID:
        grayScaleModelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        slicer.mrmlScene.AddNode(grayScaleModelNode)
        modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
        ModelColor = [0.5, 0.0, 0.0]
        modelDisplayNode.SetColor(ModelColor)
        modelDisplayNode.SetOpacity(0.5)
        slicer.mrmlScene.AddNode(modelDisplayNode)
        grayScaleModelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
        self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel",grayScaleModelNode.GetID())
        grayScaleModelNodeID = grayScaleModelNode.GetID()
        grayScaleModelNode = slicer.mrmlScene.GetNodeByID(grayScaleModelNodeID)
        self.vesselnessCalcButton.setEnabled(0)
        self.grayScaleMakerButton.setEnabled(0)
        self.logic.calculateVenousGrayScale(croppedVolumeNode, grayScaleModelNode)
        self.logic.cliNode.AddObserver('ModifiedEvent', self.onCalculateVenousCompletion)

    pass
  
  def onVenousVesselnessCalc(self):
    if self.logic.baseVolumeNode:
      croppedVolumeNode = self.logic.baseVolumeNode
      croppedVolumeNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume")
      if croppedVolumeNodeID:
        croppedVolumeNode = slicer.mrmlScene.GetNodeByID(croppedVolumeNodeID)
      vesselnessVolumeNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessVolume")
      if not vesselnessVolumeNodeID:
        vesselnessVolumeNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLScalarVolumeNode")
        vesselnessVolumeNode.SetName("VesselnessVolume-NotShownEntity31415")
        slicer.mrmlScene.AddNode(vesselnessVolumeNode)
        self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessVolume",vesselnessVolumeNode.GetID())
        vesselnessVolumeNodeID = vesselnessVolumeNode.GetID()
        vesselnessVolumeNode = slicer.mrmlScene.GetNodeByID(vesselnessVolumeNodeID)
        self.vesselnessCalcButton.setEnabled(0)
        self.grayScaleMakerButton.setEnabled(0)
        self.logic.calculateVenousVesselness(croppedVolumeNode, vesselnessVolumeNode)
        self.logic.cliNode.AddObserver('ModifiedEvent', self.onCalculateVenousCompletion)
    pass
  
  def onCalculateVenousCompletion(self,node,event):
    status = node.GetStatusString()
    self.venousCalcStatus.setText(node.GetName() +' '+status)
    if status == 'Completed':
      self.vesselnessCalcButton.setEnabled(1)
      self.grayScaleMakerButton.setEnabled(1)
      #self.onSelect(self.logic.baseVolumeNode)
      self.logic.calculateGrayScaleWithMargin()
      self.logic.setSliceViewer()## the slice widgets are set to none after the  cli module calculation. reason unclear...
    pass
  
  # Event handlers for trajectory
  def onEditPlanningTarget(self):
    self.imageSlider.setValue(100.0)
    self.lengthCannulaEdit.text = '--'
    self.lengthSagittalPlanningLineEdit.text = '--'
    self.lengthCoronalPlanningLineEdit.text = '--'
    self.pitchAngleEdit.text = '--'
    self.yawAngleEdit.text = '--'
    self.logic.setSliceForCylindar()
    self.logic.startEditPlanningTarget()

  # Event handlers for trajectory
  def onEditPlanningDistal(self):
    self.imageSlider.setValue(100.0)
    self.lengthCannulaEdit.text = '--'
    self.lengthSagittalPlanningLineEdit.text = '--'
    self.lengthCoronalPlanningLineEdit.text = '--'
    self.pitchAngleEdit.text = '--'
    self.yawAngleEdit.text = '--'
    self.logic.startEditPlanningDistal()

  def onGeneratePath(self):
    self.logic.generatePath()
    
  def onClearTrajectory(self):
    self.logic.clearTrajectory()
    
  def onCannulaModified(self, caller, event):
    self.lengthCannulaEdit.text = '%.2f' % self.logic.getCannulaLength()

  # Event handlers for sagittalPlanning line
  def onEditSagittalPlanningLine(self, switch):

    if switch == True:
      self.addCannulaTargetButton.checked = False
      self.logic.startEditSagittalPlanningLine()
    else:
      self.logic.endEditSagittalPlanningLine()

  def onClearSagittalPlanningLine(self):
    self.logic.clearSagittalPlanningLine()

  def onSagittalPlanningLineModified(self, caller, event):
    self.lengthSagittalPlanningLineEdit.text = '%.2f' % self.logic.getSagittalPlanningLineLength()

  def onMoveSliceSagittalPlanningLine(self):
    self.logic.moveSliceSagittalPlanningLine()

  # Event handlers for coronalPlanning line
  def onEditCoronalPlanningLine(self, switch):

    if switch == True:
      self.addCannulaTargetButton.checked = False
      self.logic.startEditCoronalPlanningLine()
    else:
      self.logic.endEditCoronalPlanningLine()

  def onClearCoronalPlanningLine(self):
    
    self.logic.clearCoronalPlanningLine()

  def onCoronalPlanningLineModified(self, caller, event):
    self.lengthCoronalPlanningLineEdit.text = '%.2f' % self.logic.getCoronalPlanningLineLength()
    
  def onMoveSliceCoronalPlanningLine(self):
    self.logic.moveSliceCoronalPlanningLine()

  def onLock(self):
    if self.lockTrajectoryCheckBox.checked == 1:
      self.addCannulaTargetButton.enabled = False
      self.clearTrajectoryButton.enabled = False
      self.logic.lockTrajectoryLine()
    else:
      self.addCannulaTargetButton.enabled = True
      self.clearTrajectoryButton.enabled = True
      self.logic.unlockTrajectoryLine()

  def onReload(self,moduleName="VentriculostomyPlanning"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    self.logic.clear()
    slicer.mrmlScene.Clear(0)
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)
    self.logic = VentriculostomyPlanningLogic()
    
class CurveManager():

  def __init__(self):
    try:
      import CurveMaker
    except ImportError:
      return slicer.util.warningDisplay(
            "Error: Could not find extension CurveMaker. Open Slicer Extension Manager and install "
       "CurveMaker.", "Missing Extension")
    self.cmLogic = CurveMaker.CurveMakerLogic()
    self.curveFiducials = None
    self._curveModel = None
    self.opacity = 1
    self.tubeRadius = 1.0
    self.curveName = ""
    self.curveModelName = ""
    self.step = 1
    self.tagEventExternal = None
    self.externalHandler = None

    self.sliceID = "vtkMRMLSliceNodeRed"

    # Slice is aligned to the first point (0) or last point (1)
    self.slicePosition = 0

  def setName(self, name):
    self.curveName = name
    self.curveModelName = "%s-Model" % (name)

  def setSliceID(self, name):
    # ID is either "vtkMRMLSliceNodeRed", "vtkMRMLSliceNodeYellow", or "vtkMRMLSliceNodeGreen"
    self.sliceID = name

  def setDefaultSlicePositionToFirstPoint(self):
    self.slicePosition = 0

  def setDefaultSlicePositionToLastPoint(self):
    self.slicePosition = 1
    
  def setModelColor(self, r, g, b):

    self.cmLogic.ModelColor = [r, g, b]
    
    # Make slice intersetion visible
    if self._curveModel:
      dnode = self._curveModel.GetDisplayNode()
      if dnode:
        dnode.SetColor([r, g, b])

    if self.curveFiducials:
      dnode = self.curveFiducials.GetMarkupsDisplayNode()
      if dnode:
        dnode.SetSelectedColor([r, g, b])

  def setModelOpacity(self, opacity):
    # Make slice intersetion visible
    self.opacity = opacity
    if self._curveModel:
      dnode = self._curveModel.GetDisplayNode()
      if dnode:
        dnode.opacity(opacity)

  def setManagerTubeRadius(self,radius):
    self.tubeRadius = radius

  def setModifiedEventHandler(self, handler = None):

    self.externalHandler = handler
    
    if self._curveModel:
      self.tagEventExternal = self._curveModel.AddObserver(vtk.vtkCommand.ModifiedEvent, self.externalHandler)
      return self.tagEventExternal
    else:
      return None

  def resetModifiedEventHandle(self):
    
    if self._curveModel and self.tagEventExternal:
      self._curveModel.RemoveObserver(self.tagEventExternal)

    self.externalHandler = None
    self.tagEventExternal = None

  def onLineSourceUpdated(self,caller=None,event=None):
    
    self.cmLogic.updateCurve()

    # Make slice intersetion visible
    if self._curveModel:
      dnode = self._curveModel.GetDisplayNode()
      if dnode:
        dnode.SetSliceIntersectionVisibility(1)
    
  def startEditLine(self, initPoint=None):

    if self.curveFiducials == None:
      self.curveFiducials = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
      self.curveFiducials.SetName(self.curveName)
      slicer.mrmlScene.AddNode(self.curveFiducials)
      dnode = self.curveFiducials.GetMarkupsDisplayNode()
      if dnode:
        dnode.SetSelectedColor(self.cmLogic.ModelColor)
    if initPoint != None:
      self.curveFiducials.AddFiducial(initPoint[0],initPoint[1],initPoint[2])
      self.moveSliceToLine()
      
    if self._curveModel == None:
      self._curveModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
      self._curveModel.SetName(self.curveModelName)
      self.setModelOpacity(self.opacity)
      slicer.mrmlScene.AddNode(self._curveModel)
      modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
      modelDisplayNode.SetColor(self.cmLogic.ModelColor)
      modelDisplayNode.SetOpacity(self.opacity)
      slicer.mrmlScene.AddNode(modelDisplayNode)
      self._curveModel.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

    # Set exetrnal handler, if it has not been.
    if self.tagEventExternal == None and self.externalHandler:
      self.tagEventExternal = self._curveModel.AddObserver(vtk.vtkCommand.ModifiedEvent, self.externalHandler)
      
    self.cmLogic.DestinationNode = self._curveModel
    self.cmLogic.SourceNode = self.curveFiducials
    self.cmLogic.SourceNode.SetAttribute('CurveMaker.CurveModel', self.cmLogic.DestinationNode.GetID())
    self.cmLogic.updateCurve()

    self.cmLogic.CurvePoly = vtk.vtkPolyData() ## For CurveMaker bug
    self.cmLogic.enableAutomaticUpdate(1)
    self.cmLogic.setInterpolationMethod(1)
    self.cmLogic.setTubeRadius(self.tubeRadius)

    self.tagSourceNode = self.cmLogic.SourceNode.AddObserver('ModifiedEvent', self.onLineSourceUpdated)

  def endEditLine(self):

    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)  ## Turn off
    
  def clearLine(self):

    if self.curveFiducials:
      self.curveFiducials.RemoveAllMarkups()
      #To trigger the initializaton, when the user clear the trajectory and restart the planning, 
      #the last point of the coronal reference line should be added to the trajectory

    self.cmLogic.updateCurve()

    if self._curveModel:
      pdata = self._curveModel.GetPolyData()
      if pdata:
        pdata.Initialize()

  def getLength(self):

    return self.cmLogic.CurveLength

  def getFirstPoint(self, position):

    if self.curveFiducials == None:
      return False
    elif self.curveFiducials.GetNumberOfFiducials() == 0:
      return False
    else:
      self.curveFiducials.GetNthFiducialPosition(0,position)
      return True

  def getLastPoint(self, position):
    if self.curveFiducials == None:
      return False
    else:
      nFiducials = self.curveFiducials.GetNumberOfFiducials()
      if nFiducials == 0:
        return False
      else:
        self.curveFiducials.GetNthFiducialPosition(nFiducials-1,position)
        return True

  def moveSliceToLine(self):

    viewer = slicer.mrmlScene.GetNodeByID(self.sliceID)

    if viewer == None:
      return

    if self.curveFiducials.GetNumberOfFiducials() == 0:
      return

    if self.slicePosition == 0:
      index = 0
    else:
      index = self.curveFiducials.GetNumberOfFiducials()-1

    pos = [0.0] * 3
    self.curveFiducials.GetNthFiducialPosition(index,pos)

    if self.sliceID == "vtkMRMLSliceNodeRed":
      viewer.SetOrientationToAxial()
      viewer.SetSliceOffset(pos[2])
    elif self.sliceID == "vtkMRMLSliceNodeYellow":
      viewer.SetOrientationToSagittal()
      viewer.SetSliceOffset(pos[0])
    elif self.sliceID == "vtkMRMLSliceNodeGreen":
      viewer.SetOrientationToCoronal()
      viewer.SetSliceOffset(pos[1])

  def lockLine(self):
    
    if (self.curveFiducials):
      self.curveFiducials.SetDisplayVisibility(0)

  def unlockLine(self):
    
    if (self.curveFiducials):
      self.curveFiducials.SetDisplayVisibility(1)
      

#
# VentriculostomyPlanningLogic
#

class VentriculostomyPlanningLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    self.sagittalReferenceCurveManager = CurveManager()
    self.sagittalReferenceCurveManager.setName("SR1")
    self.sagittalReferenceCurveManager.setSliceID("vtkMRMLSliceNodeYellow")
    self.sagittalReferenceCurveManager.setDefaultSlicePositionToFirstPoint()
    self.sagittalReferenceCurveManager.setModelColor(1.0, 1.0, 0.5)
    
    self.coronalReferenceCurveManager = CurveManager()
    self.coronalReferenceCurveManager.setName("CR1")
    self.coronalReferenceCurveManager.setSliceID("vtkMRMLSliceNodeGreen")
    self.coronalReferenceCurveManager.setDefaultSlicePositionToLastPoint()
    self.coronalReferenceCurveManager.setModelColor(0.5, 1.0, 0.5)
    
    self.trajectoryManager = CurveManager()
    self.trajectoryManager.setName("T")
    self.trajectoryManager.setDefaultSlicePositionToLastPoint()
    self.trajectoryManager.setModelColor(0.0, 1.0, 1.0)
    self.trajectoryManager.setDefaultSlicePositionToFirstPoint()
    self.trajectoryManager.setModelOpacity(0.5)

    self.cannulaManager = CurveManager()
    self.cannulaManager.setName("Cannula")
    self.cannulaManager.setDefaultSlicePositionToLastPoint()
    self.cannulaManager.setModelColor(0.5, 1.0, 0.0)
    self.cannulaManager.setDefaultSlicePositionToFirstPoint()

    self.coronalPlanningCurveManager = CurveManager()
    self.coronalPlanningCurveManager.setName("CP1")
    self.coronalPlanningCurveManager.setSliceID("vtkMRMLSliceNodeGreen")
    self.coronalPlanningCurveManager.setDefaultSlicePositionToLastPoint()
    self.coronalPlanningCurveManager.setModelColor(0.0, 1.0, 0.0)

    self.sagittalPlanningCurveManager = CurveManager()
    self.sagittalPlanningCurveManager.setName("SP1")
    self.sagittalPlanningCurveManager.setSliceID("vtkMRMLSliceNodeYellow")
    self.sagittalPlanningCurveManager.setDefaultSlicePositionToFirstPoint()
    self.sagittalPlanningCurveManager.setModelColor(1.0, 1.0, 0.0)

    ##Path Planning variables
    self.PercutaneousApproachAnalysisLogic = PercutaneousApproachAnalysisLogic()
    self.cylindarMiddlePointNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    self.pathCandidatesModel = slicer.vtkMRMLModelNode()
    # Create display node
    modelDisplay = slicer.vtkMRMLModelDisplayNode()
    yellow = [1, 1, 0]
    modelDisplay.SetColor(yellow[0], yellow[1], yellow[2])
    modelDisplay.SetScene(slicer.mrmlScene)
    modelDisplay.SetVisibility(0)
    modelDisplay.SetSliceIntersectionVisibility(True)  # Show in slice view
    slicer.mrmlScene.AddNode(modelDisplay)
    self.pathCandidatesModel.SetAndObserveDisplayNodeID(modelDisplay.GetID())
    slicer.mrmlScene.AddNode(self.pathCandidatesModel)
    modelDisplay = slicer.vtkMRMLModelDisplayNode()
    modelDisplay.SetColor(yellow[0], yellow[1], yellow[2])
    modelDisplay.SetScene(slicer.mrmlScene)
    modelDisplay.SetVisibility(0)
    slicer.mrmlScene.AddNode(modelDisplay)
    self.pathNavigationModel = slicer.vtkMRMLModelNode()
    self.pathNavigationModel.SetAndObserveDisplayNodeID(modelDisplay.GetID())
    slicer.mrmlScene.AddNode(self.pathNavigationModel)
    self.pathCandidatesPoly = vtk.vtkPolyData()
    self.pathNavigationPoly = vtk.vtkPolyData()
    ##

    self.ROIListNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLAnnotationHierarchyNode")
    self.ROIListNode.SetName("ROIListForAllCases")
    self.ROIListNode.HideFromEditorsOff()
    slicer.mrmlScene.AddNode(self.ROIListNode)
    self.currentVolumeNode = None
    self.baseVolumeNode = None
    self.ventricleVolume = None
    self.useLeftHemisphere = False
    self.cliNode = None
    self.samplingFactor = 1
    self.topPoint = []
    self.resetROI = False 
    self.threshold = -500.0
    self.minimalVentricleLen = 10.0 # in mm
    self.yawAngle = 0.0
    self.pitchAngle = 0.0
    self.cannulaToNormAngle = 0.0
    self.cannulaToCoronalAngle = 0.0
    self.skullNormToCoronalAngle = 0.0
    self.skullNormToSagittalAngle = 0.0
    self.sagittalYawAngle = 0
    self.trueSagittalPlane = None
    self.activeTrajectoryMarkup = 0
    self.cylindarRadius = 2.5 # unit mm
    self.entryRadius = 25.0
    self.cylindarInteractor = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    self.cylindarInteractor.SetName("")
    slicer.mrmlScene.AddNode(self.cylindarInteractor)
    self.cylindarInteractor.AddObserver(slicer.vtkMRMLMarkupsNode().PointModifiedEvent, self.updateCylindarRadius)
    displayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsDisplayNode")
    slicer.mrmlScene.AddNode(displayNode)
    self.cylindarInteractor.SetAndObserveDisplayNodeID(displayNode.GetID())
    self.trajectoryProjectedMarker = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    self.trajectoryProjectedMarker.SetName("trajectoryProject")
    slicer.mrmlScene.AddNode(self.trajectoryProjectedMarker)
    self.nasionProjectedMarker = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    self.nasionProjectedMarker.SetName("nasionProject")
    slicer.mrmlScene.AddNode(self.nasionProjectedMarker)

    self.interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    self.interactionNode.AddObserver(self.interactionNode.EndPlacementEvent, self.endPlacement)
    self.interactionMode = "none"

  def clear(self):
    if self.trajectoryProjectedMarker and self.trajectoryProjectedMarker.GetID():
      slicer.mrmlScene.RemoveNode(slicer.mrmlScene.GetNodeByID(self.trajectoryProjectedMarker.GetID()))
      self.trajectoryProjectedMarker = None
    if self.nasionProjectedMarker and self.nasionProjectedMarker.GetID():
      slicer.mrmlScene.RemoveNode(slicer.mrmlScene.GetNodeByID(self.nasionProjectedMarker.GetID()))
      self.nasionProjectedMarker = None
    if self.pathCandidatesModel and self.pathCandidatesModel.GetID():
      slicer.mrmlScene.RemoveNode(self.pathCandidatesModel.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(self.pathCandidatesModel)
      self.pathCandidatesModel = None
    if self.pathNavigationModel and self.pathNavigationModel.GetID():
      slicer.mrmlScene.RemoveNode(self.pathNavigationModel.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(self.pathNavigationModel)
      self.pathNavigationModel = None
    if self.trajectoryProjectedMarker and self.trajectoryProjectedMarker.GetID():
      slicer.mrmlScene.RemoveNode(self.trajectoryProjectedMarker)
      self.trajectoryProjectedMarker = None
    if self.nasionProjectedMarker and self.nasionProjectedMarker.GetID():
      slicer.mrmlScene.RemoveNode(self.nasionProjectedMarker)
      self.nasionProjectedMarker = None

  def hasImageData(self,volumeNode):
    """This is an example logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      logging.debug('hasImageData failed: no volume node')
      return False
    if volumeNode.GetImageData() is None:
      logging.debug('hasImageData failed: no image data in volume node')
      return False
    return True

  def startEditSagittalReferenceLine(self):

    self.sagittalReferenceCurveManager.startEditLine()
    
  def endEditSagittalReferenceLine(self):

    self.sagittalReferenceCurveManager.endEditLine()

  def clearSagittalReferenceLine(self):
    
    self.sagittalReferenceCurveManager.clearLine()

  def setSagittalReferenceLineModifiedEventHandler(self, handler):

    self.sagittalReferenceCurveManager.setModifiedEventHandler(handler)

  def getSagittalReferenceLineLength(self):
    return self.sagittalReferenceCurveManager.getLength()

  def moveSliceSagittalReferenceLine(self):
    self.sagittalReferenceCurveManager.moveSliceToLine()

  def startEditCoronalReferenceLine(self):

    pos = [0.0] * 3
    self.sagittalReferenceCurveManager.getLastPoint(pos)
    self.coronalReferenceCurveManager.startEditLine(pos)
    
  def endEditCoronalReferenceLine(self):

    self.coronalReferenceCurveManager.endEditLine()

  def clearCoronalReferenceLine(self):
    
    self.coronalReferenceCurveManager.clearLine()

  def setCoronalReferenceLineModifiedEventHandler(self, handler):

    self.coronalReferenceCurveManager.setModifiedEventHandler(handler)

  def getCoronalReferenceLineLength(self):
    return self.coronalReferenceCurveManager.getLength()

  def moveSliceCoronalReferenceLine(self):
    self.coronalReferenceCurveManager.moveSliceToLine()

  def lockReferenceLine(self):
    self.sagittalReferenceCurveManager.lockLine()
    self.coronalReferenceCurveManager.lockLine()

  def unlockReferenceLine(self):
    self.sagittalReferenceCurveManager.unlockLine()
    self.coronalReferenceCurveManager.unlockLine()

  def setSliceViewer(self):
    red_widget = slicer.app.layoutManager().sliceWidget("Red")
    red_logic = red_widget.sliceLogic()
    red_cn = red_logic.GetSliceCompositeNode()

    yellow_widget = slicer.app.layoutManager().sliceWidget("Yellow")
    yellow_logic = yellow_widget.sliceLogic()
    yellow_cn = yellow_logic.GetSliceCompositeNode()

    green_widget = slicer.app.layoutManager().sliceWidget("Green")
    green_logic = green_widget.sliceLogic()
    green_cn = green_logic.GetSliceCompositeNode()

    if self.currentVolumeNode:
      red_cn.SetBackgroundVolumeID(self.currentVolumeNode.GetID())
      yellow_cn.SetBackgroundVolumeID(self.currentVolumeNode.GetID())
      green_cn.SetBackgroundVolumeID(self.currentVolumeNode.GetID())
      red_widget.fitSliceToBackground()
      yellow_widget.fitSliceToBackground()
      green_widget.fitSliceToBackground()

    if self.ventricleVolume:
      red_cn.SetForegroundVolumeID(self.ventricleVolume.GetID())
      yellow_cn.SetForegroundVolumeID(self.ventricleVolume.GetID())
      green_cn.SetForegroundVolumeID(self.ventricleVolume.GetID())
    pass
  
  def setSliceForCylindar(self):
    shiftX = 20
    shiftY = -40
    shiftZ = 50
    if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"):
      nasionNode = slicer.mrmlScene.GetNodeByID(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"))
      if (nasionNode.GetNumberOfFiducials() == 1):
        posNasion = numpy.array([0.0, 0.0, 0.0])
        nasionNode.GetNthFiducialPosition(0, posNasion)
        posTarget = numpy.array([posNasion[0]+shiftX,posNasion[1]+shiftY, posNasion[2]+shiftZ])
        direction = numpy.array([1,1,0])
        #posDistal = numpy.array([posTarget[0]-40, posTarget[1]-40, posTarget[2]])
        redSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeRed")
        yellowSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeYellow")
        greenSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeGreen")
        self.updateSliceViewBasedOnPoints(posTarget, posTarget+direction)
        lm = slicer.app.layoutManager()
        sliceLogics = lm.mrmlSliceLogics()
        for n in range(sliceLogics.GetNumberOfItems()):
          sliceLogic = sliceLogics.GetItemAsObject(n)
          sliceWidget = lm.sliceWidget(sliceLogic.GetName())
          if (sliceWidget.objectName == 'qMRMLSliceWidgetRed'):
            redSliceNode.SetFieldOfView(sliceWidget.width/3, sliceWidget.height/3, 0.5)
          if (sliceWidget.objectName == 'qMRMLSliceWidgetYellow'):
            yellowSliceNode.SetFieldOfView(sliceWidget.width/3, sliceWidget.height/3, 0.5)
          if (sliceWidget.objectName == 'qMRMLSliceWidgetGreen'):
            greenSliceNode.SetFieldOfView(sliceWidget.width/3, sliceWidget.height/3, 0.5)
        
    pass
  
  def initialSlicesOrientation(self):
    redSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeRed")
    redSliceNode.SetOrientation("Axial")    
    yellowSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeYellow")
    yellowSliceNode.SetOrientation("Sagittal") 
    greenSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeGreen")
    greenSliceNode.SetOrientation("Coronal") 
    
  def startEditPlanningTarget(self):
    if self.baseVolumeNode:
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target"):
        targetNode = slicer.mrmlScene.GetNodeByID(
          self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target"))
        targetNode.RemoveAllMarkups()
        #targetNode.SetLocked(True)
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        # interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if (selectionNode == None) or (self.interactionNode == None):
          return
        
        #self.initialSlicesOrientation()
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        selectionNode.SetActivePlaceNodeID(targetNode.GetID())
        self.interactionMode = "target"
        self.interactionNode.SwitchToSinglePlaceMode()
        self.interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)
        targetNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointModifiedEvent, self.createVentricleCylindar)
        targetNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointEndInteractionEvent, self.endModifiyCylindar)


  def endTargetSelectInteraction(self, targetNode = None, event=None):
    if self.baseVolumeNode:
      self.startEditPlanningDistal()
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal"):
        distalNode = slicer.mrmlScene.GetNodeByID(
          self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal"))
        if(distalNode and (distalNode.GetNumberOfFiducials()==0)):
          self.startEditPlanningDistal()
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target"):
        targetNode = slicer.mrmlScene.GetNodeByID(
          self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target"))
    pass
  
  def startEditPlanningDistal(self):
    if self.baseVolumeNode:
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal"):
        distalNode = slicer.mrmlScene.GetNodeByID(
          self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal"))
        dnode = distalNode.GetMarkupsDisplayNode()
        distalNode.RemoveAllMarkups()
        #distalNode.SetLocked(True)

        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        # interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if (selectionNode == None) or (self.interactionNode == None):
          return
        #self.initialSlicesOrientation()
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        selectionNode.SetActivePlaceNodeID(distalNode.GetID())
        # self.interactionNode.SetAttribute("vtkMRMLInteractionNode.rel_marker", "sagittalPoint")
        self.interactionMode = "distal"
        self.interactionNode.SwitchToSinglePlaceMode()
        self.interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)
        distalNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointModifiedEvent, self.createVentricleCylindar)
        distalNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointEndInteractionEvent, self.endModifiyCylindar)

  def endDistalSelectInteraction(self, distalnode = None, event=None):
    if self.baseVolumeNode:
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target"):
        targetNode = slicer.mrmlScene.GetNodeByID(
          self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target"))
        if(targetNode and (targetNode.GetNumberOfFiducials()==0)):
          self.startEditPlanningTarget()
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal"):
        distalNode = slicer.mrmlScene.GetNodeByID(
          self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal"))
    pass
  
  def endEditTrajectory(self):
    self.trajectoryManager.endEditLine()
  
  def calculateGrayScaleWithMargin(self):
    grayScaleModelWithMarginNode = None
    if not self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin"):
      distanceMapFilter = sitk.ApproximateSignedDistanceMapImageFilter()
      originImage = sitk.Cast(sitkUtils.PullFromSlicer(self.currentVolumeNode.GetID()), sitk.sitkInt16)
      threshold = 100
      distanceMap = distanceMapFilter.Execute(originImage, threshold - 10, threshold )
      sitkUtils.PushToSlicer(distanceMap, "distanceMap", 0, True)
      imageCollection = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode", "distanceMap")
      if imageCollection:
        distanceMapNode = imageCollection.GetItemAsObject(0)
        grayScaleModelWithMarginNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        slicer.mrmlScene.AddNode(grayScaleModelWithMarginNode)
        parameters = {}
        parameters["InputVolume"] = distanceMapNode.GetID()
        parameters["OutputGeometry"] = grayScaleModelWithMarginNode.GetID()
        parameters["Threshold"] = -10.0
        grayMaker = slicer.modules.grayscalemodelmaker
        self.cliNode = slicer.cli.run(grayMaker, None, parameters, wait_for_completion=True)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin", grayScaleModelWithMarginNode.GetID())
      self.setSliceViewer()
    else:
      grayScaleModelWithMarginNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin")
      grayScaleModelWithMarginNode = slicer.mrmlScene.GetNodeByID(grayScaleModelWithMarginNodeID)
    grayScaleModelWithMarginNode.SetDisplayVisibility(0)  
    return grayScaleModelWithMarginNode
  
  
  def generatePath(self):
    self.interactionMode = "none"
    targetNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
    distalNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
    if targetNodeID and distalNodeID:
      targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
      distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
      if targetNode.GetNumberOfFiducials() and distalNode.GetNumberOfFiducials():
        targetNode.SetLocked(True)
        distalNode.SetLocked(True)
        posTarget = numpy.array([0.0, 0.0, 0.0])
        targetNode.GetNthFiducialPosition(0, posTarget)
        posDistal = numpy.array([0.0, 0.0, 0.0])
        distalNode.GetNthFiducialPosition(0, posDistal)
        modelID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
        direction = (numpy.array(posDistal) - numpy.array(posTarget))/numpy.linalg.norm(numpy.array(posDistal) - numpy.array(posTarget))
        if self.trajectoryProjectedMarker.GetNumberOfFiducials() == 0:
          self.trajectoryProjectedMarker.AddFiducial(0,0,0)
        self.calculateLineModelIntersect(modelID, posDistal+1e6*direction, posTarget-1e6*direction, self.trajectoryProjectedMarker)
        posEntry = numpy.array([0.0, 0.0, 0.0])
        self.trajectoryProjectedMarker.GetNthFiducialPosition(1,posEntry)
        self.trajectoryProjectedMarker.RemoveAllMarkups()
        self.cylindarMiddlePointNode.RemoveAllMarkups()
        self.cylindarMiddlePointNode.AddFiducial((posTarget[0]+posDistal[0])/2.0, (posTarget[1]+posDistal[1])/2.0, (posTarget[2]+posDistal[2])/2.0)
        grayScaleModelNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel")
        grayScaleModelNode = slicer.mrmlScene.GetNodeByID(grayScaleModelNodeID)
        skullModelNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
        skullModelNode = slicer.mrmlScene.GetNodeByID(skullModelNodeID)
        angleForModelCut = float(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_planningRadius"))

        pathPlanningBasePoint = numpy.array(posTarget) + (numpy.array(posEntry)-numpy.array(posTarget))*1.2
        cannulaDirection = (numpy.array(posEntry) - numpy.array(posTarget))/numpy.linalg.norm(numpy.array(posTarget) - numpy.array(posEntry))
        angle = math.acos(numpy.dot(numpy.array([0,0,1.0]),cannulaDirection))
        rotationAxis = numpy.cross(numpy.array([0,0,1.0]),cannulaDirection)
        matrix = vtk.vtkMatrix4x4()
        transform = vtk.vtkTransform()
        transform.RotateWXYZ(angle*180.0/numpy.pi, rotationAxis[0],rotationAxis[1],rotationAxis[2])
        matrix = transform.GetMatrix()
        synthesizedData = vtk.vtkPolyData()
        points = vtk.vtkPoints()
        phiResolution = 5*numpy.pi/180.0
        radiusResolution = 1.0
        points.InsertNextPoint(posEntry)
        distance2 = numpy.linalg.norm(numpy.array(posTarget) - numpy.array(posEntry))
        distance1 = numpy.linalg.norm(numpy.array(posTarget) - numpy.array(posDistal))/2 # Divided by 2 is because, all the cylindar bottom are possible target points
        self.entryRadius = self.cylindarRadius * distance2 / distance1
        for radius in numpy.arange(radiusResolution, self.entryRadius+radiusResolution, radiusResolution):
          for angle in numpy.arange(phiResolution, numpy.pi, phiResolution):
            point = matrix.MultiplyPoint(numpy.array([radius*math.cos(angle), radius*math.sin(angle),0,1]))
            pointTranslated = [point[0]+pathPlanningBasePoint[0],point[1]+pathPlanningBasePoint[1],point[2]+pathPlanningBasePoint[2]]
            points.InsertNextPoint(pointTranslated)
          for angle in numpy.arange(numpy.pi, 2*numpy.pi, phiResolution):
            point = matrix.MultiplyPoint(numpy.array([-radius * math.cos(angle), radius * math.sin(angle), 0, 1]))
            pointTranslated = [point[0] + pathPlanningBasePoint[0], point[1] + pathPlanningBasePoint[1], point[2] + pathPlanningBasePoint[2]]
            points.InsertNextPoint(pointTranslated)
        synthesizedData.SetPoints(points)
        tempModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        tempModel.SetAndObservePolyData(synthesizedData)
        grayScaleModelWithMarginNode = self.calculateGrayScaleWithMargin()
        
        if synthesizedData.GetNumberOfPoints() and grayScaleModelWithMarginNode:

          self.pathReceived, self.nPathReceived, self.apReceived, self.minimumPoint, self.minimumDistance, self.maximumPoint, self.maximumDistance = self.PercutaneousApproachAnalysisLogic.makePaths(
            self.cylindarMiddlePointNode, None, 0, grayScaleModelWithMarginNode, tempModel)
          # display all paths model
          red =[1, 0, 0]
          self.makePath(self.pathReceived, self.nPathReceived,   1, "candidatePaths", self.pathCandidatesPoly, self.pathCandidatesModel)
          obbTree = vtk.vtkOBBTree()
          obbTree.SetDataSet(grayScaleModelWithMarginNode.GetPolyData())
          obbTree.BuildLocator()
          pointsVTKintersection = vtk.vtkPoints()
          hasIntersection = obbTree.IntersectWithLine(posEntry, posTarget, pointsVTKintersection, None)
          self.cannulaManager.clearLine()
          self.cannulaManager.curveFiducials.RemoveAllMarkups()
          self.cannulaManager.startEditLine() # initialize the tube model
          if hasIntersection > 0:
            if self.nPathReceived>0:
              if slicer.util.confirmYesNoDisplay("The cannula is within the safty margin of the venous, use location optimization?",
                                                 windowTitle=""):
                self.relocateCannula(self.pathReceived, 1)
              else:
                self.cannulaManager.curveFiducials.AddFiducialFromArray(posTarget)
                self.cannulaManager.curveFiducials.AddFiducialFromArray(posEntry + 0.005*cannulaDirection)
            else:
              slicer.util.warningDisplay(
                "No any cannula candidate exists here, considering redefine the ventricle area?")
              distalNode.SetLocked(False)
              targetNode.SetLocked(False)
          else:
            if slicer.util.confirmYesNoDisplay("The current cannula is fine, however, would you like to make it closer to the kocher's point?",
                                                 windowTitle=""):
              self.relocateCannula(self.pathReceived, 1)
            else:
              self.cannulaManager.curveFiducials.AddFiducialFromArray(posTarget)
              self.cannulaManager.curveFiducials.AddFiducialFromArray(posEntry + 0.005*cannulaDirection)



      #slicer.mrmlScene.RemoveNode(distanceMapNode)
  def makePath(self, path, approachablePoints, visibilityParam, modelName, polyData, modelNode):

    # Create an array for all approachable points
    p = numpy.zeros([approachablePoints * 2, 3])
    p1 = [0.0, 0.0, 0.0]

    scene = slicer.mrmlScene

    points = vtk.vtkPoints()
    polyData.SetPoints(points)

    lines = vtk.vtkCellArray()
    polyData.SetLines(lines)
    linesIDArray = lines.GetData()
    linesIDArray.Reset()
    linesIDArray.InsertNextTuple1(0)

    polygons = vtk.vtkCellArray()
    polyData.SetPolys(polygons)
    idArray = polygons.GetData()
    idArray.Reset()
    idArray.InsertNextTuple1(0)

    if approachablePoints != 0:

      for point in path:
        pointIndex = points.InsertNextPoint(*point)
        linesIDArray.InsertNextTuple1(pointIndex)
        linesIDArray.SetTuple1(0, linesIDArray.GetNumberOfTuples() - 1)
        lines.SetNumberOfCells(1)

        # Save all approachable points
        p1[0] = linesIDArray.GetTuple1(1)
        p1[1] = linesIDArray.GetTuple1(2)
        p1[2] = linesIDArray.GetTuple1(3)

        coord = [p1[0], p1[1], p1[2]]
        p[pointIndex] = coord

    # Create model node
    modelNode.SetAndObservePolyData(polyData)
    modelNode.GetDisplayNode().SetVisibility(visibilityParam)
    pass

  def relocateCannula(self, pathReceived, optimizationMethod=1):
    if pathReceived:
      self.cannulaManager.curveFiducials.RemoveAllMarkups()
      posTarget = numpy.array([0.0] * 3)
      self.trajectoryManager.getFirstPoint(posTarget)
      posDistal = numpy.array([0.0] * 3)
      self.trajectoryManager.getLastPoint(posDistal)
      direction1Norm = (posDistal - posTarget)/numpy.linalg.norm(posTarget - posDistal)
      angleCalc =numpy.pi
      if optimizationMethod == 0: # the cannula is relocated so that its direction is closer to the ventricle center
        optimizedEntry = numpy.array([])
        for pointIndex in range(1, len(pathReceived),2):
          direction2 = numpy.array(pathReceived[pointIndex]) - numpy.array(pathReceived[pointIndex-1])
          direction2Norm = direction2/numpy.linalg.norm(direction2)
          angle = math.acos(numpy.dot(direction1Norm, direction2Norm))
          if angle < angleCalc:
            angleCalc = angle
            optimizedEntry = numpy.array(pathReceived[pointIndex])
        if optimizedEntry.any():
          posEntry = numpy.array([0.0] * 3)
          self.trajectoryProjectedMarker.GetNthFiducialPosition(0, posEntry)
          distance2 = numpy.linalg.norm(numpy.array(posTarget) - numpy.array(posEntry))
          distance1 = numpy.linalg.norm(numpy.array(posTarget) - numpy.array(posDistal))
          posDistalModified = numpy.array(posTarget) + (numpy.array(optimizedEntry) - numpy.array(posTarget))/distance2*distance1
          #self.trajectoryManager.curveFiducials.SetNthFiducialPositionFromArray(1,optimizedEntry)
          self.cannulaManager.curveFiducials.AddFiducialFromArray(posTarget)
          self.cannulaManager.curveFiducials.AddFiducialFromArray(posDistalModified)
      elif optimizationMethod == 1: # relocate the cannula so that it is close to the reference entry point
        inputModelNodeID =  self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
        if inputModelNodeID:
          inputModelNode = slicer.mrmlScene.GetNodeByID(inputModelNodeID) 
          if (inputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "True"):
            polyData = inputModelNode.GetPolyData()
            locator = vtk.vtkCellLocator()
            locator.SetDataSet(polyData)
            locator.BuildLocator()
            t = vtk.mutable(0)
            x = [0.0,0.0,0.0]
            pcoords = [0.0,0.0,0.0]
            subId = vtk.mutable(0)
            numOfRef = self.coronalReferenceCurveManager.curveFiducials.GetNumberOfFiducials()
            distanceMin = 1e20
            minIndex = 1
            if numOfRef >= 1:
              posRef = [0.0,0.0,0.0]
              self.coronalReferenceCurveManager.curveFiducials.GetNthFiducialPosition(numOfRef-1,posRef)
              for pointIndex in range(1, len(pathReceived),2):
                hasIntersection = locator.IntersectWithLine(pathReceived[pointIndex], pathReceived[pointIndex-1], 1e-2, t, x, pcoords, subId)
                if hasIntersection>0:
                  if distanceMin > numpy.linalg.norm(numpy.array(posRef)-numpy.array(x)):
                    distanceMin = numpy.linalg.norm(numpy.array(posRef)-numpy.array(x))
                    minIndex = pointIndex
              self.cannulaManager.curveFiducials.AddFiducialFromArray(pathReceived[minIndex-1])
              self.cannulaManager.curveFiducials.AddFiducialFromArray(pathReceived[minIndex])
              direction2 = numpy.array(pathReceived[minIndex]) - numpy.array(pathReceived[minIndex-1])
              direction2Norm = direction2/numpy.linalg.norm(direction2)
              angleCalc = math.acos(numpy.dot(direction1Norm, direction2Norm))
      self.updateCannulaPosition(self.cannulaManager.curveFiducials)
      posProject =  numpy.array([0.0] * 3)
      self.trajectoryProjectedMarker.GetNthFiducialPosition(0,posProject)
      posMiddle = (posTarget+posDistal)/2
      posBottom = posMiddle+numpy.linalg.norm(posMiddle - posDistal)/math.cos(angleCalc)*(posMiddle-posProject)/numpy.linalg.norm(posMiddle - posProject)
      self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(0, posBottom)
      self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(1, posProject)
      self.trajectoryProjectedMarker.RemoveAllMarkups()        
    pass

  def clearTrajectory(self):
    self.trajectoryManager.clearLine()

  def setTrajectoryModifiedEventHandler(self, handler):
    self.trajectoryManager.setModifiedEventHandler(handler)

  def getCannulaLength(self):
    return self.cannulaManager.getLength()

  def lockTrajectoryLine(self):
    self.trajectoryManager.lockLine()
    self.trajectoryManager.lockLine()

  def unlockTrajectoryLine(self):
    self.trajectoryManager.unlockLine()
    self.trajectoryManager.unlockLine()

  def moveSliceTrajectory(self):
    self.trajectoryManager.moveSliceToLine()


  def startEditCoronalPlanningLine(self):

    pos = [0.0] * 3
    self.trajectoryManager.getFirstPoint(pos)
    self.coronalPlanningCurveManager.startEditLine(pos)
    
  def endEditCoronalPlanningLine(self):

    self.coronalPlanningCurveManager.endEditLine()

  def clearCoronalPlanningLine(self):
    
    self.coronalPlanningCurveManager.clearLine()

  def setCoronalPlanningLineModifiedEventHandler(self, handler):

    self.coronalPlanningCurveManager.setModifiedEventHandler(handler)

  def getCoronalPlanningLineLength(self):
    return self.coronalPlanningCurveManager.getLength()

  def moveSliceCoronalPlanningLine(self):
    self.coronalPlanningCurveManager.moveSliceToLine()

  def lockPlanningLine(self):
    self.sagittalPlanningCurveManager.lockLine()
    self.coronalPlanningCurveManager.lockLine()

  def unlockPlanningLine(self):
    self.sagittalPlanningCurveManager.unlockLine()
    self.coronalPlanningCurveManager.unlockLine()


  def startEditSagittalPlanningLine(self):

    pos = [0.0] * 3

    self.coronalPlanningCurveManager.getLastPoint(pos)
    self.sagittalPlanningCurveManager.startEditLine(pos)
    
  def endEditSagittalPlanningLine(self):

    self.sagittalPlanningCurveManager.endEditLine()

  def clearSagittalPlanningLine(self):
    
    self.sagittalPlanningCurveManager.clearLine()

  def setSagittalPlanningLineModifiedEventHandler(self, handler):

    self.sagittalPlanningCurveManager.setModifiedEventHandler(handler)

  def getSagittalPlanningLineLength(self):
    return self.sagittalPlanningCurveManager.getLength()

  def moveSliceSagittalPlanningLine(self):
    self.sagittalPlanningCurveManager.moveSliceToLine()



  def createModel(self, outputModelNode, thresholdValue):

    Decimate = 0.05

    if self.baseVolumeNode == None or self.currentVolumeNode == None:
      return
    if outputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False":
      resampleFilter = sitk.ResampleImageFilter()
      originImage = sitk.Cast(sitkUtils.PullFromSlicer(self.currentVolumeNode.GetID()), sitk.sitkInt16)   
      self.samplingFactor = 2
      resampleFilter.SetSize(numpy.array(originImage.GetSize())/self.samplingFactor)
      resampleFilter.SetOutputSpacing(numpy.array(originImage.GetSpacing())*self.samplingFactor)
      resampleFilter.SetOutputOrigin(numpy.array(originImage.GetOrigin()))
      resampledImage = resampleFilter.Execute(originImage)
      thresholdFilter = sitk.BinaryThresholdImageFilter()
      thresholdImage = thresholdFilter.Execute(resampledImage,thresholdValue,10000,1,0)
      dilateFilter = sitk.BinaryDilateImageFilter()
      dilateFilter.SetKernelRadius([10,10,6])
      dilateFilter.SetBackgroundValue(0)
      dilateFilter.SetForegroundValue(1)
      dilatedImage = dilateFilter.Execute(thresholdImage)
      erodeFilter = sitk.BinaryErodeImageFilter()
      erodeFilter.SetKernelRadius([10,10,6])
      erodeFilter.SetBackgroundValue(0)
      erodeFilter.SetForegroundValue(1)
      erodedImage = erodeFilter.Execute(dilatedImage)
      fillHoleFilter = sitk.BinaryFillholeImageFilter()
      holefilledImage = fillHoleFilter.Execute(erodedImage)
      sitkUtils.PushToSlicer(holefilledImage, "holefilledImage", 0, True)
      imageCollection = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode","holefilledImage")
      if imageCollection:
        holefilledImageNode = imageCollection.GetItemAsObject(0)
        holefilledImageData = holefilledImageNode.GetImageData()
        
        cast = vtk.vtkImageCast()
        cast.SetInputData(holefilledImageData)
        cast.SetOutputScalarTypeToUnsignedChar()
        cast.Update()
    
        labelVolumeNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLLabelMapVolumeNode")
        slicer.mrmlScene.AddNode(labelVolumeNode)
        labelVolumeNode.SetName("Threshold")
        labelVolumeNode.SetSpacing(holefilledImageData.GetSpacing())
        labelVolumeNode.SetOrigin(holefilledImageData.GetOrigin())
    
        matrix = vtk.vtkMatrix4x4()
        holefilledImageNode.GetIJKToRASMatrix(matrix)
        labelVolumeNode.SetIJKToRASMatrix(matrix)
    
        labelImage = cast.GetOutput()
        labelVolumeNode.SetAndObserveImageData(labelImage)
    
        transformIJKtoRAS = vtk.vtkTransform()
        matrix = vtk.vtkMatrix4x4()
        labelVolumeNode.GetRASToIJKMatrix(matrix)
        transformIJKtoRAS.SetMatrix(matrix)
        transformIJKtoRAS.Inverse()
    
        padder = vtk.vtkImageConstantPad()
        padder.SetInputData(labelImage)
        padder.SetConstant(0)
        extent = labelImage.GetExtent()
        padder.SetOutputWholeExtent(extent[0], extent[1] + 2,
                                    extent[2], extent[3] + 2,
                                    extent[4], extent[5] + 2)
        
        cubes = vtk.vtkDiscreteMarchingCubes()
        cubes.SetInputConnection(padder.GetOutputPort())
        cubes.GenerateValues(1, 1, 1)
        cubes.Update()
    
        smoother = vtk.vtkWindowedSincPolyDataFilter()
        smoother.SetInputConnection(cubes.GetOutputPort())
        smoother.SetNumberOfIterations(10)
        smoother.BoundarySmoothingOff()
        smoother.FeatureEdgeSmoothingOff()
        smoother.SetFeatureAngle(120.0)
        smoother.SetPassBand(0.001)
        smoother.NonManifoldSmoothingOn()
        smoother.NormalizeCoordinatesOn()
        smoother.Update()
    
        pthreshold = vtk.vtkThreshold()
        pthreshold.SetInputConnection(smoother.GetOutputPort())
        pthreshold.ThresholdBetween(1, 1) ## Label 1
        pthreshold.ReleaseDataFlagOn()

        geometryFilter = vtk.vtkGeometryFilter()
        geometryFilter.SetInputConnection(pthreshold.GetOutputPort())
        geometryFilter.ReleaseDataFlagOn()
        
        decimator = vtk.vtkDecimatePro()
        decimator.SetInputConnection(geometryFilter.GetOutputPort())
        decimator.SetFeatureAngle(60)
        decimator.SplittingOff()
        decimator.PreserveTopologyOn()
        decimator.SetMaximumError(1)
        decimator.SetTargetReduction(0.5) #0.001 only reduce the points by 0.1%, 0.5 is 50% off
        decimator.ReleaseDataFlagOff()
        decimator.Update()
        
        smootherPoly = vtk.vtkSmoothPolyDataFilter()
        smootherPoly.SetRelaxationFactor(0.33)
        smootherPoly.SetFeatureAngle(60)
        smootherPoly.SetConvergence(0)
    
        if transformIJKtoRAS.GetMatrix().Determinant() < 0:
          reverser = vtk.vtkReverseSense()
          reverser.SetInputConnection(decimator.GetOutputPort())
          reverser.ReverseNormalsOn()
          reverser.ReleaseDataFlagOn()
          smootherPoly.SetInputConnection(reverser.GetOutputPort())
        else:
          smootherPoly.SetInputConnection(decimator.GetOutputPort())
    
        Smooth = 10
        smootherPoly.SetNumberOfIterations(Smooth)
        smootherPoly.FeatureEdgeSmoothingOff()
        smootherPoly.BoundarySmoothingOff()
        smootherPoly.ReleaseDataFlagOn()
        smootherPoly.Update()
    
        transformer = vtk.vtkTransformPolyDataFilter()
        transformer.SetInputConnection(smootherPoly.GetOutputPort())
        transformer.SetTransform(transformIJKtoRAS)
        transformer.ReleaseDataFlagOn()
        transformer.Update()
        
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputConnection(transformer.GetOutputPort())
        normals.SetFeatureAngle(60)
        normals.SetSplitting(True)
        normals.ReleaseDataFlagOn()
        
        stripper = vtk.vtkStripper()
        stripper.SetInputConnection(normals.GetOutputPort())
        stripper.ReleaseDataFlagOff()
        stripper.Update()
        
        outputModel = stripper.GetOutput()
        outputModelNode.SetAndObservePolyData(outputModel)
        outputModelNode.SetAttribute("vtkMRMLModelNode.modelCreated","True")
        outputModelNode.GetDisplayNode().SetVisibility(1)
        layoutManager = slicer.app.layoutManager()
        threeDWidget = layoutManager.threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        threeDView.resetFocalPoint()
        threeDView.lookFromViewAxis(ctkAxesWidget.Anterior)
      imageCollection = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode","holefilledImage")
      if imageCollection:
        holefilledImageNode = imageCollection.GetItemAsObject(0)
        slicer.mrmlScene.RemoveNode(holefilledImageNode)
      imageCollection = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode","Threshold")
      if imageCollection:
        thresholdImageNode = imageCollection.GetItemAsObject(0)
        slicer.mrmlScene.RemoveNode(thresholdImageNode)  
  
  def calculateVenousGrayScale(self, inputVolumeNode, grayScaleModelNode):    
      parameters = {}
      parameters["InputVolume"] = inputVolumeNode.GetID()
      parameters["OutputGeometry"] = grayScaleModelNode.GetID()
      grayMaker = slicer.modules.grayscalemodelmaker
      self.cliNode = slicer.cli.run(grayMaker, None, parameters, wait_for_completion=False)
  
  
  def calculateVenousVesselness(self,inputVolumeNode, vesselnessNode):      
      convolutionFilter = vtk.vtkImageSeparableConvolution()
      zKernel = vtk.vtkFloatArray()
      zKernel.SetNumberOfTuples(5)
      zKernel.SetNumberOfComponents(1)
      zKernel.SetValue(0,1)
      zKernel.SetValue(1,1)
      zKernel.SetValue(2,1)
      zKernel.SetValue(3,1)
      zKernel.SetValue(4,1)
      convolutionFilter.SetZKernel(zKernel)
      convolutionFilter.SetInputData(inputVolumeNode.GetImageData())
      convolutionFilter.Update()
      convolutedImage = convolutionFilter.GetOutput()
      convolutedVolumeNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLScalarVolumeNode")
      convolutedVolumeNode.SetName("ConvolutedVolume-NotShownEntity31415")
      ijkToRAS = vtk.vtkMatrix4x4()
      inputVolumeNode.GetIJKToRASMatrix(ijkToRAS)
      convolutedVolumeNode.SetIJKToRASMatrix(ijkToRAS) 
      convolutedVolumeNode.SetAndObserveImageData(convolutionFilter.GetOutput())
      slicer.mrmlScene.AddNode(convolutedVolumeNode)
      vesselnessFilter = slicer.modules.hessianvesselnessfilter
      parameters = {"inputVolume": convolutedVolumeNode.GetID(), "outputVolume": vesselnessNode.GetID(), "alpha1": -40, "alpha2":-100, "sigma":0.8}
      self.cliNode = slicer.cli.run(vesselnessFilter, None, parameters, wait_for_completion=False)
      
        
  def enableAttribute(self, attribute, caseName = None):
    enabledAttributeID = self.baseVolumeNode.GetAttribute(attribute)
    if enabledAttributeID:
      attributeNode = slicer.mrmlScene.GetNodeByID(enabledAttributeID)
      if attributeNode and attributeNode.GetDisplayNode():
        attributeNode.GetDisplayNode().SetVisibility(1)
    else:
      if attribute == "vtkMRMLScalarVolumeNode.rel_nasion":
        nasionNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        nasionNode.SetName(caseName+"nasion")
        displayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsDisplayNode")
        slicer.mrmlScene.AddNode(displayNode)
        slicer.mrmlScene.AddNode(nasionNode)
        nasionNode.SetAndObserveDisplayNodeID(displayNode.GetID())
        nasionNode.SetLocked(True)
        self.baseVolumeNode.SetAttribute(attribute, nasionNode.GetID())
      if attribute == "vtkMRMLScalarVolumeNode.rel_sagittalPoint":
        sagittalPointNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        sagittalPointNode.SetName(caseName+"sagittalPoint")
        displayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsDisplayNode")
        slicer.mrmlScene.AddNode(displayNode)
        slicer.mrmlScene.AddNode(sagittalPointNode)
        sagittalPointNode.SetAndObserveDisplayNodeID(displayNode.GetID())
        sagittalPointNode.SetLocked(True)
        self.baseVolumeNode.SetAttribute(attribute, sagittalPointNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_target":
        targetNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        targetNode.SetName(caseName+"target")
        displayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsDisplayNode")
        slicer.mrmlScene.AddNode(displayNode)
        slicer.mrmlScene.AddNode(targetNode)
        targetNode.SetAndObserveDisplayNodeID(displayNode.GetID())
        self.baseVolumeNode.SetAttribute(attribute, targetNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_distal":
        distalNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        distalNode.SetName(caseName+"distal")
        displayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsDisplayNode")
        slicer.mrmlScene.AddNode(displayNode)
        slicer.mrmlScene.AddNode(distalNode)
        distalNode.SetAndObserveDisplayNodeID(displayNode.GetID())
        self.baseVolumeNode.SetAttribute(attribute, distalNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_cylindarRadius":
        self.baseVolumeNode.SetAttribute(attribute, str(self.cylindarRadius))  
      elif attribute == "vtkMRMLScalarVolumeNode.rel_skullNorm":
        skullNormNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        skullNormNode.SetName(caseName+"skullNorm")
        slicer.mrmlScene.AddNode(skullNormNode)
        self.baseVolumeNode.SetAttribute(attribute, skullNormNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_cannula":
        cannulaNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        cannulaNode.SetName(caseName+"cannula")
        slicer.mrmlScene.AddNode(cannulaNode)
        self.baseVolumeNode.SetAttribute(attribute, cannulaNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_model":  
        modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        modelNode.SetAttribute("vtkMRMLModelNode.modelCreated", "False")
        slicer.mrmlScene.AddNode(modelNode)
        modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
        ModelColor = [0.0, 0.0, 1.0]
        modelDisplayNode.SetColor(ModelColor)
        modelDisplayNode.SetOpacity(0.5)
        slicer.mrmlScene.AddNode(modelDisplayNode)
        modelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_model", modelNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_cannulaModel":
        modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        modelNode.SetName(caseName+"cannulaModel")
        slicer.mrmlScene.AddNode(modelNode)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_cannulaModel", modelNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_sagittalReferenceModel":
        modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        modelNode.SetName(caseName+"sagittalReferenceModel")
        slicer.mrmlScene.AddNode(modelNode)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalReferenceModel", modelNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_coronalReferenceModel":
        modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        modelNode.SetName(caseName+"coronalReferenceModel")
        slicer.mrmlScene.AddNode(modelNode)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_coronalReferenceModel", modelNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_sagittalPlanningModel":
        modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        modelNode.SetName(caseName+"sagittalPlanningModel")
        slicer.mrmlScene.AddNode(modelNode)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPlanningModel", modelNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_coronalPlanningModel":
        modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        modelNode.SetName(caseName+"coronalPlanningModel")
        slicer.mrmlScene.AddNode(modelNode)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_coronalPlanningModel", modelNode.GetID())
      enabledAttributeID = self.baseVolumeNode.GetAttribute(attribute)  
        # to do update the logic regarding the current attribute // self.nasionPointNode = nasionNode
    volumeCollection = slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode") 
    if volumeCollection:
      for iVolume in range(volumeCollection.GetNumberOfItems ()):
        volumeNode = volumeCollection.GetItemAsObject(iVolume)
        attributeNodeID = volumeNode.GetAttribute(attribute)
        if attributeNodeID and (not  attributeNodeID == enabledAttributeID):
          attributeNode = slicer.mrmlScene.GetNodeByID(attributeNodeID)
          if attributeNode and attributeNode.GetDisplayNode():  
            attributeNode.GetDisplayNode().SetVisibility(0)

    
  def updateMeasureLength(self, sagittalReferenceLength=None, coronalReferenceLength=None):
    if not self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength"):
      if sagittalReferenceLength:
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength", '%.1f' % sagittalReferenceLength)      
    if not self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength"):    
      if coronalReferenceLength:
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength", '%.1f' % coronalReferenceLength)

  def updatePathPlanningRadius(self, radius):
    if not self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_planningRadius"):
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_planningRadius", '%.1f' % radius)

  @vtk.calldata_type(vtk.VTK_INT)
  def updateSelectedMarker(self,node, eventID, callData):
    self.activeTrajectoryMarkup = callData
    pass
  
  def updateCannulaPosition(self, fiducicalMarkerNode, eventID = None):
    inputModelNodeID =  self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
    if inputModelNodeID:
      inputModelNode = slicer.mrmlScene.GetNodeByID(inputModelNodeID)
      if (inputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "True"):
        self.trajectoryProjectedMarker.RemoveAllMarkups()
        self.trajectoryProjectedMarker.AddFiducial(0,0,0)
        self.trajectoryProjectedMarker.GetMarkupsDisplayNode().SetVisibility(1)
        polyData = inputModelNode.GetPolyData()
        posFirst = [0.0,0.0,0.0]
        fiducicalMarkerNode.GetNthFiducialPosition(0,posFirst)
        posSecond = [0.0,0.0,0.0]
        fiducicalMarkerNode.GetNthFiducialPosition(1,posSecond)
        if fiducicalMarkerNode.GetNumberOfFiducials()>=2: #  self.activeTrajectoryMarkup == 0 means the target fiducial, 1 is the fiducial closer to the surface
          direction = numpy.array(posSecond)- numpy.array(posFirst)
          locator = vtk.vtkCellLocator()
          locator.SetDataSet(polyData)
          locator.BuildLocator()
          t = vtk.mutable(0)
          x = [0.0,0.0,0.0]
          pcoords = [0.0,0.0,0.0]
          subId = vtk.mutable(0)
          hasIntersection = locator.IntersectWithLine( posSecond + 1e6*direction, posFirst -  1e6*direction, 1e-2, t, x, pcoords, subId)
          if hasIntersection>0:
            self.trajectoryProjectedMarker.SetNthFiducialPositionFromArray(0,x)
            self.trajectoryProjectedMarker.SetNthFiducialLabel(0,"")  
          else:
            self.trajectoryProjectedMarker.SetNthFiducialLabel(0,"invalid")
        else:
          self.trajectoryProjectedMarker.SetNthFiducialPositionFromArray(0,posSecond)
          self.trajectoryProjectedMarker.SetNthFiducialLabel(0,"")
          #self.trajectoryProjectedMarker.SetNthFiducialVisibility(0,False)
    self.cannulaManager.onLineSourceUpdated()
    self.updateSlicePosition(fiducicalMarkerNode,self.activeTrajectoryMarkup)
    #self.calcPitchYawAngles()
  
  def endTrajectoryInteraction(self, fiducialNode, event=None):
    posEntry = [0.0, 0.0, 0.0]
    if not self.trajectoryProjectedMarker.GetNthFiducialLabel(0) == "invalid":
      self.trajectoryProjectedMarker.GetNthFiducialPosition(0, posEntry)
      posEntry[1] = posEntry[1] + 0.005
      fiducialNode.SetNthFiducialPositionFromArray(1, posEntry)
    self.trajectoryProjectedMarker.SetNthFiducialVisibility(0, False)
    self.trajectoryProjectedMarker.SetLocked(True)
    self.trajectoryProjectedMarker.SetLocked(True)
    # update the intersection of trajectory with venous
    posTarget = [0.0,0.0,0.0]
    fiducialNode.GetNthFiducialPosition(0,posTarget)
    posEntry = [0.0,0.0,0.0]
    fiducialNode.GetNthFiducialPosition(1,posEntry)
    inputVesselModelNodeID =  self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel")
    if inputVesselModelNodeID:
      self.calculateLineModelIntersect(inputVesselModelNodeID, posEntry, posTarget, self.trajectoryProjectedMarker)
    pass

  def calculateLineModelIntersect(self, modelID, posFirst, posSecond, intersectionNode):
    inputModelNode = slicer.mrmlScene.GetNodeByID(modelID)
    obbTree = vtk.vtkOBBTree()
    obbTree.SetDataSet(inputModelNode.GetPolyData())
    obbTree.BuildLocator()
    pointsVTKintersection = vtk.vtkPoints()
    hasIntersection = obbTree.IntersectWithLine(posFirst, posSecond, pointsVTKintersection, None)
    if hasIntersection>0:
      pointsVTKIntersectionData = pointsVTKintersection.GetData()
      numPointsVTKIntersection = pointsVTKIntersectionData.GetNumberOfTuples()
      validPosIndex = 1
      for idx in range(numPointsVTKIntersection):
        posTuple = pointsVTKIntersectionData.GetTuple3(idx)
        if ((posTuple[0]-posFirst[0])*(posSecond[0]-posFirst[0])>0) and abs(posTuple[0]-posFirst[0])<abs(posSecond[0]-posFirst[0]):
          # check if the intersection if within the posFist and posSecond
          intersectionNode.AddFiducial(0,0,0)
          intersectionNode.SetNthFiducialPositionFromArray(validPosIndex,posTuple)
          intersectionNode.SetNthFiducialLabel(validPosIndex,"")
          intersectionNode.SetNthFiducialVisibility(validPosIndex,True)
          validPosIndex = validPosIndex + 1
    else:
      numOfFiducial = intersectionNode.GetNumberOfFiducials()
      for idx in range(1, numOfFiducial):
        intersectionNode.SetNthFiducialLabel(idx,"invalid")

  def updateNasionPosition(self, fiducicalMarkerNode, eventID):
    inputModelNodeID =  self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
    if inputModelNodeID:
      inputModelNode = slicer.mrmlScene.GetNodeByID(inputModelNodeID) 
      if (inputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "True"):
        self.nasionProjectedMarker.GetMarkupsDisplayNode().SetVisibility(1)
        polyData = inputModelNode.GetPolyData()
        posFirst = [0.0,0.0,0.0]
        fiducicalMarkerNode.GetNthFiducialPosition(0,posFirst)
        posSecond = [posFirst[0],posFirst[1]-1e6,posFirst[2]]
        posFirst[1] = posFirst[1]+ 1e6 
        locator = vtk.vtkCellLocator()
        locator.SetDataSet(polyData)
        locator.BuildLocator()
        t = vtk.mutable(0)
        x = [0.0,0.0,0.0]
        pcoords = [0.0,0.0,0.0]
        subId = vtk.mutable(0)
        hasIntersection = locator.IntersectWithLine(posFirst, posSecond, 1e-2, t, x, pcoords, subId)
        if hasIntersection>0:
          self.nasionProjectedMarker.SetNthFiducialPositionFromArray(0,x)
          self.nasionProjectedMarker.SetNthFiducialLabel(0,"")  
        else:
          self.nasionProjectedMarker.SetNthFiducialLabel(0,"invalid")  
    self.updateSlicePosition(fiducicalMarkerNode, 0)
       
  def updateSlicePosition(self, fiducicalMarkerNode, markupIndex):
    pos = [0.0]*4
    fiducicalMarkerNode.GetNthFiducialWorldCoordinates(markupIndex,pos)
    viewerRed = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeRed")
    viewerRed.SetOrientationToAxial()
    viewerRed.SetSliceOffset(pos[2])
    viewerYellow = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeYellow")
    viewerYellow.SetOrientationToSagittal()
    viewerYellow.SetSliceOffset(pos[0])
    viewerBlue = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeGreen")
    viewerBlue.SetOrientationToCoronal()
    viewerBlue.SetSliceOffset(pos[1]) 
    pass
  
  def endPlacement(self, interactionNode, event):
    ## when place a new trajectory point, the UpdatePosition is called, the projectedMarker will be visiable.
    ## set the projected marker to invisiable here
    self.interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)
    if self.interactionMode == "nasion":
      self.createTrueSagittalPlane()
      self.createEntryPoint()
      self.nasionProjectedMarker.GetMarkupsDisplayNode().SetVisibility(0)
    elif self.interactionMode == "sagittalPoint":
      self.createTrueSagittalPlane()
      self.createEntryPoint()
    elif self.interactionMode == "target":
      self.endTargetSelectInteraction()
      if self.trajectoryProjectedMarker:
        self.trajectoryProjectedMarker.GetMarkupsDisplayNode().SetVisibility(0)
      self.createVentricleCylindar()
      self.endModifiyCylindar()
    elif self.interactionMode == "distal":
      self.endDistalSelectInteraction()
      if self.trajectoryProjectedMarker:
        self.trajectoryProjectedMarker.GetMarkupsDisplayNode().SetVisibility(1)
      self.createVentricleCylindar()
      self.endModifiyCylindar()
      #self.generatePath()
    pass
  
  def endNasionInteraction(self, nasionNode, event):
    posFirst = [0.0,0.0,0.0]
    if not self.nasionProjectedMarker.GetNthFiducialLabel(0) == "invalid":
      self.nasionProjectedMarker.GetNthFiducialPosition(0,posFirst)
      posFirst[1] = posFirst[1] + 0.005 # Plus 0.005 for the purpose of interaction, if the marker is directly at the skull model, interaction will be impossible
      nasionNode.SetNthFiducialPositionFromArray(0,posFirst)
    self.nasionProjectedMarker.GetMarkupsDisplayNode().SetVisibility(0)
    pass
   
  def selectNasionPointNode(self, modelNode, initPoint = None):
    if self.baseVolumeNode:
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"):
        nasionNode = slicer.mrmlScene.GetNodeByID(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"))
        dnode = nasionNode.GetMarkupsDisplayNode()
        if dnode :
          dnode.SetVisibility(1)
        nasionNode.RemoveAllMarkups()
        #slicer.mrmlScene.AddNode(nasionNode)
        nasionNode.SetLocked(True)
        self.nasionProjectedMarker.AddFiducial(0,0,0)
        self.nasionProjectedMarker.SetNthFiducialLabel(0, "")
        dnode = self.nasionProjectedMarker.GetMarkupsDisplayNode()
        if dnode:
          rgbColor = [1.0, 0.0, 1.0]
          dnode.SetSelectedColor(rgbColor)
          dnode.SetVisibility(0)
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        #interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if (selectionNode == None) or (self.interactionNode == None):
          return

        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        selectionNode.SetActivePlaceNodeID(nasionNode.GetID())
        #interactionNode.RemoveObserver(interactionNode.EndPlacementEvent, self.endPlacement)
        #self.interactionNode.SetAttribute("vtkMRMLInteractionNode.rel_marker", "nasion")
        self.interactionMode = "nasion"
        self.interactionNode.SwitchToSinglePlaceMode ()
        self.interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)
        #interactionNode.AddObserver(interactionNode.EndPlacementEvent, self.endPlacement)
        nasionNode.AddObserver(nasionNode.PointModifiedEvent, self.updateNasionPosition)
        nasionNode.AddObserver(nasionNode.PointEndInteractionEvent, self.endNasionInteraction)

  def selectSagittalPointNode(self, modelNode):
    if self.baseVolumeNode:
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPoint"):
        sagittalPointNode = slicer.mrmlScene.GetNodeByID(
          self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPoint"))
        dnode = sagittalPointNode.GetMarkupsDisplayNode()
        sagittalPointNode.RemoveAllMarkups()
        # slicer.mrmlScene.AddNode(nasionNode)
        sagittalPointNode.SetLocked(True)

        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        #interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if (selectionNode == None) or (self.interactionNode == None):
          return

        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
        selectionNode.SetActivePlaceNodeID(sagittalPointNode.GetID())
        #self.interactionNode.SetAttribute("vtkMRMLInteractionNode.rel_marker", "sagittalPoint")
        self.interactionMode = "sagittalPoint"
        self.interactionNode.SwitchToSinglePlaceMode()
        self.interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)
        
  def endModifiyCylindar(self,  caller = None, eventID = None):
    targetNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
    distalNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
    if targetNodeID and distalNodeID:
      targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
      distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
      if targetNode.GetNumberOfFiducials() and distalNode.GetNumberOfFiducials():
        posTarget = numpy.array([0.0, 0.0, 0.0])
        targetNode.GetNthFiducialPosition(0, posTarget)
        posDistal = numpy.array([0.0, 0.0, 0.0])
        distalNode.GetNthFiducialPosition(0, posDistal)
        redSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeRed")
        matrixRed = redSliceNode.GetSliceToRAS()
        matrixRedInv = vtk.vtkMatrix4x4()
        matrixRedInv.DeepCopy(matrixRed)
        matrixRedInv.Invert()
        posTarget = [posTarget[0],posTarget[1],posTarget[2],1]
        posTargetInRAS = matrixRedInv.MultiplyPoint(posTarget)
        posDistal = [posDistal[0],posDistal[1],posDistal[2],1]
        posDistalInRAS = matrixRedInv.MultiplyPoint(posDistal)
        verticalDirect = numpy.array([-(posDistalInRAS[1]-posTargetInRAS[1]), posDistalInRAS[0]-posTargetInRAS[0], 0, 0])
        verticalDirect = self.cylindarRadius*verticalDirect/numpy.linalg.norm(verticalDirect)
        cylindarInteractorPosInRAS = numpy.array(posTargetInRAS)/2.0 + verticalDirect 
        cylindarInteractorPosInRAS[3] = 1.0
        cylindarInteractorPos = matrixRed.MultiplyPoint(cylindarInteractorPosInRAS)
        self.cylindarInteractor.RemoveAllMarkups()
        self.cylindarInteractor.AddFiducial(cylindarInteractorPos[0],cylindarInteractorPos[1],cylindarInteractorPos[2])
        self.cylindarInteractor.SetNthFiducialLabel(0,"")
        self.cylindarInteractor.SetDisplayVisibility(1)    
    pass
  
  def ReleaseLeftButton(self):
    lm = slicer.app.layoutManager()
    sliceLogics = lm.mrmlSliceLogics()
    for n in range(sliceLogics.GetNumberOfItems()):
      sliceLogic = sliceLogics.GetItemAsObject(n)
      sliceWidget = lm.sliceWidget(sliceLogic.GetName())
      sliceView = sliceWidget.sliceView()  
      interactor = sliceView.interactor()
      interactor.LeftButtonReleaseEvent()  
  
  def createVentricleCylindar(self, caller = None, eventID = None):
    targetNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
    distalNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
    self.cylindarInteractor.SetDisplayVisibility(0)
    if targetNodeID and distalNodeID:
      targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
      distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
      if targetNode and distalNode:
        if targetNode.GetNumberOfFiducials() and distalNode.GetNumberOfFiducials():
          posTarget = numpy.array([0.0, 0.0, 0.0])
          targetNode.GetNthFiducialPosition(0, posTarget)
          posDistal = numpy.array([0.0, 0.0, 0.0])
          distalNode.GetNthFiducialPosition(0, posDistal)
          if numpy.linalg.norm(posDistal-posTarget)<(self.minimalVentricleLen*0.999):
            slicer.util.warningDisplay("The define ventricle horn is too short, distal point is automatically modified to make length longer than 10.0 mm")
            posDistalNew = (posDistal-posTarget)/numpy.linalg.norm(posDistal-posTarget)*self.minimalVentricleLen + posTarget
            distalNode.SetNthFiducialPositionFromArray(0,posDistalNew)
            posDistal = posDistalNew
            self.ReleaseLeftButton()
          if self.trajectoryManager.curveFiducials:
            slicer.mrmlScene.RemoveNode(self.trajectoryManager.curveFiducials)
            self.trajectoryManager.curveFiducials = None
          tempFiducialNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
          tempFiducialNode.RemoveAllMarkups()
          tempFiducialNode.AddFiducial(posTarget[0], posTarget[1], posTarget[2])
          tempFiducialNode.AddFiducial(posDistal[0], posDistal[1], posDistal[2])
          slicer.mrmlScene.AddNode(tempFiducialNode)
          tempFiducialNode.SetDisplayVisibility(0)
          self.trajectoryManager.setManagerTubeRadius(self.cylindarRadius)
          self.trajectoryManager.curveFiducials = tempFiducialNode
          self.trajectoryManager.startEditLine()
          self.trajectoryManager.onLineSourceUpdated()
          self.updateSliceViewBasedOnPoints(posTarget,posDistal)
        else:
          self.trajectoryManager.clearLine()
    else:
      self.trajectoryManager.clearLine()

  def updateCylindarRadius(self, fiducicalMarkerNode = None, eventID = None):
    posInteractor = [0.0,0.0,0.0]
    fiducicalMarkerNode.GetNthFiducialPosition(0,posInteractor)
    targetNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
    distalNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
    if targetNodeID and distalNodeID:
      targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
      distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
      if targetNode.GetNumberOfFiducials() and distalNode.GetNumberOfFiducials():
        posTarget = numpy.array([0.0, 0.0, 0.0])
        targetNode.GetNthFiducialPosition(0, posTarget)
        posDistal = numpy.array([0.0, 0.0, 0.0])
        distalNode.GetNthFiducialPosition(0, posDistal)
        a = (posDistal- posTarget)/numpy.linalg.norm(posDistal-posTarget)
        radius = numpy.linalg.norm(numpy.cross(posInteractor-posTarget,a))
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_cylindarRadius", str(radius))
        self.cylindarRadius = radius
        self.trajectoryManager.setManagerTubeRadius(radius)
        self.trajectoryManager.startEditLine()
        self.trajectoryManager.onLineSourceUpdated()
    pass 

  def createROI(self):
    cropVolumeLogic = slicer.modules.cropvolume.logic()
    if self.baseVolumeNode:
      if not self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume"):
        croppedVolumeNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLScalarVolumeNode")
        croppedVolumeNode.SetName("croppedVolume-NotShownEntity31415")
        slicer.mrmlScene.AddNode(croppedVolumeNode)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume",croppedVolumeNode.GetID())
      croppedVolumeNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume")
      croppedVolumeNode = slicer.mrmlScene.GetNodeByID(croppedVolumeNodeID)
      if self.resetROI:
        children= vtk.vtkCollection()
        self.ROIListNode.GetAllChildren(children)
        ROINodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_ROI")
        if children.GetNumberOfItems():
          if ROINodeID and slicer.mrmlScene.GetNodeByID(ROINodeID):
            slicer.mrmlScene.RemoveNode(slicer.mrmlScene.GetNodeByID(ROINodeID))
          ROINode = children.GetItemAsObject(children.GetNumberOfItems()-1)
          self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_ROI", ROINode.GetID())
          if croppedVolumeNode and ROINode :
            cropVolumeLogic.CropVoxelBased(ROINode,self.baseVolumeNode,croppedVolumeNode)
            ROINode.SetDisplayVisibility(0)
            self.currentVolumeNode = croppedVolumeNode
      else:
        ROINodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_ROI")
        ROINode = slicer.mrmlScene.GetNodeByID(ROINodeID)
        if croppedVolumeNode and ROINode :
          cropVolumeLogic.CropVoxelBased(ROINode,self.baseVolumeNode,croppedVolumeNode)
          ROINode.SetDisplayVisibility(0)
          self.currentVolumeNode = croppedVolumeNode      
    self.resetROI = False   
    pass
    
  
  def defineROI(self):
    if self.baseVolumeNode:
      selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
      interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
      if (selectionNode == None) or (interactionNode == None):
        return
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLAnnotationROINode");
      interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place) 
      slicer.modules.annotations.logic().SetActiveHierarchyNodeID(self.ROIListNode.GetID())
      self.resetROI = True

    pass
  
  def endROIPlacement(self,interactionNode, event):
    pass
    
  def sortPoints(self, inputPointVector, referencePoint):
    minDistanceIndex = 0
    minDistance = 1e10
    for iPos in range(inputPointVector.GetNumberOfPoints()):
      currentPos = numpy.array(inputPointVector.GetPoint(iPos))
      minDistance = numpy.linalg.norm(currentPos-referencePoint)
      minDistanceIndex = iPos
      for jPos in range(iPos, inputPointVector.GetNumberOfPoints()):
        posModelPost = numpy.array(inputPointVector.GetPoint(jPos))
        distanceModelPostNasion = numpy.linalg.norm(posModelPost-referencePoint)
        if distanceModelPostNasion <  minDistance:
          minDistanceIndex = jPos
          minDistance = distanceModelPostNasion
      inputPointVector.SetPoint(iPos,inputPointVector.GetPoint(minDistanceIndex))
      inputPointVector.SetPoint(minDistanceIndex,currentPos)
      
  def constructCurveReference(self, CurveManager,points, distance):
    step = int(0.5*distance/self.samplingFactor)
    CurveManager.step = step
    ApproximityPos = distance * 0.85
    DestiationPos = distance
  
    if CurveManager.curveFiducials == None:
      CurveManager.curveFiducials = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
      CurveManager.curveFiducials.SetName(CurveManager.curveName)
      slicer.mrmlScene.AddNode(CurveManager.curveFiducials) 
    else:
      CurveManager.curveFiducials.RemoveAllMarkups()
      CurveManager.cmLogic.updateCurve()
      
    iPos = 0
    iPosValid = iPos
    posModel = numpy.array(points.GetPoint(iPos))
    CurveManager.cmLogic.DestinationNode = CurveManager._curveModel
    CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2]) 
    CurveManager.cmLogic.CurvePoly = vtk.vtkPolyData() ## For CurveMaker bug
    #CurveManager.cmLogic.enableAutomaticUpdate(1)
    #CurveManager.cmLogic.setInterpolationMethod(1)
    #CurveManager.cmLogic.setTubeRadius(1.0)
    for iPos in range(step,points.GetNumberOfPoints(),step):
      posModel = numpy.array(points.GetPoint(iPos))
      posModelValid = numpy.array(points.GetPoint(iPosValid))
      if  numpy.linalg.norm(posModel-posModelValid)> 50.0:
        continue
      iPosValid = iPos
      CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2]) #adding fiducials takes too long, check the event triggered by this operation
      CurveManager.cmLogic.SourceNode = CurveManager.curveFiducials
      CurveManager.cmLogic.updateCurve()
      if CurveManager.cmLogic.CurveLength>ApproximityPos:
        break
    jPos = iPosValid 
    jPosValid = jPos
    posApprox = numpy.array(points.GetPoint(iPos))
    for jPos in range(iPosValid,points.GetNumberOfPoints(), 1):
      posModel = numpy.array(points.GetPoint(jPos))
      posModelValid = numpy.array(points.GetPoint(jPosValid))
      if  numpy.linalg.norm(posModel-posModelValid)> 50.0:
        continue
      distance = numpy.linalg.norm(posModel-posApprox)+ CurveManager.cmLogic.CurveLength
      if (distance>DestiationPos) or (jPos==points.GetNumberOfPoints()-1):
        CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2])  
        jPosValid = jPos 
        break
       
    #CurveManager.cmLogic.SourceNode.SetAttribute('CurveMaker.CurveModel', CurveManager.cmLogic.DestinationNode.GetID())
    CurveManager.cmLogic.updateCurve()
    CurveManager.cmLogic.CurvePoly = vtk.vtkPolyData() ## For CurveMaker bug
    CurveManager.cmLogic.enableAutomaticUpdate(1)
    CurveManager.cmLogic.setInterpolationMethod(1)
    CurveManager.cmLogic.setTubeRadius(0.5)  
    self.topPoint = points.GetPoint(jPos)
  
  def constructCurvePlanning(self, CurveManager,CurveManagerReference, points, axis):
    posNasion = numpy.array([0.0,0.0,0.0])
    #nasionNode = slicer.mrmlScene.GetNodeByID(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"))
    #nasionNode.GetNthFiducialPosition(0,posNasion)
    if self.sagittalReferenceCurveManager.curveFiducials:
      self.sagittalReferenceCurveManager.curveFiducials.GetNthFiducialPosition(0,posNasion)
    if CurveManager.curveFiducials == None:
      CurveManager.curveFiducials = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
      CurveManager.curveFiducials.SetName(CurveManager.curveName)
      slicer.mrmlScene.AddNode(CurveManager.curveFiducials) 
    else:
      CurveManager.curveFiducials.RemoveAllMarkups()
      CurveManager.cmLogic.updateCurve()
      
    iPos = 0
    iPosValid = iPos
    posModel = numpy.array(points.GetPoint(iPos))
    step = CurveManagerReference.step
    CurveManager.cmLogic.DestinationNode = CurveManager._curveModel
    CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2]) 
    
    numOfRef = CurveManagerReference.curveFiducials.GetNumberOfFiducials()
    
    eps = 1e-2
    if axis == 1:
      lastRefPos = [0.0]*3
      CurveManagerReference.curveFiducials.GetNthFiducialPosition(numOfRef-1, lastRefPos)
      if numpy.linalg.norm(numpy.array(lastRefPos)-numpy.array(points.GetPoint(0)))<eps: #if the planning and reference entry points are identical
        pos = [0.0]*3  
        for iPos in range(1,numOfRef): 
          CurveManagerReference.curveFiducials.GetNthFiducialPosition(numOfRef-iPos-1, pos)
          CurveManager.curveFiducials.AddFiducial(pos[0],pos[1],pos[2])
        CurveManagerReference.curveFiducials.GetNthFiducialPosition(0, pos)    
        self.topPoint = pos       
      else:
        posIntersect = [0.0]*3
        posSearch = [0.0]*3
        minDistance = 1e10
        for iSearch in range(points.GetNumberOfPoints()):
          posSearch = points.GetPoint(iSearch)
          if posSearch[2] > posNasion[2]: #Only the upper part of the cutted sagittal plan is considered
            distance = self.trueSagittalPlane.DistanceToPlane(posSearch)
            if distance < minDistance:
              minDistance = distance
              posIntersect = posSearch

        shift = step
        """
        for iPos in range(1,numOfRef):
          pos = [0.0]*3
          CurveManagerReference.curveFiducials.GetNthFiducialPosition(numOfRef-iPos-1, pos)
          #check if the points is aligned with the reference coronal line, if yes, take the point into the planning curvemanager
          if abs(pos[0]-posIntersect[0])< abs(points.GetPoint(0)[0]-posIntersect[0])and abs(pos[1]-points.GetPoint(0)[1])<eps and abs(pos[2]-points.GetPoint(0)[2])<eps:
            CurveManager.curveFiducials.AddFiducial(pos[0],pos[1],pos[2])
            shift = iPos
            break
        """
        for iPos in range(shift,points.GetNumberOfPoints(),step):
          posModel = numpy.array(points.GetPoint(iPos))
          posModelValid = numpy.array(points.GetPoint(iPosValid))
          if  numpy.linalg.norm(posModel-posModelValid)> 50.0:
            continue
          if (not self.useLeftHemisphere) and (abs(posModel[0]-posIntersect[0])<eps or (posModel[0]<posIntersect[0])):
            break
          elif self.useLeftHemisphere and (abs(posModel[0]-posIntersect[0])<eps or (posModel[0]>posIntersect[0])):
            break
          iPosValid = iPos
          CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2]) #adding fiducials takes too long, check the event triggered by this operation
        jPos = iPosValid
        jPosValid = jPos
        for jPos in range(iPosValid, points.GetNumberOfPoints(), 1):
          posModel = numpy.array(points.GetPoint(jPos))
          posModelValid = numpy.array(points.GetPoint(jPosValid))
          if  numpy.linalg.norm(posModel-posModelValid)> 50.0:
            continue
          if (not self.useLeftHemisphere) and (abs(posModel[0]-posIntersect[0])<eps or (posModel[0]<posIntersect[0])):
            break
          elif self.useLeftHemisphere and (abs(posModel[0]-posIntersect[0])<eps or (posModel[0]>posIntersect[0])):
            break
          jPosValid = jPos
        self.topPoint = points.GetPoint(jPosValid)
        posModel = numpy.array(points.GetPoint(jPosValid))
        CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2])

    if axis ==0:
      for iPos in range(1,numOfRef): 
        pos = [0.0]*3;
        CurveManagerReference.curveFiducials.GetNthFiducialPosition(numOfRef-iPos-1, pos)  
        if float(pos[2])<self.topPoint[2]:
          CurveManager.curveFiducials.AddFiducial(pos[0],pos[1],pos[2]) 
    
    for i in range(CurveManager.curveFiducials.GetNumberOfFiducials()/2):
      pos = [0.0]*3  
      CurveManager.curveFiducials.GetNthFiducialPosition(i,pos)
      posReverse = [0.0]*3  
      CurveManager.curveFiducials.GetNthFiducialPosition(CurveManager.curveFiducials.GetNumberOfFiducials()-i-1,posReverse)
      CurveManager.curveFiducials.SetNthFiducialPositionFromArray(i,posReverse)
      CurveManager.curveFiducials.SetNthFiducialPositionFromArray(CurveManager.curveFiducials.GetNumberOfFiducials()-i-1,pos)
    """  
    for i in range(CurveManager.curveFiducials.GetNumberOfFiducials()):
      pos = [0.0]*3  
      CurveManager.curveFiducials.GetNthFiducialPosition(i,pos)
      print "Planning Pos: ", pos
      CurveManagerReference.curveFiducials.GetNthFiducialPosition(i,pos)
      print "Reference Pos: ", pos
    """  
    CurveManager.cmLogic.SourceNode = CurveManager.curveFiducials
    CurveManager.cmLogic.updateCurve()
    CurveManager.cmLogic.CurvePoly = vtk.vtkPolyData() ## For CurveMaker bug   
    CurveManager.cmLogic.SourceNode.SetAttribute('CurveMaker.CurveModel', CurveManager.cmLogic.DestinationNode.GetID())  
    CurveManager.cmLogic.enableAutomaticUpdate(1)
    CurveManager.cmLogic.setInterpolationMethod(1)
    CurveManager.cmLogic.setTubeRadius(0.5)

  def getIntersectPoints(self, polyData, plane, referencePoint, targetDistance, axis, intersectPoints):
    cutter = vtk.vtkCutter()
    cutter.SetCutFunction(plane)
    cutter.SetInputData(polyData)
    cutter.Update()
    cuttedPolyData = cutter.GetOutput()
    points = cuttedPolyData.GetPoints()
    for iPos in range(points.GetNumberOfPoints()):
      posModel = numpy.array(points.GetPoint(iPos))
      ## distance calculation could be simplified if the patient is well aligned in the scanner
      distanceModelNasion = numpy.linalg.norm(posModel - referencePoint)
      valid = False
      if axis == 0:
        valid = posModel[2] >= referencePoint[2]
      elif axis == 1:
        if self.useLeftHemisphere:
          valid = posModel[0] <= referencePoint[0]
        else:
          valid = posModel[0] >= referencePoint[0]
      if (distanceModelNasion < targetDistance) and valid:
        intersectPoints.InsertNextPoint(posModel)
          
  def getIntersectPointsPlanning(self, polyData, plane, referencePoint, axis, intersectPoints):
    cutter = vtk.vtkCutter()
    cutter.SetCutFunction(plane)
    cutter.SetInputData(polyData)
    cutter.Update()
    cuttedPolyData = cutter.GetOutput()
    points = cuttedPolyData.GetPoints()      
    for iPos in range(points.GetNumberOfPoints()):
      posModel = numpy.array(points.GetPoint(iPos))
      ## distance calculation could be simplified if the patient is well aligned in the scanner
      distanceModelNasion = numpy.linalg.norm(posModel-referencePoint)
      valid = False
      if axis == 0:
        valid = (posModel[2]<=referencePoint[2] or abs(posModel[2]-referencePoint[2])<1e-3 )
      elif axis == 1:
        if self.useLeftHemisphere:
          valid = (posModel[0]>=referencePoint[0] or abs(posModel[0]-referencePoint[0])<1e-3 )
        else:
          valid = (posModel[0]<=referencePoint[0] or abs(posModel[0]-referencePoint[0])<1e-3 )
      if valid:        
          intersectPoints.InsertNextPoint(posModel)        

  def createTrueSagittalPlane(self):
    nasionNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion")
    sagittalPointNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPoint")
    if nasionNodeID and sagittalPointNodeID:
      nasionNode = slicer.mrmlScene.GetNodeByID(nasionNodeID)
      sagittalPointNode = slicer.mrmlScene.GetNodeByID(sagittalPointNodeID)
      posNasion = numpy.array([0.0, 0.0, 0.0])
      if nasionNode:
        if nasionNode.GetNumberOfFiducials():
          nasionNode.GetNthFiducialPosition(0, posNasion)
          posSagittal = numpy.array([0.0, 0.0, 0.0])
          sagittalPointNode.GetNthFiducialPosition(0, posSagittal)
          self.sagittalYawAngle = -numpy.arctan2(posNasion[0] - posSagittal[0], posNasion[1] - posSagittal[1])
          self.trueSagittalPlane = vtk.vtkPlane()
          self.trueSagittalPlane.SetOrigin(posNasion[0], posNasion[1], posNasion[2])
          self.trueSagittalPlane.SetNormal(math.cos(self.sagittalYawAngle), math.sin(self.sagittalYawAngle), 0)

  def createEntryPoint(self) :
    ###All calculation is based on the RAS coordinates system 
    inputModelNode = None
    nasionNode = None
    inputModelNodeID =  self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
    if inputModelNodeID:
      inputModelNode = slicer.mrmlScene.GetNodeByID(inputModelNodeID) 
    nasionNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion")  
    if nasionNodeID:
      nasionNode = slicer.mrmlScene.GetNodeByID(nasionNodeID)  
    if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength"):
      sagittalReferenceLength = float(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength"))   
    if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength")  :
      coronalReferenceLength = float(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength")  )  
    if inputModelNode and (inputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "True") and (nasionNode.GetNumberOfMarkups()) and sagittalReferenceLength and coronalReferenceLength:
      polyData = inputModelNode.GetPolyData()
      if polyData and self.trueSagittalPlane:
        posNasion = numpy.array([0.0,0.0,0.0])
        nasionNode.GetNthFiducialPosition(0,posNasion)
        sagittalPoints = vtk.vtkPoints()
        self.getIntersectPoints(polyData, self.trueSagittalPlane, posNasion, sagittalReferenceLength, 0, sagittalPoints)

        ## Sorting   
        self.sortPoints(sagittalPoints, posNasion)
        self.constructCurveReference(self.sagittalReferenceCurveManager, sagittalPoints, sagittalReferenceLength)  
            
        ##To do, calculate the curvature value points by point might be necessary to exclude the outliers   
        if self.topPoint:
          posNasionBack100 = self.topPoint
          coronalPoints = vtk.vtkPoints()
          coronalPlane = vtk.vtkPlane()
          coronalPlane.SetOrigin(posNasionBack100[0],posNasionBack100[1],posNasionBack100[2])
          coronalPlane.SetNormal(math.sin(self.sagittalYawAngle),-math.cos(self.sagittalYawAngle),0)
          self.getIntersectPoints(polyData, coronalPlane, posNasionBack100, coronalReferenceLength, 1, coronalPoints)
                    
          ## Sorting      
          self.sortPoints(coronalPoints, posNasionBack100)  
          self.constructCurveReference(self.coronalReferenceCurveManager, coronalPoints, coronalReferenceLength)  
    self.lockReferenceLine()        
    pass
   
  def createPlanningLine(self):
    ###All calculation is based on the RAS coordinates system
    inputModelNode = None
    nasionNode = None
    sagittalPlanningLength = None
    coronalPlanningLength = None
    inputModelNodeID =  self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
    if inputModelNodeID:
      inputModelNode = slicer.mrmlScene.GetNodeByID(inputModelNodeID) 
    nasionNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion")  
    if nasionNodeID:
      nasionNode = slicer.mrmlScene.GetNodeByID(nasionNodeID)   
    if inputModelNode and (inputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "True") and (nasionNode.GetNumberOfMarkups()):
      polyData = inputModelNode.GetPolyData()
      if polyData and self.trueSagittalPlane:
        posNasion = numpy.array([0.0,0.0,0.0])
        nasionNode.GetNthFiducialPosition(0,posNasion)
        posEntry = numpy.array([0.0,0.0,0.0])
        if self.cannulaManager.getLastPoint(posEntry):
          normalVec = numpy.array(self.trueSagittalPlane.GetNormal())
          originPos = numpy.array(self.trueSagittalPlane.GetOrigin())
          entryPointAtLeft = -numpy.sign(numpy.dot(numpy.array(posEntry)-originPos, normalVec)) # here left hemisphere means from the patient's perspective
          if entryPointAtLeft >= 0 and self.useLeftHemisphere ==False:
            self.useLeftHemisphere = True
            self.createEntryPoint()
          if entryPointAtLeft < 0 and self.useLeftHemisphere == True:
            self.useLeftHemisphere = False
            self.createEntryPoint()
          coronalPlane = vtk.vtkPlane()
          coronalPlane.SetOrigin(posEntry[0], posEntry[1], posEntry[2])
          coronalPlane.SetNormal(-math.sin(self.sagittalYawAngle), math.cos(self.sagittalYawAngle), 0)
          coronalPoints = vtk.vtkPoints()
          self.getIntersectPointsPlanning(polyData, coronalPlane, posEntry, 1 , coronalPoints)

          ## Sorting   
          self.sortPoints(coronalPoints, posEntry)
          
          self.constructCurvePlanning(self.coronalPlanningCurveManager, self.coronalReferenceCurveManager, coronalPoints, 1)
              
          ##To do, calculate the curvature value points by point might be necessary to exclude the outliers   
          if self.topPoint:
            posTractoryBack = self.topPoint
            sagittalPoints = vtk.vtkPoints()
            sagittalPlane = vtk.vtkPlane()
            sagittalPlane.SetOrigin(posTractoryBack[0],posTractoryBack[1],posTractoryBack[2])
            sagittalPlane.SetNormal(math.cos(self.sagittalYawAngle), math.sin(self.sagittalYawAngle), 0)
            self.getIntersectPointsPlanning(polyData, sagittalPlane, posTractoryBack, 0, sagittalPoints)
                      
            ## Sorting      
            self.sortPoints(sagittalPoints, posTractoryBack)  
            self.constructCurvePlanning(self.sagittalPlanningCurveManager, self.sagittalReferenceCurveManager, sagittalPoints, 0)
            self.lockPlanningLine()
            return True
    return False
    
  def calcPitchYawAngles(self):
    firstPos = numpy.array([0.0,0.0,0.0])
    self.cannulaManager.getFirstPoint(firstPos)
    lastPos = numpy.array([0.0,0.0,0.0])
    self.cannulaManager.getLastPoint(lastPos)
    self.updateSliceViewBasedOnPoints(firstPos, lastPos)
    pass

  def calcCannulaAngles(self):
    inputModelNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
    if inputModelNodeID:
      inputModelNode = slicer.mrmlScene.GetNodeByID(inputModelNodeID)
      if self.cannulaManager.curveFiducials and inputModelNode:
        if self.cannulaManager.curveFiducials.GetNumberOfFiducials():
          posTarget = [0.0,0.0,0.0]
          self.cannulaManager.curveFiducials.GetNthFiducialPosition(0,posTarget)
          posEntry = [0.0,0.0,0.0]
          self.cannulaManager.curveFiducials.GetNthFiducialPosition(1,posEntry)
          p_ES = numpy.array([math.cos(self.sagittalYawAngle), math.sin(self.sagittalYawAngle), 0])
          p_EC = numpy.array([-math.sin(self.sagittalYawAngle), math.cos(self.sagittalYawAngle), 0])
          p_EN = self.calculateModelNorm(inputModelNode, posEntry, self.entryRadius)#numpy.array([-0.5,math.sqrt(0.5),0.5]) #this vector we need to get from the skull Norm calculation

          self.skullNormToCoronalAngle = 90.0 - math.acos(abs(numpy.dot(p_EC, p_EN))) * 180.0 / numpy.pi
          self.skullNormToSaggitalAngle = 90.0 - math.acos(abs(numpy.dot(p_ES, p_EN))) * 180.0 / numpy.pi
          p_EC = p_EC/numpy.linalg.norm(p_EC)
          p_EN = p_EN/numpy.linalg.norm(p_EN)
          p_ET = numpy.array(posEntry) - numpy.array(posTarget)
          p_ET = p_ET / numpy.linalg.norm(p_ET)
          cosCalc = numpy.dot(p_EN, p_ET)
          sinCalc = math.sqrt(1 - cosCalc*cosCalc)
          p_EM = numpy.array([])
          if cosCalc>1e-6: # make sure the p_EN and p_ET are not perpenticular.
            sinTheta1 = numpy.dot(p_EC, p_EN)
            cosTheta1 = math.sqrt(1-sinTheta1*sinTheta1)
            if cosTheta1 < cosCalc:  # here means no intesection between the coronal plan and the cone composed by p_EN and p_ET
              p_EN2 = p_EN - p_EC * sinTheta1
              p_EM = p_EN2 + p_EC * cosTheta1*(sinTheta1 * cosCalc - cosTheta1 * sinCalc) / (cosTheta1 * cosCalc + sinTheta1 * sinCalc)  # sin(theta1 - Calc) = sin(theta1)*cos(Calc) - cos(theta1)*sin(Calc)
              p_EM = p_EM / numpy.linalg.norm(p_EM)
            else:
              p_EN2 = p_EN - p_EC * (sinTheta1)
              cosTheta2 = cosCalc/cosTheta1
              tanTheta2 =  math.sqrt(1/(cosTheta2*cosTheta2) - 1)
              p_EM = p_EN2 + numpy.cross(p_EC, p_EN2)*tanTheta2
              p_EM = p_EM / numpy.linalg.norm(p_EM)
            cosMT = numpy.dot(p_EM, p_ET)
            cosMN = numpy.dot(p_EN, p_EM)
            if p_EM.any():
              self.cannulaToCoronalAngle = math.acos(cosMT) * 180.0 / numpy.pi
              self.cannulaToNormAngle = math.acos(cosCalc) * 180.0 / numpy.pi
              pathNavigationPoints = [numpy.array(posEntry), numpy.array(posEntry) + p_EN * 80,
                                      #numpy.array(posEntry), numpy.array(posEntry) + p_EM * 50,
                                      numpy.array(posEntry), numpy.array(posEntry) + p_ET * 20]
              self.makePath(pathNavigationPoints, 3, 1, "CannulaNavigationLines", self.pathNavigationPoly,
                            self.pathNavigationModel)
              self.pathNavigationModel.GetDisplayNode().SetVisibility(1)
              return 1
            else:
              return 0
          else:
            self.cannulaToCoronalAngle = 0.0
            self.cannulaToNormAngle = 0.0
            return 1
        
    return 0

  def calculateModelNorm(self, inputModel, spherePos, sphereRadius):
    sphere = vtk.vtkSphere()
    sphere.SetCenter(spherePos)
    sphere.SetRadius(sphereRadius)

    triangle = vtk.vtkTriangleFilter()
    triangle.SetInputData(inputModel.GetPolyData())
    triangle.Update()

    clip = vtk.vtkClipPolyData()
    clip.SetInputData(triangle.GetOutput())
    clip.SetClipFunction(sphere)
    clip.InsideOutOn()
    clip.Update()

    clean = vtk.vtkCleanPolyData()
    clean.SetInputConnection(clip.GetOutputPort())
    clean.Update()

    clippedModel = clip.GetOutput()
    cellsNormal = clippedModel.GetPointData().GetNormals()

    averageNormal = numpy.array([0.0, 0.0, 0.0])

    for cellIndex in range(0, cellsNormal.GetNumberOfTuples()):
      cellNormal = [0.0, 0.0, 0.0]
      cellsNormal.GetTuple(cellIndex, cellNormal)

      if not (math.isnan(cellNormal[0]) or math.isnan(cellNormal[1]) or math.isnan(cellNormal[2])):
        averageNormal[0] = averageNormal[0] + cellNormal[0]
        averageNormal[1] = averageNormal[1] + cellNormal[1]
        averageNormal[2] = averageNormal[2] + cellNormal[2]
    averageNormal = averageNormal/numpy.linalg.norm(averageNormal)

    return averageNormal

  def updateSliceViewBasedOnPoints(self, firstPos, lastPos):
    ## due to the RAS and vtk space difference, the X axis is flipped, So the standard rotation matrix is multiplied by -1 in the X axis
    self.pitchAngle = numpy.arctan2(lastPos[2]-firstPos[2], abs(lastPos[1]-firstPos[1]))*180.0/numpy.pi
    self.yawAngle = -numpy.arctan2(lastPos[0]-firstPos[0], abs(lastPos[1]-firstPos[1]))*180.0/numpy.pi
    redSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeRed")
    
    matrixRedOri = redSliceNode.GetSliceToRAS()
    matrixRedNew = vtk.vtkMatrix4x4()
    matrixRedNew.Identity()
    matrixRedNew.SetElement(0, 3, lastPos[0])
    matrixRedNew.SetElement(1, 3, lastPos[1])
    matrixRedNew.SetElement(2, 3, lastPos[2])
    matrixRedNew.SetElement(0, 0, -1)   # The X axis is flipped
    matrixRedNew.SetElement(1, 1, numpy.cos(self.pitchAngle / 180.0 * numpy.pi))
    matrixRedNew.SetElement(1, 2, -numpy.sin(self.pitchAngle / 180.0 * numpy.pi))
    matrixRedNew.SetElement(2, 1, numpy.sin(self.pitchAngle / 180.0 * numpy.pi))
    matrixRedNew.SetElement(2, 2, numpy.cos(self.pitchAngle / 180.0 * numpy.pi))
    matrixRedOri.DeepCopy(matrixRedNew)
    redSliceNode.UpdateMatrices()


    matrixMultiplier = vtk.vtkMatrix4x4()
    yellowSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeYellow")
    matrixYellowOri = yellowSliceNode.GetSliceToRAS()
    matrixYaw = vtk.vtkMatrix4x4()
    matrixYaw.Identity()
    matrixYaw.SetElement(0, 3, lastPos[0])
    matrixYaw.SetElement(1, 3, lastPos[1])
    matrixYaw.SetElement(2, 3, lastPos[2])
    matrixYaw.SetElement(0, 0, -1)  # The X axis is flipped
    matrixYaw.SetElement(0, 0, numpy.cos(self.yawAngle / 180.0 * numpy.pi)) # definition of
    matrixYaw.SetElement(0, 1, -numpy.sin(self.yawAngle / 180.0 * numpy.pi))
    matrixYaw.SetElement(1, 0, numpy.sin(self.yawAngle / 180.0 * numpy.pi))
    matrixYaw.SetElement(1, 1, numpy.cos(self.yawAngle / 180.0 * numpy.pi))
    matrixYellowNew = vtk.vtkMatrix4x4()
    matrixYellowNew.Zero()
    matrixYellowNew.SetElement(0, 2, 1)
    matrixYellowNew.SetElement(1, 0, -1)
    matrixYellowNew.SetElement(2, 1, 1)
    matrixYellowNew.SetElement(3, 3, 1)
    matrixMultiplier.Multiply4x4(matrixYaw, matrixYellowNew, matrixYellowOri)
    yellowSliceNode.UpdateMatrices()

    greenSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeGreen")
    matrixGreenOri = greenSliceNode.GetSliceToRAS()
    matrixGreenOri.DeepCopy(matrixYellowOri)
    greenSliceNode.UpdateMatrices()

    pass

class VentriculostomyPlanningTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_VentriculostomyPlanning1()

  def test_VentriculostomyPlanning1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = VentriculostomyPlanningLogic()
    self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
