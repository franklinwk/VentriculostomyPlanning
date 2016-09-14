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
    self.parent.dependencies = []
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
    
    ROIConfigLayout = qt.QHBoxLayout()
    self.selectROIButton = qt.QPushButton("ROI definition")
    self.selectROIButton.toolTip = "Add two points in the 2D window"
    self.selectROIButton.enabled = True
    ROIConfigLayout.addWidget(self.selectROIButton)
    
    self.createROIButton = qt.QPushButton("Crop Volume")
    self.createROIButton.toolTip = "Created cropped volume"
    self.createROIButton.enabled = True
    ROIConfigLayout.addWidget(self.createROIButton)
    configurationFormLayout.addRow("ROI definition for cropping Volume:",None)
    configurationFormLayout.addRow(ROIConfigLayout)
    self.selectROIButton.connect('clicked(bool)',self.onDefineROI)
    self.createROIButton.connect('clicked(bool)',self.onCreateROI)
    self.lengthSagittalReferenceLineEdit.connect('textEdited(QString)', self.onModifyMeasureLength)
    self.lengthCoronalReferenceLineEdit.connect('textEdited(QString)', self.onModifyMeasureLength)
    
    
    # PatientModel Area
    #
    referenceCollapsibleButton = ctk.ctkCollapsibleButton()
    referenceCollapsibleButton.text = "Reference Generating "
    self.layout.addWidget(referenceCollapsibleButton)
    
    # Layout within the dummy collapsible button
    referenceFormLayout = qt.QFormLayout(referenceCollapsibleButton)
    
    #
    # input volume selector
    #
    volumeModelLayout = qt.QHBoxLayout()
    self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputVolumeSelector.selectNodeUponCreation = True
    self.inputVolumeSelector.addEnabled = False
    self.inputVolumeSelector.removeEnabled = False
    self.inputVolumeSelector.noneEnabled = False
    self.inputVolumeSelector.showHidden = False
    self.inputVolumeSelector.showChildNodeTypes = False
    self.inputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.inputVolumeSelector.setToolTip( "Pick the input to the algorithm." )
    #self.inputVolumeSelector.sortFilterProxyModel().setFilterRegExp("^(-originalVolume)$" )    
    volumeModelLayout.addWidget(self.inputVolumeSelector)
    
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
    self.createModelButton = qt.QPushButton("Create Model")
    self.createModelButton.toolTip = "Create a surface model."
    self.createModelButton.enabled = True
    volumeModelLayout.addWidget(self.createModelButton)

    self.createModelButton.connect('clicked(bool)', self.onCreateModel)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.inputVolumeSelector.connect("nodeAdded(vtkMRMLNode*)", self.onAddedNode)
    referenceFormLayout.addRow("Input Volume: ", volumeModelLayout)
    #
    # Create Entry point Button
    #
    automaticEntryHorizontalLayout = qt.QHBoxLayout()
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
    self.addTrajectoryButton = qt.QPushButton("Add Trajectory")
    self.addTrajectoryButton.toolTip = "Add Trajectory"
    self.addTrajectoryButton.enabled = True
    trajectoryLayout.addWidget(self.addTrajectoryButton)

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
    self.createPlanningLineButton = qt.QPushButton("Create planning Line")
    self.createPlanningLineButton.toolTip = "Create the planning line."
    self.createPlanningLineButton.enabled = True
    createPlanningLineHorizontalLayout.addWidget(self.createPlanningLineButton)
    self.createPlanningLineButton.connect('clicked(bool)', self.onCreatePlanningLine)
    planningFormLayout.addRow("Lock:", createPlanningLineHorizontalLayout)

     # Needle trajectory
    self.addTrajectoryButton.connect('clicked(bool)', self.onEditTrajectory)
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
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_ROI")
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_model")
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_nasion")
      self.logic.enableAttribute("vtkMRMLScalarVolumeNode.rel_trajectory")
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
    pass 
    
  def onCreateModel(self):
    threshold = -500.0
    if self.inputVolumeSelector.currentNode():
      outputModelNodeID = self.inputVolumeSelector.currentNode().GetAttribute("vtkMRMLScalarVolumeNode.rel_model") 
      if outputModelNodeID:
        outputModelNode = slicer.mrmlScene.GetNodeByID(outputModelNodeID)
        outputModelNode.SetAttribute("vtkMRMLModelNode.modelCreated","False")
        self.inputVolumeSelector.disconnect("nodeAdded(vtkMRMLNode*)")
        self.logic.createModel(outputModelNode, threshold)
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
      self.addTrajectoryButton.checked = False
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
      self.addTrajectoryButton.checked = False
      self.logic.startEditCoronalReferenceLine()
    else:
      self.logic.endEditCoronalReferenceLine()

  def onClearCoronalReferenceLine(self):
    self.logic.clearCoronalReferenceLine()

  def onCoronalReferenceLineModified(self, caller, event):
    self.lengthCoronalReferenceLineEdit.text = '%.2f' % self.logic.getCoronalReferenceLineLength()
    
  def onMoveSliceCoronalReferenceLine(self):
    self.logic.moveSliceCoronalReferenceLine()

  # Event handlers for trajectory
  def onEditTrajectory(self):
    self.logic.startEditTrajectory()
    
  def onClearTrajectory(self):
    self.logic.clearTrajectory()
    
  def onTrajectoryModified(self, caller, event):
    self.lengthTrajectoryEdit.text = '%.2f' % self.logic.getTrajectoryLength()

  # Event handlers for sagittalPlanning line
  def onEditSagittalPlanningLine(self, switch):

    if switch == True:
      self.addTrajectoryButton.checked = False
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
      self.addTrajectoryButton.checked = False
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
      self.addTrajectoryButton.enabled = False
      self.clearTrajectoryButton.enabled = False
      self.logic.lockTrajectoryLine()
    else:
      self.addTrajectoryButton.enabled = True
      self.clearTrajectoryButton.enabled = True
      self.logic.unlockTrajectoryLine()

  def onReload(self,moduleName="VentriculostomyPlanning"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)


