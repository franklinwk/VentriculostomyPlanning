import os, inspect
import json
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
from SlicerCaseManager import SlicerCaseManagerWidget, onReturnProcessEvents, beforeRunProcessEvents
from VentriculostomyPlanningUtils.PopUpMessageBox import SerialAssignMessageBox
from SlicerDevelopmentToolboxUtils.buttons import WindowLevelEffectsButton
from shutil import copyfile
from os.path import basename
from os import listdir
from VentriculostomyPlanningUtils.UserEvents import VentriculostomyUserEvents
from abc import ABCMeta, abstractmethod
import datetime
#
# VentriculostomyPlanning


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
    self.logic.register(self)
    self.dicomWidget = DICOMWidget()
    self.dicomWidget.parent.close()
    self.SerialAssignBox = SerialAssignMessageBox()
    self.cameraPos = [0.0]*3
    self.cameraReversePos = None
    self.camera = None
    self.volumeSelected = False
    self.jsonFile = ""
    self.isLoadingCase = False
    layoutManager = slicer.app.layoutManager()
    threeDView = layoutManager.threeDWidget(0).threeDView()
    displayManagers = vtk.vtkCollection()
    threeDView.getDisplayableManagers(displayManagers)
    for index in range(displayManagers.GetNumberOfItems()):
      if displayManagers.GetItemAsObject(index).GetClassName() == 'vtkMRMLCameraDisplayableManager':
        self.camera = displayManagers.GetItemAsObject(index).GetCameraNode().GetCamera()
        self.cameraPos = self.camera.GetPosition()
    self.progressBar = slicer.util.createProgressDialog()
    self.progressBar.close()
    self.red_widget = slicer.app.layoutManager().sliceWidget("Red")
    self.red_cn = self.red_widget.mrmlSliceCompositeNode()
    self.red_cn.SetDoPropagateVolumeSelection(False)

    self.yellow_widget = slicer.app.layoutManager().sliceWidget("Yellow")
    self.yellow_cn = self.yellow_widget.mrmlSliceCompositeNode()
    self.yellow_cn.SetDoPropagateVolumeSelection(False)

    self.green_widget = slicer.app.layoutManager().sliceWidget("Green")
    self.green_cn = self.green_widget.mrmlSliceCompositeNode()
    self.green_cn.SetDoPropagateVolumeSelection(False)
    # Instantiate and connect widgets ...
    #
    # Lines Area
    #


    settingCollapsibleButton = ctk.ctkCollapsibleButton()
    settingCollapsibleButton.collapsed = True
    settingCollapsibleButton.text = "Configuration"
    #self.layout.addWidget(settingCollapsibleButton)
    settingCollapsibleButton.setVisible(True)
    # Layout within the dummy collapsible button
    appSettingLayout = qt.QFormLayout(settingCollapsibleButton)

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
    self.radiusPathPlanningEdit = qt.QLineEdit()
    self.radiusPathPlanningEdit.text = '30.0'
    self.radiusPathPlanningEdit.readOnly = False
    self.radiusPathPlanningEdit.frame = True
    self.radiusPathPlanningEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.radiusPathPlanningEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    radiusPathPlanningUnitLabel = qt.QLabel('mm  ')
    # referenceConfigLayout.addWidget(radiusPathPlanningLabel)
    # referenceConfigLayout.addWidget(self.radiusPathPlanningEdit)
    # referenceConfigLayout.addWidget(radiusPathPlanningUnitLabel)
    appSettingLayout.addRow(referenceConfigLayout)

    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "VentriculostomyPlanning Reload"
    referenceConfigLayout.addWidget(self.reloadButton)

    #
    # Create Entry point Button
    #

    self.createModelButton = qt.QPushButton("Create Surface")
    self.createModelButton.toolTip = "Create a surface model."
    self.createModelButton.enabled = True
    self.createModelButton.connect('clicked(bool)', self.onCreateModel)
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
    self.grayScaleMakerButton = qt.QPushButton("Segment Venous")
    self.grayScaleMakerButton.enabled = True
    self.grayScaleMakerButton.toolTip = "Use the GrayScaleMaker module for vessel calculation "
    detectVesselLabel = qt.QLabel('Detect Vessel')
    # detectVesselLayout.addWidget(detectVesselLabel)
    detectVesselLayout.addWidget(self.grayScaleMakerButton)
    #self.grayScaleMakerButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "vessel.png"))))
    #self.grayScaleMakerButton.setIconSize(qt.QSize(self.grayScaleMakerButton.size))
    self.detectVesselBox.setStyleSheet('QGroupBox{border:0;}')
    # self.mainGUIGroupBoxLayout.addWidget(self.detectVesselBox, 2, 2)


    self.grayScaleMakerButton.connect('clicked(bool)', self.onVenousGrayScaleCalc)
    createVesselHorizontalLayout.addWidget(self.venousCalcStatus)
    self.vesselnessCalcButton = qt.QPushButton("VesselnessCalc")
    self.vesselnessCalcButton.toolTip = "Use Vesselness calculation "
    self.vesselnessCalcButton.enabled = True
    self.vesselnessCalcButton.connect('clicked(bool)', self.onVenousVesselnessCalc)

    # -- Algorithm setting
    surfaceModelConfigLayout = qt.QHBoxLayout()
    surfaceModelThresholdLabel = qt.QLabel('Surface Model Intensity Threshold Setting:  ')
    surfaceModelConfigLayout.addWidget(surfaceModelThresholdLabel)
    self.surfaceModelThresholdEdit = qt.QLineEdit()
    self.surfaceModelThresholdEdit.text = '-500'
    self.surfaceModelThresholdEdit.toolTip = "set this value to the intensity of the skull, higher value means less segmented skull"
    self.surfaceModelThresholdEdit.setMaxLength(6)
    self.surfaceModelThresholdEdit.readOnly = False
    self.surfaceModelThresholdEdit.frame = True
    self.surfaceModelThresholdEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.surfaceModelThresholdEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    surfaceModelConfigLayout.addWidget(self.surfaceModelThresholdEdit)
    surfaceModelConfigLayout.addWidget(self.createModelButton)

    distanceMapConfigLayout = qt.QHBoxLayout()
    distanceMapThresholdLabel = qt.QLabel('Distance Map Intensity Threshold Setting:  ')
    distanceMapConfigLayout.addWidget(distanceMapThresholdLabel)
    self.distanceMapThresholdEdit = qt.QLineEdit()
    self.distanceMapThresholdEdit.text = '100'
    self.distanceMapThresholdEdit.toolTip = "Set the value to the intensity of venous. higher value means less venous"
    self.distanceMapThresholdEdit.setMaxLength(6)
    self.distanceMapThresholdEdit.readOnly = False
    self.distanceMapThresholdEdit.frame = True
    self.distanceMapThresholdEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.distanceMapThresholdEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    distanceMapConfigLayout.addWidget(self.distanceMapThresholdEdit)

    venousMarginLabel = qt.QLabel('Venous Safty Margin:  ')
    distanceMapConfigLayout.addWidget(venousMarginLabel)
    self.venousMarginEdit = qt.QLineEdit()
    self.venousMarginEdit.text = '10.0'
    self.venousMarginEdit.setMaxLength(6)
    self.venousMarginEdit.readOnly = False
    self.venousMarginEdit.frame = True
    self.venousMarginEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.venousMarginEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    distanceMapConfigLayout.addWidget(self.venousMarginEdit)
    venousMarginUnitLabel = qt.QLabel('mm  ')
    distanceMapConfigLayout.addWidget(venousMarginUnitLabel)
    distanceMapConfigLayout.addWidget(self.grayScaleMakerButton)
    appSettingLayout.addRow(surfaceModelConfigLayout)
    appSettingLayout.addRow(distanceMapConfigLayout)

    self.surfaceModelThresholdEdit.connect('textEdited(QString)', self.onModifySurfaceModel)
    self.distanceMapThresholdEdit.connect('textEdited(QString)', self.onModifyVenousMargin)
    self.venousMarginEdit.connect('textEdited(QString)', self.onModifyVenousMargin)


    self.reloadButton.connect('clicked()', self.onReload)
    self.lengthSagittalReferenceLineEdit.connect('textEdited(QString)', self.onModifyMeasureLength)
    self.lengthCoronalReferenceLineEdit.connect('textEdited(QString)', self.onModifyMeasureLength)
    self.radiusPathPlanningEdit.connect('textEdited(QString)', self.onModifyPathPlanningRadius)

    # PatientModel Area
    #
    #referenceCollapsibleButton = ctk.ctkCollapsibleButton()
    #referenceCollapsibleButton.text = "Reference Generating "
    #self.layout.addWidget(referenceCollapsibleButton)
    
    # Layout within the dummy collapsible button
    #referenceFormLayout = qt.QFormLayout(referenceCollapsibleButton)

    self.caseManagerBox = qt.QGroupBox()
    CaseManagerConfigLayout = qt.QVBoxLayout()
    self.caseManagerBox.setLayout(CaseManagerConfigLayout)
    slicerCaseWidgetParent = slicer.qMRMLWidget()
    slicerCaseWidgetParent.setLayout(qt.QVBoxLayout())
    slicerCaseWidgetParent.setMRMLScene(slicer.mrmlScene)
    self.slicerCaseWidget = SlicerCaseManagerWidget(slicerCaseWidgetParent)
    self.slicerCaseWidget.logic.register(self)
    CaseManagerConfigLayout.addWidget(self.slicerCaseWidget.patientWatchBox)
    CaseManagerConfigLayout.addWidget(self.slicerCaseWidget.collapsibleDirectoryConfigurationArea)
    CaseManagerConfigLayout.addWidget(self.slicerCaseWidget.mainGUIGroupBox)
    self.layout.addWidget(self.caseManagerBox)

    #referenceFormLayout.addRow(CaseManagerConfigLayout)
    #
    # input volume selector
    #

    self.mainGUIGroupBox = qt.QGroupBox()
    self.mainGUIGroupBoxLayout = qt.QGridLayout()
    self.mainGUIGroupBox.setLayout(self.mainGUIGroupBoxLayout)

    buttonWidth = 45
    buttonHeight = 45

    self.inputVolumeBox = qt.QGroupBox()
    inputVolumeLayout = qt.QGridLayout()
    #inputVolumeLayout.setAlignment(qt.Qt.AlignHCenter)
    self.inputVolumeBox.setLayout(inputVolumeLayout)
    venousVolumeLabel = qt.QLabel('Venous: ')
    self.venousVolumeNameLabel = qt.QLineEdit()
    self.venousVolumeNameLabel.text = '--'
    self.venousVolumeNameLabel.setMaxLength(50)
    self.venousVolumeNameLabel.readOnly = True
    #self.venousVolumeNameLabel.frame = True
    self.venousVolumeNameLabel.styleSheet = "QLineEdit { background:transparent; }"
    inputVolumeLayout.addWidget(venousVolumeLabel,0,0)
    inputVolumeLayout.addWidget(self.venousVolumeNameLabel,0,1)
    ventricleVolumeLabel = qt.QLabel('Ventricle: ')
    self.ventricleVolumeNameLabel = qt.QLineEdit()
    self.ventricleVolumeNameLabel.text = '--'
    self.ventricleVolumeNameLabel.setMaxLength(50)
    self.ventricleVolumeNameLabel.readOnly = True
    #self.ventricleVolumeNameLabel.frame = True
    self.ventricleVolumeNameLabel.styleSheet = "QLineEdit { background:transparent; }"
    inputVolumeLayout.addWidget(ventricleVolumeLabel,0,2)
    inputVolumeLayout.addWidget(self.ventricleVolumeNameLabel,0,3)
    self.showVolumeTable = qt.QPushButton("Show Table")
    self.showVolumeTable.toolTip = "Show the table of volumes for assignment."
    self.showVolumeTable.enabled = True
    self.showVolumeTable.connect('clicked(bool)', self.onShowVolumeTable)
    inputVolumeLayout.addWidget(self.showVolumeTable,0,4)
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.inputVolumeSelector.editEnabled = False
    self.inputVolumeSelector.addEnabled = False
    self.inputVolumeSelector.removeEnabled = False
    self.inputVolumeSelector.selectNodeUponCreation = False
    #self.inputVolumeSelector.sortFilterProxyModel().setFilterRegExp("(Venous)")
    #self.inputVolumeSelector.sortFilterProxyModel().setFilterRegExp("^((?!NotShownEntity31415).)*$" )
    #self.inputVolumeSelector.connect("nodeAdded(vtkMRMLNode*)", self.onAddedNode)
    #self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    #inputVolumeLayout.addWidget(self.inputVolumeSelector)
    self.layout.addWidget(self.inputVolumeBox)
    self.layout.addWidget(self.mainGUIGroupBox)
    self.importedNodeIDs= []

    self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, self.onVolumeAddedNode)
    #
    # Create Model Button
    #
    #self.mainGUIGroupBoxLayout.addWidget(self.inputVolumeSelector,1,0)


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
    self.selectNasionButton.setCheckable(True)
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
    self.selectSagittalButton.setCheckable(True)
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

    self.LoadCaseButton.connect('clicked(bool)', self.onLoadDicom)
    self.selectNasionButton.connect('clicked(bool)', self.onSelectNasionPoint)
    self.selectSagittalButton.connect('clicked(bool)', self.onSelectSagittalPoint)
    self.createEntryPointButton.connect('clicked(bool)', self.onCreateEntryPoint)

    

    #
    # Trajectory
    #


    #-- Add Point
    self.addCannulaBox = qt.QGroupBox()
    addCannulaLayout = qt.QVBoxLayout()
    addCannulaLayout.setAlignment(qt.Qt.AlignCenter)
    self.addCannulaBox.setLayout(addCannulaLayout)
    self.addCannulaTargetButton = qt.QPushButton("")
    self.addCannulaTargetButton.setCheckable(True)
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

    self.addVesselSeedBox = qt.QGroupBox()
    addVesselSeedLayout = qt.QVBoxLayout()
    addVesselSeedLayout.setAlignment(qt.Qt.AlignCenter)
    self.addVesselSeedBox.setLayout(addVesselSeedLayout)
    self.addVesselSeedButton = qt.QPushButton("")
    self.addVesselSeedButton.setCheckable(True)
    self.addVesselSeedButton.toolTip = ""
    self.addVesselSeedButton.enabled = True
    addVesselSeedLayout.addWidget(self.addVesselSeedButton)
    self.addVesselSeedButton.setMaximumHeight(buttonHeight)
    self.addVesselSeedButton.setMaximumWidth(buttonWidth)
    self.addVesselSeedButton.setToolTip("place the seeds on the vessels")
    self.addVesselSeedButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "cannula.png"))))
    self.addVesselSeedButton.setIconSize(qt.QSize(self.addVesselSeedButton.size))
    self.addVesselSeedButton.connect('clicked(bool)', self.onPlaceVesselSeed)
    self.mainGUIGroupBoxLayout.addWidget(self.addVesselSeedButton, 2, 4)

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
    self.mainGUIGroupBoxLayout.addWidget(self.generatePathButton, 2, 5)

    # end of GUI section
    #####################################
    createPlanningLineHorizontalLayout = qt.QHBoxLayout()
    self.lockTrajectoryCheckBox = qt.QCheckBox()
    self.lockTrajectoryCheckBox.checked = 0
    self.lockTrajectoryCheckBox.setToolTip("If checked, the trajectory will be locked.")
    createPlanningLineHorizontalLayout.addWidget(self.lockTrajectoryCheckBox)

    self.setReverseViewButton = qt.QPushButton("Set Reverse 3D View")
    self.setReverseViewButton.setMinimumWidth(150)
    self.setReverseViewButton.toolTip = "Change the perspective view in 3D viewer."
    self.setReverseViewButton.enabled = True
    createPlanningLineHorizontalLayout.addWidget(self.setReverseViewButton)
    self.setReverseViewButton.connect('clicked(bool)', self.onSetReverseView)
    self.isReverseView = False

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
    # self.viewSubGroupBox.setStyleSheet("border:3")

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
    self.createPlanningLineButton.connect('clicked(bool)', self.onCreatePlanningLine)
    self.createPlanningLineButton.setMaximumHeight(buttonHeight)
    self.createPlanningLineButton.setMaximumWidth(buttonWidth)
    self.createPlanningLineButton.setIcon(qt.QIcon(qt.QPixmap(os.path.join(self.scriptDirectory, "confirm.png"))))
    self.createPlanningLineButton.setIconSize(qt.QSize(self.createPlanningLineButton.size))
    self.confirmBox.setStyleSheet('QGroupBox{border:0;}')
    self.mainGUIGroupBoxLayout.addWidget(self.createPlanningLineButton, 2, 6)

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

     # Needle trajectory
    self.addCannulaTargetButton.connect('clicked(bool)', self.onEditPlanningTarget)
    #self.addCannulaDistalButton.connect('clicked(bool)', self.onEditPlanningDistal)
    self.generatePathButton.connect('clicked(bool)', self.onGeneratePath)
    self.clearTrajectoryButton.connect('clicked(bool)', self.onClearTrajectory)
    self.lockTrajectoryCheckBox.connect('toggled(bool)', self.onLock)

    #
    # Mid-sagittalReference line
    #


    #-- Curve length
    planningSagittalLineLayout = qt.QHBoxLayout()
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

    planningDistanceKocherLayout = qt.QHBoxLayout()
    distanceKocherPointLabel = qt.QLabel("Distance to Kocher's point:  ")
    planningDistanceKocherLayout.addWidget(distanceKocherPointLabel)
    self.distanceKocherPointEdit = qt.QLineEdit()
    self.distanceKocherPointEdit.text = '--'
    self.distanceKocherPointEdit.setMaxLength(5)
    self.distanceKocherPointEdit.readOnly = True
    self.distanceKocherPointEdit.frame = True
    self.distanceKocherPointEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.distanceKocherPointEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningDistanceKocherLayout.addWidget(self.distanceKocherPointEdit)
    distanceKocherPointUnitLabel = qt.QLabel('mm  ')
    planningDistanceKocherLayout.addWidget(distanceKocherPointUnitLabel)

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
    self.infoGroupBoxLayout.addLayout(planningDistanceKocherLayout)
    self.infoGroupBoxLayout.addLayout(planningPitchAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningYawAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningSkullNormToSagittalAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningSkullNormToCoronalAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningCannulaToNormAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningCannulaToCoronalAngleLayout)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    #self.onSelect(self.inputVolumeSelector.currentNode())
    self.initialNodesIDList = []
    allNodes = slicer.mrmlScene.GetNodes()
    for nodeIndex in range(allNodes.GetNumberOfItems()):
      node = allNodes.GetItemAsObject(nodeIndex)
      self.initialNodesIDList.append(node.GetID())
    self.onSetSliceViewer()

  def cleanup(self):
    self.importedNodeIDs = []
    pass

  def updateFromCaseManager(self, EventID):
    if EventID == VentriculostomyUserEvents.CloseCaseEvent:
      self.logic.clear()
      self.SerialAssignBox = SerialAssignMessageBox()
      self.initialFieldsValue()
      self.volumeSelected = False
      self.venousVolumeNameLabel.text = ""
      self.ventricleVolumeNameLabel.text = ""
      self.isLoadingCase = False
    elif EventID == VentriculostomyUserEvents.LoadCaseCompletedEvent:
      allNodes = slicer.mrmlScene.GetNodes()
      for nodeIndex in range(allNodes.GetNumberOfItems()):
        node = allNodes.GetItemAsObject(nodeIndex)
        if node.IsA("vtkMRMLVolumeNode") and node.GetAttribute("vtkMRMLScalarVolumeNode.rel_ventricleVolume"):
          self.logic.baseVolumeNode = node
          self.logic.ventricleVolume = slicer.mrmlScene.GetNodeByID(node.GetAttribute("vtkMRMLScalarVolumeNode.rel_ventricleVolume"))
      if self.logic.baseVolumeNode and self.logic.ventricleVolume:
        self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_ventricleVolume",
                                               self.logic.ventricleVolume.GetID())
        self.venousVolumeNameLabel.text = self.logic.baseVolumeNode.GetName()
        self.ventricleVolumeNameLabel.text = self.logic.ventricleVolume.GetName()
        self.SerialAssignBox.volumesCheckedDict = { "Venous" : self.logic.baseVolumeNode,
                                                    "Ventricle": self.logic.ventricleVolume,
                                                  }
        self.SerialAssignBox.AppendVolumeNode(self.logic.baseVolumeNode)
        self.SerialAssignBox.AppendVolumeNode(self.logic.ventricleVolume)
        self.onSelect(self.logic.baseVolumeNode)
      else:
        slicer.util.warningDisplay("Case is not valid, no venous volume found")
      self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                   self.onVolumeAddedNode)
      self.isLoadingCase = False
    elif EventID == VentriculostomyUserEvents.StartCaseImportEvent:
      self.red_cn.SetDoPropagateVolumeSelection(False) # make sure the compositenode doesn't get updated,
      self.green_cn.SetDoPropagateVolumeSelection(False) # so that the background and foreground volumes are not messed up
      self.yellow_cn.SetDoPropagateVolumeSelection(False)
      self.isLoadingCase = True
      slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
    pass

  def updateFromLogic(self, EventID):
    if EventID == VentriculostomyUserEvents.ResetButtonEvent:
      self.onResetButtons()
    if EventID == VentriculostomyUserEvents.SetSliceViewerEvent:
      self.onSetSliceViewer()
    if EventID == VentriculostomyUserEvents.SaveModifiedFiducialEvent:
      self.onSaveData()

  def initialFieldsValue(self):
    self.lengthSagittalPlanningLineEdit.text = '--'
    self.lengthCoronalPlanningLineEdit.text = '--'
    self.distanceKocherPointEdit.text = '--'
    self.lengthCannulaEdit.text = '--'
    self.pitchAngleEdit.text = '--'
    self.yawAngleEdit.text = '--'
    self.skullNormToSagittalAngleEdit.text = '--'
    self.skullNormToCoronalAngleEdit.text = '--'
    self.cannulaToNormAngleEdit.text = '--'
    self.cannulaToCoronalAngleEdit.text = '--'

  def onLoadDicom(self):
    self.logic.baseVolumeNode = None
    self.logic.ventricleVolume = None
    self.inputVolumeSelector.setCurrentNode(None)
    self.dicomWidget.detailsPopup.open()  
    pass

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onVolumeAddedNode(self, caller, eventId, callData):
    # When we are loading the cases, though the slicer.mrmlScene.NodeAddedEvent is removed, sometimes this function is still triggered.
    # We use the flag isLoadingCase to make sure it is not called.
    if callData.IsA("vtkMRMLVolumeNode") and (not self.isLoadingCase):
      volumeName = callData.GetName()
      #self.importedNodeIDs.append(callData.GetID())
      if self.onSaveDicomFiles():
        self.SerialAssignBox.AppendVolumeNode(callData)
        self.initialNodesIDList.append(callData.GetID())
        if ("Venous" in volumeName) or ("venous" in volumeName) :
          self.logic.baseVolumeNode = callData
          self.SerialAssignBox.volumesCheckedDict["Venous"] = callData
          self.SerialAssignBox.SetCheckBoxAccordingToAssignment()
          self.venousVolumeNameLabel.text = self.logic.baseVolumeNode.GetName()
        elif ("Ventricle" in volumeName) or ("ventricle" in volumeName) :
          self.logic.ventricleVolume = callData
          self.SerialAssignBox.volumesCheckedDict["Ventricle"] = callData
          self.SerialAssignBox.SetCheckBoxAccordingToAssignment()
          self.ventricleVolumeNameLabel.text = self.logic.ventricleVolume.GetName()
        else:
          self.onShowVolumeTable()
        if self.logic.baseVolumeNode and self.logic.ventricleVolume and (not self.volumeSelected):
          self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_ventricleVolume", self.logic.ventricleVolume.GetID())
          self.logic.ventricleVolume.SetAttribute("vtkMRMLScalarVolumeNode.rel_venousVolume", self.logic.baseVolumeNode.GetID())
          self.volumeSelected = True
          self.dicomWidget.detailsPopup.close()
          self.progressBar.value = 0
          self.progressBar.labelText = 'Saving imported volume'
          slicer.app.processEvents()
          outputDir = os.path.join(self.slicerCaseWidget.currentCaseDirectory, "Results")
          self.logic.savePlanningDataToDirectory(self.logic.baseVolumeNode, outputDir)
          self.logic.savePlanningDataToDirectory(self.logic.ventricleVolume, outputDir)
          self.onSelect(self.logic.baseVolumeNode)



        #the setForegroundVolume will not work, because the slicerapp triggers the SetBackgroundVolume after the volume is loaded
  def onShowVolumeTable(self):
    userAction = self.SerialAssignBox.ShowVolumeTable()
    if userAction == 0:
      if (not self.logic.baseVolumeNode == self.SerialAssignBox.volumesCheckedDict.get("Venous")) or (not self.logic.ventricleVolume == self.SerialAssignBox.volumesCheckedDict.get("Ventricle")):
        userSelectValid = False
        if self.logic.baseVolumeNode == None or self.logic.ventricleVolume == None:
          userSelectValid = True
        else:   
          if slicer.util.confirmYesNoDisplay("Are you sure you want set the base image?",
                                                 windowTitle=""):
            userSelectValid = True
        if userSelectValid:    
          self.SerialAssignBox.ConfirmUserChanges()
          if (self.SerialAssignBox.volumesCheckedDict.get("Venous")):
            self.logic.baseVolumeNode = self.SerialAssignBox.volumesCheckedDict.get("Venous")
          if (self.SerialAssignBox.volumesCheckedDict.get("Ventricle")):
            self.logic.ventricleVolume = self.SerialAssignBox.volumesCheckedDict.get("Ventricle")
          if self.logic.baseVolumeNode:
            self.venousVolumeNameLabel.text = self.logic.baseVolumeNode.GetName()
          if self.logic.ventricleVolume:
            self.ventricleVolumeNameLabel.text = self.logic.ventricleVolume.GetName()
          if self.logic.baseVolumeNode and self.logic.ventricleVolume:
            self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_ventricleVolume",
                                                 self.logic.ventricleVolume.GetID())
            self.initialNodesIDList.append(self.logic.baseVolumeNode.GetDisplayNodeID()) 
            self.initialNodesIDList.append(self.logic.baseVolumeNode.GetStorageNodeID()) 
            self.initialNodesIDList.append(self.logic.ventricleVolume.GetDisplayNodeID())  
            self.initialNodesIDList.append(self.logic.ventricleVolume.GetStorageNodeID())
            allNodes = slicer.mrmlScene.GetNodes()
            for nodeIndex in range(allNodes.GetNumberOfItems()):
              node = allNodes.GetItemAsObject(nodeIndex)
              if node and (not (node.GetID() in self.initialNodesIDList)):
                if (not (node.GetClassName() == "vtkMRMLScriptedModuleNode")) and \
                   (not node.IsA("vtkMRMLDisplayNode")) and (not node.IsA("vtkMRMLStorageNode"))\
                   and (not (node.GetClassName() == "vtkMRMLCommandLineModuleNode")) and node.GetDisplayNode():
                     slicer.mrmlScene.RemoveNode(node.GetDisplayNode())
                slicer.mrmlScene.RemoveNode(node)
            slicer.app.processEvents()    
            self.onSelect(self.logic.baseVolumeNode)
            self.venousVolumeNameLabel.text = self.logic.baseVolumeNode.GetName()
            self.ventricleVolumeNameLabel.text = self.logic.ventricleVolume.GetName()
        else:
          self.SerialAssignBox.CancelUserChanges()
      else:
        self.SerialAssignBox.CancelUserChanges()
    else:
      self.SerialAssignBox.CancelUserChanges()

  def onSaveDicomFiles(self):
    # use decoration to improve the method
    if not os.path.exists(self.slicerCaseWidget.planningDICOMDataDirectory):
      slicer.util.warningDisplay("No case is created, create a case first. The current serial is not saved.")
      return False
    checkedFiles = self.dicomWidget.detailsPopup.fileLists
    for dicomseries in checkedFiles:
      for dicom in dicomseries:
        copyfile(dicom,os.path.join(self.slicerCaseWidget.planningDICOMDataDirectory,basename(dicom)))
    return True
  
  @beforeRunProcessEvents
  def onSelect(self, selectedNode=None):
    if selectedNode:
      self.red_cn.SetDoPropagateVolumeSelection(False)  # make sure the compositenode doesn't get updated,
      self.green_cn.SetDoPropagateVolumeSelection(False)  # so that the background and foreground volumes are not messed up
      self.yellow_cn.SetDoPropagateVolumeSelection(False)
      self.initialFieldsValue()
      self.logic.clear()
      self.logic.__init__()
      self.logic.register(self)
      if self.slicerCaseWidget.planningDICOMDataDirectory and listdir(self.slicerCaseWidget.planningDICOMDataDirectory):
        self.slicerCaseWidget.patientWatchBox.sourceFile = os.path.join(self.slicerCaseWidget.planningDICOMDataDirectory,listdir(self.slicerCaseWidget.planningDICOMDataDirectory)[0])
      self.logic.baseVolumeNode = selectedNode
      if self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_ventricleVolume"):
        self.logic.ventricleVolume = slicer.mrmlScene.GetNodeByID(self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_ventricleVolume"))
      """
      ventricleVolumeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_ventricleVolume")
      if not ventricleVolumeID:
        if len(self.importedNodeIDs) ==2:
          slicer.util.warningDisplay("No ventricle volume defined, the other volume is selected as Ventricle volume.")
          if self.logic.baseVolumeNode.GetID() == self.importedNodeIDs[0]:
            self.logic.ventricleVolume = slicer.mrmlScene.GetNodeByID(self.importedNodeIDs[1])
          else:
            self.logic.ventricleVolume = slicer.mrmlScene.GetNodeByID(self.importedNodeIDs[0])  
        else:    
          slicer.util.warningDisplay("This case has a volume number other than two, please load the data correctly into slicer or define the images manually", windowTitle="")
      else:
        self.logic.ventricleVolume = slicer.mrmlScene.GetNodeByID(ventricleVolumeID)
      """
      if self.logic.ventricleVolume and self.logic.baseVolumeNode:
        outputDir = os.path.join(self.slicerCaseWidget.currentCaseDirectory, "Results")
        self.jsonFile = os.path.join(outputDir, "PlanningTimeStamp.json")
        self.logic.appendPlanningTimeStampToJson(self.jsonFile, "StartPreProcessing",
                                                 datetime.datetime.now().time().isoformat())
        caseName = ""
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_model",caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_nasion",caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPoint", caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_target",caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_distal", caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_cylinderRadius",caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_cannula", caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_skullNorm", caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_cannulaModel",caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_sagittalReferenceModel",caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_coronalReferenceModel",caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPlanningModel",caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_coronalPlanningModel",caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel",caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin", caseName)
        self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessVolume",caseName) # currently not used
        self.logic.enableEventObserver()
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
        #self.logic.sagittalReferenceCurveManager.startEditLine()
        #self.logic.coronalReferenceCurveManager.startEditLine()
        #self.logic.sagittalPlanningCurveManager.startEditLine()
        #self.logic.coronalPlanningCurveManager.startEditLine()
        #self.logic.cylinderManager.startEditLine()
        self.logic.createTrueSagittalPlane()
        self.logic.createEntryPoint()
        cannulaModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cannulaModel")
        cannulaFiducialsID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cannula")
        self.logic.pathNavigationModel.SetDisplayVisibility(0)
        self.logic.cannulaManager._curveModel = slicer.mrmlScene.GetNodeByID(cannulaModelID)
        self.logic.cannulaManager.curveFiducials = slicer.mrmlScene.GetNodeByID(cannulaFiducialsID)
        self.logic.cannulaManager.curveFiducials.AddObserver(slicer.vtkMRMLMarkupsNode().PointStartInteractionEvent, self.logic.updateSelectedMarker)
        self.logic.cannulaManager.curveFiducials.AddObserver(slicer.vtkMRMLMarkupsNode().PointModifiedEvent, self.logic.updateCannulaPosition)
        self.logic.cannulaManager.curveFiducials.AddObserver(slicer.vtkMRMLMarkupsNode().PointEndInteractionEvent, self.logic.endCannulaInteraction)
        #self.logic.cannulaManager.curveFiducials.AddObserver(VentriculostomyUserEvents.UpdateCannulaTargetPoint, self.logic.updateCannulaTargetPoint)
        self.logic.cannulaManager.setModifiedEventHandler(self.onCannulaModified)
        self.logic.cannulaManager.startEditLine()
        self.logic.createVentricleCylinder()
        self.onCreatePlanningLine()
        self.isReverseView = False
        self.progressBar.show()
        self.progressBar.labelText = 'Calculating Skull Surface'
        slicer.app.processEvents()
        self.onCreateModel()
        self.progressBar.value = 25
        self.progressBar.labelText = 'Calculating Vessel'
        slicer.app.processEvents()
        self.onVenousGrayScaleCalc()
        self.progressBar.value = 75
        self.logic.calculateCannulaTransform()
        self.onSetSliceViewer()
        self.onSet3DViewer()
        self.progressBar.labelText = 'Saving Preprocessed Data'
        slicer.app.processEvents()
        self.onSaveData()
        self.progressBar.close()
        self.logic.appendPlanningTimeStampToJson(self.jsonFile, "EndPreprocessing",
                                                 datetime.datetime.now().time().isoformat())
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
      self.logic.calculateDistanceToKocher()
      self.lengthSagittalPlanningLineEdit.text = '%.1f' % self.logic.getSagittalPlanningLineLength()
      self.lengthCoronalPlanningLineEdit.text = '%.1f' % self.logic.getCoronalPlanningLineLength()
      self.distanceKocherPointEdit.text = '%.1f' % self.logic.kocherDistance
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
    self.distanceKocherPointEdit.text = '--'
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
        self.setReverseViewButton.setText("  Reset View     ")
        self.isReverseView = True
        displayManagers = vtk.vtkCollection()
        threeDView.getDisplayableManagers(displayManagers)
        for index in range(displayManagers.GetNumberOfItems()):
          if displayManagers.GetItemAsObject(index).GetClassName() == 'vtkMRMLCameraDisplayableManager':
            self.camera = displayManagers.GetItemAsObject(index).GetCameraNode().GetCamera()
            self.cameraPos = self.camera.GetPosition()
        if not self.cameraReversePos:
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
          self.cameraReversePos = self.camera.GetPosition()
        else:
          self.camera.SetPosition(self.cameraReversePos)
          threeDView.zoomIn()  # to refresh the 3D viewer, when the view position is inside the skull model, the model is not rendered,
          threeDView.zoomOut()  # Zoom in and out will refresh the viewer
      else:
        displayManagers = vtk.vtkCollection()
        threeDView.getDisplayableManagers(displayManagers)
        for index in range(displayManagers.GetNumberOfItems()):
          if displayManagers.GetItemAsObject(index).GetClassName() == 'vtkMRMLCameraDisplayableManager':
            self.camera = displayManagers.GetItemAsObject(index).GetCameraNode().GetCamera()
            self.cameraReversePos = self.camera.GetPosition()
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
  
  def onPlaceVesselSeed(self):
    if self.addVesselSeedButton.isChecked():
      if not self.logic.baseVolumeNode:
        slicer.util.warningDisplay("No case is selected, please create a case", windowTitle="")
      else:
        targetNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
        distalNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
        if targetNodeID and distalNodeID:
          ventriculCylinder = self.cylinderManager._curveModel.GetPolyData()
          if ventriculCylinder:
            print "adding"
            self.onSet3DViewer()
          self.onSetSliceViewer()
    else:
      self.logic.placeWidget.setPlaceModeEnabled(False)
    pass
    
  def onCreateModel(self):
    if self.logic.baseVolumeNode:
      outputModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
      if outputModelNodeID:
        outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
        #outputModelNode.SetAttribute("vtkMRMLModelNode.modelCreated","False")
        slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
        try:
          self.logic.createModel(outputModelNode, self.logic.sufaceModelThreshold)
        except ValueError:
          slicer.util.warningDisplay(
            "Skull surface calculation error, volumes might not be suitable for calculation")
        finally:
          slicer.app.processEvents()
          self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                     self.onVolumeAddedNode)
          self.onSet3DViewer()
          self.onSaveData()

  def onSelectNasionPoint(self):
    if self.selectNasionButton.isChecked():
      if not self.logic.baseVolumeNode:
        slicer.util.warningDisplay("No case is selected, please select the case in the combox", windowTitle="")
      else:
        outputModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
        if outputModelNodeID:
          outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
          if (not outputModelNode) or outputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False":
              self.logic.createModel(outputModelNode, self.logic.sufaceModelThreshold)
              self.onSet3DViewer()
          self.logic.selectNasionPointNode(outputModelNode) # when the model is not available, the model will be created, so nodeAdded signal should be disconnected
          self.onSetSliceViewer()
    else:
      self.logic.placeWidget.setPlaceModeEnabled(False)
      nasionNode = slicer.mrmlScene.GetNodeByID(self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"))
      dnode = nasionNode.GetMarkupsDisplayNode()
      if dnode:
        dnode.SetVisibility(1)

  def onSelectSagittalPoint(self):
    if self.selectSagittalButton.isChecked():
      if not self.logic.baseVolumeNode:
        slicer.util.warningDisplay("No case is selected, please select the case in the combox", windowTitle="")
      else:
        outputModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
        if outputModelNodeID:
          outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
          if (not outputModelNode) or outputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False":
              self.logic.createModel(outputModelNode, self.logic.sufaceModelThreshold)
              self.onSet3DViewer()
          self.logic.selectSagittalPointNode(outputModelNode) # when the model is not available, the model will be created, so nodeAdded signal should be disconnected
          self.onSetSliceViewer()
    else:
      self.logic.placeWidget.setPlaceModeEnabled(False)

  def onSaveData(self):
    if not self.isLoadingCase:
      outputDir = os.path.join(self.slicerCaseWidget.currentCaseDirectory, "Results")
      nodeAttributes=["rel_model","rel_nasion","rel_sagittalPoint","rel_target","rel_distal",\
                      "rel_cannula","rel_skullNorm","rel_cannulaModel","rel_sagittalReferenceModel","rel_coronalReferenceModel",\
                      "rel_sagittalPlanningModel","rel_coronalPlanningModel","rel_grayScaleModel","rel_grayScaleModelWithMargin","rel_vesselnessVolume"]
      for attribute in nodeAttributes:
        nodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode."+attribute)
        if nodeID and slicer.mrmlScene.GetNodeByID(nodeID):
          node = slicer.mrmlScene.GetNodeByID(nodeID)
          if node.GetModifiedSinceRead():
            self.logic.savePlanningDataToDirectory(node, outputDir)
      slicer.util.saveScene(os.path.join(outputDir, "Results.mrml"))
      self.logic.appendPlanningTimeStampToJson(self.jsonFile, "CaseSavedTime", datetime.datetime.now().time().isoformat())
    pass

  def onModifyVenousMargin(self):
    self.logic.venousMargin = float(self.venousMarginEdit.text)
    self.logic.distanceMapThreshold = float(self.distanceMapThresholdEdit.text)
    grayScaleModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel")
    grayScaleModelNode = slicer.mrmlScene.GetNodeByID(grayScaleModelNodeID)
    if grayScaleModelNode:
      grayScaleModelNode.SetAttribute("vtkMRMLModelNode.modelCreated","False")
    nodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin")
    node = slicer.mrmlScene.GetNodeByID(nodeID)
    if not node:
      node = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
      slicer.mrmlScene.AddNode(node)
    if node:
      node.SetAttribute("vtkMRMLModelNode.modelCreated","False")
    pass

  def onModifySurfaceModel(self):
    self.logic.sufaceModelThreshold = float(self.surfaceModelThresholdEdit.text)
    outputModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
    if outputModelNodeID:
      outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
      if outputModelNode:
        outputModelNode.SetAttribute("vtkMRMLModelNode.modelCreated","False")
    pass

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
      grayScaleModelNode = slicer.mrmlScene.GetNodeByID(grayScaleModelNodeID)
      if grayScaleModelNode and (grayScaleModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False"):
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
        slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
        try:
          self.logic.calculateVenousGrayScale(croppedVolumeNode, grayScaleModelNode)
        except ValueError:
          slicer.util.warningDisplay(
            "Venouse Calculation error, volumes might not be suitable for calculation")
        finally:
          slicer.app.processEvents()
          self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                       self.onVolumeAddedNode)
          self.onCalculateVenousCompletion(self.logic.cliNode)
          self.onSaveData()
        #self.logic.cliNode.AddObserver('ModifiedEvent', self.onCalculateVenousCompletion)
        #self.logic.cliNode.InvokeEvent(self.logic.cliNode.ModifiedEvent)
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
        slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
        try:
          self.logic.calculateVenousVesselness(croppedVolumeNode, vesselnessVolumeNode)
        except ValueError:
          slicer.util.warningDisplay(
            "Vessel Margin Calculation error, volumes might not be suitable for calculation")
        finally:
          slicer.app.processEvents()
          self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                     self.onVolumeAddedNode)
          self.onCalculateVenousCompletion(self.logic.cliNode)
          self.onSaveData()
        #self.logic.cliNode.AddObserver('ModifiedEvent', self.onCalculateVenousCompletion)
        #self.logic.cliNode.InvokeEvent(self.logic.cliNode.ModifiedEvent)
    pass

  #@beforeRunProcessEvents
  def onCalculateVenousCompletion(self,node,event=None):
    status = node.GetStatusString()
    self.venousCalcStatus.setText(node.GetName() +' '+status)
    if status == 'Completed':
      self.progressBar.value = 50
      self.progressBar.labelText = 'Calculating Vessel margin'
      slicer.app.processEvents()
      self.vesselnessCalcButton.setEnabled(1)
      self.grayScaleMakerButton.setEnabled(1)
      slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
      try:
        self.logic.calculateGrayScaleWithMargin()
      except ValueError:
        slicer.util.warningDisplay(
          "Vessel Margin Calculation error, volumes might not be suitable for calculation")
      finally:
        slicer.app.processEvents()
        self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                   self.onVolumeAddedNode)
        self.onSetSliceViewer()## the slice widgets are set to none after the  cli module calculation. reason unclear...
        self.progressBar.value = 100
        self.progressBar.close()
        self.onSaveData()
    pass

  def onResetButtons(self, caller = None, event = None):
    self.addCannulaTargetButton.setChecked(False)
    self.selectNasionButton.setChecked(False)
    self.selectSagittalButton.setChecked(False)
    pass

  def onSet3DViewer(self):
    layoutManager = slicer.app.layoutManager()
    threeDWidget = layoutManager.threeDWidget(0)
    threeDView = threeDWidget.threeDView()
    threeDView.lookFromViewAxis(ctkAxesWidget.Anterior)
    threeDView.resetFocalPoint()


  def onSetSliceViewer(self):
    if self.logic.currentVolumeNode:
      self.red_cn.SetBackgroundVolumeID(self.logic.currentVolumeNode.GetID())
      self.yellow_cn.SetBackgroundVolumeID(self.logic.currentVolumeNode.GetID())
      self.green_cn.SetBackgroundVolumeID(self.logic.currentVolumeNode.GetID())
      self.red_widget.fitSliceToBackground()
      self.yellow_widget.fitSliceToBackground()
      self.green_widget.fitSliceToBackground()

    if self.logic.ventricleVolume:
      self.red_cn.SetForegroundVolumeID(self.logic.ventricleVolume.GetID())
      self.yellow_cn.SetForegroundVolumeID(self.logic.ventricleVolume.GetID())
      self.green_cn.SetForegroundVolumeID(self.logic.ventricleVolume.GetID())
      
    pass

  # Event handlers for trajectory
  def onEditPlanningTarget(self):
    if self.addCannulaTargetButton.isChecked():
      self.imageSlider.setValue(100.0)
      self.initialFieldsValue()
      #self.logic.setSliceForCylinder()
      self.logic.startEditPlanningTarget()
    else:
      self.logic.placeWidget.setPlaceModeEnabled(False)

  # Event handlers for trajectory
  def onEditPlanningDistal(self):
    self.imageSlider.setValue(100.0)
    self.initialFieldsValue()
    self.logic.startEditPlanningDistal()

  def onGeneratePath(self):
    slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
    try:
      self.logic.generatePath()
    except ValueError:
      slicer.util.warningDisplay(
        "Vessel Margin Calculation error, volumes might not be suitable for calculation")
    finally:
      slicer.app.processEvents()
      self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                 self.onVolumeAddedNode)
      self.onSaveData()

    
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
    self.SerialAssignBox = SerialAssignMessageBox()
    self.logic = VentriculostomyPlanningLogic()
    self.logic.register(self)
    
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
  
  def clear(self):
    if self._curveModel:
      slicer.mrmlScene.RemoveNode(self._curveModel.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(self._curveModel)
    if self.curveFiducials:
      slicer.mrmlScene.RemoveNode(self.curveFiducials.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(self.curveFiducials)
    self.curveFiducials = None
    self._curveModel = None
  
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
  def update_observers(self, *args, **kwargs):
    for observer in self.observers:
      observer.updateFromLogic(*args, **kwargs)

  def __init__(self):
    self.observers = []
    self.unregister_all()
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
    
    self.cylinderManager = CurveManager()
    self.cylinderManager.setName("T")
    self.cylinderManager.setDefaultSlicePositionToLastPoint()
    self.cylinderManager.setModelColor(0.0, 1.0, 1.0)
    self.cylinderManager.setDefaultSlicePositionToFirstPoint()
    self.cylinderManager.setModelOpacity(0.5)
    self.cylinderManager.startEditLine()

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
    self.cylinderMiddlePointNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")

    self.pathCandidatesPoly = vtk.vtkPolyData()
    self.pathNavigationPoly = vtk.vtkPolyData()
    ##
    self.pathCandidatesModel = None
    self.pathNavigationModel = None
    self.cylinderInteractor = None
    self.trajectoryProjectedMarker = None
    self.enableAuxilaryNodes()

    self.distanceMapFilter = sitk.ApproximateSignedDistanceMapImageFilter()
    self.currentVolumeNode = None
    self.baseVolumeNode = None
    self.ventricleVolume = None
    self.useLeftHemisphere = False
    self.cliNode = None
    self.samplingFactor = 1
    self.topPoint = []
    self.sufaceModelThreshold = -500.0
    self.distanceMapThreshold = 100
    self.venousMargin = 10.0 #in mm
    self.minimalVentricleLen = 10.0 # in mm
    self.yawAngle = 0.0
    self.pitchAngle = 0.0
    self.kocherDistance = 0.0
    self.cannulaToNormAngle = 0.0
    self.cannulaToCoronalAngle = 0.0
    self.skullNormToCoronalAngle = 0.0
    self.skullNormToSagittalAngle = 0.0
    self.sagittalYawAngle = 0
    self.trueSagittalPlane = None
    self.activeTrajectoryMarkup = 0
    self.cylinderRadius = 2.5 # unit mm
    self.entryRadius = 25.0
    self.transform = vtk.vtkTransform()
    self.placeWidget = slicer.qSlicerMarkupsPlaceWidget()
    self.interactionMode = "none"

  def enableAuxilaryNodes(self):
    # Create display node
    self.pathCandidatesModel = None
    self.pathNavigationModel = None
    self.cylinderInteractor = None
    self.trajectoryProjectedMarker = None
    modelDisplay = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
    yellow = [1, 1, 0]
    red = [1, 0, 0]
    modelDisplay.SetColor(yellow[0], yellow[1], yellow[2])
    modelDisplay.SetScene(slicer.mrmlScene)
    modelDisplay.SetVisibility(0)
    modelDisplay.SetSliceIntersectionVisibility(True)  # Show in slice view
    slicer.mrmlScene.AddNode(modelDisplay)
    self.pathCandidatesModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
    slicer.mrmlScene.AddNode(self.pathCandidatesModel)
    self.pathCandidatesModel.SetAndObserveDisplayNodeID(modelDisplay.GetID())
    modelDisplay2 = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
    modelDisplay2.SetColor(yellow[0], yellow[1], yellow[2])
    modelDisplay2.SetScene(slicer.mrmlScene)
    modelDisplay2.SetVisibility(0)
    slicer.mrmlScene.AddNode(modelDisplay2)
    self.pathNavigationModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
    slicer.mrmlScene.AddNode(self.pathNavigationModel)
    self.pathNavigationModel.SetAndObserveDisplayNodeID(modelDisplay2.GetID())
    displayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsDisplayNode")
    displayNode.SetColor(red[0], red[1], red[2])
    displayNode.SetScene(slicer.mrmlScene)
    displayNode.SetVisibility(0)
    slicer.mrmlScene.AddNode(displayNode)
    self.cylinderInteractor = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    self.cylinderInteractor.SetName("")
    self.cylinderInteractor.AddObserver(slicer.vtkMRMLMarkupsNode().PointModifiedEvent, self.updateCylinderRadius)
    slicer.mrmlScene.AddNode(self.cylinderInteractor)
    self.cylinderInteractor.SetAndObserveDisplayNodeID(displayNode.GetID())
    markupDisplay = slicer.vtkMRMLMarkupsDisplayNode()
    markupDisplay.SetColor(red[0], red[1], red[2])
    markupDisplay.SetScene(slicer.mrmlScene)
    markupDisplay.SetVisibility(0)
    slicer.mrmlScene.AddNode(markupDisplay)
    self.trajectoryProjectedMarker = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    self.trajectoryProjectedMarker.SetName("trajectoryProject")
    slicer.mrmlScene.AddNode(self.trajectoryProjectedMarker)
    self.trajectoryProjectedMarker.SetAndObserveDisplayNodeID(markupDisplay.GetID())

  def clear(self):
    if self.trajectoryProjectedMarker and self.trajectoryProjectedMarker.GetID():
      slicer.mrmlScene.RemoveNode(self.trajectoryProjectedMarker.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(self.trajectoryProjectedMarker)
      self.trajectoryProjectedMarker = None
    if self.pathCandidatesModel and self.pathCandidatesModel.GetID():
      slicer.mrmlScene.RemoveNode(self.pathCandidatesModel.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(self.pathCandidatesModel)
      self.pathCandidatesModel = None
    if self.pathNavigationModel and self.pathNavigationModel.GetID():
      slicer.mrmlScene.RemoveNode(self.pathNavigationModel.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(self.pathNavigationModel)
      self.pathNavigationModel = None
    if self.trajectoryProjectedMarker and self.trajectoryProjectedMarker.GetID():
      slicer.mrmlScene.RemoveNode(self.trajectoryProjectedMarker.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(self.trajectoryProjectedMarker)
      self.trajectoryProjectedMarker = None
    if self.cylinderManager:
      self.cylinderManager.clear()
      self.cylinderManager = None
    if self.cannulaManager:
      self.cannulaManager.clear()
      self.cannulaManager = None
    if self.coronalPlanningCurveManager:
      self.coronalPlanningCurveManager.clear()
      self.coronalPlanningCurveManager = None
    if self.coronalReferenceCurveManager:
      self.coronalReferenceCurveManager.clear()
      self.coronalReferenceCurveManager = None
    if self.sagittalReferenceCurveManager:
      self.sagittalReferenceCurveManager.clear()
      self.sagittalReferenceCurveManager = None
    if self.sagittalPlanningCurveManager:
      self.sagittalPlanningCurveManager.clear()
      self.sagittalPlanningCurveManager = None

  def appendPlanningTimeStampToJson(self, JSONFile, parameterName, value):
    data = {}
    if not os.path.isfile(JSONFile):
      data[parameterName] = value
      with open(JSONFile, "w") as jsonFile:
        json.dump(data, jsonFile)
        jsonFile.close()
    else:
      with open(JSONFile, "r") as jsonFile:
        data = json.load(jsonFile)
        jsonFile.close()
      data[parameterName] = value  
      with open(JSONFile, "w") as jsonFile:
        json.dump(data, jsonFile)
        jsonFile.close()
  pass

  def savePlanningDataToDirectory(self, node, outputDir):
    nodeName = node.GetName()
    characters = [": ", " ", ":", "/"]
    for character in characters:
      nodeName = nodeName.replace(character, "-")
    if not node.GetStorageNode():
      node.AddDefaultStorageNode()
    storageNode = node.GetStorageNode()
    extension = storageNode.GetDefaultWriteFileExtension()
    baseNodeName = self.baseVolumeNode.GetName()
    for character in characters:
      baseNodeName = baseNodeName.replace(character, "-")
    filename = os.path.join(outputDir, nodeName +'.'+ extension)
    if slicer.util.saveNode(node, filename):
      return True
    #warningMSG = "Error in saving the %s" %(nodeName)
    #slicer.util.warningDisplay(warningMSG)

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

  def setSliceForCylinder(self):
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
        self.interactionMode = "target"
        self.placeWidget.setPlaceMultipleMarkups(self.placeWidget.ForcePlaceMultipleMarkups)
        self.placeWidget.setMRMLScene(slicer.mrmlScene)
        self.placeWidget.setCurrentNode(targetNode)
        self.placeWidget.setPlaceModeEnabled(True)

  def startEditPlanningDistal(self, caller = None, event = None):
    if self.baseVolumeNode:
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal"):
        distalNode = slicer.mrmlScene.GetNodeByID(
          self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal"))
        self.interactionMode = "distal"
        self.placeWidget.setMRMLScene(slicer.mrmlScene)
        self.placeWidget.setCurrentNode(distalNode)
        self.placeWidget.setPlaceModeEnabled(True)

  def endVentricleCylinderDefinition(self):
    if self.baseVolumeNode:
      distalID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
      distalNode = slicer.mrmlScene.GetNodeByID(distalID)
      if distalNode:
        posDistal = numpy.array([0.0, 0.0, 0.0])
        distalNode.GetNthFiducialPosition(distalNode.GetNumberOfMarkups() - 1, posDistal)
        if distalNode.GetNumberOfMarkups() > 1:
          distalNode.RemoveAllMarkups()
          distalNode.AddFiducial(posDistal[0], posDistal[1], posDistal[2])
      targetID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
      targetNode = slicer.mrmlScene.GetNodeByID(targetID)
      if targetNode:
        posTarget = numpy.array([0.0, 0.0, 0.0])
        targetNode.GetNthFiducialPosition(targetNode.GetNumberOfMarkups() - 1, posTarget)
        if targetNode.GetNumberOfMarkups() > 1:
          targetNode.RemoveAllMarkups()
          targetNode.AddFiducial(posTarget[0], posTarget[1], posTarget[2])
    self.placeWidget.setPlaceModeEnabled(False)
    pass
  
  def endEditTrajectory(self):
    self.cylinderManager.endEditLine()
  
  def calculateGrayScaleWithMargin(self):
    nodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin")
    node = slicer.mrmlScene.GetNodeByID(nodeID)
    if not node:
      node = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
      slicer.mrmlScene.AddNode(node)
    if node and (node.GetAttribute("vtkMRMLModelNode.modelCreated") == "False"):
      originImage = sitk.Cast(sitkUtils.PullFromSlicer(self.currentVolumeNode.GetID()), sitk.sitkInt16)
      try:
        distanceMap = self.distanceMapFilter.Execute(originImage, self.distanceMapThreshold - 10, self.distanceMapThreshold )
      except ValueError:
        slicer.util.warningDisplay(
          "distance map calucation failed, try use different settings")
        return None
      sitkUtils.PushToSlicer(distanceMap, "distanceMap", 0, True)
      imageCollection = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode", "distanceMap")
      if imageCollection:
        distanceMapNode = imageCollection.GetItemAsObject(0)
        parameters = {}
        parameters["InputVolume"] = distanceMapNode.GetID()
        parameters["OutputGeometry"] = node.GetID()
        parameters["Threshold"] = -self.venousMargin
        grayMaker = slicer.modules.grayscalemodelmaker
        self.cliNode = slicer.cli.run(grayMaker, None, parameters, wait_for_completion=True)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin", node.GetID())
        node.SetAttribute("vtkMRMLModelNode.modelCreated", "True")
      self.update_observers(VentriculostomyUserEvents.SetSliceViewerEvent)
    node.SetDisplayVisibility(0)  
    return node

  def calculateCannulaTransform(self):
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
        cannulaDirection = (numpy.array(posDistal) - numpy.array(posTarget)) / numpy.linalg.norm(
          numpy.array(posTarget) - numpy.array(posDistal))
        angle = math.acos(numpy.dot(numpy.array([0, 0, 1.0]), cannulaDirection))
        rotationAxis = numpy.cross(numpy.array([0, 0, 1.0]), cannulaDirection)
        self.transform.Identity()
        self.transform.RotateWXYZ(angle * 180.0 / numpy.pi, rotationAxis[0], rotationAxis[1], rotationAxis[2])
  
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
        inputModelNode = slicer.mrmlScene.GetNodeByID(modelID)
        polyData = inputModelNode.GetPolyData()
        FiducialPointAlongVentricle = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        self.calculateLineModelIntersect(polyData, posDistal+1e6*direction, posTarget-1e6*direction, FiducialPointAlongVentricle)
        posEntry = numpy.array([0.0, 0.0, 0.0])
        FiducialPointAlongVentricle.GetNthFiducialPosition(0,posEntry)
        self.cylinderMiddlePointNode.RemoveAllMarkups()
        self.cylinderMiddlePointNode.AddFiducial((posTarget[0]+posDistal[0])/2.0, (posTarget[1]+posDistal[1])/2.0, (posTarget[2]+posDistal[2])/2.0)
        grayScaleModelNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel")
        grayScaleModelNode = slicer.mrmlScene.GetNodeByID(grayScaleModelNodeID)
        skullModelNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
        skullModelNode = slicer.mrmlScene.GetNodeByID(skullModelNodeID)
        angleForModelCut = float(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_planningRadius"))
        pathPlanningBasePoint = numpy.array(posTarget) + (numpy.array(posEntry) - numpy.array(posTarget)) * 1.2
        self.calculateCannulaTransform()
        matrix = vtk.vtkMatrix4x4()
        matrix = self.transform.GetMatrix()
        synthesizedData = vtk.vtkPolyData()
        points = vtk.vtkPoints()
        phiResolution = 5*numpy.pi/180.0
        radiusResolution = 1.0
        points.InsertNextPoint(posEntry)
        distance2 = numpy.linalg.norm(numpy.array(posTarget) - numpy.array(posEntry))
        distance1 = numpy.linalg.norm(numpy.array(posTarget) - numpy.array(posDistal))/2 # Divided by 2 is because, all the cylinder bottom are possible target points
        self.entryRadius = self.cylinderRadius * distance2 / distance1
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
            self.cylinderMiddlePointNode, None, 0, grayScaleModelWithMarginNode, tempModel)
          # display all paths model
          red =[1, 0, 0]
          self.makePath(self.pathReceived, self.nPathReceived,   1, "candidatePaths", self.pathCandidatesPoly, self.pathCandidatesModel)
          obbTree = vtk.vtkOBBTree()
          obbTree.SetDataSet(grayScaleModelWithMarginNode.GetPolyData())
          obbTree.BuildLocator()
          pointsVTKintersection = vtk.vtkPoints()
          #self.cannulaManager.clearLine()
          #self.cannulaManager.curveFiducials.RemoveAllMarkups()
          #self.cannulaManager.startEditLine() # initialize the tube model
          if self.nPathReceived>0:
            self.relocateCannula(self.pathReceived, 1)
          else:
            slicer.util.warningDisplay(
              "No any cannula candidate exists here, considering redefine the ventricle area?")
            distalNode.SetLocked(False)
            targetNode.SetLocked(False)

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
      #self.cannulaManager.curveFiducials.RemoveAllMarkups()
      posTarget = numpy.array([0.0] * 3)
      self.cylinderManager.getFirstPoint(posTarget)
      posDistal = numpy.array([0.0] * 3)
      self.cylinderManager.getLastPoint(posDistal)
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
          #self.cylinderManager.curveFiducials.SetNthFiducialPositionFromArray(1,optimizedEntry)
          self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(0, posTarget)
          self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(1, posDistalModified)
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
              self.cannulaManager.curveFiducials.RemoveAllMarkups()
              self.cannulaManager.curveFiducials.AddFiducial(0, 0, 0)
              self.cannulaManager.curveFiducials.AddFiducial(0, 0, 0)
              self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(0, pathReceived[minIndex-1])
              self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(1, pathReceived[minIndex])
              direction2 = numpy.array(pathReceived[minIndex]) - numpy.array(pathReceived[minIndex-1])
              direction2Norm = direction2/numpy.linalg.norm(direction2)
              angleCalc = math.acos(numpy.dot(direction1Norm, direction2Norm))
      self.activeTrajectoryMarkup = 1
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
    self.cylinderManager.clearLine()

  def setTrajectoryModifiedEventHandler(self, handler):
    self.cylinderManager.setModifiedEventHandler(handler)

  def getCannulaLength(self):
    return self.cannulaManager.getLength()

  def lockTrajectoryLine(self):
    self.cylinderManager.lockLine()
    self.cylinderManager.lockLine()

  def unlockTrajectoryLine(self):
    self.cylinderManager.unlockLine()
    self.cylinderManager.unlockLine()

  def moveSliceTrajectory(self):
    self.cylinderManager.moveSliceToLine()


  def startEditCoronalPlanningLine(self):

    pos = [0.0] * 3
    self.cylinderManager.getFirstPoint(pos)
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
      self.cliNode = slicer.cli.run(grayMaker, None, parameters, wait_for_completion=True)
  
  
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

  def enableEventObserver(self):
    nasionNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion")
    nasionNode = slicer.mrmlScene.GetNodeByID(nasionNodeID)
    sagittalID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPoint")
    sagittalPointNode = slicer.mrmlScene.GetNodeByID(sagittalID)
    targetNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
    targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
    distalNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
    distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
    if nasionNode:
      nasionNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self.endPlacement)
    if sagittalPointNode:
      sagittalPointNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self.endPlacement)
    if targetNode:
      targetNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self.endPlacement)
      targetNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointModifiedEvent, self.createVentricleCylinder)
      targetNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointEndInteractionEvent, self.endModifiyCylinder)
      targetNode.AddObserver(VentriculostomyUserEvents.TriggerDistalSelectionEvent, self.startEditPlanningDistal)
    if distalNode:
      distalNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self.endPlacement)
      distalNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointModifiedEvent, self.createVentricleCylinder)
      distalNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointEndInteractionEvent, self.endModifiyCylinder)

        
  def enableAttribute(self, attribute, caseName = None):
    enabledAttributeID = self.baseVolumeNode.GetAttribute(attribute)
    invisableAttribute = ['vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin']
    if enabledAttributeID and slicer.mrmlScene.GetNodeByID(enabledAttributeID):
      attributeNode = slicer.mrmlScene.GetNodeByID(enabledAttributeID)
      if attributeNode and attributeNode.GetDisplayNode() and (not (attribute in invisableAttribute)):
        attributeNode.GetDisplayNode().SetVisibility(1)
      if attribute == 'vtkMRMLScalarVolumeNode.rel_cylinderRadius':
        self.cylinderRadius = float(self.baseVolumeNode.GetAttribute(attribute))
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
      elif attribute == "vtkMRMLScalarVolumeNode.rel_cylinderRadius":
        self.baseVolumeNode.SetAttribute(attribute, str(self.cylinderRadius))
      elif attribute == "vtkMRMLScalarVolumeNode.rel_skullNorm":
        skullNormNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        skullNormNode.SetName(caseName+"skullNorm")
        slicer.mrmlScene.AddNode(skullNormNode)
        self.baseVolumeNode.SetAttribute(attribute, skullNormNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_cannula":
        cannulaNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        cannulaNode.SetName(caseName+"cannulaFiducial")
        displayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsDisplayNode")
        slicer.mrmlScene.AddNode(displayNode)
        cannulaNode.SetAndObserveDisplayNodeID(displayNode.GetID())
        slicer.mrmlScene.AddNode(cannulaNode)
        self.baseVolumeNode.SetAttribute(attribute, cannulaNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_model":  
        modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        modelNode.SetAttribute("vtkMRMLModelNode.modelCreated", "False")
        modelNode.SetName(caseName+"surfaceModel")
        slicer.mrmlScene.AddNode(modelNode)
        modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
        ModelColor = [0.0, 0.0, 1.0]
        modelDisplayNode.SetColor(ModelColor)
        modelDisplayNode.SetOpacity(0.5)
        slicer.mrmlScene.AddNode(modelDisplayNode)
        modelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_model", modelNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_grayScaleModel":
        modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        modelNode.SetAttribute("vtkMRMLModelNode.modelCreated", "False")
        modelNode.SetName(caseName + "vesselModel")
        slicer.mrmlScene.AddNode(modelNode)
        modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
        ModelColor = [1.0, 0.0, 0.0]
        modelDisplayNode.SetColor(ModelColor)
        modelDisplayNode.SetOpacity(0.5)
        slicer.mrmlScene.AddNode(modelDisplayNode)
        modelNode.SetDisplayVisibility(1)
        modelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel", modelNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin":
        modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        modelNode.SetAttribute("vtkMRMLModelNode.modelCreated", "False")
        modelNode.SetName(caseName + "vesselModelWithMargin")
        slicer.mrmlScene.AddNode(modelNode)
        modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
        ModelColor = [1.0, 0.0, 0.0]
        modelDisplayNode.SetColor(ModelColor)
        modelDisplayNode.SetOpacity(0.5)
        slicer.mrmlScene.AddNode(modelDisplayNode)
        modelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
        modelNode.SetDisplayVisibility(0)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin", modelNode.GetID())
      elif attribute == "vtkMRMLScalarVolumeNode.rel_cannulaModel":
        modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        modelNode.SetName(caseName + "cannulaModel")
        slicer.mrmlScene.AddNode(modelNode)
        modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
        ModelColor = [1.0, 0.0, 0.0]
        modelDisplayNode.SetColor(ModelColor)
        modelDisplayNode.SetOpacity(0.5)
        slicer.mrmlScene.AddNode(modelDisplayNode)
        modelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
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
    if inputModelNodeID and self.activeTrajectoryMarkup == 1:
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
            self.updateCannulaTargetPoint(fiducicalMarkerNode)
            #fiducicalMarkerNode.InvokeEvent(VentriculostomyUserEvents.UpdateCannulaTargetPoint)
          else:
            self.trajectoryProjectedMarker.SetNthFiducialLabel(0,"invalid")
        else:
          self.trajectoryProjectedMarker.SetNthFiducialPositionFromArray(0,posSecond)
          self.trajectoryProjectedMarker.SetNthFiducialLabel(0,"")
          #self.trajectoryProjectedMarker.SetNthFiducialVisibility(0,False)
      self.activeTrajectoryMarkup = 1
    self.cannulaManager.onLineSourceUpdated()
    self.updateSlicePosition(fiducicalMarkerNode,self.activeTrajectoryMarkup)

  def updateCannulaTargetPoint(self, fiducialNode, eventID = None):
    posTarget = numpy.array([0.0] * 3)
    self.cylinderManager.getFirstPoint(posTarget)
    posDistal = numpy.array([0.0] * 3)
    self.cylinderManager.getLastPoint(posDistal)
    posProjected = [0.0,0.0,0.0]
    self.trajectoryProjectedMarker.GetNthFiducialPosition(0, posProjected)
    posMiddle = (posTarget + posDistal) / 2
    direction1Norm = (posDistal - posTarget) / numpy.linalg.norm(posTarget - posDistal)
    direction2 = numpy.array(posProjected) - numpy.array(posMiddle)
    direction2Norm = direction2 / numpy.linalg.norm(direction2)
    angleCalc = math.acos(numpy.dot(direction1Norm, direction2Norm))
    posCannulaTarget = [0.0,0.0,0.0]
    fiducialNode.GetNthFiducialPosition(0, posCannulaTarget)
    posCannulaTarget = numpy.array(posCannulaTarget)
    projectedLength = -numpy.dot(posMiddle - posCannulaTarget, posMiddle - posDistal)/numpy.linalg.norm(posMiddle - posDistal)
    #if numpy.dot(posMiddle - posCannulaTarget, posMiddle - posDistal)>0:
    #  shortenFactor = -1*projectedLength
    posBottom = posMiddle + projectedLength / math.cos(angleCalc) * (
    posMiddle - posProjected) / numpy.linalg.norm(posMiddle - posProjected)
    self.activeTrajectoryMarkup = 0
    self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(0, posBottom)
    pass
    
  def endCannulaInteraction(self, fiducialNode, event=None):
    posEntry = [0.0, 0.0, 0.0]
    if (not self.trajectoryProjectedMarker.GetNthFiducialLabel(0) == "invalid") and self.trajectoryProjectedMarker.GetNumberOfFiducials():
      self.trajectoryProjectedMarker.GetNthFiducialPosition(0, posEntry)
      posEntry[1] = posEntry[1] + 0.005
      fiducialNode.SetNthFiducialPositionFromArray(1, posEntry)
    self.trajectoryProjectedMarker.SetNthFiducialVisibility(0, False)
    self.trajectoryProjectedMarker.SetLocked(True)
    # update the intersection of trajectory with venous
    posTarget = [0.0,0.0,0.0]
    fiducialNode.GetNthFiducialPosition(0,posTarget)
    posEntry = [0.0,0.0,0.0]
    fiducialNode.GetNthFiducialPosition(1,posEntry)
    inputVesselMarginModelNodeID =  self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModelWithMargin")
    if inputVesselMarginModelNodeID:
      inputModelNode = slicer.mrmlScene.GetNodeByID(inputVesselMarginModelNodeID)
      polyData = inputModelNode.GetPolyData()
      for index in range(1, self.trajectoryProjectedMarker.GetNumberOfFiducials()):
        self.trajectoryProjectedMarker.RemoveMarkup(index)
      self.calculateLineModelIntersect(polyData, posEntry, posTarget, self.trajectoryProjectedMarker)
      if self.trajectoryProjectedMarker.GetNumberOfFiducials()>1: # The intersection is not only the projected skull point
        slicer.util.warningDisplay("Within the margin area of the vessel")
    distalNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
    distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
    posDistal = numpy.array([0.0, 0.0, 0.0])
    distalNode.GetNthFiducialPosition(0, posDistal)
    cylinderTop = vtk.vtkCylinderSource()
    cylinderTop.SetCenter(numpy.array([0.0, 0.0, 0.0]))
    cylinderTop.SetRadius(self.cylinderRadius)
    cylinderTop.SetHeight(0.05)
    cylinderTop.SetResolution(200)
    cylinderTop.Update()
    self.calculateCannulaTransform()
    transformWithTranslate = vtk.vtkTransform()
    matrixWithTranslate = vtk.vtkMatrix4x4()
    matrixWithTranslate.DeepCopy(self.transform.GetMatrix())
    #transformWithTranslate.DeepCopy(self.transform)
    transformWithTranslate.SetMatrix(matrixWithTranslate)
    transformWithTranslate.RotateX(-90.0)
    transformWithTranslate.PostMultiply()
    transformWithTranslate.Translate(posDistal)
    transformFilter = vtk.vtkTransformPolyDataFilter()
    transformFilter.SetInputConnection(cylinderTop.GetOutputPort())
    transformFilter.SetTransform(transformWithTranslate)
    transformFilter.ReleaseDataFlagOn()
    transformFilter.Update()
    """
    modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
    modelNode.SetName("ForTesting")
    slicer.mrmlScene.AddNode(modelNode)
    modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
    ModelColor = [0.0, 1.0, 1.0]
    modelDisplayNode.SetColor(ModelColor)
    modelDisplayNode.SetOpacity(0.5)
    slicer.mrmlScene.AddNode(modelDisplayNode)
    modelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
    modelNode.SetAndObservePolyData(transformFilter.GetOutput())
    """
    ventriculCylinder = self.cylinderManager._curveModel.GetPolyData()
    posTargetBoundary = list(posTarget+(numpy.array(posEntry)-numpy.array(posTarget))/2000.0)
    intersectNumber2 = self.calculateLineModelIntersect(ventriculCylinder, posEntry,posTargetBoundary, self.trajectoryProjectedMarker)
    intersectNumber1 = self.calculateLineModelIntersect(transformFilter.GetOutput(), posEntry, posTargetBoundary, self.trajectoryProjectedMarker)
    if (intersectNumber2 == 2 or intersectNumber2 == 0) and intersectNumber1 == 0:
      slicer.util.warningDisplay("Both entry and target points are out of the ventricle cylinder")   
    elif intersectNumber2 == 2 and intersectNumber1 == 2:
      slicer.util.warningDisplay("target point is out of the ventricle cylinder") 
    elif intersectNumber2 == 1 and intersectNumber1 == 0:
      slicer.util.warningDisplay("Entry point is out of the ventricle cylinder")
    pass

  def calculateLineModelIntersect(self, polyData, posFirst, posSecond, intersectionNode=None):
    if polyData:
      obbTree = vtk.vtkOBBTree()
      obbTree.SetDataSet(polyData)
      obbTree.BuildLocator()
      pointsVTKintersection = vtk.vtkPoints()
      hasIntersection = obbTree.IntersectWithLine(posFirst, posSecond, pointsVTKintersection, None)
      if hasIntersection>0:
        pointsVTKIntersectionData = pointsVTKintersection.GetData()
        numPointsVTKIntersection = pointsVTKIntersectionData.GetNumberOfTuples()
        if intersectionNode:
          validPosIndex = intersectionNode.GetNumberOfFiducials()
          for idx in range(numPointsVTKIntersection):
            posTuple = pointsVTKIntersectionData.GetTuple3(idx)
            if ((posTuple[0]-posFirst[0])*(posSecond[0]-posFirst[0])>0) and abs(posTuple[0]-posFirst[0])<abs(posSecond[0]-posFirst[0]):
              # check if the intersection if within the posFist and posSecond
              intersectionNode.AddFiducial(0,0,0)
              intersectionNode.SetNthFiducialPositionFromArray(validPosIndex,posTuple)
              intersectionNode.SetNthFiducialLabel(validPosIndex,"")
              intersectionNode.SetNthFiducialVisibility(validPosIndex,True)
              validPosIndex = validPosIndex + 1
        return numPointsVTKIntersection    
      else:
        if intersectionNode:
          numOfFiducial = intersectionNode.GetNumberOfFiducials()
          for idx in range(1, numOfFiducial):
            intersectionNode.SetNthFiducialLabel(idx,"invalid")  
    return 0
       
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
    if self.interactionMode == "nasion":
      self.createTrueSagittalPlane()
      self.createEntryPoint()
      self.update_observers(VentriculostomyUserEvents.ResetButtonEvent)
    elif self.interactionMode == "sagittalPoint":
      self.createTrueSagittalPlane()
      self.createEntryPoint()
      self.update_observers(VentriculostomyUserEvents.ResetButtonEvent)
    elif self.interactionMode == "target":
      #self.startEditPlanningDistal()
      if self.trajectoryProjectedMarker and self.trajectoryProjectedMarker.GetMarkupsDisplayNode():
        self.trajectoryProjectedMarker.GetMarkupsDisplayNode().SetVisibility(0)
      targetNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
      targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
      self.endVentricleCylinderDefinition()
      self.createVentricleCylinder()
      self.endModifiyCylinder()
      targetNode.InvokeEvent(VentriculostomyUserEvents.TriggerDistalSelectionEvent)
    elif self.interactionMode == "distal":
      if self.trajectoryProjectedMarker and self.trajectoryProjectedMarker.GetMarkupsDisplayNode():
        self.trajectoryProjectedMarker.GetMarkupsDisplayNode().SetVisibility(1)
      self.createVentricleCylinder()
      self.endVentricleCylinderDefinition()
      self.endModifiyCylinder()
      self.update_observers(VentriculostomyUserEvents.ResetButtonEvent)
    elif self.interactionMode == "vesselSeeds":
      pass
    self.update_observers(VentriculostomyUserEvents.SaveModifiedFiducialEvent)
    pass
   
  def selectNasionPointNode(self, modelNode, initPoint = None):
    if self.baseVolumeNode:
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"):
        nasionNode = slicer.mrmlScene.GetNodeByID(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"))
        dnode = nasionNode.GetMarkupsDisplayNode()
        if dnode :
          dnode.SetVisibility(1)
        nasionNode.SetLocked(True)
        self.interactionMode = "nasion"
        self.placeWidget.setPlaceMultipleMarkups(self.placeWidget.ForcePlaceSingleMarkup)
        self.placeWidget.setMRMLScene(slicer.mrmlScene)
        self.placeWidget.setCurrentNode(nasionNode)
        self.placeWidget.setPlaceModeEnabled(True)

  def selectSagittalPointNode(self, modelNode):
    if self.baseVolumeNode:
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPoint"):
        sagittalPointNode = slicer.mrmlScene.GetNodeByID(
          self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPoint"))
        dnode = sagittalPointNode.GetMarkupsDisplayNode()
        if dnode :
          dnode.SetVisibility(1)
        sagittalPointNode.SetLocked(True)
        self.interactionMode = "sagittalPoint"
        self.placeWidget.setPlaceMultipleMarkups(self.placeWidget.ForcePlaceSingleMarkup)
        self.placeWidget.setMRMLScene(slicer.mrmlScene)
        self.placeWidget.setCurrentNode(sagittalPointNode)
        self.placeWidget.setPlaceModeEnabled(True)
        
  def endModifiyCylinder(self,  caller = None, eventID = None):
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
        verticalDirect = self.cylinderRadius*verticalDirect/numpy.linalg.norm(verticalDirect)
        cylinderInteractorPosInRAS = numpy.array(posTargetInRAS)/2.0 + verticalDirect
        cylinderInteractorPosInRAS[3] = 1.0
        cylinderInteractorPos = matrixRed.MultiplyPoint(cylinderInteractorPosInRAS)
        self.cylinderInteractor.RemoveAllMarkups()
        self.cylinderInteractor.AddFiducial(cylinderInteractorPos[0],cylinderInteractorPos[1],cylinderInteractorPos[2])
        self.cylinderInteractor.SetNthFiducialLabel(0,"")
        self.cylinderInteractor.SetDisplayVisibility(1)
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
  
  def createVentricleCylinder(self, caller = None, eventID = None):
    targetNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
    distalNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
    radius= self.cylinderRadius
    if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cylinderRadius"):
      radius = float(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cylinderRadius"))
    self.cylinderInteractor.SetDisplayVisibility(0)
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
          if self.cylinderManager.curveFiducials:
            slicer.mrmlScene.RemoveNode(self.cylinderManager.curveFiducials)
            self.cylinderManager.curveFiducials = None
          tempFiducialNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
          tempFiducialNode.RemoveAllMarkups()
          tempFiducialNode.AddFiducial(posTarget[0], posTarget[1], posTarget[2])
          tempFiducialNode.AddFiducial(posDistal[0], posDistal[1], posDistal[2])
          slicer.mrmlScene.AddNode(tempFiducialNode)
          tempFiducialNode.SetDisplayVisibility(0)
          self.cylinderManager.setManagerTubeRadius(radius)
          #self.cylinderManager.cmLogic.setTubeRadius(radius)
          self.cylinderManager.curveFiducials = tempFiducialNode
          self.cylinderManager.startEditLine()
          self.cylinderManager.onLineSourceUpdated()
          self.updateSliceViewBasedOnPoints(posTarget,posDistal)
        else:
          self.cylinderManager.clearLine()
    else:
      self.cylinderManager.clearLine()

  def updateCylinderRadius(self, fiducicalMarkerNode = None, eventID = None):
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
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_cylinderRadius", str(radius))
        self.cylinderRadius = radius
        self.cylinderManager.setManagerTubeRadius(radius)
        self.cylinderManager.startEditLine()
        self.cylinderManager.onLineSourceUpdated()
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
      if nasionNode and sagittalPointNode:
        # create a sagital plane when nasion point is exist, if sagittal doesn't exist, use  [0,0,0] As default sagittal point, which might not be correct
        if nasionNode.GetNumberOfFiducials():
          nasionNode.GetNthFiducialPosition(0, posNasion)
          posSagittal = numpy.array([0.0, 0.0, 0.0])
          sagittalPointNode.GetNthFiducialPosition(sagittalPointNode.GetNumberOfMarkups() - 1, posSagittal)
          if sagittalPointNode.GetNumberOfMarkups() > 1:
            sagittalPointNode.RemoveAllMarkups()
            sagittalPointNode.AddFiducial(posSagittal[0], posSagittal[1], posSagittal[2])
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
      if polyData and self.trueSagittalPlane and nasionNode.GetNumberOfMarkups()> 0:
        posNasion = numpy.array([0.0,0.0,0.0])
        nasionNode.GetNthFiducialPosition(nasionNode.GetNumberOfMarkups()-1,posNasion)
        if nasionNode.GetNumberOfMarkups()>1:
          nasionNode.RemoveAllMarkups()
          nasionNode.AddFiducial(posNasion[0],posNasion[1],posNasion[2])
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

  def calculateDistanceToKocher(self):
    numOfRef = self.coronalReferenceCurveManager.curveFiducials.GetNumberOfFiducials()
    numOfCannulaPoints = self.cannulaManager.curveFiducials.GetNumberOfFiducials()
    if numOfRef >= 1 and numOfCannulaPoints>=2:
      posRef = [0.0, 0.0, 0.0]
      posEntry = [0.0, 0.0, 0.0]
      self.coronalReferenceCurveManager.getLastPoint(posRef)
      self.cannulaManager.getLastPoint(posEntry)
      self.kocherDistance = numpy.linalg.norm(numpy.array(posRef)-numpy.array(posEntry))
    pass

  def createPlanningLine(self):
    ###All calculation is based on the RAS coordinates system
    inputModelNode = None
    nasionNode = None
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
