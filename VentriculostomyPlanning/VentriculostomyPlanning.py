import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from ctk import ctkAxesWidget
import logging
import tempfile
import CurveMaker
import numpy
import SimpleITK as sitk
import sitkUtils
import SlicerCaseManager

#
# VentriculostomyPlanning
#

class VentriculostomyPlanning(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "VentriculostomyPlanning" # TODO make this more human readable by adding spaces
    self.parent.categories = ["IGT"]
    self.parent.dependencies = ["SlicerCaseManager"]
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
        
    # Instantiate and connect widgets ...
    #
    # Lines Area
    #
    configurationCollapsibleButton = ctk.ctkCollapsibleButton()
    configurationCollapsibleButton.text = "Configuration"
    self.layout.addWidget(configurationCollapsibleButton)
    # Layout within the dummy collapsible button
    configurationFormLayout = qt.QFormLayout(configurationCollapsibleButton)
    #
    # Mid-sagittalReference line
    #
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
    configurationFormLayout.addRow(referenceConfigLayout)
    
    #configurationFormLayout.addRow()
    self.lengthSagittalReferenceLineEdit.connect('textEdited(QString)', self.onModifyMeasureLength)
    self.lengthCoronalReferenceLineEdit.connect('textEdited(QString)', self.onModifyMeasureLength)
    
    
    # PatientModel Area
    #
    referenceCollapsibleButton = ctk.ctkCollapsibleButton()
    referenceCollapsibleButton.text = "Reference Generating "
    self.layout.addWidget(referenceCollapsibleButton)
    
    # Layout within the dummy collapsible button
    referenceFormLayout = qt.QFormLayout(referenceCollapsibleButton)
    
    
    CaseManagerConfigLayout = qt.QVBoxLayout()
    slicerCaseWidgetParent = slicer.qMRMLWidget()
    slicerCaseWidgetParent.setLayout(qt.QVBoxLayout())
    slicerCaseWidgetParent.setMRMLScene(slicer.mrmlScene)
    self.slicerCaseWidget = SlicerCaseManager.SlicerCaseManagerWidget(slicerCaseWidgetParent)
    self.slicerCaseWidget.setup()
    #CaseManagerConfigLayout.addWidget(self.slicerCaseWidget.collapsibleDirectoryConfigurationArea)
    #CaseManagerConfigLayout.addWidget(self.slicerCaseWidget.mainGUIGroupBox)


    referenceFormLayout.addRow(CaseManagerConfigLayout)
    #
    # input volume selector
    #
    volumeModelLayout = qt.QHBoxLayout()
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
    self.inputVolumeSelector.sortFilterProxyModel().setFilterRegExp("^((?!NotShownEntity31415).)*$" )    
    volumeModelLayout.addWidget(self.inputVolumeSelector)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.inputVolumeSelector.connect("nodeAdded(vtkMRMLNode*)", self.onAddedNode)
    #
    # output volume selector
    #
    '''
    self.outputModelSelector = slicer.qMRMLNodeComboBox()
    self.outputModelSelector.nodeTypes = ["vtkMRMLModelNode"]
    self.outputModelSelector.selectNodeUponCreation = True
    self.outputModelSelector.addEnabled = True
    self.outputModelSelector.removeEnabled = True
    self.outputModelSelector.noneEnabled = True
    self.outputModelSelector.showHidden = False
    self.outputModelSelector.showChildNodeTypes = False
    self.outputModelSelector.setMRMLScene( slicer.mrmlScene )
    self.outputModelSelector.setToolTip( "Pick the output to the algorithm." )
    self.outputModelSelector.sortFilterProxyModel().setFilterRegExp("^\\b(Model)" )    
    '''
    #
    # Create Model Button
    #
    referenceFormLayout.addRow("Input Volume:", volumeModelLayout)
    
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
    referenceFormLayout.addRow("ROI definition for cropping Volume:",None)
    referenceFormLayout.addRow(ROIConfigLayout)
    
    #
    # Create Entry point Button
    #
    automaticEntryHorizontalLayout = qt.QHBoxLayout()
    
    self.createModelButton = qt.QPushButton("Create Model")
    self.createModelButton.toolTip = "Create a surface model."
    self.createModelButton.enabled = True
    self.createModelButton.connect('clicked(bool)', self.onCreateModel)    
    
    automaticEntryHorizontalLayout.addWidget(self.createModelButton)
    self.selectNasionButton = qt.QPushButton("Select Nasion")
    self.selectNasionButton.toolTip = "Add a point in the 3D window"
    self.selectNasionButton.enabled = True
    automaticEntryHorizontalLayout.addWidget(self.selectNasionButton)
    self.createEntryPointButton = qt.QPushButton("Create Entry Point")
    self.createEntryPointButton.toolTip = "Create the initial entry point."
    self.createEntryPointButton.enabled = True
    automaticEntryHorizontalLayout.addWidget(self.createEntryPointButton)
    referenceFormLayout.addRow("Automatic Entry Point: ", automaticEntryHorizontalLayout)
    
    self.selectNasionButton.connect('clicked(bool)', self.onSelectNasionPointNode)
    self.createEntryPointButton.connect('clicked(bool)', self.onCreateEntryPoint)
    
    
    #
    # Venous Segmentation/Rendering
    #
    VenousCollapsibleButton = ctk.ctkCollapsibleButton()
    VenousCollapsibleButton.text = "Venous Segmentation"
    self.layout.addWidget(VenousCollapsibleButton)
    
    # Layout within the dummy collapsible button
    VenousFormLayout = qt.QFormLayout(VenousCollapsibleButton)
    
    createVesselHorizontalLayout = qt.QHBoxLayout()
    self.venousCalcStatus = qt.QLabel('VenousCalcStatus')
    self.grayScaleMakerButton = qt.QPushButton("GrayScaleCalc")
    self.grayScaleMakerButton.enabled = True
    self.grayScaleMakerButton.toolTip = "Use the GrayScaleMaker module for vessel calculation "
    self.grayScaleMakerButton.connect('clicked(bool)', self.onVenousGrayScaleCalc)
    createVesselHorizontalLayout.addWidget(self.venousCalcStatus)
    createVesselHorizontalLayout.addWidget(self.grayScaleMakerButton)
    self.vesselnessCalcButton = qt.QPushButton("VesselnessCalc")
    self.vesselnessCalcButton.toolTip = "Use Vesselness calculation "
    self.vesselnessCalcButton.enabled = True
    self.vesselnessCalcButton.connect('clicked(bool)', self.onVenousVesselnessCalc)
    #createVesselHorizontalLayout.addWidget(self.vesselnessCalcButton)
    VenousFormLayout.addRow("Create venous model: ",None)
    VenousFormLayout.addRow(createVesselHorizontalLayout)
    
    #
    # Trajectory
    #
    planningCollapsibleButton = ctk.ctkCollapsibleButton()
    planningCollapsibleButton.text = "Planning"
    self.layout.addWidget(planningCollapsibleButton)
    
    # Layout within the dummy collapsible button
    planningFormLayout = qt.QFormLayout(planningCollapsibleButton)
    
    #
    # Trajectory
    #
    trajectoryLayout = qt.QHBoxLayout()

    #-- Add Point
    self.addCannulaPointButton = qt.QPushButton("Add Cannula Points")
    self.addCannulaPointButton.toolTip = "Add Cannula Points"
    self.addCannulaPointButton.enabled = True
    trajectoryLayout.addWidget(self.addCannulaPointButton)

    #-- Curve length
    self.lengthTrajectoryEdit = qt.QLineEdit()
    self.lengthTrajectoryEdit.text = '--'
    self.lengthTrajectoryEdit.readOnly = True
    self.lengthTrajectoryEdit.frame = True
    self.lengthTrajectoryEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthTrajectoryEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    trajectoryLayout.addWidget(self.lengthTrajectoryEdit)
    lengthTrajectoryUnitLabel = qt.QLabel('mm  ')
    trajectoryLayout.addWidget(lengthTrajectoryUnitLabel)


    #-- Clear Point
    self.clearTrajectoryButton = qt.QPushButton("Clear")
    self.clearTrajectoryButton.toolTip = "Remove Trajectory"
    self.clearTrajectoryButton.enabled = True
    trajectoryLayout.addWidget(self.clearTrajectoryButton)
    planningFormLayout.addRow(trajectoryLayout)
    
    createPlanningLineHorizontalLayout = qt.QHBoxLayout()
    self.lockTrajectoryCheckBox = qt.QCheckBox()
    self.lockTrajectoryCheckBox.checked = 0
    self.lockTrajectoryCheckBox.setToolTip("If checked, the trajectory will be locked.")
    createPlanningLineHorizontalLayout.addWidget(self.lockTrajectoryCheckBox)
    self.createPlanningLineButton = qt.QPushButton("Create Planning Line")
    self.createPlanningLineButton.toolTip = "Create the planning line."
    self.createPlanningLineButton.enabled = True
    createPlanningLineHorizontalLayout.addWidget(self.createPlanningLineButton)
    self.setReverseViewButton = qt.QPushButton("Set Reverse View")
    self.setReverseViewButton.toolTip = "Change the perspective view in 3D viewer."
    self.setReverseViewButton.enabled = True
    createPlanningLineHorizontalLayout.addWidget(self.setReverseViewButton)
    self.createPlanningLineButton.connect('clicked(bool)', self.onCreatePlanningLine)
    self.setReverseViewButton.connect('clicked(bool)', self.onSetReverseView)
    self.isReverseView = False
    planningFormLayout.addRow("Lock:", createPlanningLineHorizontalLayout)

     # Needle trajectory
    self.addCannulaPointButton.connect('clicked(bool)', self.onEditCannula)
    self.clearTrajectoryButton.connect('clicked(bool)', self.onClearTrajectory)
    self.logic.setTrajectoryModifiedEventHandler(self.onTrajectoryModified)
    self.lockTrajectoryCheckBox.connect('toggled(bool)', self.onLock)
    

    #
    # Mid-sagittalReference line
    #
    planningLineLayout = qt.QHBoxLayout()

    #-- Curve length
    lengthSagittalPlanningLineLabel = qt.QLabel('Sagittal Length:  ')
    planningLineLayout.addWidget(lengthSagittalPlanningLineLabel)
    self.lengthSagittalPlanningLineEdit = qt.QLineEdit()
    self.lengthSagittalPlanningLineEdit.text = '--'
    self.lengthSagittalPlanningLineEdit.readOnly = True
    self.lengthSagittalPlanningLineEdit.frame = True
    self.lengthSagittalPlanningLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthSagittalPlanningLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningLineLayout.addWidget(self.lengthSagittalPlanningLineEdit)
    lengthSagittalPlanningLineUnitLabel = qt.QLabel('mm  ')
    planningLineLayout.addWidget(lengthSagittalPlanningLineUnitLabel)
    
    lengthCoronalPlanningLineLabel = qt.QLabel('Coronal Length:  ')
    planningLineLayout.addWidget(lengthCoronalPlanningLineLabel)
    self.lengthCoronalPlanningLineEdit = qt.QLineEdit()
    self.lengthCoronalPlanningLineEdit.text = '--'
    self.lengthCoronalPlanningLineEdit.readOnly = True
    self.lengthCoronalPlanningLineEdit.frame = True
    self.lengthCoronalPlanningLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthCoronalPlanningLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningLineLayout.addWidget(self.lengthCoronalPlanningLineEdit)
    lengthCoronalPlanningLineUnitLabel = qt.QLabel('mm  ')
    planningLineLayout.addWidget(lengthCoronalPlanningLineUnitLabel)
    planningFormLayout.addRow(planningLineLayout)
    
    planningAnglesLayout = qt.QHBoxLayout()
    #-- Curve length
    pitchAngleLabel = qt.QLabel('Pitch Angle:  ') 
    planningAnglesLayout.addWidget(pitchAngleLabel)
    self.pitchAngleEdit = qt.QLineEdit()
    self.pitchAngleEdit.text = '--'
    self.pitchAngleEdit.readOnly = True
    self.pitchAngleEdit.frame = True
    self.pitchAngleEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.pitchAngleEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningAnglesLayout.addWidget(self.pitchAngleEdit)
    pitchAngleUnitLabel = qt.QLabel('degree  ')
    planningAnglesLayout.addWidget(pitchAngleUnitLabel)
    
    yawAngleLabel = qt.QLabel('Yaw Angle:  ') 
    planningAnglesLayout.addWidget(yawAngleLabel)
    self.yawAngleEdit = qt.QLineEdit()
    self.yawAngleEdit.text = '--'
    self.yawAngleEdit.readOnly = True
    self.yawAngleEdit.frame = True
    self.yawAngleEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.yawAngleEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    planningAnglesLayout.addWidget(self.yawAngleEdit)
    yawAngleUnitLabel = qt.QLabel('degree  ')
    planningAnglesLayout.addWidget(yawAngleUnitLabel)
    planningFormLayout.addRow(planningAnglesLayout)
    
    #end of GUI section
    #####################################

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect(self.inputVolumeSelector.currentNode())

  def cleanup(self):
    pass
  
  def initialFieldsValue(self):
    self.lengthSagittalPlanningLineEdit.text = '--'
    self.lengthCoronalPlanningLineEdit.text = '--'
    self.lengthTrajectoryEdit.text = '--'
    self.logic.clearSagittalPlanningLine()
    self.logic.clearCoronalPlanningLine()
    self.logic.clearSagittalReferenceLine()
    self.logic.clearCoronalReferenceLine()
  
  def onAddedNode(self, addedNode):
    if addedNode:
      self.inputVolumeSelector.setCurrentNode(addedNode)
      
  def onSelect(self, selectedNode=None):
    if selectedNode:        
      self.initialFieldsValue()
      self.logic.baseVolumeNode = selectedNode
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_model")
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_nasion")
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_trajectory")
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel")
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_vesselnessVolume")
      #Set the cropped image for processing
      if selectedNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume"):
        self.logic.currentVolumeNode = slicer.mrmlScene.GetNodeByID(selectedNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume"))
      else:
        self.logic.currentVolumeNode = selectedNode  
      self.logic.updateMeasureLength(float(self.lengthSagittalReferenceLineEdit.text), float(self.lengthCoronalReferenceLineEdit.text))
      self.lengthSagittalReferenceLineEdit.text = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength")
      self.lengthCoronalReferenceLineEdit.text = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength")
      self.logic.createEntryPoint()
      curveFiducialsID = self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_trajectory")
      self.logic.trajectoryManager.curveFiducials = slicer.mrmlScene.GetNodeByID(curveFiducialsID)
      self.logic.trajectoryManager.startEditLine()
      self.onCreatePlanningLine()
      self.onSetSliceViewer()
      
      layoutManager = slicer.app.layoutManager()
      threeDView = layoutManager.threeDWidget(0).threeDView()
      threeDView.lookFromViewAxis(ctkAxesWidget.Anterior)
          
    pass
  
  def onSetSliceViewer(self):
    red_widget = slicer.app.layoutManager().sliceWidget("Red")
    red_logic = red_widget.sliceLogic()
    red_cn = red_logic.GetSliceCompositeNode()
    yellow_widget = slicer.app.layoutManager().sliceWidget("Yellow")
    yellow_logic = yellow_widget.sliceLogic()
    yellow_cn = yellow_logic.GetSliceCompositeNode()
    green_widget = slicer.app.layoutManager().sliceWidget("Green")
    green_logic = green_widget.sliceLogic()
    green_cn = green_logic.GetSliceCompositeNode()
    if self.logic.currentVolumeNode:
      red_cn.SetBackgroundVolumeID(self.logic.currentVolumeNode.GetID()) 
      red_widget.fitSliceToBackground()
      yellow_cn.SetBackgroundVolumeID(self.logic.currentVolumeNode.GetID())  
      yellow_widget.fitSliceToBackground()
      green_cn.SetBackgroundVolumeID(self.logic.currentVolumeNode.GetID())   
      green_widget.fitSliceToBackground()
    pass
    
  def onCreatePlanningLine(self):
    self.logic.createPlanningLine()  
    self.lengthSagittalPlanningLineEdit.text = '%.1f' % self.logic.getSagittalPlanningLineLength()
    self.lengthCoronalPlanningLineEdit.text = '%.1f' % self.logic.getCoronalPlanningLineLength()
    if self.logic.baseVolumeNode:
      trajectoryNode = slicer.mrmlScene.GetNodeByID(self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_trajectory"))
      trajectoryNode.AddObserver(trajectoryNode.PointStartInteractionEvent, self.onResetPlanningOutput)
    pass

  @vtk.calldata_type(vtk.VTK_INT)
  def onResetPlanningOutput(self, node, eventID, callData):
    self.lengthSagittalPlanningLineEdit.text = '--'
    self.lengthCoronalPlanningLineEdit.text = '--'
    self.pitchAngleEdit.text = '--'
    self.yawAngleEdit.text = '--'

  def onSetReverseView(self):
    if self.isReverseView == False:
      self.logic.calcPitchYawAngles()
      self.pitchAngleEdit.text = '%.1f' % self.logic.pitchAngle
      self.yawAngleEdit.text = '%.1f' % (-self.logic.yawAngle)
      self.setReverseViewButton.setText("Reset View")
      self.isReverseView = True
    else:
      layoutManager = slicer.app.layoutManager()
      threeDView = layoutManager.threeDWidget(0).threeDView()
      threeDView.lookFromViewAxis(ctkAxesWidget.Anterior)
      self.setReverseViewButton.setText("Set Reverse View")
      self.isReverseView = False
    pass
    
  def onCreateModel(self):
    if self.inputVolumeSelector.currentNode():
      outputModelNodeID = self.inputVolumeSelector.currentNode().GetAttribute("vtkMRMLScalarVolumeNode.rel_model") 
      if outputModelNodeID:
        outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
        outputModelNode.SetAttribute("vtkMRMLModelNode.modelCreated","False")
        self.inputVolumeSelector.disconnect("nodeAdded(vtkMRMLNode*)")
        self.logic.createModel(outputModelNode, self.logic.threshold)
        self.inputVolumeSelector.connect("nodeAdded(vtkMRMLNode*)", self.onAddedNode)
  
  def onSelectNasionPointNode(self):
    outputModelNodeID = self.inputVolumeSelector.currentNode().GetAttribute("vtkMRMLScalarVolumeNode.rel_model") 
    if outputModelNodeID:
      outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
      self.inputVolumeSelector.disconnect("nodeAdded(vtkMRMLNode*)")
      self.logic.selectNasionPointNode(outputModelNode) # when the model is not available, the model will be created, so nodeAdded signal should be disconnected
      self.inputVolumeSelector.connect("nodeAdded(vtkMRMLNode*)", self.onAddedNode)
  
  def onDefineROI(self):
    self.logic.currentVolumeNode = self.logic.baseVolumeNode
    self.onSetSliceViewer()
    self.logic.defineROI()
  
  def onCreateROI(self):
    self.inputVolumeSelector.disconnect("nodeAdded(vtkMRMLNode*)")
    self.logic.createROI()
    self.inputVolumeSelector.connect("nodeAdded(vtkMRMLNode*)", self.onAddedNode)
    self.onSetSliceViewer()
      
  def onModifyMeasureLength(self):
    sagittalReferenceLength = float(self.lengthSagittalReferenceLineEdit.text)
    coronalReferenceLength = float(self.lengthCoronalReferenceLineEdit.text)
    if self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength"):
        self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_sagittalLength", '%.1f' % sagittalReferenceLength) 
    if self.logic.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength"):
        self.logic.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_coronalLength", '%.1f' % coronalReferenceLength)    
    
  
  def onCreateEntryPoint(self):
    self.onModifyMeasureLength()
    self.logic.createEntryPoint()
    #self.lengthSagittalReferenceLineEdit.text = '%.2f' % self.logic.getSagittalReferenceLineLength()
    #self.lengthCoronalReferenceLineEdit.text = '%.2f' % self.logic.getCoronalReferenceLineLength()
    

  # Event handlers for sagittalReference line
  def onEditSagittalReferenceLine(self, switch):

    if switch == True:
      self.addCannulaPointButton.checked = False
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
      self.addCannulaPointButton.checked = False
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
    self.inputVolumeSelector.disconnect("nodeAdded(vtkMRMLNode*)")
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
    self.inputVolumeSelector.connect("nodeAdded(vtkMRMLNode*)", self.onAddedNode)    
    pass
  
  def onVenousVesselnessCalc(self):
    self.inputVolumeSelector.disconnect("nodeAdded(vtkMRMLNode*)")
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
    self.inputVolumeSelector.connect("nodeAdded(vtkMRMLNode*)", self.onAddedNode)    
    pass
  
  def onCalculateVenousCompletion(self,node,event):
    status = node.GetStatusString()
    self.venousCalcStatus.setText(node.GetName() +' '+status)
    if status == 'Completed':
      self.vesselnessCalcButton.setEnabled(1)
      self.grayScaleMakerButton.setEnabled(1)
      self.onSelect(self.logic.baseVolumeNode) ## the slice widgets are set to none after the  cli module calculation. reason unclear...
    pass
  
  # Event handlers for trajectory
  def onEditCannula(self):
    self.logic.startEditCannula()
    
  def onClearTrajectory(self):
    self.logic.clearTrajectory()
    
  def onTrajectoryModified(self, caller, event):
    self.lengthTrajectoryEdit.text = '%.2f' % self.logic.getTrajectoryLength()

  # Event handlers for sagittalPlanning line
  def onEditSagittalPlanningLine(self, switch):

    if switch == True:
      self.addCannulaPointButton.checked = False
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
      self.addCannulaPointButton.checked = False
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
      self.addCannulaPointButton.enabled = False
      self.clearTrajectoryButton.enabled = False
      self.logic.lockTrajectoryLine()
    else:
      self.addCannulaPointButton.enabled = True
      self.clearTrajectoryButton.enabled = True
      self.logic.unlockTrajectoryLine()

  def onReload(self,moduleName="VentriculostomyPlanning"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    slicer.mrmlScene.Clear(0)
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)
    
class CurveManager:
  
  def __init__(self):
    try:
      import CurveMaker
    except ImportError:
      return slicer.util.warningDisplay(
            "Error: Could not find extension CurveMaker. Open Slicer Extension Manager and install "
       "CurveMaker.", "Missing Extension")
    self.cmLogic = CurveMaker.CurveMakerLogic()
    self.curveFiducials = None
    self.curveModel = None

    self.curveName = ""
    self.curveModelName = ""
    self.step = 1;
    self.tagEventExternal = None

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
    if self.curveModel:
      dnode = self.curveModel.GetDisplayNode()
      if dnode:
        dnode.SetColor([r, g, b])

    if self.curveFiducials:
      dnode = self.curveFiducials.GetMarkupsDisplayNode()
      if dnode:
        dnode.SetSelectedColor([r, g, b])
      
  def setModifiedEventHandler(self, handler):

    self.externalHandler = handler
    
    if self.curveModel:
      self.tagEventExternal = self.curveModel.AddObserver(vtk.vtkCommand.ModifiedEvent, self.externalHandler)
      return self.tagEventExternal
    else:
      return None

  def resetModifiedEventHandle(self):
    
    if self.curveModel and self.tagEventExternal:
      self.curveModel.RemoveObserver(self.tagEventExternal)

    self.externalHandler = None
    self.tagEventExternal = None

  def onLineSourceUpdated(self,caller,event):
    
    self.cmLogic.updateCurve()

    # Make slice intersetion visible
    if self.curveModel:
      dnode = self.curveModel.GetDisplayNode()
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
      
    if self.curveModel == None:
      self.curveModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
      self.curveModel.SetName(self.curveModelName)
      slicer.mrmlScene.AddNode(self.curveModel)

    # Set exetrnal handler, if it has not been.
    if self.tagEventExternal == None and self.externalHandler:
      self.tagEventExternal = self.curveModel.AddObserver(vtk.vtkCommand.ModifiedEvent, self.externalHandler)
      
    self.cmLogic.DestinationNode = self.curveModel
    self.cmLogic.SourceNode = self.curveFiducials
    self.cmLogic.SourceNode.SetAttribute('CurveMaker.CurveModel', self.cmLogic.DestinationNode.GetID())
    self.cmLogic.updateCurve()

    self.cmLogic.CurvePoly = vtk.vtkPolyData() ## For CurveMaker bug
    self.cmLogic.enableAutomaticUpdate(1)
    self.cmLogic.setInterpolationMethod(1)
    self.cmLogic.setTubeRadius(1.0)

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

    if self.curveModel:
      pdata = self.curveModel.GetPolyData()
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
    self.sagittalReferenceCurveManager.curveModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
    self.sagittalReferenceCurveManager.curveModel.SetName(self.sagittalReferenceCurveManager.curveModelName)
    slicer.mrmlScene.AddNode(self.sagittalReferenceCurveManager.curveModel)
    self.sagittalReferenceCurveManager.setModelColor(1.0, 1.0, 0.5)
    
    self.coronalReferenceCurveManager = CurveManager()
    self.coronalReferenceCurveManager.setName("CR1")
    self.coronalReferenceCurveManager.setSliceID("vtkMRMLSliceNodeGreen")
    self.coronalReferenceCurveManager.setDefaultSlicePositionToLastPoint()
    self.coronalReferenceCurveManager.curveModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
    self.coronalReferenceCurveManager.curveModel.SetName(self.coronalReferenceCurveManager.curveModelName)
    slicer.mrmlScene.AddNode(self.coronalReferenceCurveManager.curveModel)
    self.coronalReferenceCurveManager.setModelColor(0.5, 1.0, 0.5)
    
    self.trajectoryManager = CurveManager()
    self.trajectoryManager.setName("T")
    self.trajectoryManager.setDefaultSlicePositionToLastPoint()
    self.trajectoryManager.setModelColor(0.0, 1.0, 1.0)
    self.trajectoryManager.setDefaultSlicePositionToFirstPoint()

    self.coronalPlanningCurveManager = CurveManager()
    self.coronalPlanningCurveManager.setName("CP1")
    self.coronalPlanningCurveManager.setSliceID("vtkMRMLSliceNodeGreen")
    self.coronalPlanningCurveManager.setDefaultSlicePositionToLastPoint()
    self.coronalPlanningCurveManager.curveModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
    self.coronalPlanningCurveManager.curveModel.SetName(self.coronalPlanningCurveManager.curveModelName)
    slicer.mrmlScene.AddNode(self.coronalPlanningCurveManager.curveModel)
    self.coronalPlanningCurveManager.setModelColor(0.0, 1.0, 0.0)

    self.sagittalPlanningCurveManager = CurveManager()
    self.sagittalPlanningCurveManager.setName("SP1")
    self.sagittalPlanningCurveManager.setSliceID("vtkMRMLSliceNodeYellow")
    self.sagittalPlanningCurveManager.setDefaultSlicePositionToFirstPoint()
    self.sagittalPlanningCurveManager.curveModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
    self.sagittalPlanningCurveManager.curveModel.SetName(self.sagittalPlanningCurveManager.curveModelName)
    slicer.mrmlScene.AddNode(self.sagittalPlanningCurveManager.curveModel)
    self.sagittalPlanningCurveManager.setModelColor(1.0, 1.0, 0.0)
    
    self.ROIListNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLAnnotationHierarchyNode")
    self.ROIListNode.SetName("ROIListForAllCases")
    self.ROIListNode.HideFromEditorsOff()
    slicer.mrmlScene.AddNode(self.ROIListNode)
    self.currentVolumeNode = None
    self.baseVolumeNode = None
    self.cliNode = None
    self.samplingFactor = 1
    self.topPoint = []
    self.resetROI = False 
    self.threshold = -500.0
    self.yawAngle = 0
    self.pitchAngle = 0
    self.activeTrajectoryMarkup = 0
    self.trajectoryProjectedMarker = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    self.trajectoryProjectedMarker.SetName("trajectoryProject")
    slicer.mrmlScene.AddNode(self.trajectoryProjectedMarker)
    self.nasionProjectedMarker = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    self.nasionProjectedMarker.SetName("nasionProject")
    slicer.mrmlScene.AddNode(self.nasionProjectedMarker)
    
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

  def startEditCannula(self):
    if self.baseVolumeNode:
      nasionID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion")
      nasionNode = slicer.mrmlScene.GetNodeByID(nasionID)
      if nasionNode.GetNumberOfFiducials()>0:
        trajectoryNode = slicer.mrmlScene.GetNodeByID(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_trajectory"))
        slicer.mrmlScene.AddNode(trajectoryNode)
        dnode = trajectoryNode.GetMarkupsDisplayNode()
        if dnode:
          rgbColor = [0.0, 1.0, 1.0]
          dnode.SetSelectedColor(rgbColor)
          dnode.SetVisibility(1)
        self.trajectoryManager.curveFiducials = trajectoryNode  
        self.trajectoryProjectedMarker.RemoveAllMarkups()
        dnode = self.trajectoryProjectedMarker.GetMarkupsDisplayNode()
        if dnode:
          rgbColor = [1.0, 0.0, 1.0]
          dnode.SetSelectedColor(rgbColor)
          dnode.SetVisibility(0)
          dnode.SetGlyphScale(2.5)
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if (selectionNode == None) or (interactionNode == None):
          return
        
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode");
        selectionNode.SetActivePlaceNodeID(trajectoryNode.GetID())
    
        interactionNode.SwitchToSinglePlaceMode ()
        interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place) 
        trajectoryNode.AddObserver(trajectoryNode.PointStartInteractionEvent, self.updateSelectedMarker)
        trajectoryNode.AddObserver(trajectoryNode.PointModifiedEvent, self.updateTrajectoryPosition)
        trajectoryNode.AddObserver(trajectoryNode.PointEndInteractionEvent, self.endTrajectoryInteraction)
        interactionNode.SetAttribute("vtkMRMLInteractionNode.rel_marker", "trajectory")
        interactionNode.AddObserver(interactionNode.EndPlacementEvent, self.endPlacement) 
        
        pos = [0.0] * 3
        if trajectoryNode.GetNumberOfMarkups () > 0:
          pos = None
        else:  
          self.coronalReferenceCurveManager.getLastPoint(pos)    
        self.trajectoryManager.startEditLine(pos)
  
  def endEditTrajectory(self):
    self.trajectoryManager.endEditLine()

  def clearTrajectory(self):
    self.trajectoryManager.clearLine()

  def setTrajectoryModifiedEventHandler(self, handler):
    self.trajectoryManager.setModifiedEventHandler(handler)

  def getTrajectoryLength(self):
    return self.trajectoryManager.getLength()

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
        pthreshold.ThresholdBetween(1, 1); ## Label 1
        pthreshold.ReleaseDataFlagOn();
    
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
          reverser.ReverseNormalsOn();
          reverser.ReleaseDataFlagOn();
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
      zKernel.SetNumberOfTuples(5);
      zKernel.SetNumberOfComponents(1);
      zKernel.SetValue(0,1);
      zKernel.SetValue(1,1);
      zKernel.SetValue(2,1);
      zKernel.SetValue(3,1);
      zKernel.SetValue(4,1);
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
      
        
  def enableAttribute(self, attribute):
    enabledAttributeID = self.baseVolumeNode.GetAttribute(attribute)
    if enabledAttributeID:
      attributeNode = slicer.mrmlScene.GetNodeByID(enabledAttributeID)
      if attributeNode and attributeNode.GetDisplayNode():
        attributeNode.GetDisplayNode().SetVisibility(1)
    else:
      if attribute == "vtkMRMLScalarVolumeNode.rel_nasion":
        nasionNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        nasionNode.SetName("nasion"+self.baseVolumeNode.GetID()[-1:])
        slicer.mrmlScene.AddNode(nasionNode)
        self.baseVolumeNode.SetAttribute(attribute, nasionNode.GetID())      
      elif attribute == "vtkMRMLScalarVolumeNode.rel_trajectory":
        trajectoryNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        trajectoryNode.SetName("trajectory"+self.baseVolumeNode.GetID()[-1:])
        slicer.mrmlScene.AddNode(trajectoryNode)
        self.baseVolumeNode.SetAttribute(attribute, trajectoryNode.GetID())  
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
  
  @vtk.calldata_type(vtk.VTK_INT)
  def updateSelectedMarker(self,node, eventID, callData):
    self.activeTrajectoryMarkup = callData
    pass
  
  def updateTrajectoryPosition(self, fiducicalMarkerNode, eventID = None):
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
        if self.activeTrajectoryMarkup == 0:
          direction = numpy.array(posFirst)- numpy.array(posSecond)
          locator = vtk.vtkCellLocator()
          locator.SetDataSet(polyData)
          locator.BuildLocator()
          t = vtk.mutable(0)
          x = [0.0,0.0,0.0]
          pcoords = [0.0,0.0,0.0]
          subId = vtk.mutable(0)
          hasIntersection = locator.IntersectWithLine( posFirst + 1e6*direction, posSecond -  1e6*direction, 1e-2, t, x, pcoords, subId)
          if hasIntersection>0:
            self.trajectoryProjectedMarker.SetNthFiducialPositionFromArray(0,x)
            self.trajectoryProjectedMarker.SetNthFiducialLabel(0,"")  
          else:
            self.trajectoryProjectedMarker.SetNthFiducialLabel(0,"invalid")  
        else:
          self.trajectoryProjectedMarker.SetNthFiducialPositionFromArray(0,posFirst)
          self.trajectoryProjectedMarker.SetNthFiducialLabel(0,"")    
          self.trajectoryProjectedMarker.SetNthFiducialVisibility(0,False)
    
                
    self.updateSlicePosition(fiducicalMarkerNode,self.activeTrajectoryMarkup)
    #self.calcPitchYawAngles()
  
  def endTrajectoryInteraction(self, trajectoryNode, event=None):
    posFirst = [0.0,0.0,0.0]
    if not self.trajectoryProjectedMarker.GetNthFiducialLabel(0) == "invalid":
      self.trajectoryProjectedMarker.GetNthFiducialPosition(0,posFirst)
      posFirst[1] = posFirst[1] + 0.005
      trajectoryNode.SetNthFiducialPositionFromArray(0,posFirst)  
    self.trajectoryProjectedMarker.SetNthFiducialVisibility(0,False)
    
    # update the intersection of trajectory with venous
    posFirst = [0.0,0.0,0.0]
    trajectoryNode.GetNthFiducialPosition(0,posFirst)
    posSecond = [0.0,0.0,0.0]
    trajectoryNode.GetNthFiducialPosition(1,posSecond)
    inputVesselModelNodeID =  self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_grayScaleModel")
    if inputVesselModelNodeID:
      inputVesselModelNode = slicer.mrmlScene.GetNodeByID(inputVesselModelNodeID)   
      obbTree = vtk.vtkOBBTree()
      obbTree.SetDataSet(inputVesselModelNode.GetPolyData())  
      obbTree.BuildLocator()
      pointsVTKintersection = vtk.vtkPoints()
      hasIntersection = obbTree.IntersectWithLine(posFirst, posSecond, pointsVTKintersection, None)  
      if hasIntersection>0: 
        pointsVTKIntersectionData = pointsVTKintersection.GetData()
        noPointsVTKIntersection = pointsVTKIntersectionData.GetNumberOfTuples()
        validPosIndex = 1
        for idx in range(noPointsVTKIntersection):
          posTuple = pointsVTKIntersectionData.GetTuple3(idx)
          if ((posTuple[0]-posFirst[0])*(posSecond[0]-posFirst[0])>0) and abs(posTuple[0]-posFirst[0])<abs(posSecond[0]-posFirst[0]): 
            # check if the intersection if within the posFist and posSecond
            self.trajectoryProjectedMarker.AddFiducial(0,0,0)
            self.trajectoryProjectedMarker.SetNthFiducialPositionFromArray(validPosIndex,posTuple)
            self.trajectoryProjectedMarker.SetNthFiducialLabel(validPosIndex,"")  
            self.trajectoryProjectedMarker.SetNthFiducialVisibility(validPosIndex,True)
            validPosIndex = validPosIndex + 1
      else:
        numOfFiducial = self.trajectoryProjectedMarker.GetNumberOfFiducials()
        for idx in range(1, numOfFiducial):
          self.trajectoryProjectedMarker.SetNthFiducialLabel(idx,"invalid")  
    pass
  
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
    interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)
    if interactionNode.GetAttribute("vtkMRMLInteractionNode.rel_marker") == "nasion":
      self.createEntryPoint()
      self.nasionProjectedMarker.GetMarkupsDisplayNode().SetVisibility(0)
    if interactionNode.GetAttribute("vtkMRMLInteractionNode.rel_marker") == "trajectory":
      self.trajectoryProjectedMarker.GetMarkupsDisplayNode().SetVisibility(0)    
      ## Trigger the venous intersection computation
      trajectoryNode = slicer.mrmlScene.GetNodeByID(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_trajectory"))
      self.updateTrajectoryPosition(trajectoryNode)
      self.endTrajectoryInteraction(trajectoryNode)                                              
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
      if modelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False":
        self.createModel(modelNode,self.threshold)
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"):
        nasionNode = slicer.mrmlScene.GetNodeByID(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"))
        dnode = nasionNode.GetMarkupsDisplayNode()
        nasionNode.RemoveAllMarkups()
        slicer.mrmlScene.AddNode(nasionNode)  
        self.nasionProjectedMarker.AddFiducial(0,0,0)
        self.nasionProjectedMarker.SetNthFiducialLabel(0, "")
        dnode = self.nasionProjectedMarker.GetMarkupsDisplayNode()
        if dnode:
          rgbColor = [1.0, 0.0, 1.0]
          dnode.SetSelectedColor(rgbColor)
          dnode.SetVisibility(0)
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if (selectionNode == None) or (interactionNode == None):
          return
    
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode");
        selectionNode.SetActivePlaceNodeID(nasionNode.GetID())
        
        interactionNode.SetAttribute("vtkMRMLInteractionNode.rel_marker", "nasion")
        interactionNode.SwitchToSinglePlaceMode ()
        interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)
        interactionNode.AddObserver(interactionNode.EndPlacementEvent, self.endPlacement) 
        nasionNode.AddObserver(nasionNode.PointModifiedEvent, self.updateNasionPosition)
        nasionNode.AddObserver(nasionNode.PointEndInteractionEvent, self.endNasionInteraction)
        
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
    CurveManager.cmLogic.DestinationNode = CurveManager.curveModel
    CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2]) 
    CurveManager.cmLogic.CurvePoly = vtk.vtkPolyData() ## For CurveMaker bug
    CurveManager.cmLogic.enableAutomaticUpdate(1)
    CurveManager.cmLogic.setInterpolationMethod(1)
    CurveManager.cmLogic.setTubeRadius(1.0)
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
       
    CurveManager.cmLogic.SourceNode.SetAttribute('CurveMaker.CurveModel', CurveManager.cmLogic.DestinationNode.GetID())
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
    CurveManager.cmLogic.DestinationNode = CurveManager.curveModel
    CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2]) 
    
    numOfRef = CurveManagerReference.curveFiducials.GetNumberOfFiducials()
    
    eps = 1e-2
    if axis == 1:
      lastRefPos = [0.0]*3
      CurveManagerReference.curveFiducials.GetNthFiducialPosition(numOfRef-1, lastRefPos)  
      if abs(lastRefPos[1]-points.GetPoint(0)[1])<eps: #if the planning and reference entry points are identical 
        for jPos in range(step, points.GetNumberOfPoints(), step):
          if points.GetPoint(jPos)[0]>lastRefPos[0]:
            CurveManager.curveFiducials.AddFiducial(points.GetPoint(jPos)[0],points.GetPoint(jPos)[1],points.GetPoint(jPos)[2])
          else:
            break
        pos = [0.0]*3  
        for iPos in range(1,numOfRef): 
          CurveManagerReference.curveFiducials.GetNthFiducialPosition(numOfRef-iPos-1, pos)  
          if pos[0]<points.GetPoint(0)[0]:
            CurveManager.curveFiducials.AddFiducial(pos[0],pos[1],pos[2])
        CurveManagerReference.curveFiducials.GetNthFiducialPosition(0, pos)    
        self.topPoint = pos       
      else:   
        shift = step
        for iPos in range(1,numOfRef): 
          pos = [0.0]*3;
          CurveManagerReference.curveFiducials.GetNthFiducialPosition(numOfRef-iPos-1, pos) 
          if float(pos[0])<points.GetPoint(0)[0] and float(pos[1]-points.GetPoint(0)[1])<eps and float(pos[2]-points.GetPoint(0)[2])<eps:
            CurveManager.curveFiducials.AddFiducial(pos[0],pos[1],pos[2]) 
            shift = iPos
            break
        for iPos in range(shift,points.GetNumberOfPoints(),step):
          posModel = numpy.array(points.GetPoint(iPos))
          posModelValid = numpy.array(points.GetPoint(iPosValid))
          if  numpy.linalg.norm(posModel-posModelValid)> 50.0:
            continue
          if abs(posModel[0]-posNasion[0])<eps or (posModel[0]<posNasion[0]):
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
          if abs(posModel[0]-posNasion[0])<eps or (posModel[0]<posNasion[0]):
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
      distanceModelNasion = numpy.linalg.norm(posModel-referencePoint)
      valid = False
      if axis == 0:
        valid = posModel[2]>=referencePoint[2]
      elif axis == 1:
        valid = posModel[0]>=referencePoint[0]
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
        valid = posModel[2]<=referencePoint[2]
      elif axis == 1:
        valid = posModel[0]<=referencePoint[0]
      if valid:        
          intersectPoints.InsertNextPoint(posModel)        
  
  def createEntryPoint(self) :
    ###All calculation is based on the RAS coordinates system 
    inputModelNode = None
    nasionNode = None
    sagittalReferenceLength = None
    coronalReferenceLength = None
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
      if polyData: 
        posNasion = numpy.array([0.0,0.0,0.0])
        nasionNode.GetNthFiducialPosition(0,posNasion)
        plane = vtk.vtkPlane()
        plane.SetOrigin(posNasion[0],0,0)
        plane.SetNormal(1,0,0)
        sagittalPoints = vtk.vtkPoints()
        self.getIntersectPoints(polyData, plane, posNasion, sagittalReferenceLength, 0, sagittalPoints)
              
        ## Sorting   
        self.sortPoints(sagittalPoints, posNasion)
        self.constructCurveReference(self.sagittalReferenceCurveManager, sagittalPoints, sagittalReferenceLength)  
            
        ##To do, calculate the curvature value points by point might be necessary to exclude the outliers   
        if self.topPoint:
          posNasionBack100 = self.topPoint
          coronalPoints = vtk.vtkPoints() 
          plane.SetOrigin(0,posNasionBack100[1],0)
          plane.SetNormal(0,1,0)
          self.getIntersectPoints(polyData, plane, posNasionBack100, coronalReferenceLength, 1, coronalPoints) 
                    
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
      if polyData: 
        posNasion = numpy.array([0.0,0.0,0.0])
        nasionNode.GetNthFiducialPosition(0,posNasion)
        posTrajectory = numpy.array([0.0,0.0,0.0])
        if self.trajectoryManager.getFirstPoint(posTrajectory):
          plane = vtk.vtkPlane()
          plane.SetOrigin(0,posTrajectory[1],0)
          plane.SetNormal(0,1,0)
          coronalPoints = vtk.vtkPoints()
          self.getIntersectPointsPlanning(polyData, plane, posTrajectory, 1 , coronalPoints)
                
          ## Sorting   
          self.sortPoints(coronalPoints, posTrajectory)   
          
          self.constructCurvePlanning(self.coronalPlanningCurveManager, self.coronalReferenceCurveManager, coronalPoints, 1)  
              
          ##To do, calculate the curvature value points by point might be necessary to exclude the outliers   
          if self.topPoint:
            posTractoryBack = self.topPoint
            sagittalPoints = vtk.vtkPoints() 
            plane.SetOrigin(posTractoryBack[0],0,0)
            plane.SetNormal(1,0,0)
            self.getIntersectPointsPlanning(polyData, plane, posTractoryBack, 0, sagittalPoints) 
                      
            ## Sorting      
            self.sortPoints(sagittalPoints, posTractoryBack)  
            self.constructCurvePlanning(self.sagittalPlanningCurveManager, self.sagittalReferenceCurveManager, sagittalPoints, 0)
      self.lockPlanningLine()     
    pass  
    
  def calcPitchYawAngles(self):
    firstPos = numpy.array([0.0,0.0,0.0])
    self.trajectoryManager.getFirstPoint(firstPos)
    lastPos = numpy.array([0.0,0.0,0.0])
    self.trajectoryManager.getLastPoint(lastPos)
    self.pitchAngle = numpy.arctan2(firstPos[2]-lastPos[2], firstPos[1]-lastPos[1])*180.0/numpy.pi
    self.yawAngle = -numpy.arctan2(firstPos[0]-lastPos[0], firstPos[1]-lastPos[1])*180.0/numpy.pi
    layoutManager = slicer.app.layoutManager()
    threeDView = layoutManager.threeDWidget(0).threeDView()
    threeDView.lookFromViewAxis(ctkAxesWidget.Posterior)
    threeDView.pitchDirection = threeDView.PitchUp
    threeDView.yawDirection = threeDView.YawRight
    threeDView.setPitchRollYawIncrement(self.pitchAngle)
    threeDView.pitch()
    threeDView.setPitchRollYawIncrement(abs(self.yawAngle))
    threeDView.yaw()
    self.updateSliceView()
    pass

  def updateSliceView(self):
    ## due to the RAS and vtk space difference, the X axis is flipped, So the standard rotation matrix is multiplied by -1 in the X axis
    trajectoryNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_trajectory")
    if trajectoryNodeID:
      trajectoryNode = slicer.mrmlScene.GetNodeByID(trajectoryNodeID)
      if trajectoryNode and (trajectoryNode.GetNumberOfFiducials() > 1):
        pos = [0.0] * 3
        trajectoryNode.GetNthFiducialPosition(1, pos)
        redSliceNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeRed")
        matrixRedOri = redSliceNode.GetSliceToRAS()
        matrixRedNew = vtk.vtkMatrix4x4()
        matrixRedNew.Identity()
        matrixRedNew.SetElement(0, 3, pos[0])
        matrixRedNew.SetElement(1, 3, pos[1])
        matrixRedNew.SetElement(2, 3, pos[2])
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
        matrixYaw.SetElement(0, 3, pos[0])
        matrixYaw.SetElement(1, 3, pos[1])
        matrixYaw.SetElement(2, 3, pos[2])
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
