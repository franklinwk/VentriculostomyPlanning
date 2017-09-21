import os, inspect
import json
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import logging
import tempfile
from ctk import ctkAxesWidget
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
from VentriculostomyPlanningUtils.UserEvents import VentriculostomyUserEvents
from VentriculostomyPlanningUtils.UsefulFunctions import UsefulFunctions
from VentriculostomyPlanningUtils.VentriclostomyButtons import GreenSliceLayoutButton, ConventionalSliceLayoutButton, ReverseViewOnCannulaButton, ScreenShotButton
from SlicerDevelopmentToolboxUtils.buttons import WindowLevelEffectsButton
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin
from shutil import copyfile
from os.path import basename
from os import listdir
import ScreenCapture

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
    This is an scripted module for ventriclostomy planning
    """
    self.parent.acknowledgementText = """
    This module was developed based on an example code provided by Jean-Christophe Fillion-Robin, Kitware Inc.
    and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# VentriculostomyPlanningWidget
#

class VentriculostomyPlanningWidget(ScriptedLoadableModuleWidget, ModuleWidgetMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  buttonWidth = 45
  buttonHeight = 45

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    ModuleWidgetMixin.__init__(self)
    self.logic = VentriculostomyPlanningLogic()
    self.logic.register(self)
    self.dicomWidget = DICOMWidget()
    self.dicomWidget.parent.close()
    self.SerialAssignBox = SerialAssignMessageBox()
    self.volumeSelected = False
    self.volumePrepared = False
    self.baseVolumeWindowValue = 974
    self.baseVolumeLevelValue = 270
    self.jsonFile = ""
    self.isLoadingCase = False
    self.isInAlgorithmSteps = False
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
    self.layout.addWidget(settingCollapsibleButton)
    settingCollapsibleButton.setVisible(True)
    # Layout within the dummy collapsible button
    appSettingLayout = qt.QFormLayout(settingCollapsibleButton)

    #
    # Mid-sagittalReference line
    #
    """"""
    referenceConfigLayout = qt.QHBoxLayout()
    appSettingLayout.addRow(referenceConfigLayout)

    lengthSagittalReferenceLineLabel = self.createLabel('Sagittal Length:  ')
    #-- Curve length
    referenceConfigLayout.addWidget(lengthSagittalReferenceLineLabel)
    self.lengthSagittalReferenceLineEdit = self.createLineEdit(title= "", text = '100.0', readOnly = False, frame = True,
                                                               styleSheet = "QLineEdit { background:transparent; }", cursor = qt.QCursor(qt.Qt.IBeamCursor))
    self.lengthSagittalReferenceLineEdit.connect('textEdited(QString)', self.onModifyMeasureLength)
    referenceConfigLayout.addWidget(self.lengthSagittalReferenceLineEdit)
    lengthSagittalReferenceLineUnitLabel = self.createLabel('mm  ')
    referenceConfigLayout.addWidget(lengthSagittalReferenceLineUnitLabel)

    lengthCoronalReferenceLineLabel = self.createLabel('Coronal Length:  ')
    referenceConfigLayout.addWidget(lengthCoronalReferenceLineLabel)
    self.lengthCoronalReferenceLineEdit = self.createLineEdit(title= "", text = '30.0', readOnly = False, frame = True,
                                                              styleSheet="QLineEdit { background:transparent; }", cursor = qt.QCursor(qt.Qt.IBeamCursor))
    self.lengthCoronalReferenceLineEdit.connect('textEdited(QString)', self.onModifyMeasureLength)
    referenceConfigLayout.addWidget(self.lengthCoronalReferenceLineEdit)
    lengthCoronalReferenceLineUnitLabel = self.createLabel('mm  ')
    referenceConfigLayout.addWidget(lengthCoronalReferenceLineUnitLabel)

    self.reloadButton = self.createButton(title="Reload", toolTip = "Reload this module.", name = "VentriculostomyPlanning Reload")
    self.reloadButton.connect('clicked()', self.onReload)
    referenceConfigLayout.addWidget(self.reloadButton)

    # -- Algorithm setting
    # Surface Model calculation
    surfaceModelConfigLayout = qt.QHBoxLayout()
    appSettingLayout.addRow(surfaceModelConfigLayout)
    surfaceModelThresholdLabel = self.createLabel('Surface Model Intensity Threshold Setting:  ')
    surfaceModelConfigLayout.addWidget(surfaceModelThresholdLabel)
    self.surfaceModelThresholdEdit = self.createLineEdit(title= "", text = '-500', readOnly = False, frame = True, toolTip = "set this value to the intensity of the skull, higher value means less segmented skull",
                                                         maxLength = 6, styleSheet = "QLineEdit { background:transparent; }", cursor = qt.QCursor(qt.Qt.IBeamCursor))
    self.surfaceModelThresholdEdit.connect('textEdited(QString)', self.onModifySurfaceModel)
    surfaceModelConfigLayout.addWidget(self.surfaceModelThresholdEdit)

    self.createModelButton = self.createButton(title="Create Surface", toolTip="Create a surface model.", enabled=True)
    self.createModelButton.connect('clicked(bool)', self.onCreateModel)
    surfaceModelConfigLayout.addWidget(self.createModelButton)

    # Venous model calculation and margin setting
    venousMarginConfigLayout = qt.QHBoxLayout()
    appSettingLayout.addRow(venousMarginConfigLayout)
    venousMarginLabel = self.createLabel('Venous Safety Margin: ')
    venousMarginConfigLayout.addWidget(venousMarginLabel)
    self.venousMarginEdit = self.createLineEdit(title="", text='10.0', readOnly=False, frame=True, maxLength = 6,
                                                styleSheet="QLineEdit { background:transparent; }",
                                                         cursor=qt.QCursor(qt.Qt.IBeamCursor))
    self.venousMarginEdit.connect('textEdited(QString)', self.onModifyVenousMargin)
    venousMarginConfigLayout.addWidget(self.venousMarginEdit)
    venousMarginUnitLabel = qt.QLabel('mm  ')
    venousMarginConfigLayout.addWidget(venousMarginUnitLabel)

    # Posterior margin distance setting
    posteriorMarginConfigLayout = qt.QHBoxLayout()
    appSettingLayout.addRow(posteriorMarginConfigLayout)
    posteriorMarginLabel = self.createLabel('Posterior Safety Margin: ')
    posteriorMarginConfigLayout.addWidget(posteriorMarginLabel)
    self.posteriorMarginEdit = self.createLineEdit(title="", text='60.0', readOnly=False, frame=True, maxLength=6,
                                                styleSheet="QLineEdit { background:transparent; }",
                                                cursor=qt.QCursor(qt.Qt.IBeamCursor))
    self.posteriorMarginEdit.connect('textEdited(QString)', self.onChangePosteriorMargin)
    posteriorMarginConfigLayout.addWidget(self.posteriorMarginEdit)
    posteriorMarginUnitLabel = qt.QLabel('mm  ')
    posteriorMarginConfigLayout.addWidget(posteriorMarginUnitLabel)

    kocherMarginConfigLayout = qt.QHBoxLayout()
    appSettingLayout.addRow(kocherMarginConfigLayout)
    kocherMarginLabel = self.createLabel('Kocher Distance Limit: ')
    kocherMarginConfigLayout.addWidget(kocherMarginLabel)
    self.kocherMarginEdit = self.createLineEdit(title="", text='20.0', readOnly=False, frame=True, maxLength=6,
                                                   styleSheet="QLineEdit { background:transparent; }",
                                                   cursor=qt.QCursor(qt.Qt.IBeamCursor))
    self.kocherMarginEdit.connect('textEdited(QString)', self.onChangeKocherMargin)
    kocherMarginConfigLayout.addWidget(self.kocherMarginEdit)
    kocherMarginUnitLabel = qt.QLabel('mm  ')
    kocherMarginConfigLayout.addWidget(kocherMarginUnitLabel)
    self.grayScaleMakerButton = self.createButton(title="Segment GrayScale", enabled = True, toolTip = "Use the GrayScaleMaker module for vessel calculation ")
    self.grayScaleMakerButton.connect('clicked(bool)', self.onVenousGrayScaleCalc)
    venousMarginConfigLayout.addWidget(self.grayScaleMakerButton)


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

    self.mainGUIGroupBox = qt.QGroupBox()
    self.mainGUIGroupBoxLayout = qt.QGridLayout()
    self.mainGUIGroupBox.setLayout(self.mainGUIGroupBoxLayout)
    self.layout.addWidget(self.mainGUIGroupBox)

    self.inputVolumeBox = qt.QGroupBox()
    inputVolumeLayout = qt.QGridLayout()
    self.inputVolumeBox.setLayout(inputVolumeLayout)
    self.layout.addWidget(self.inputVolumeBox)
    venousVolumeLabel = self.createLabel(title = 'Venous: ')
    self.venousVolumeNameLabel = self.createLineEdit(title="", text = '--', readOnly = True, maxLength = 50, styleSheet = "QLineEdit { background:transparent; }")
    inputVolumeLayout.addWidget(venousVolumeLabel,0,0)
    inputVolumeLayout.addWidget(self.venousVolumeNameLabel,0,1)
    ventricleVolumeLabel = self.createLabel(title='Ventricle: ')
    self.ventricleVolumeNameLabel = self.createLineEdit(title="", text='--', readOnly=True,
                                                     styleSheet="QLineEdit { background:transparent; }")
    self.venousVolumeNameLabel.setMaxLength(50)
    self.ventricleVolumeNameLabel.setMaxLength(50)
    inputVolumeLayout.addWidget(ventricleVolumeLabel,0,2)
    inputVolumeLayout.addWidget(self.ventricleVolumeNameLabel,0,3)
    self.showVolumeTable = self.createButton(title = "Show Table", maximumHeight = 35, maximumWidth = 80, toolTip = "Show the table of volumes for assignment.", enabled = True)
    self.showVolumeTable.connect('clicked(bool)', self.onShowVolumeTable)
    inputVolumeLayout.addWidget(self.showVolumeTable,0,4)

    self.importedNodeIDs= []
    self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent, self.onVolumeAddedNode)
    self.scriptDirectory = os.path.join(os.path.dirname(os.path.realpath(__file__)),"Resources", "icons")


    self.LoadCaseButton = self.createButton(title = "", toolTip = "Load a dicom dataset", enabled = True,
                                            maximumHeight = self.buttonHeight, maximumWidth = self.buttonWidth,
                                            icon = self.createIcon("load.png", self.scriptDirectory),
                                            iconSize = qt.QSize(self.buttonHeight, self.buttonWidth))
    self.LoadCaseButton.connect('clicked(bool)', self.onLoadDicom)
    self.mainGUIGroupBoxLayout.addWidget(self.LoadCaseButton, 2, 0)

    self.selectNasionButton = self.createButton(title="", toolTip="Add a point in the 3D window", enabled=True,
                                            maximumHeight=self.buttonHeight, maximumWidth=self.buttonWidth, checkable = True,
                                            icon=self.createIcon("nasion.png", self.scriptDirectory),
                                            iconSize=qt.QSize(self.buttonHeight, self.buttonWidth))
    self.selectNasionButton.connect('clicked(bool)', self.onSelectNasionPoint)
    self.mainGUIGroupBoxLayout.addWidget(self.selectNasionButton, 2, 1)

    self.selectSagittalButton = self.createButton(title="", toolTip="Add a point in the 3D window to identify the sagittal plane", enabled=True,
                                                maximumHeight=self.buttonHeight, maximumWidth=self.buttonWidth, checkable = True,
                                                icon=self.createIcon("sagittalPoint.png", self.scriptDirectory),
                                                iconSize=qt.QSize(self.buttonHeight, self.buttonWidth))
    self.selectSagittalButton.connect('clicked(bool)', self.onSelectSagittalPoint)
    self.mainGUIGroupBoxLayout.addWidget(self.selectSagittalButton, 2, 2)


    #-- Add Point
    self.addCannulaTargetButton = self.createButton(title="",
                                                  toolTip="Define the ventricle cylinder",
                                                  enabled=True, checkable = True,
                                                  maximumHeight=self.buttonHeight, maximumWidth=self.buttonWidth,
                                                  icon=self.createIcon("cannula.png", self.scriptDirectory),
                                                  iconSize=qt.QSize(self.buttonHeight, self.buttonWidth))
    self.addCannulaTargetButton.connect('clicked(bool)', self.onEditPlanningTarget)
    self.mainGUIGroupBoxLayout.addWidget(self.addCannulaTargetButton,2,3)

    self.addVesselSeedButton = self.createButton(title="",
                                                    toolTip="Place the seeds for venous segmentation",
                                                    enabled=True, checkable = True,
                                                    maximumHeight=self.buttonHeight, maximumWidth=self.buttonWidth,
                                                    icon=self.createIcon("vessel.png", self.scriptDirectory),
                                                    iconSize=qt.QSize(self.buttonHeight, self.buttonWidth))
    self.addVesselSeedButton.connect('clicked(bool)', self.onPlaceVesselSeed)
    self.mainGUIGroupBoxLayout.addWidget(self.addVesselSeedButton, 2, 4)


    self.relocatePathToKocherButton = self.createButton(title="",
                                                 toolTip="Relocate the cannula to be close to Kocher's point",
                                                 enabled=True,
                                                 maximumHeight=self.buttonHeight, maximumWidth=self.buttonWidth,
                                                 icon=self.createIcon("pathPlanning.png", self.scriptDirectory),
                                                 iconSize=qt.QSize(self.buttonHeight, self.buttonWidth))
    self.relocatePathToKocherButton.connect('clicked(bool)', self.onRelocatePathToKocher)
    self.mainGUIGroupBoxLayout.addWidget(self.relocatePathToKocherButton, 2, 5)


    self.createPlanningLineButton = self.createButton(title="",
                                                 toolTip="Confirm the target and generate the planning line.",
                                                 enabled=True,
                                                 maximumHeight=self.buttonHeight, maximumWidth=self.buttonWidth,
                                                 icon=self.createIcon("confirm.png", self.scriptDirectory),
                                                 iconSize=qt.QSize(self.buttonHeight, self.buttonWidth))
    self.createPlanningLineButton.connect('clicked(bool)', self.onCreatePlanningLine)
    self.mainGUIGroupBoxLayout.addWidget(self.createPlanningLineButton, 2, 6)

    self.saveDataButton = self.createButton(title="",
                                                toolTip="Save the scene and data.",
                                                enabled=True,
                                                maximumHeight=self.buttonHeight, maximumWidth=self.buttonWidth,
                                                icon=self.createIcon("save.png", self.scriptDirectory),
                                                iconSize=qt.QSize(self.buttonHeight, self.buttonWidth))
    self.saveDataButton.connect('clicked(bool)', self.onSaveData)
    self.mainGUIGroupBoxLayout.addWidget(self.saveDataButton, 2, 7)

    self.viewGroupBox = qt.QGroupBox()
    self.viewGroupBoxLayout = qt.QHBoxLayout()
    self.viewGroupBox.setLayout(self.viewGroupBoxLayout)
    self.layout.addWidget(self.viewGroupBox)

    #viewGroupBoxLabel = qt.QLabel('Viewer Configuration')
    #self.viewGroupBoxLayout.addWidget(viewGroupBoxLabel)

    self.viewSubGroupBox = qt.QGroupBox()
    self.viewSubGroupBoxLayout = qt.QHBoxLayout()
    self.viewSubGroupBox.setLayout(self.viewSubGroupBoxLayout)

    self.tabWidget = qt.QTabWidget()
    self.layout.addWidget(self.tabWidget)
    self.tabWidget.tabBar().hide()
    # end of GUI section
    #####################################
    self.tabMainGroupBox = qt.QGroupBox()
    self.tabMainGroupBoxLayout = qt.QVBoxLayout()
    self.tabMainGroupBox.setLayout(self.tabMainGroupBoxLayout)
    self.tabMainGroupBoxName = "tabMainGroup"
    self.tabMarkupsName = "markups"
    self.tabWidgetChildrenName = [self.tabMainGroupBoxName, self.tabMarkupsName]
    self.tabWidget.addTab(self.tabMainGroupBox, self.tabMainGroupBoxName)

    self.tabMarkupPlacementGroupBox = qt.QGroupBox()
    self.tabMarkupPlacementGroupBoxLayout = qt.QVBoxLayout()
    self.tabMarkupPlacementGroupBox.setLayout(self.tabMarkupPlacementGroupBoxLayout)
    vesselThresholdLabel = qt.QLabel('Vessel Threshold')
    vesselThresholdLayout = qt.QHBoxLayout()
    self.vesselThresholdGroupBox = qt.QGroupBox()
    self.vesselThresholdGroupBox.setLayout(vesselThresholdLayout)
    self.rangeThresholdWidget = slicer.qMRMLRangeWidget()
    self.rangeThresholdWidget.minimum = 50
    self.rangeThresholdWidget.maximum = 900
    self.rangeThresholdWidget.setValues(100,300)
    self.rangeThresholdWidget.connect('valuesChanged(double, double)', self.onChangeThresholdValues)
    vesselThresholdLayout.addWidget(vesselThresholdLabel)
    vesselThresholdLayout.addWidget(self.rangeThresholdWidget)
    self.segmentVesselWithSeedsButton = self.createButton(title="",
                                                toolTip="Segment the vessel based on threshold and seeds.",
                                                enabled=True,
                                                maximumHeight=self.buttonHeight*0.8, maximumWidth=self.buttonWidth*0.8,
                                                icon=self.createIcon("startVesselSegment.png", self.scriptDirectory),
                                                iconSize=qt.QSize(self.buttonHeight*0.8, self.buttonWidth*0.8))
    self.segmentVesselWithSeedsButton.connect('clicked(bool)', self.onSegmentVesselWithSeeds)
    #vesselThresholdLayout.addWidget(self.currentLowerThresholdValue)
    vesselThresholdLayout.addWidget(self.segmentVesselWithSeedsButton)
    self.tabMarkupPlacementGroupBoxLayout.addWidget(self.vesselThresholdGroupBox)

    self.simpleMarkupsWidget = slicer.qSlicerSimpleMarkupsWidget()
    self.simpleMarkupsWidget.setMRMLScene(slicer.mrmlScene)
    self.tabMarkupPlacementGroupBoxLayout.addWidget(self.simpleMarkupsWidget)

    self.tabWidget.addTab(self.tabMarkupPlacementGroupBox, self.tabMarkupsName)
    index = next((i for i, name in enumerate(self.tabWidgetChildrenName) if name == self.tabMainGroupBoxName), None)
    self.tabWidget.setCurrentIndex(index)

    venousVolumeLabel = qt.QLabel('Venous Image')
    self.viewSubGroupBoxLayout.addWidget(venousVolumeLabel)
    self.imageSlider = qt.QSlider(qt.Qt.Horizontal)
    self.imageSlider.setMinimum(0)
    self.imageSlider.setMaximum(100)
    self.viewSubGroupBoxLayout.addWidget(self.imageSlider)
    ventricleVolumeLabel = qt.QLabel('Ventricle Image')
    self.setWindowLevelButton = WindowLevelEffectsButton()
    self.greenLayoutButton = GreenSliceLayoutButton()
    self.conventionalLayoutButton = ConventionalSliceLayoutButton()
    self.viewSubGroupBoxLayout.addWidget(ventricleVolumeLabel)
    self.screenShotButton = ScreenShotButton()
    self.setReverseViewButton = ReverseViewOnCannulaButton()
    self.viewGroupBoxLayout.addWidget(self.setReverseViewButton,0, 0)
    self.viewGroupBoxLayout.addWidget(self.greenLayoutButton, 0, 1)
    self.viewGroupBoxLayout.addWidget(self.conventionalLayoutButton, 0, 2)
    self.viewGroupBoxLayout.addWidget(self.screenShotButton, 0, 3)
    self.viewGroupBoxLayout.addWidget(self.setWindowLevelButton, 0, 4)
    self.viewGroupBoxLayout.addWidget(venousVolumeLabel)
    self.viewGroupBoxLayout.addWidget(self.imageSlider)
    self.viewGroupBoxLayout.addWidget(ventricleVolumeLabel)

    self.imageSlider.connect('valueChanged(int)', self.onChangeSliceViewImage)

    #-- Curve length
    self.infoGroupBox = qt.QGroupBox()
    self.infoGroupBoxLayout = qt.QVBoxLayout()
    self.infoGroupBox.setLayout(self.infoGroupBoxLayout)

    cannulaLengthInfoLayout = qt.QHBoxLayout()
    lengthCannulaLabel = self.createLabel('Cannula Length:  ')
    cannulaLengthInfoLayout.addWidget(lengthCannulaLabel)
    self.lengthCannulaEdit = self.createLineEdit(title="", text='--', readOnly=True, frame=True, maxLength = 5,
                                                              styleSheet="QLineEdit { background:transparent; }",
                                                              cursor=qt.QCursor(qt.Qt.IBeamCursor))
    cannulaLengthInfoLayout.addWidget(self.lengthCannulaEdit)
    lengthCannulaUnitLabel = self.createLabel('mm  ')
    cannulaLengthInfoLayout.addWidget(lengthCannulaUnitLabel)

    planningSagittalLineLayout = qt.QHBoxLayout()
    lengthSagittalPlanningLineLabel = self.createLabel('Sagittal Length:  ')
    planningSagittalLineLayout.addWidget(lengthSagittalPlanningLineLabel)
    self.lengthSagittalPlanningLineEdit = self.createLineEdit(title="", text='--', readOnly=True, frame=True,
                                                              maxLength=5, styleSheet="QLineEdit { background:transparent; }",
                                                              cursor=qt.QCursor(qt.Qt.IBeamCursor))
    planningSagittalLineLayout.addWidget(self.lengthSagittalPlanningLineEdit)
    lengthSagittalPlanningLineUnitLabel = self.createLabel('mm  ')
    planningSagittalLineLayout.addWidget(lengthSagittalPlanningLineUnitLabel)

    planningCoronalLineLayout = qt.QHBoxLayout()
    lengthCoronalPlanningLineLabel = self.createLabel('Coronal Length:  ')
    planningCoronalLineLayout.addWidget(lengthCoronalPlanningLineLabel)
    self.lengthCoronalPlanningLineEdit = self.createLineEdit(title="", text='--', readOnly=True, frame=True,
                                                              maxLength=5,
                                                              styleSheet="QLineEdit { background:transparent; }",
                                                              cursor=qt.QCursor(qt.Qt.IBeamCursor))
    planningCoronalLineLayout.addWidget(self.lengthCoronalPlanningLineEdit)
    lengthCoronalPlanningLineUnitLabel = self.createLabel('mm  ')
    planningCoronalLineLayout.addWidget(lengthCoronalPlanningLineUnitLabel)


    planningDistanceKocherLayout = qt.QHBoxLayout()
    distanceKocherPointLabel = self.createLabel("Distance to Kocher's point:  ")
    planningDistanceKocherLayout.addWidget(distanceKocherPointLabel)
    self.distanceKocherPointEdit = self.createLineEdit(title="", text='--', readOnly=True, frame=True,
                                                             maxLength=5,
                                                             styleSheet="QLineEdit { background:transparent; }",
                                                             cursor=qt.QCursor(qt.Qt.IBeamCursor))
    planningDistanceKocherLayout.addWidget(self.distanceKocherPointEdit)
    distanceKocherPointUnitLabel = self.createLabel('mm  ')
    planningDistanceKocherLayout.addWidget(distanceKocherPointUnitLabel)

    planningPitchAngleLayout = qt.QHBoxLayout()
    #-- Curve length
    pitchAngleLabel = self.createLabel('Pitch Angle:       ')
    planningPitchAngleLayout.addWidget(pitchAngleLabel)
    self.pitchAngleEdit = self.createLineEdit(title="", text='--', readOnly=True, frame=True,
                                                       maxLength=5,
                                                       styleSheet="QLineEdit { background:transparent; }",
                                                       cursor=qt.QCursor(qt.Qt.IBeamCursor))
    planningPitchAngleLayout.addWidget(self.pitchAngleEdit)
    pitchAngleUnitLabel = self.createLabel('degree  ')
    planningPitchAngleLayout.addWidget(pitchAngleUnitLabel)

    planningYawAngleLayout = qt.QHBoxLayout()
    yawAngleLabel = self.createLabel('Yaw Angle:        ')
    planningYawAngleLayout.addWidget(yawAngleLabel)
    self.yawAngleEdit = self.createLineEdit(title="", text='--', readOnly=True, frame=True,
                                              maxLength=5,
                                              styleSheet="QLineEdit { background:transparent; }",
                                              cursor=qt.QCursor(qt.Qt.IBeamCursor))
    planningYawAngleLayout.addWidget(self.yawAngleEdit)
    yawAngleUnitLabel = self.createLabel('degree  ')
    planningYawAngleLayout.addWidget(yawAngleUnitLabel)

    planningCannulaToNormAngleLayout = qt.QHBoxLayout()
    cannulaToNormAngleLabel = self.createLabel('Cannula To Norm Angle:   ')
    planningCannulaToNormAngleLayout.addWidget(cannulaToNormAngleLabel)
    self.cannulaToNormAngleEdit = self.createLineEdit(title="", text='--', readOnly=True, frame=True,
                                            maxLength=5,
                                            styleSheet="QLineEdit { background:transparent; }",
                                            cursor=qt.QCursor(qt.Qt.IBeamCursor))
    planningCannulaToNormAngleLayout.addWidget(self.cannulaToNormAngleEdit)
    cannulaToNormAngleUnitLabel = self.createLabel('degree  ')
    planningCannulaToNormAngleLayout.addWidget(cannulaToNormAngleUnitLabel)


    planningCannulaToCoronalAngleLayout = qt.QHBoxLayout()
    cannulaToCoronalAngleLabel = self.createLabel('Cannula To Coronal Angle:')
    planningCannulaToCoronalAngleLayout.addWidget(cannulaToCoronalAngleLabel)
    self.cannulaToCoronalAngleEdit = self.createLineEdit(title="", text='--', readOnly=True, frame=True,
                                                      maxLength=5,
                                                      styleSheet="QLineEdit { background:transparent; }",
                                                      cursor=qt.QCursor(qt.Qt.IBeamCursor))
    planningCannulaToCoronalAngleLayout.addWidget(self.cannulaToCoronalAngleEdit)
    cannulaToCoronalAngleUnitLabel = self.createLabel('degree  ')
    planningCannulaToCoronalAngleLayout.addWidget(cannulaToCoronalAngleUnitLabel)

    planningSkullNormToSagittalAngleLayout = qt.QHBoxLayout()
    skullNormToSagittalAngleLabel = self.createLabel('Skull Norm To Sagital Angle:')
    planningSkullNormToSagittalAngleLayout.addWidget(skullNormToSagittalAngleLabel)
    self.skullNormToSagittalAngleEdit = self.createLineEdit(title="", text='--', readOnly=True, frame=True,
                                                         maxLength=5,
                                                         styleSheet="QLineEdit { background:transparent; }",
                                                         cursor=qt.QCursor(qt.Qt.IBeamCursor))
    planningSkullNormToSagittalAngleLayout.addWidget(self.skullNormToSagittalAngleEdit)
    skullNormToSagittalAngleUnitLabel = self.createLabel('degree  ')
    planningSkullNormToSagittalAngleLayout.addWidget(skullNormToSagittalAngleUnitLabel)

    planningSkullNormToCoronalAngleLayout = qt.QHBoxLayout()
    skullNormToCoronalAngleLabel = self.createLabel('Skull Norm To Coronal Angle:')
    planningSkullNormToCoronalAngleLayout.addWidget(skullNormToCoronalAngleLabel)
    self.skullNormToCoronalAngleEdit = self.createLineEdit(title="", text='--', readOnly=True, frame=True,
                                                            maxLength=5,
                                                            styleSheet="QLineEdit { background:transparent; }",
                                                            cursor=qt.QCursor(qt.Qt.IBeamCursor))
    planningSkullNormToCoronalAngleLayout.addWidget(self.skullNormToCoronalAngleEdit)
    skullNormToCoronalAngleUnitLabel = self.createLabel('degree  ')
    planningSkullNormToCoronalAngleLayout.addWidget(skullNormToCoronalAngleUnitLabel)

    self.infoGroupBoxLayout.addLayout(cannulaLengthInfoLayout)
    self.infoGroupBoxLayout.addLayout(planningSagittalLineLayout)
    self.infoGroupBoxLayout.addLayout(planningCoronalLineLayout)
    self.infoGroupBoxLayout.addLayout(planningDistanceKocherLayout)
    self.infoGroupBoxLayout.addLayout(planningPitchAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningYawAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningSkullNormToSagittalAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningSkullNormToCoronalAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningCannulaToNormAngleLayout)
    self.infoGroupBoxLayout.addLayout(planningCannulaToCoronalAngleLayout)
    self.tabMainGroupBoxLayout.addWidget(self.infoGroupBox)
    self.tabMainGroupBoxLayout.addStretch(1)

    # Add vertical spacer
    self.layout.addStretch(1)
    self.setBackgroundAndForegroundIDs(foregroundVolumeID=None,
                                       backgroundVolumeID=None)
    self.initialNodesIDList = []
    allNodes = slicer.mrmlScene.GetNodes()
    for nodeIndex in range(allNodes.GetNumberOfItems()):
      node = allNodes.GetItemAsObject(nodeIndex)
      self.initialNodesIDList.append(node.GetID())


  def cleanup(self):
    self.importedNodeIDs = []
    pass

  def updateFromCaseManager(self, EventID):
    if EventID == self.slicerCaseWidget.CloseCaseEvent:
      self.logic.clear()
      self.simpleMarkupsWidget
      self.initialFieldsValue()
      self.volumeSelected = False
      self.venousVolumeNameLabel.text = ""
      self.ventricleVolumeNameLabel.text = ""
      self.isLoadingCase = False
      self.screenShotButton.caseResultDir = ""
    elif EventID == self.slicerCaseWidget.LoadCaseCompletedEvent:
      self.screenShotButton.caseResultDir = self.slicerCaseWidget.currentCaseDirectory
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
        self.SerialAssignBox.Clear()
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
    elif EventID == self.slicerCaseWidget.StartCaseImportEvent:
      self.red_cn.SetDoPropagateVolumeSelection(False) # make sure the compositenode doesn't get updated,
      self.green_cn.SetDoPropagateVolumeSelection(False) # so that the background and foreground volumes are not messed up
      self.yellow_cn.SetDoPropagateVolumeSelection(False)
      self.isLoadingCase = True
      slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
    elif EventID == self.slicerCaseWidget.CreatedNewCaseEvent:
      self.screenShotButton.caseResultDir = self.slicerCaseWidget.currentCaseDirectory
      self.SerialAssignBox.Clear()
    pass

  def updateFromLogic(self, EventID):
    if EventID == VentriculostomyUserEvents.ResetButtonEvent:
      self.onResetButtons()
    if EventID == VentriculostomyUserEvents.SetSliceViewerEvent:
      self.setBackgroundAndForegroundIDs(foregroundVolumeID=self.logic.ventricleVolume.GetID(),
                                         backgroundVolumeID=self.logic.baseVolumeNode.GetID())
    if EventID == VentriculostomyUserEvents.SaveModifiedFiducialEvent:
      self.onSaveData()
    if EventID == VentriculostomyUserEvents.VentricleCylinderModified:
      self.volumePrepared = False # As the cylinder has been modified, the cropped, clipped and quartervolume is not valid, needs to be recalculated.
      normalVec = numpy.array(self.logic.trueSagittalPlane.GetNormal()) # the kocher's point might need to be relocated if the cylinder is pointing to another hemisphere of the brain
      originPos = numpy.array(self.logic.trueSagittalPlane.GetOrigin())
      targetPos = numpy.array([0.0, 0.0, 0.0])
      targetNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
      targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
      targetNode.GetNthFiducialPosition(0, targetPos)
      distalPos = numpy.array([0.0, 0.0, 0.0])
      distalNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
      distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
      distalNode.GetNthFiducialPosition(0, distalPos)
      ventriclePointLeft = -numpy.sign(numpy.dot(distalPos - targetPos,
                                               normalVec))  # here left hemisphere means from the patient's perspective
      if ventriclePointLeft >= 0 and self.logic.useLeftHemisphere == False:
        self.logic.useLeftHemisphere = True
        self.logic.createEntryPoint()
      if ventriclePointLeft < 0 and self.logic.useLeftHemisphere == True:
        self.logic.useLeftHemisphere = False
        self.logic.createEntryPoint()

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
    self.dicomWidget.detailsPopup.open()  
    pass

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onVolumeAddedNode(self, caller, eventId, callData):
    # When we are loading the cases, though the slicer.mrmlScene.NodeAddedEvent is removed, sometimes this function is still triggered.
    # We use the flag isLoadingCase to make sure it is not called.
    slicer.app.processEvents()
    if callData.IsA("vtkMRMLScalarVolumeDisplayNode"):
      callData.SetAutoWindowLevel(False)
      callData.SetWindow(self.baseVolumeWindowValue)
      callData.SetLevel(self.baseVolumeLevelValue)
    if callData.IsA("vtkMRMLVolumeNode") and (not self.isLoadingCase) and (not self.isInAlgorithmSteps):
      if self.onSaveDicomFiles():
        self.SerialAssignBox.AppendVolumeNode(callData)
        self.initialNodesIDList.append(callData.GetID())

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
            # To start the whole planning procedure, the MRMLScene needs to be clean up, but the nodes such as cameraNode, sliceNodes, baseVolumeNode and ventricleVolumeNode should not be deleted.
            # The following lines deletes the nodes generated from the previous planning case.
            allNodes = slicer.mrmlScene.GetNodes()
            for nodeIndex in range(allNodes.GetNumberOfItems()):
              node = allNodes.GetItemAsObject(nodeIndex)
              if node and (not (node.GetID() in self.initialNodesIDList)):
                if (not (node.GetClassName() == "vtkMRMLScriptedModuleNode")) \
                   and (not node.IsA("vtkMRMLDisplayNode")) and (not node.IsA("vtkMRMLStorageNode"))\
                   and (not (node.GetClassName() == "vtkMRMLCommandLineModuleNode")) \
                   and (not (node.GetClassName() == "vtkMRMLCameraNode")) \
                   and (not (node.GetClassName() == "vtkMRMLSceneViewNode")) \
                   and node.GetDisplayNode():
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
    slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
    if selectedNode:
      qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
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
      if self.logic.ventricleVolume and self.logic.baseVolumeNode:
        self.volumePrepared = False
        outputDir = os.path.join(self.slicerCaseWidget.currentCaseDirectory, "Results")
        self.logic.savePlanningDataToDirectory(self.logic.baseVolumeNode, outputDir)
        self.logic.savePlanningDataToDirectory(self.logic.ventricleVolume, outputDir)
        outputDir = os.path.join(self.slicerCaseWidget.currentCaseDirectory, "Results")
        self.jsonFile = os.path.join(outputDir, "PlanningTimeStamp.json")
        self.logic.appendPlanningTimeStampToJson(self.jsonFile, "StartPreProcessing",
                                                 datetime.datetime.now().time().isoformat())
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_model", "surfaceModel", intersectionVis=False)
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_clipModel", "clipModel", visibility=False, intersectionVis=False)
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_cannulaModel", "cannulaModel", color = [0.5, 1.0, 0.0])
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_sagittalReferenceModel", "sagittalReferenceModel",color=[1.0, 1.0, 0.5], intersectionVis=False)
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_coronalReferenceModel", "coronalReferenceModel", color =[0.5, 1.0, 0.5], intersectionVis=False)
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_sagittalPlanningModel", "sagittalPlanningModel", color=[1.0,1.0,0.0])
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_cylinderModel", "cylinderModel",
                                      color=[0.0, 1.0, 1.0])
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_pathCandidateModel", "pathCandidateModel",
                                      color=[1.0, 1.0, 0.0], visibility= False)
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_pathNavigationModel", "pathNavigationModel",
                                      color=[1.0, 1.0, 0.0], visibility= False)
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_coronalPlanningModel", "coronalPlanningModel", color=[0.0,1.0,0.0])
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_vesselnessModel", "vesselnessModel", color=[1.0, 0.0, 0.0])
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_vesselnessWithMarginModel", "vesselnessWithMarginModel", visibility=False)
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_grayScaleModel", "grayScaleModel",
                                      color=[0.8, 0.2, 0.0])
        self.logic.enableRelatedModel("vtkMRMLScalarVolumeNode.rel_grayScaleWithMarginModel",
                                      "grayScaleWithMarginModel", visibility=False)
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_nasion", "nasion")
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_kocher","kocher")
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_sagittalPoint", "sagittalPoint")
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_target", "target")
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_distal", "distal")
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_vesselSeeds", "vesselSeeds")
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_cannula", "cannula")
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_cylinderMarker", "cylinderMarker")
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_sagittalReferenceMarker", "sagittalReferenceMarker",visibility=False)
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_coronalReferenceMarker", "coronalReferenceMarker", visibility=False)
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_sagittalPlanningMarker", "sagittalPlanningMarker", visibility=False)
        self.logic.enableRelatedMarkups("vtkMRMLScalarVolumeNode.rel_coronalPlanningMarker", "coronalPlanningMarker", visibility=False)
        self.logic.enableRelatedVolume("vtkMRMLScalarVolumeNode.rel_croppedVolume","croppedVolume")
        self.logic.enableRelatedVolume("vtkMRMLScalarVolumeNode.rel_clippedVolume", "clippedVolume")
        self.logic.enableRelatedVolume("vtkMRMLScalarVolumeNode.rel_quarterVolume", "quarterVolume")
        self.logic.enableRelatedVolume("vtkMRMLScalarVolumeNode.rel_vesselnessVolume", "vesselnessVolume")
        self.logic.enableRelatedVariables("vtkMRMLScalarVolumeNode.rel_kocherMargin", "kocherMargin")
        self.logic.enableRelatedVariables("vtkMRMLScalarVolumeNode.rel_venousMargin", "venousMargin")
        self.logic.enableRelatedVariables("vtkMRMLScalarVolumeNode.rel_surfaceModelThreshold", "surfaceModelThreshold")
        self.logic.enableRelatedVariables("vtkMRMLScalarVolumeNode.rel_cylinderRadius", "cylinderRadius")
        self.logic.enableRelatedVariables("vtkMRMLScalarVolumeNode.rel_vesselLowerThreshold", "vesselLowerThreshold")
        self.logic.enableRelatedVariables("vtkMRMLScalarVolumeNode.rel_vesselUpperThreshold", "vesselUpperThreshold")
        self.logic.enableRelatedVariables("vtkMRMLScalarVolumeNode.rel_posteriorMargin", "posteriorMargin")
        if self.rangeThresholdWidget.minimum >= self.logic.vesselLowerThreshold:
          self.rangeThresholdWidget.minimum = self.logic.vesselLowerThreshold-50
        if self.rangeThresholdWidget.maximum <= self.logic.vesselUpperThreshold:
          self.rangeThresholdWidget.maximum = self.logic.vesselUpperThreshold+100
        self.rangeThresholdWidget.setValues(self.logic.vesselLowerThreshold, self.logic.vesselUpperThreshold)
        vesselSeedsNodelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselSeeds")
        self.simpleMarkupsWidget.setCurrentNode(slicer.mrmlScene.GetNodeByID(vesselSeedsNodelID))
        self.kocherMarginEdit.setText(self.logic.kocherMargin)
        self.posteriorMarginEdit.setText(self.logic.posteriorMargin)
        self.surfaceModelThresholdEdit.setText(self.logic.surfaceModelThreshold)
        self.venousMarginEdit.setText(self.logic.venousMargin)
        self.logic.enableEventObserver()
        self.setReverseViewButton.cannulaNode = slicer.mrmlScene.GetNodeByID(self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cannula"))
        self.logic.updateMeasureLength(float(self.lengthSagittalReferenceLineEdit.text), float(self.lengthCoronalReferenceLineEdit.text))
        self.lengthSagittalReferenceLineEdit.text = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength")
        self.lengthCoronalReferenceLineEdit.text = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength")

        cylinderModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cylinderModel")
        self.logic.cylinderManager.connectModelNode(slicer.mrmlScene.GetNodeByID(cylinderModelID))
        cylinderMarkerID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cylinderMarker")
        self.logic.cylinderManager.connectMarkerNode(slicer.mrmlScene.GetNodeByID(cylinderMarkerID))
        
        pathCandidateModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_pathCandidateModel")
        self.logic.pathCandidatesModel = slicer.mrmlScene.GetNodeByID(pathCandidateModelID)
        pathNavigationModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_pathNavigationModel")
        self.logic.pathNavigationModel = slicer.mrmlScene.GetNodeByID(pathNavigationModelID)

        ReferenceModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalReferenceModel")
        self.logic.sagittalReferenceCurveManager.connectModelNode(slicer.mrmlScene.GetNodeByID(ReferenceModelID))
        ReferenceModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalReferenceModel")
        self.logic.coronalReferenceCurveManager.connectModelNode(slicer.mrmlScene.GetNodeByID(ReferenceModelID))
        PlanningModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPlanningModel")
        self.logic.sagittalPlanningCurveManager.connectModelNode(slicer.mrmlScene.GetNodeByID(PlanningModelID))
        PlanningModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalPlanningModel")
        self.logic.coronalPlanningCurveManager.connectModelNode(slicer.mrmlScene.GetNodeByID(PlanningModelID))

        ReferenceMarkerID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalReferenceMarker")
        self.logic.sagittalReferenceCurveManager.connectMarkerNode(slicer.mrmlScene.GetNodeByID(ReferenceMarkerID))
        ReferenceMarkerID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalReferenceMarker")
        self.logic.coronalReferenceCurveManager.connectMarkerNode(slicer.mrmlScene.GetNodeByID(ReferenceMarkerID))
        PlanningMarkerID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPlanningMarker")
        self.logic.sagittalPlanningCurveManager.connectMarkerNode(slicer.mrmlScene.GetNodeByID(PlanningMarkerID))
        PlanningMarkerID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalPlanningMarker")
        self.logic.coronalPlanningCurveManager.connectMarkerNode(slicer.mrmlScene.GetNodeByID(PlanningMarkerID))
        self.logic.createTrueSagittalPlane()
        self.logic.createEntryPoint()
        cannulaModelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cannulaModel")
        cannulaFiducialsID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_cannula")
        self.logic.pathNavigationModel.SetDisplayVisibility(0)
        self.logic.cannulaManager.connectModelNode(slicer.mrmlScene.GetNodeByID(cannulaModelID))
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
        self.createModel()
        self.progressBar.value = 25
        self.progressBar.labelText = 'Calculating Vessel'
        slicer.app.processEvents()
        vesselSeedsID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselSeeds")
        vesselSeedsNode = slicer.mrmlScene.GetNodeByID(vesselSeedsID)
        self.prepareVolumes()
        self.prepareCandidatePath()
        if vesselSeedsNode and vesselSeedsNode.GetNumberOfFiducials():
          self.onConnectedComponentCalc()
        self.progressBar.value = 75
        self.logic.calculateCannulaTransform()
        self.setBackgroundAndForegroundIDs(foregroundVolumeID=self.logic.ventricleVolume.GetID(),
                                           backgroundVolumeID=self.logic.baseVolumeNode.GetID())
        self.onSet3DViewer()
        self.progressBar.labelText = 'Saving Preprocessed Data'
        slicer.app.processEvents()
        self.onSaveData()
        self.progressBar.close()
        self.logic.appendPlanningTimeStampToJson(self.jsonFile, "EndPreprocessing",
                                                 datetime.datetime.now().time().isoformat())
        self.imageSlider.setValue(100.0)
      qt.QApplication.restoreOverrideCursor()  
    self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                 self.onVolumeAddedNode)
    pass

  def onCreatePlanningLine(self):
    self.logic.pitchAngle="--"
    self.logic.yawAngle = "--"
    self.logic.skullNormToSaggitalAngle = "--"
    self.logic.skullNormToCoronalAngle = "--"
    self.logic.cannulaToNormAngle = "--"
    self.logic.cannulaToCoronalAngle = "--"
    if self.addVesselSeedButton.isChecked():
      self.addVesselSeedButton.click()
      slicer.app.processEvents()
    if self.logic.baseVolumeNode and self.logic.createPlanningLine():
      self.logic.pathCandidatesModel.SetDisplayVisibility(0)
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


  def onChangeThresholdValues(self, sliderLowerValue, sliderUpperValue):
    if self.logic.baseVolumeNode:
      self.logic.vesselLowerThreshold = sliderLowerValue
      self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_vesselLowerThreshold", str(sliderLowerValue))
      self.logic.vesselUpperThreshold = sliderUpperValue
      self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_vesselUpperThreshold", str(sliderUpperValue))

  def onChangePosteriorMargin(self, value):
    if self.logic.baseVolumeNode:
      self.logic.posteriorMargin = value
      self.posteriorMarginEdit.setText(str(value))
      self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_posteriorMargin", str(value))

  def onChangeKocherMargin(self, value):
    if self.logic.baseVolumeNode:
      self.logic.kocherMargin = value
      self.kocherMarginEdit.setText(str(value))
      self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_kocherMargin", str(value))

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
    red_cn.SetForegroundOpacity(sliderValue / 100.0)
    yellow_cn.SetForegroundOpacity(sliderValue / 100.0)
    green_cn.SetForegroundOpacity(sliderValue / 100.0)

  def prepareVolumes(self):
    quarterVolumeNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_quarterVolume")
    quarterVolume = slicer.mrmlScene.GetNodeByID(quarterVolumeNodeID)
    if quarterVolumeNodeID:
      targetNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
      distalNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
      clipModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_clipModel")
      croppedVolumeNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume")
      clippedVolumeNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_clippedVolume")
      if targetNodeID and distalNodeID and clippedVolumeNodeID and croppedVolumeNodeID and clipModelNodeID:
          targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
          distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
          targetNode.SetLocked(True)
          distalNode.SetLocked(True)
          croppedVolumeNode = slicer.mrmlScene.GetNodeByID(croppedVolumeNodeID)
          clippedVolumeNode = slicer.mrmlScene.GetNodeByID(clippedVolumeNodeID)
          clipModelNode = slicer.mrmlScene.GetNodeByID(clipModelNodeID)
          if targetNode.GetNumberOfFiducials() and distalNode.GetNumberOfFiducials() and clipModelNode:
            posTarget = numpy.array([0.0, 0.0, 0.0])
            targetNode.GetNthFiducialPosition(0, posTarget)
            posDistal = numpy.array([0.0, 0.0, 0.0])
            distalNode.GetNthFiducialPosition(0, posDistal)
            if self.volumePrepared == False:
              coneForVolumeClip = vtk.vtkConeSource()
              coneHeight = 100.0  # in millimeter
              coneForVolumeClip.SetHeight(coneHeight)
              coneForVolumeClip.SetResolution(60)
              ventricleDirect = (posDistal - posTarget) / numpy.linalg.norm(
                posTarget - posDistal)
              coneTipPoint = posTarget - numpy.linalg.norm(posDistal - posTarget) / 2.0 * ventricleDirect
              coneCenter = coneHeight / 2.0 * ventricleDirect + coneTipPoint
              coneForVolumeClip.SetCenter(coneCenter)
              coneForVolumeClip.SetDirection(-1.0 * ventricleDirect)  # we want the open end of the cone towards outside
              angle = 180.0 / math.pi * math.atan(2 * self.logic.cylinderRadius / numpy.linalg.norm(
                posTarget - posDistal))
              coneForVolumeClip.SetAngle(angle)
              coneForVolumeClip.Update()
              clipModelNode.SetAndObservePolyData(coneForVolumeClip.GetOutput())
              # -----------
              ROICenterPoint = coneTipPoint + ventricleDirect * numpy.array([0, 1, 1])* coneHeight
              self.logic.ROINode.SetXYZ(ROICenterPoint)
              # ROICenterPoint = coneTipPoint + numpy.array([0, 1, 1]) * 75
              ROIRadiusXYZ = [150, coneHeight * ventricleDirect[1],
                              max(coneHeight * math.tan(angle * math.pi / 180.0), coneHeight * ventricleDirect[2])]
              self.logic.ROINode.SetRadiusXYZ(ROIRadiusXYZ)
              cropVolumeLogic = slicer.modules.cropvolume.logic()

              cropVolumeLogic.CropVoxelBased(self.logic.ROINode, self.logic.baseVolumeNode, quarterVolume)
              slicer.app.processEvents()
              ROICenterPoint = coneTipPoint + ventricleDirect * coneHeight
              self.logic.ROINode.SetXYZ(ROICenterPoint)
              ROIRadiusXYZ = [max(coneHeight * math.tan(angle * math.pi / 180.0), coneHeight * ventricleDirect[0]),
                              coneHeight * ventricleDirect[1],
                              max(coneHeight * math.tan(angle * math.pi / 180.0), coneHeight * ventricleDirect[2])]
              self.logic.ROINode.SetRadiusXYZ(ROIRadiusXYZ)
              cropVolumeLogic = slicer.modules.cropvolume.logic()
              cropVolumeLogic.CropVoxelBased(self.logic.ROINode, self.logic.baseVolumeNode, croppedVolumeNode)
              slicer.app.processEvents()
              self.logic.createClippedVolume(croppedVolumeNode, clipModelNode, clippedVolumeNode)
              self.volumePrepared = True
            self.setBackgroundAndForegroundIDs(foregroundVolumeID=self.logic.ventricleVolume.GetID(),
                                               backgroundVolumeID=quarterVolume.GetID(), fitToSlice=True)
            self.logic.updateSliceViewBasedOnPoints(posTarget, posDistal)
            slicer.app.processEvents()
            if quarterVolume.GetDisplayNode():
              print "volume display ID", quarterVolume.GetDisplayNode().GetID()
              quarterVolume.GetDisplayNode().SetAutoWindowLevel(False)
              quarterVolume.GetDisplayNode().SetWindow(self.baseVolumeWindowValue)
              quarterVolume.GetDisplayNode().SetLevel(self.baseVolumeLevelValue)
    return True

  def prepareCandidatePath(self):
    self.logic.interactionMode = "none"
    targetNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
    distalNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
    nasionNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion")
    if targetNodeID and distalNodeID and nasionNodeID:
      targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
      distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
      nasionNode = slicer.mrmlScene.GetNodeByID(nasionNodeID)
      if targetNode.GetNumberOfFiducials() and distalNode.GetNumberOfFiducials() and nasionNode.GetNumberOfFiducials():
        posTarget = numpy.array([0.0, 0.0, 0.0])
        targetNode.GetNthFiducialPosition(0, posTarget)
        posDistal = numpy.array([0.0, 0.0, 0.0])
        distalNode.GetNthFiducialPosition(0, posDistal)
        posNasion = numpy.array([0.0, 0.0, 0.0])
        nasionNode.GetNthFiducialPosition(0, posNasion)
        direction = (numpy.array(posDistal) - numpy.array(posTarget))/numpy.linalg.norm(numpy.array(posDistal) - numpy.array(posTarget))
        if self.logic.trajectoryProjectedMarker.GetNumberOfFiducials() == 0:
          self.logic.trajectoryProjectedMarker.AddFiducial(0,0,0)
        vesselModelWithMarginNodeID = self.logic.baseVolumeNode.GetAttribute(
          "vtkMRMLScalarVolumeNode.rel_vesselnessWithMarginModel")
        vesselModelWithMarginNode = slicer.mrmlScene.GetNodeByID(vesselModelWithMarginNodeID)
        modelID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
        inputModelNode = slicer.mrmlScene.GetNodeByID(modelID)
        surfacePolyData = inputModelNode.GetPolyData()
        FiducialPointAlongVentricle = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        self.logic.calculateLineModelIntersect(surfacePolyData, posDistal+1e6*direction, posTarget-1e6*direction, FiducialPointAlongVentricle)
        posEntry = numpy.array([0.0, 0.0, 0.0])
        FiducialPointAlongVentricle.GetNthFiducialPosition(0,posEntry)
        self.logic.cylinderMiddlePointNode.RemoveAllMarkups()
        posCenter = numpy.array([(posTarget[0]+posDistal[0])/2.0, (posTarget[1]+posDistal[1])/2.0, (posTarget[2]+posDistal[2])/2.0])
        self.logic.cylinderMiddlePointNode.AddFiducial(posCenter[0], posCenter[1], posCenter[2])
        pathPlanningBasePoint = numpy.array(posTarget) + (numpy.array(posEntry) - numpy.array(posTarget)) * 1.2
        self.logic.calculateCannulaTransform()
        matrix = self.logic.transform.GetMatrix()
        points = vtk.vtkPoints()
        phiResolution = 1*numpy.pi/180.0
        radiusResolution = 1.0
        points.InsertNextPoint(posEntry)
        distance2 = numpy.linalg.norm(numpy.array(posTarget) - numpy.array(posEntry))
        distance1 = numpy.linalg.norm(numpy.array(posTarget) - numpy.array(posDistal))/2 # Divided by 2 is because, all the cylinder bottom are possible target points
        self.logic.entryRadius = self.logic.cylinderRadius * distance2 / distance1
        for radius in numpy.arange(radiusResolution, self.logic.entryRadius+radiusResolution, radiusResolution):
          for angle in numpy.arange(0, numpy.pi, phiResolution):
            point = matrix.MultiplyPoint(numpy.array([radius*math.cos(angle), radius*math.sin(angle),0,1]))
            pointTranslated = [point[0]+pathPlanningBasePoint[0],point[1]+pathPlanningBasePoint[1],point[2]+pathPlanningBasePoint[2]]
            points.InsertNextPoint(pointTranslated)
          for angle in numpy.arange(numpy.pi, 2*numpy.pi, phiResolution):
            point = matrix.MultiplyPoint(numpy.array([-radius * math.cos(angle), radius * math.sin(angle), 0, 1]))
            pointTranslated = [point[0] + pathPlanningBasePoint[0], point[1] + pathPlanningBasePoint[1], point[2] + pathPlanningBasePoint[2]]
            points.InsertNextPoint(pointTranslated)
        self.logic.synthesizedData.SetPoints(points)
        tempModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
        tempModel.SetName("candicateCannula")
        tempModel.SetAndObservePolyData(self.logic.synthesizedData)
        numOfRef = self.logic.coronalReferenceCurveManager.curveFiducials.GetNumberOfFiducials()
        if self.logic.synthesizedData.GetNumberOfPoints() and numOfRef >= 1:
          # display all paths model
          posKocher = [0.0,0.0,0.0]
          self.logic.coronalReferenceCurveManager.curveFiducials.GetNthFiducialPosition(numOfRef-1,posKocher)
          if not self.logic.pathCandidatesModel.GetPolyData():
            polyData = vtk.vtkPolyData()
            self.logic.pathCandidatesModel.SetAndObservePolyData(polyData)
          self.logic.pathReceived, self.logic.nPathReceived, self.logic.apReceived, self.logic.minimumPoint, self.logic.minimumDistance, self.logic.maximumPoint, self.logic.maximumDistance = self.logic.PercutaneousApproachAnalysisLogic.makePaths(
            self.logic.cylinderMiddlePointNode, None, 0, vesselModelWithMarginNode, tempModel)
          self.logic.makePathMeetAllConditions(self.logic.pathReceived, self.logic.nPathReceived, self.logic.pathCandidatesModel.GetPolyData(),posKocher,
                                         posNasion, surfacePolyData)
          #self.logic.createCandidatesWithinKocherPoint(points, posCenter, self.logic.pathCandidatesModel.GetPolyData(), posKocher, posNasion, surfacePolyData)
          self.logic.pathCandidatesModel.GetDisplayNode().SetVisibility(1)
          self.logic.pathCandidatesModel.GetDisplayNode().SetSliceIntersectionOpacity(0.2)
          if self.logic.nPathReceived<=0:
            slicer.util.warningDisplay(
              "No any cannula candidate exists here, considering redefine the ventricle area?")
            distalNode.SetLocked(False)
            targetNode.SetLocked(False)
            return False
          else:
            return True
    else:
      return False
    return False

  def onPlaceVesselSeed(self):
    slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
    self.imageSlider.setValue(0.0)
    if self.addVesselSeedButton.isChecked():
      index = next((i for i, name in enumerate(self.tabWidgetChildrenName) if name == self.tabMarkupsName), None)
      self.tabWidget.setCurrentIndex(index)
      self.isInAlgorithmSteps = True
      if not self.logic.baseVolumeNode:
        slicer.util.warningDisplay("No case is selected, please create a case", windowTitle="")
      else:
        if self.prepareVolumes() and self.prepareCandidatePath():
          #self.green_widget.sliceOrientation = 'Coronal' #provide coronal view at green widget
          if self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselSeeds"):
            vesselSeedsNode = slicer.mrmlScene.GetNodeByID(
              self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselSeeds"))
            self.logic.interactionMode = "vesselSeeds"
            self.simpleMarkupsWidget.setCurrentNode(vesselSeedsNode)
            self.greenLayoutButton.click()    
    else:
      self.logic.interactionMode = "none"
      self.simpleMarkupsWidget.markupsPlaceWidget().setPlaceModeEnabled(False)
      index = next((i for i, name in enumerate(self.tabWidgetChildrenName) if name == self.tabMainGroupBoxName), None)
      self.tabWidget.setCurrentIndex(index)
      self.isInAlgorithmSteps = False
      self.conventionalLayoutButton.click()
    self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                 self.onVolumeAddedNode)
    pass

  def onSegmentVesselWithSeeds(self):
    slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
    self.logic.interactionMode = "none"
    self.simpleMarkupsWidget.markupsPlaceWidget().setPlaceModeEnabled(False)
    self.onConnectedComponentCalc()
    self.prepareCandidatePath()
    #self.logic.pathCandidatesModel.SetDisplayVisibility(0)
    self.isInAlgorithmSteps = False

    self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                               self.onVolumeAddedNode)
    pass

  def onCreateModel(self):
    if self.logic.baseVolumeNode:
      outputModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
      if outputModelNodeID:
        outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
        outputModelNode.SetAttribute("vtkMRMLModelNode.modelCreated", "False")
        self.createModel()

  def createModel(self):
    self.isInAlgorithmSteps = True
    if self.logic.baseVolumeNode:
      outputModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
      if outputModelNodeID:
        outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
        slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
        try:
          self.logic.createModel(outputModelNode, self.logic.surfaceModelThreshold)
        except ValueError:
          slicer.util.warningDisplay(
            "Skull surface calculation error, volumes might not be suitable for calculation")
          self.isInAlgorithmSteps = False
        finally:
          slicer.app.processEvents()
          self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                     self.onVolumeAddedNode)
          self.onSet3DViewer()
          self.onSaveData()
    self.isInAlgorithmSteps = False

  def onSelectNasionPoint(self):
    if self.selectNasionButton.isChecked():
      if not self.logic.baseVolumeNode:
        slicer.util.warningDisplay("No case is selected, please select the case in the combox", windowTitle="")
      else:
        outputModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
        if outputModelNodeID:
          outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
          if (not outputModelNode) or outputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False":
              self.logic.createModel(outputModelNode, self.logic.surfaceModelThreshold)
              self.onSet3DViewer()
          self.logic.selectNasionPointNode(outputModelNode) # when the model is not available, the model will be created, so nodeAdded signal should be disconnected
          self.setBackgroundAndForegroundIDs(foregroundVolumeID=self.logic.ventricleVolume.GetID(),
                                             backgroundVolumeID=self.logic.baseVolumeNode.GetID())
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
              self.logic.createModel(outputModelNode, self.logic.surfaceModelThreshold)
              self.onSet3DViewer()
          self.logic.selectSagittalPointNode(outputModelNode) # when the model is not available, the model will be created, so nodeAdded signal should be disconnected
          self.setBackgroundAndForegroundIDs(foregroundVolumeID=self.logic.ventricleVolume.GetID(),
                                             backgroundVolumeID=self.logic.baseVolumeNode.GetID())
    else:
      self.logic.placeWidget.setPlaceModeEnabled(False)

  def onSaveData(self):
    if not self.isLoadingCase:
      outputDir = os.path.join(self.slicerCaseWidget.currentCaseDirectory, "Results")
      if self.logic.baseVolumeNode:
        if self.logic.baseVolumeNode.GetModifiedSinceRead():
          self.logic.savePlanningDataToDirectory(self.logic.baseVolumeNode, outputDir)

      nodeAttributes=["rel_ventricleVolume", "rel_model","rel_nasion", "rel_kocher", "rel_sagittalPoint","rel_target","rel_distal", "rel_vesselSeeds", \
                      "rel_cannula","rel_skullNorm","rel_cannulaModel","rel_sagittalReferenceModel","rel_sagittalReferenceMarker","rel_coronalReferenceModel","rel_coronalReferenceMarker",\
                      "rel_sagittalPlanningModel","rel_sagittalPlanningMarker","rel_coronalPlanningModel","rel_coronalPlanningMarker","rel_cylinderMarker","rel_vesselnessModel","rel_vesselnessWithMarginModel","rel_vesselnessVolume"]
      for attribute in nodeAttributes:
        nodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode."+attribute)
        if nodeID and slicer.mrmlScene.GetNodeByID(nodeID):
          node = slicer.mrmlScene.GetNodeByID(nodeID)
          if node and node.GetModifiedSinceRead():
            self.logic.savePlanningDataToDirectory(node, outputDir)
      slicer.util.saveScene(os.path.join(outputDir, "Results.mrml"))
      self.logic.appendPlanningTimeStampToJson(self.jsonFile, "CaseSavedTime", datetime.datetime.now().time().isoformat())
    pass

  def onModifyVenousMargin(self):
    self.logic.venousMargin = float(self.venousMarginEdit.text)
    self.logic.distanceMapThreshold = float(self.distanceMapThresholdEdit.text)
    vesselnessModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessModel")
    vesselnessModelNode = slicer.mrmlScene.GetNodeByID(vesselnessModelNodeID)
    grayScaleModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel")
    grayScaleModelNode = slicer.mrmlScene.GetNodeByID(grayScaleModelNodeID)
    if vesselnessModelNode:
      vesselnessModelNode.SetAttribute("vtkMRMLModelNode.modelCreated","False")
    if grayScaleModelNode:
      grayScaleModelNode.SetAttribute("vtkMRMLModelNode.modelCreated","False")
    nodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessWithMarginModel")
    node = slicer.mrmlScene.GetNodeByID(nodeID)
    if node:
      node.SetAttribute("vtkMRMLModelNode.modelCreated","False")
    nodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleWithMarginModel")
    node = slicer.mrmlScene.GetNodeByID(nodeID)
    if node:
      node.SetAttribute("vtkMRMLModelNode.modelCreated", "False")
    pass

  def onModifySurfaceModel(self):
    self.logic.surfaceModelThreshold = float(self.surfaceModelThresholdEdit.text)
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
    self.isInAlgorithmSteps = True
    if self.logic.baseVolumeNode and self.prepareVolumes():
      quarterVolumeNode = self.logic.baseVolumeNode
      quarterVolumeNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_quarterVolume")
      if quarterVolumeNodeID:
        quarterVolumeNode = slicer.mrmlScene.GetNodeByID(quarterVolumeNodeID)
      grayScaleModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel")
      grayScaleModelNode = slicer.mrmlScene.GetNodeByID(grayScaleModelNodeID)
      if grayScaleModelNode and (grayScaleModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False"):
        grayScaleModelNodeID = grayScaleModelNode.GetID()
        grayScaleModelNode = slicer.mrmlScene.GetNodeByID(grayScaleModelNodeID)
        self.grayScaleMakerButton.setEnabled(0)
        slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
        try:
          self.logic.calculateVenousGrayScale(quarterVolumeNode, grayScaleModelNode)
        except ValueError:
          slicer.util.warningDisplay(
            "Venouse Calculation error, volumes might not be suitable for calculation")
        finally:
          slicer.app.processEvents()
          self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                       self.onVolumeAddedNode)
          self.onCalculateVenousCompletion(self.logic.cliNode)
          self.onSaveData()
    self.isInAlgorithmSteps = False    
    pass

  def onConnectedComponentCalc(self):
    self.isInAlgorithmSteps = True
    vesselSeedsNode = None
    #self.logic.pathCandidatesModel.SetDisplayVisibility(0)
    if self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselSeeds"):
      vesselSeedsNode = slicer.mrmlScene.GetNodeByID(
        self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselSeeds"))
      vesselSeedsNode.SetLocked(True)
    if self.logic.baseVolumeNode and vesselSeedsNode and self.prepareVolumes():
      quarterVolumeNode = self.logic.baseVolumeNode
      quarterVolumeNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_quarterVolume")
      if quarterVolumeNodeID:
        quarterVolumeNode = slicer.mrmlScene.GetNodeByID(quarterVolumeNodeID)
      vesselnessModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessModel")
      if vesselnessModelNodeID:
        vesselnessModelNode = slicer.mrmlScene.GetNodeByID(vesselnessModelNodeID)
        slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
        try:
          self.logic.calculateConnectedComponent(quarterVolumeNode, vesselSeedsNode, vesselnessModelNode)
        except ValueError:
          slicer.util.warningDisplay(
            "Vessel Margin Calculation error, volumes might not be suitable for calculation")
        finally:
          slicer.app.processEvents()
          self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                       self.onVolumeAddedNode)
          marginNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessWithMarginModel")
          marginNode = slicer.mrmlScene.GetNodeByID(marginNodeID)
          marginNode.SetAttribute("vtkMRMLModelNode.modelCreated", "False")
          self.onCalculateVenousCompletion()
          self.onSaveData()
    self.isInAlgorithmSteps = False
    pass

  def onVenousVesselnessCalc(self):
    self.isInAlgorithmSteps = True
    vesselSeedsNode = None
    if self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselSeeds"):
        vesselSeedsNode = slicer.mrmlScene.GetNodeByID(self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselSeeds"))
    if self.logic.baseVolumeNode and vesselSeedsNode:
      quarterVolumeNode = self.logic.baseVolumeNode
      quarterVolumeNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_quarterVolume")
      if quarterVolumeNodeID:
        quarterVolumeNode = slicer.mrmlScene.GetNodeByID(quarterVolumeNodeID)
      vesselnessVolumeNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessVolume")
      vesselnessModelNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessModel")
      if vesselnessVolumeNodeID and vesselnessModelNodeID:
        vesselnessVolumeNode = slicer.mrmlScene.GetNodeByID(vesselnessVolumeNodeID)
        vesselnessModelNode = slicer.mrmlScene.GetNodeByID(vesselnessModelNodeID)
        slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
        outputTubeFile = os.path.join(self.slicerCaseWidget.outputDir, "OutputTubeTree")
        try:
          self.logic.calculateVenousVesselness(quarterVolumeNode, vesselnessVolumeNode, vesselSeedsNode, outputTubeFile, vesselnessModelNode)
        except ValueError:
          slicer.util.warningDisplay(
            "Vessel Margin Calculation error, volumes might not be suitable for calculation")
        finally:
          slicer.app.processEvents()
          self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                     self.onVolumeAddedNode)
          self.onCalculateVenousCompletion(self.logic.cliNode)
          self.onSaveData()
    self.isInAlgorithmSteps = False    
    pass

  #@beforeRunProcessEvents
  def onCalculateVenousCompletion(self,node=None,event=None):
    status = 'Completed'
    if node:
      status = node.GetStatusString()
      self.venousCalcStatus.setText(node.GetName() +' '+status)
    if status == 'Completed':
      self.progressBar.value = 50
      self.progressBar.labelText = 'Calculating Vessel margin'
      slicer.app.processEvents()
      slicer.mrmlScene.RemoveObserver(self.nodeAddedEventObserverID)
      try:
        self.logic.calculateConnectedCompWithMargin()
        #self.logic.calculateVesselWithMargin()
        #self.logic.calculateGrayScaleWithMargin()
      except ValueError:
        slicer.util.warningDisplay(
          "Vessel Margin Calculation error, volumes might not be suitable for calculation")
      finally:
        slicer.app.processEvents()
        self.nodeAddedEventObserverID = slicer.mrmlScene.AddObserver(slicer.mrmlScene.NodeAddedEvent,
                                                                   self.onVolumeAddedNode)
        self.setBackgroundAndForegroundIDs(foregroundVolumeID=self.logic.ventricleVolume.GetID(), backgroundVolumeID=self.logic.baseVolumeNode.GetID())## the slice widgets are set to none after the  cli module calculation. reason unclear...
        self.progressBar.value = 100
        self.progressBar.close()
        self.onSaveData()
    else:
      slicer.util.warningDisplay("Vessel segmentation failed.")
    self.grayScaleMakerButton.enabled = True
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

  def setBackgroundAndForegroundIDs(self, foregroundVolumeID, backgroundVolumeID, fitToSlice = True):
    if foregroundVolumeID:
      self.red_cn.SetForegroundVolumeID(foregroundVolumeID)
      self.yellow_cn.SetForegroundVolumeID(foregroundVolumeID)
      self.green_cn.SetForegroundVolumeID(foregroundVolumeID)
    if backgroundVolumeID:
      self.red_cn.SetBackgroundVolumeID(backgroundVolumeID)
      self.yellow_cn.SetBackgroundVolumeID(backgroundVolumeID)
      self.green_cn.SetBackgroundVolumeID(backgroundVolumeID)
      if fitToSlice:
        self.red_widget.fitSliceToBackground()
        self.yellow_widget.fitSliceToBackground()
        self.green_widget.fitSliceToBackground()
    pass

  # Event handlers for trajectory
  def onEditPlanningTarget(self):
    if self.logic.baseVolumeNode and self.addCannulaTargetButton.isChecked():
      self.imageSlider.setValue(100.0)
      self.initialFieldsValue()
      targetNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
      distalNodeID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
      if targetNodeID and distalNodeID:
        targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
        distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
        targetNode.SetLocked(False)
        distalNode.SetLocked(False)
        self.setBackgroundAndForegroundIDs(foregroundVolumeID=self.logic.ventricleVolume.GetID(), backgroundVolumeID=self.logic.baseVolumeNode.GetID(), fitToSlice=False
                                           )
        self.logic.startEditPlanningTarget()
    else:
      self.logic.placeWidget.setPlaceModeEnabled(False)

  # Event handlers for trajectory
  def onEditPlanningDistal(self):
    self.imageSlider.setValue(100.0)
    self.initialFieldsValue()
    self.logic.startEditPlanningDistal()

  def onRelocatePathToKocher(self):
    if self.logic.baseVolumeNode:
      self.logic.relocateCannula(1)
      self.logic.pathCandidatesModel.SetDisplayVisibility(1)

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
      self.logic.lockTrajectoryLine()
    else:
      self.addCannulaTargetButton.enabled = True
      self.logic.unlockTrajectoryLine()

  def onReload(self,moduleName="VentriculostomyPlanning"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    self.logic.clear()
    slicer.mrmlScene.Clear(0)
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)

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

  def connectModelNode(self, mrmlModelNode):
    if self._curveModel:
      slicer.mrmlScene.RemoveNode(self._curveModel.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(self._curveModel)
    self._curveModel =  mrmlModelNode

  def connectMarkerNode(self, mrmlMarkerNode):
    if self.curveFiducials:
      slicer.mrmlScene.RemoveNode(self.curveFiducials.GetDisplayNode())
      slicer.mrmlScene.RemoveNode(self.curveFiducials)
    self.curveFiducials =  mrmlMarkerNode

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

class VentriculostomyPlanningLogic(ScriptedLoadableModuleLogic, ModuleLogicMixin):
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
    self.cylinderManager.setName("Cylinder")
    self.cylinderManager.setModelColor(0.0, 1.0, 1.0)
    self.cylinderManager.setDefaultSlicePositionToFirstPoint()
    self.cylinderManager.setModelOpacity(0.5)

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

    self.ROINode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLAnnotationROINode")
    self.ROINode.SetName("ROINodeForCropping")
    self.ROINode.HideFromEditorsOff()
    #slicer.mrmlScene.AddNode(self.ROINode)


    ##Path Planning variables
    self.PercutaneousApproachAnalysisLogic = PercutaneousApproachAnalysisLogic()
    self.cylinderMiddlePointNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    self.synthesizedData = vtk.vtkPolyData()
    ##
    self.pathReceived = None
    self.pathCandidatesModel = None
    self.pathNavigationModel = None
    self.cylinderInteractor = None
    self.trajectoryProjectedMarker = None
    self.enableAuxilaryNodes()

    self.distanceMapFilter = sitk.SignedMaurerDistanceMapImageFilter()
    self.distanceMapFilter.SquaredDistanceOff()
    self.connectedComponentFilter = sitk.ConnectedThresholdImageFilter()
    self.baseVolumeNode = None
    self.ventricleVolume = None
    self.functions = UsefulFunctions()
    self.useLeftHemisphere = False
    self.cliNode = None
    self.samplingFactor = 1
    self.topPoint = []
    self.surfaceModelThreshold = -500.0
    self.distanceMapThreshold = 100
    self.vesselLowerThreshold = 100
    self.vesselUpperThreshold = 800
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
    self.posteriorMargin = 60.0 #unit mm
    self.kocherMargin = 20.0 #unit mm
    self.entryRadius = 25.0
    self.transform = vtk.vtkTransform()
    self.placeWidget = slicer.qSlicerMarkupsPlaceWidget()
    self.interactionMode = "none"

  def enableAuxilaryNodes(self):
    # Create display node
    self.cylinderInteractor = None
    self.trajectoryProjectedMarker = None
    modelDisplay = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
    red = [1, 0, 0]
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
    if self.ROINode:
      self.ROINode = None
    self.baseVolumeNode = None
    self.ventricleVolume = None

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
    storageNodeAvailable = node.GetStorageNode()
    if not storageNodeAvailable:
      storageNodeAvailable = node.AddDefaultStorageNode()
      slicer.app.processEvents()
    if storageNodeAvailable:
      storageNode = node.GetStorageNode()
      extension = storageNode.GetDefaultWriteFileExtension()
      baseNodeName = self.baseVolumeNode.GetName()
      for character in characters:
        baseNodeName = baseNodeName.replace(character, "-")
      filename = os.path.join(outputDir, nodeName +'.'+ extension)
      if slicer.util.saveNode(node, filename):
        return True
    return False
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
  
  def calculateVesselWithMargin(self):
    marginNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessWithMarginModel")
    marginNode = slicer.mrmlScene.GetNodeByID(marginNodeID)
    vesselnessNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessVolume")
    vesselnessNode = slicer.mrmlScene.GetNodeByID(vesselnessNodeID)
    if not vesselnessNode.GetImageData():
      slicer.util.warningDisplay("Venous was not segmented yet, abort current procedure")
      return None
    if marginNode and (marginNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False"):
      vesselImage = sitk.Cast(sitkUtils.PullFromSlicer(vesselnessNodeID), sitk.sitkInt32)
      try:
        distanceMap = sitk.Multiply(self.distanceMapFilter.Execute(vesselImage),-1)
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
        parameters["OutputGeometry"] = marginNode.GetID()
        parameters["Threshold"] = -self.venousMargin
        grayMaker = slicer.modules.grayscalemodelmaker
        self.cliNode = slicer.cli.run(grayMaker, None, parameters, wait_for_completion=True)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessWithMarginModel", marginNode.GetID())
        marginNode.SetAttribute("vtkMRMLModelNode.modelCreated", "True")
      self.update_observers(VentriculostomyUserEvents.SetSliceViewerEvent)
    return marginNode


  def calculateConnectedCompWithMargin(self):
    marginNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessWithMarginModel")
    marginNode = slicer.mrmlScene.GetNodeByID(marginNodeID)
    imageCollection = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode", "connectedImage")
    if imageCollection:
      connectedImageNode = imageCollection.GetItemAsObject(0)
      if not connectedImageNode.GetImageData():
        slicer.util.warningDisplay("vessel was not segmented yet, abort current procedure")
        return None
      if marginNode and (marginNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False"):
        connectedImage = sitk.Cast(sitkUtils.PullFromSlicer(connectedImageNode.GetID()), sitk.sitkInt8)
        # padding is necessary, because some venous could be very close to the volume boundary. Which causes distance map to be incomplete at the coundary.
        # In the end, the incomplete distance map will create holes in the venous margin model
        padFilter = sitk.ConstantPadImageFilter()
        padFilter.SetPadLowerBound([int(self.venousMargin), int(self.venousMargin), int(self.venousMargin)])
        padFilter.SetPadUpperBound([int(self.venousMargin), int(self.venousMargin), int(self.venousMargin)])
        paddedImage = padFilter.Execute(connectedImage)
        try:
          distanceMap = sitk.Multiply(self.distanceMapFilter.Execute(paddedImage),-1)
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
          parameters["OutputGeometry"] = marginNode.GetID()
          parameters["Threshold"] = -self.venousMargin
          grayMaker = slicer.modules.grayscalemodelmaker
          self.cliNode = slicer.cli.run(grayMaker, None, parameters, wait_for_completion=True)
          self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessWithMarginModel", marginNode.GetID())
          marginNode.SetAttribute("vtkMRMLModelNode.modelCreated", "True")
        self.update_observers(VentriculostomyUserEvents.SetSliceViewerEvent)
    return marginNode
  
  def calculateGrayScaleWithMargin(self):
    nodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleWithMarginModel")
    node = slicer.mrmlScene.GetNodeByID(nodeID)
    if not node:
      node = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
      slicer.mrmlScene.AddNode(node)
    if node and (node.GetAttribute("vtkMRMLModelNode.modelCreated") == "False"):
      quarterVolumeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_quarterVolume")
      quarterVolume = slicer.mrmlScene.GetNodeByID(quarterVolumeID)
      originImage = sitk.Cast(sitkUtils.PullFromSlicer(self.baseVolumeNode.GetID()), sitk.sitkInt32)
      try:
        distanceMap = self.distanceMapFilter.Execute(quarterVolume, self.distanceMapThreshold - 10, self.distanceMapThreshold )
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
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleWithMarginModel", node.GetID())
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

  def makeNavigationLines(self, path, approachablePoints, polyData):
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
    # Create model node
    pass
  
  def createCandidatesWithinKocherPoint(self, entryPoints, posCenter, polyData, posKocher, surfacePolyData):

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

    locator = vtk.vtkCellLocator()
    locator.SetDataSet(surfacePolyData)
    locator.BuildLocator()
    t = vtk.mutable(0)
    x = [0.0, 0.0, 0.0]
    pcoords = [0.0, 0.0, 0.0]
    subId = vtk.mutable(0)
    for pointIndex in range(entryPoints.GetNumberOfPoints()):
        hasIntersection = locator.IntersectWithLine(entryPoints.GetPoint(pointIndex), posCenter, 1e-2, t, x,
                                                  pcoords, subId)
        if (hasIntersection > 0) and numpy.linalg.norm(numpy.array(x)-numpy.array(posKocher)) < self.kocherMargin:
          index = points.InsertNextPoint(*posCenter)
          linesIDArray.InsertNextTuple1(index)
          linesIDArray.SetTuple1(0, linesIDArray.GetNumberOfTuples() - 1)
          lines.SetNumberOfCells(1)
          point = entryPoints.GetPoint(pointIndex)
          index = points.InsertNextPoint(*point)
          linesIDArray.InsertNextTuple1(index)
          linesIDArray.SetTuple1(0, linesIDArray.GetNumberOfTuples() - 1)
          lines.SetNumberOfCells(1)
    # Create model node
    pass

  def makePathMeetAllConditions(self, path, approachablePoints, polyData, posKocher, posNasion, surfacePolyData):

    trimmedPath = []
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

    locator = vtk.vtkCellLocator()
    locator.SetDataSet(surfacePolyData)
    locator.BuildLocator()
    t = vtk.mutable(0)
    x = [0.0, 0.0, 0.0]
    pcoords = [0.0, 0.0, 0.0]
    subId = vtk.mutable(0)
    numOfRef = self.coronalReferenceCurveManager.curveFiducials.GetNumberOfFiducials()
    if approachablePoints != 0 and numOfRef >=1:
      for pointIndex in range(1, len(path), 2):
          hasIntersection = locator.IntersectWithLine(path[pointIndex], path[pointIndex - 1], 1e-2, t, x,
                                                    pcoords, subId)
          if (hasIntersection > 0) and abs(x[2]-posNasion[2]) > self.posteriorMargin and numpy.linalg.norm(numpy.array(x)-numpy.array(posKocher)) < self.kocherMargin:
            pointPre = path[pointIndex - 1]
            index = points.InsertNextPoint(*pointPre)
            linesIDArray.InsertNextTuple1(index)
            linesIDArray.SetTuple1(0, linesIDArray.GetNumberOfTuples() - 1)
            lines.SetNumberOfCells(1)
            point = path[pointIndex]
            index = points.InsertNextPoint(*point)
            linesIDArray.InsertNextTuple1(index)
            linesIDArray.SetTuple1(0, linesIDArray.GetNumberOfTuples() - 1)
            lines.SetNumberOfCells(1)
            trimmedPath.append(path[pointIndex - 1])
            trimmedPath.append(path[pointIndex])
    self.pathReceived = trimmedPath
    self.nPathReceived = int(len(trimmedPath)/2)
    pass

  def relocateCannula(self, optimizationMethod=1):
    if self.pathReceived:
      #self.cannulaManager.curveFiducials.RemoveAllMarkups()
      posTarget = numpy.array([0.0] * 3)
      self.cylinderManager.getFirstPoint(posTarget)
      posDistal = numpy.array([0.0] * 3)
      self.cylinderManager.getLastPoint(posDistal)
      direction1Norm = (posDistal - posTarget)/numpy.linalg.norm(posTarget - posDistal)
      angleCalc =numpy.pi
      if optimizationMethod == 0: # the cannula is relocated so that its direction is closer to the ventricle center
        optimizedEntry = numpy.array([])
        for pointIndex in range(1, len(self.pathReceived),2):
          direction2 = numpy.array(self.pathReceived[pointIndex]) - numpy.array(self.pathReceived[pointIndex-1])
          direction2Norm = direction2/numpy.linalg.norm(direction2)
          angle = math.acos(numpy.dot(direction1Norm, direction2Norm))
          if angle < angleCalc:
            angleCalc = angle
            optimizedEntry = numpy.array(self.pathReceived[pointIndex])
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
              posKocher = [0.0,0.0,0.0]
              self.coronalReferenceCurveManager.curveFiducials.GetNthFiducialPosition(numOfRef-1,posKocher)
              for pointIndex in range(1, len(self.pathReceived),2):
                hasIntersection = locator.IntersectWithLine(self.pathReceived[pointIndex], self.pathReceived[pointIndex-1], 1e-2, t, x, pcoords, subId)
                if hasIntersection>0:
                  if distanceMin > numpy.linalg.norm(numpy.array(posKocher)-numpy.array(x)):
                    distanceMin = numpy.linalg.norm(numpy.array(posKocher)-numpy.array(x))
                    minIndex = pointIndex
              self.cannulaManager.curveFiducials.RemoveAllMarkups()
              self.cannulaManager.curveFiducials.AddFiducial(0, 0, 0)
              self.cannulaManager.curveFiducials.AddFiducial(0, 0, 0)
              self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(0, self.pathReceived[minIndex-1])
              self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(1, self.pathReceived[minIndex])
              direction2 = numpy.array(self.pathReceived[minIndex]) - numpy.array(self.pathReceived[minIndex-1])
              direction2Norm = direction2/numpy.linalg.norm(direction2)
              angleCalc = math.acos(numpy.dot(direction1Norm, direction2Norm))
      self.activeTrajectoryMarkup = 1
      self.updateCannulaPosition(self.cannulaManager.curveFiducials)
      posProject =  numpy.array([0.0] * 3)
      self.trajectoryProjectedMarker.GetNthFiducialPosition(0,posProject)
      posMiddle = (posTarget+posDistal)/2
      posBottom = posMiddle+numpy.linalg.norm(posMiddle - posDistal)/math.cos(angleCalc)*(posMiddle-posProject)/numpy.linalg.norm(posMiddle - posProject)
      self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(0, posBottom)
      self.cannulaManager.curveFiducials.SetNthMarkupLocked(0,True)
      self.cannulaManager.curveFiducials.SetNthFiducialPositionFromArray(1, posProject)
      self.trajectoryProjectedMarker.RemoveAllMarkups()
    pass

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

    if self.ventricleVolume == None:
      return
    if outputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False":
      resampleFilter = sitk.ResampleImageFilter()
      originImage = sitk.Cast(sitkUtils.PullFromSlicer(self.ventricleVolume.GetID()), sitk.sitkInt16)
      self.samplingFactor = 2
      resampleFilter.SetSize(numpy.array(originImage.GetSize())/self.samplingFactor)
      resampleFilter.SetOutputSpacing(numpy.array(originImage.GetSpacing())*self.samplingFactor)
      resampleFilter.SetOutputOrigin(numpy.array(originImage.GetOrigin()))
      resampledImage = resampleFilter.Execute(originImage)
      thresholdFilter = sitk.BinaryThresholdImageFilter()
      thresholdImage = thresholdFilter.Execute(resampledImage,thresholdValue,10000,1,0)
      padFilter = sitk.ConstantPadImageFilter()
      padFilter.SetPadLowerBound([10, 10, 10])
      paddedImage = padFilter.Execute(thresholdImage)
      dilateFilter = sitk.BinaryDilateImageFilter()
      dilateFilter.SetKernelRadius([10,10,6])
      dilateFilter.SetBackgroundValue(0)
      dilateFilter.SetForegroundValue(1)
      dilatedImage = dilateFilter.Execute(paddedImage)
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

  def createClippedVolume(self, inputVolumeNode, clippingModel, outputVolume):
    self.functions.clipVolumeWithModel(inputVolumeNode, clippingModel, True, 0, outputVolume)

  def calculateVenousGrayScale(self, inputVolumeNode, grayScaleModelNode):    
      parameters = {}
      parameters["InputVolume"] = inputVolumeNode.GetID()
      parameters["Threshold"] = self.distanceMapThreshold
      parameters["OutputGeometry"] = grayScaleModelNode.GetID()
      grayMaker = slicer.modules.grayscalemodelmaker
      self.cliNode = slicer.cli.run(grayMaker, None, parameters, wait_for_completion=True)

  def calculateConnectedComponent(self,inputVolumeNode, vesselSeedsNode, vesselnessModelNode):
      if inputVolumeNode:
        oriImage = sitk.Cast(sitkUtils.PullFromSlicer(inputVolumeNode.GetID()), sitk.sitkInt16)
        matrix = vtk.vtkMatrix4x4()
        inputVolumeNode.GetRASToIJKMatrix(matrix)
        self.connectedComponentFilter.ClearSeeds()
        for iSeed in range(vesselSeedsNode.GetNumberOfFiducials()):
          posRAS = [0.0,0.0,0.0]
          vesselSeedsNode.GetNthFiducialPosition(iSeed, posRAS)
          posIJK = matrix.MultiplyFloatPoint([posRAS[0], posRAS[1], posRAS[2], 1.0])
          self.connectedComponentFilter.AddSeed([int(posIJK[0]),int(posIJK[1]),int(posIJK[2])])
        self.connectedComponentFilter.SetLower(self.vesselLowerThreshold)
        self.connectedComponentFilter.SetUpper(self.vesselUpperThreshold)
        self.connectedComponentFilter.SetConnectivity(self.connectedComponentFilter.FullConnectivity)
        connectedImage = self.connectedComponentFilter.Execute(oriImage)
        sitkUtils.PushToSlicer(connectedImage, "connectedImage", 0, True)
        imageCollection = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode", "connectedImage")
        if imageCollection:
          connectedImageNode = imageCollection.GetItemAsObject(0)
          parameters = {}
          parameters["InputVolume"] = connectedImageNode.GetID()
          parameters["Threshold"] = 0.5
          parameters["OutputGeometry"] = vesselnessModelNode.GetID()
          grayMaker = slicer.modules.grayscalemodelmaker
          slicer.cli.run(grayMaker, None, parameters, wait_for_completion=True)
  
  def calculateVenousVesselness(self,inputVolumeNode, vesselnessVolumeNode, vesselSeedsNode, outputTubeFile, vesselnessModelNode):
      parameters = {}
      parameters["inputVolume"] = inputVolumeNode.GetID()
      parameters["outputTubeFile"] = outputTubeFile
      parameters["outputTubeImage"] = vesselnessVolumeNode.GetID()
      parameters["seedP"] = vesselSeedsNode.GetID()
      parameters["scale"] = 1.0
      parameters["border"] = 6.00
      self.cliNode = slicer.cli.run(slicer.modules.segmenttubes, None, parameters, wait_for_completion=True)
      parameters = {}
      parameters["InputVolume"] = vesselnessVolumeNode.GetID()
      parameters["Threshold"] = 0.5
      parameters["OutputGeometry"] = vesselnessModelNode.GetID()
      grayMaker = slicer.modules.grayscalemodelmaker
      slicer.cli.run(grayMaker, None, parameters, wait_for_completion=True)

  def enableEventObserver(self):
    nasionNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion")
    nasionNode = slicer.mrmlScene.GetNodeByID(nasionNodeID)
    sagittalID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalPoint")
    sagittalPointNode = slicer.mrmlScene.GetNodeByID(sagittalID)
    targetNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_target")
    targetNode = slicer.mrmlScene.GetNodeByID(targetNodeID)
    distalNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_distal")
    distalNode = slicer.mrmlScene.GetNodeByID(distalNodeID)
    vesselSeedsNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselSeeds")
    vesselSeedsNode = slicer.mrmlScene.GetNodeByID(vesselSeedsNodeID)
    if nasionNode:
      nasionNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self.endPlacement)
    if sagittalPointNode:
      sagittalPointNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self.endPlacement)
    if targetNode:
      targetNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self.endPlacement)
      targetNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointModifiedEvent, self.createVentricleCylinder)
      targetNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointEndInteractionEvent, self.endModifiyCylinder)
      #targetNode.AddObserver(VentriculostomyUserEvents.TriggerDistalSelectionEvent, self.startEditPlanningDistal)
      slicer.mrmlScene.AddObserver(VentriculostomyUserEvents.TriggerDistalSelectionEvent, self.startEditPlanningDistal)
    if distalNode:
      distalNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self.endPlacement)
      distalNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointModifiedEvent, self.createVentricleCylinder)
      distalNode.AddObserver(slicer.vtkMRMLMarkupsNode().PointEndInteractionEvent, self.endModifiyCylinder)
    if vesselSeedsNode:
      vesselSeedsNode.AddObserver(slicer.vtkMRMLMarkupsNode.MarkupAddedEvent, self.endPlacement)

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def TriggerDistalSelectionEventCallback(self, caller, eventId, callData):
    self.startEditPlanningDistal()

  def enableRelatedVolume(self, attributeName, volumeName, visibility = True):
    enabledAttributeID = self.baseVolumeNode.GetAttribute(attributeName)
    volumeNode = None
    if enabledAttributeID and slicer.mrmlScene.GetNodeByID(enabledAttributeID):
      volumeNode = slicer.mrmlScene.GetNodeByID(enabledAttributeID)
      if volumeNode and volumeNode.GetDisplayNode() and visibility:
        volumeNode.GetDisplayNode().SetVisibility(1)
    else:
      volumeNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLScalarVolumeNode")
      volumeNode.SetName(volumeName)
      slicer.mrmlScene.AddNode(volumeNode)
      #volumeDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLScalarVolumeDisplayNode")
      #slicer.mrmlScene.AddNode(volumeDisplayNode)
      #volumeNode.SetAndObserveDisplayNodeID(volumeDisplayNode.GetID())
      self.baseVolumeNode.SetAttribute(attributeName, volumeNode.GetID())
    return volumeNode

  def enableRelatedModel(self, attributeName, modelName, color = [0.0, 0.0, 1.0], visibility = True, intersectionVis=True):
    enabledAttributeID = self.baseVolumeNode.GetAttribute(attributeName)
    modelNode = None
    if enabledAttributeID and slicer.mrmlScene.GetNodeByID(enabledAttributeID):
      modelNode = slicer.mrmlScene.GetNodeByID(enabledAttributeID)
      modelNode.SetAttribute("vtkMRMLModelNode.modelCreated", "True")
    else:
      modelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
      modelNode.SetAttribute("vtkMRMLModelNode.modelCreated", "False")
      modelNode.SetName(modelName)
      slicer.mrmlScene.AddNode(modelNode)
      modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
      modelDisplayNode.SetColor(color)
      modelDisplayNode.SetOpacity(0.5)
      slicer.mrmlScene.AddNode(modelDisplayNode)
      modelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
      self.baseVolumeNode.SetAttribute(attributeName, modelNode.GetID())
    if modelNode and modelNode.GetDisplayNode():
      modelNode.GetDisplayNode().SetVisibility(visibility)
      modelNode.GetDisplayNode().SetSliceIntersectionVisibility(intersectionVis)
    return modelNode

  def enableRelatedMarkups(self, attributeName, markupsName, color = [1.0, 0.0, 0.0], visibility = True):
    enabledAttributeID = self.baseVolumeNode.GetAttribute(attributeName)
    markupsNode = None
    if enabledAttributeID and slicer.mrmlScene.GetNodeByID(enabledAttributeID):
      markupsNode = slicer.mrmlScene.GetNodeByID(enabledAttributeID)
      if markupsNode and markupsNode.GetDisplayNode() and visibility:
        markupsNode.GetDisplayNode().SetVisibility(1)
    else:
      markupsNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
      markupsNode.SetName(markupsName)
      slicer.mrmlScene.AddNode(markupsNode)
      markupsDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsDisplayNode")
      markupsDisplayNode.SetColor(color)
      slicer.mrmlScene.AddNode(markupsDisplayNode)
      markupsNode.SetAndObserveDisplayNodeID(markupsDisplayNode.GetID())
      self.baseVolumeNode.SetAttribute(attributeName, markupsNode.GetID())
    return markupsNode


  def enableRelatedVariables(self, attributeName, fieldName):
    enabledAttributeID = self.baseVolumeNode.GetAttribute(attributeName)
    fieldvalue = -1
    if enabledAttributeID:
      fieldvalue = float(self.baseVolumeNode.GetAttribute(attributeName))
      setattr(self, fieldName, fieldvalue)
    else:
      fieldvalue = getattr(self, fieldName)
      self.baseVolumeNode.SetAttribute(attributeName, str(fieldvalue))
    return fieldvalue

    
  def updateMeasureLength(self, sagittalReferenceLength=None, coronalReferenceLength=None):
    if not self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength"):
      if sagittalReferenceLength:
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength", '%.1f' % sagittalReferenceLength)      
    if not self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength"):    
      if coronalReferenceLength:
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength", '%.1f' % coronalReferenceLength)


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
    inputVesselMarginModelNodeID =  self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessWithMarginModel")
    nasionNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion")
    if inputVesselMarginModelNodeID and nasionNodeID:
      inputModelNode = slicer.mrmlScene.GetNodeByID(inputVesselMarginModelNodeID)
      polyData = inputModelNode.GetPolyData()
      nasionNode = slicer.mrmlScene.GetNodeByID(nasionNodeID)
      posNasion = numpy.array([0.0, 0.0, 0.0])
      nasionNode.GetNthFiducialPosition(0, posNasion)
      for index in range(1, self.trajectoryProjectedMarker.GetNumberOfFiducials()):
        self.trajectoryProjectedMarker.RemoveMarkup(index)
      self.calculateLineModelIntersect(polyData, posEntry, posTarget, self.trajectoryProjectedMarker)
      if self.trajectoryProjectedMarker.GetNumberOfFiducials()>1: # The intersection is not only the projected skull point
        slicer.util.warningDisplay("Within the margin area of the vessel")
      if abs(posEntry[2] - posNasion[2]) < self.posteriorMargin:
        slicer.util.warningDisplay("Entry point is too close to nasion point")
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
      slicer.mrmlScene.InvokeEvent(VentriculostomyUserEvents.TriggerDistalSelectionEvent)
    elif self.interactionMode == "distal":
      if self.trajectoryProjectedMarker and self.trajectoryProjectedMarker.GetMarkupsDisplayNode():
        self.trajectoryProjectedMarker.GetMarkupsDisplayNode().SetVisibility(1)
      self.createVentricleCylinder()
      self.endVentricleCylinderDefinition()
      self.endModifiyCylinder()
      self.update_observers(VentriculostomyUserEvents.ResetButtonEvent)
    self.update_observers(VentriculostomyUserEvents.SaveModifiedFiducialEvent)
    pass

  def selectNasionPointNode(self, modelNode, initPoint = None):
    if self.baseVolumeNode:
      nasionNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion")
      kocherNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_kocher")
      if nasionNodeID and kocherNodeID:
        nasionNode = slicer.mrmlScene.GetNodeByID(nasionNodeID)
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
        self.update_observers(VentriculostomyUserEvents.VentricleCylinderModified)
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
          if numpy.linalg.norm(posDistal - posTarget) < (self.minimalVentricleLen * 0.999):
            slicer.util.warningDisplay(
              "The define ventricle horn is too short, distal point is automatically modified to make length longer than 10.0 mm")
            posDistalNew = (posDistal - posTarget) / numpy.linalg.norm(
              posDistal - posTarget) * self.minimalVentricleLen + posTarget
            distalNode.SetNthFiducialPositionFromArray(0, posDistalNew)
            posDistal = posDistalNew
            self.ReleaseLeftButton()
            self.interactionMode = "none"
          if self.cylinderManager.curveFiducials.GetNumberOfFiducials():
            self.cylinderManager.curveFiducials.RemoveAllMarkups()
          self.cylinderManager.curveFiducials.AddFiducial(posTarget[0], posTarget[1], posTarget[2])
          self.cylinderManager.curveFiducials.AddFiducial(posDistal[0], posDistal[1], posDistal[2])
          self.cylinderManager.curveFiducials.SetDisplayVisibility(0)
          self.cylinderManager.setManagerTubeRadius(radius)
          self.cylinderManager.startEditLine()
          self.cylinderManager.onLineSourceUpdated()
          self.updateSliceViewBasedOnPoints(posTarget, posDistal)
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
    inputModelNodeID =  self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_model")
    inputModelNode = slicer.mrmlScene.GetNodeByID(inputModelNodeID)
    nasionNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion")
    nasionNode = slicer.mrmlScene.GetNodeByID(nasionNodeID)
    kocherNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_kocher")
    kocherNode = slicer.mrmlScene.GetNodeByID(kocherNodeID)
    kocherNode.RemoveAllMarkups()
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
          posEntry = [0.0, 0.0, 0.0]
          self.coronalReferenceCurveManager.getLastPoint(posEntry)
          kocherNode.AddFiducial(posEntry[0], posEntry[1], posEntry[2])
    self.lockReferenceLine()
    nasionNode.SetLocked(True)
    kocherNode.SetLocked(True)
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
              if not self.pathNavigationModel.GetPolyData():
                polyData = vtk.vtkPolyData()
                self.pathNavigationModel.SetAndObservePolyData(polyData)
              self.makeNavigationLines(pathNavigationPoints, 3, self.pathNavigationModel.GetPolyData())
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
    matrixGreenOri.DeepCopy(matrixRedOri)
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