class CurveManager:
  
  def __init__(self):
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
    
    self.currentVolumeNode = None
    self.baseVolumeNode = None
    self.samplingFactor = 1
    self.topPoint = []
    
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

  def startEditTrajectory(self):
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
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        if (selectionNode == None) or (interactionNode == None):
          return
    
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode");
        selectionNode.SetActivePlaceNodeID(trajectoryNode.GetID())
    
        interactionNode.SwitchToSinglePlaceMode ()
        interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place) 
        trajectoryNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updatePosition)
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
      thresholdImage = thresholdFilter.Execute(resampledImage,-500,10000,1,0)
      dilateFilter = sitk.BinaryDilateImageFilter()
      dilateFilter.SetKernelRadius([12,12,6])
      dilateFilter.SetBackgroundValue(0)
      dilateFilter.SetForegroundValue(1)
      dilatedImage = dilateFilter.Execute(thresholdImage)
      erodeFilter = sitk.BinaryErodeImageFilter()
      erodeFilter.SetKernelRadius([12,12,6])
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
        layoutManager = slicer.app.layoutManager()
        threeDWidget = layoutManager.threeDWidget(0)
        threeDView = threeDWidget.threeDView()
        threeDView.lookFromViewAxis(ctkAxesWidget.Anterior)
        threeDView.resetFocalPoint()
      imageCollection = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode","holefilledImage")
      if imageCollection:
        holefilledImageNode = imageCollection.GetItemAsObject(0)
        slicer.mrmlScene.RemoveNode(holefilledImageNode)
      imageCollection = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLScalarVolumeNode","Threshold")
      if imageCollection:
        thresholdImageNode = imageCollection.GetItemAsObject(0)
        slicer.mrmlScene.RemoveNode(thresholdImageNode)  
        
  def enableAttribute(self, attribte):
    enabledAttributeID = self.baseVolumeNode.GetAttribute(attribte)
    if enabledAttributeID:
      attributeNode = slicer.mrmlScene.GetNodeByID(enabledAttributeID)
      if attributeNode and attributeNode.GetDisplayNode():   
        attributeNode.GetDisplayNode().SetVisibility(1)
    else:
      if attribte == "vtkMRMLScalarVolumeNode.rel_nasion":
        nasionNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        nasionNode.SetName("nasion"+self.baseVolumeNode.GetID()[-1:])
        slicer.mrmlScene.AddNode(nasionNode)
        self.baseVolumeNode.SetAttribute(attribte, nasionNode.GetID())  
      elif attribte == "vtkMRMLScalarVolumeNode.rel_ROI":
        ROIListNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLAnnotationHierarchyNode")
        ROIListNode.SetName("ROI List")
        ROINode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLAnnotationROINode")
        ROINode.SetName("ROI"+self.baseVolumeNode.GetID()[-1:])
        slicer.mrmlScene.AddNode(ROINode)
        self.baseVolumeNode.SetAttribute(attribte, ROINode.GetID())     
      elif attribte == "vtkMRMLScalarVolumeNode.rel_trajectory":
        trajectoryNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
        trajectoryNode.SetName("trajectory"+self.baseVolumeNode.GetID()[-1:])
        slicer.mrmlScene.AddNode(trajectoryNode)
        self.baseVolumeNode.SetAttribute(attribte, trajectoryNode.GetID())  
      elif attribte == "vtkMRMLScalarVolumeNode.rel_model":  
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
      enabledAttributeID = self.baseVolumeNode.GetAttribute(attribte)  
        # to do update the logic regarding the current attribute // self.nasionPointNode = nasionNode
    volumeCollection = slicer.mrmlScene.GetNodesByClass("vtkMRMLScalarVolumeNode") 
    if volumeCollection:
      for iVolume in range(volumeCollection.GetNumberOfItems ()):
        volumeNode = volumeCollection.GetItemAsObject(iVolume)
        attributeNodeID = volumeNode.GetAttribute(attribte)
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
         
  def updatePosition(self, fiducicalMarkerNode, eventID):
    pos = [0.0]*4
    fiducicalMarkerNode.GetNthFiducialWorldCoordinates(0,pos)
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
    interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)
    if interactionNode.GetAttribute("vtkMRMLInteractionNode.rel_marker") == "nasion":
      self.createEntryPoint()
    pass
   
  def selectNasionPointNode(self, modelNode, initPoint = None):
    if self.baseVolumeNode:
      if modelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "False":
        self.createModel(modelNode,-500)
      if self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"):
        nasionNode = slicer.mrmlScene.GetNodeByID(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"))
        dnode = nasionNode.GetMarkupsDisplayNode()
        nasionNode.RemoveAllMarkups()
        slicer.mrmlScene.AddNode(nasionNode)  
        if dnode:
          rgbColor = [1.0, 0.0, 1.0]
          dnode.SetSelectedColor(rgbColor)
          dnode.SetVisibility(1)
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
        nasionNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updatePosition)
  
  def createROI(self):
    cropVolumeLogic = slicer.modules.cropvolume.logic()
    if self.baseVolumeNode:
      if not self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume"):
        croppedVolumeNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLScalarVolumeNode")
        #croppedVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.notShownEntity","True")
        slicer.mrmlScene.AddNode(croppedVolumeNode)
        self.baseVolumeNode.SetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume",croppedVolumeNode.GetID())
      croppedVolumeNodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_croppedVolume")
      croppedVolumeNode = slicer.mrmlScene.GetNodeByID(croppedVolumeNodeID)
      ROINodeID = self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_ROI")
      ROINode = slicer.mrmlScene.GetNodeByID(ROINodeID)
      ROIListCollection = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLAnnotationHierarchyNode","ROI List")
      ROIList = ROIListCollection.GetItemAsObject(0)
      childrenNodes = vtk.vtkCollection()
      ROIList.GetChildren(childrenNodes, 1)
      lastNode = childrenNodes.GetItemAsObject(childrenNodes.GetNumberOfItems()-1)
      ROINode.Copy(lastNode)
      #slicer.mrmlScene.RemoveNode(lastNode)
      if croppedVolumeNode and ROINode :
        cropVolumeLogic.CropVoxelBased(ROINode,self.baseVolumeNode,croppedVolumeNode)
        self.currentVolumeNode = croppedVolumeNode
    pass
    
  
  def defineROI(self):
    if self.baseVolumeNode:
      selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
      interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
      if (selectionNode == None) or (interactionNode == None):
        return
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLAnnotationROINode");
      interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place) 
      ROINode = slicer.mrmlScene.GetNodeByID(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_ROI"))
      ROILists = slicer.mrmlScene.GetNodesByClassByName("vtkMRMLAnnotationHierarchyNode","ROI List")
      selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
      selectionNode.SetActiveROIListID(ROILists.GetItemAsObject(0).GetID())
      selectionNode.SetActivePlaceNodeID(ROINode.GetID())
  
      #interactionNode.SwitchToSinglePlaceMode ()
      #interactionNode.AddObserver(interactionNode.EndPlacementEvent, self.endROIPlacement) 
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
    nasionNode = slicer.mrmlScene.GetNodeByID(self.baseVolumeNode.GetAttribute("vtkMRMLScalarVolumeNode.rel_nasion"))
    nasionNode.GetNthFiducialPosition(0,posNasion)
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
      if abs(lastRefPos[1]-points.GetPoint(0)[1])<eps:
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
          jPosValid = jPos
          if abs(posModel[0]-posNasion[0])<eps or (posModel[0]<posNasion[0]):
            break        
        self.topPoint = points.GetPoint(jPosValid)    
        posModel = numpy.array(points.GetPoint(jPosValid))  
        CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2]) 

    if axis ==0:
      for iPos in range(1,numOfRef): 
        pos = [0.0]*3;
        CurveManagerReference.curveFiducials.GetNthFiducialPosition(numOfRef-iPos-1, pos)  
        if float(pos[2])<self.topPoint[2]:
          CurveManager.curveFiducials.AddFiducial(pos[0],pos[1],pos[2]) 
       
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
    if (inputModelNode.GetAttribute("vtkMRMLModelNode.modelCreated") == "True") and (nasionNode.GetNumberOfMarkups()):
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
