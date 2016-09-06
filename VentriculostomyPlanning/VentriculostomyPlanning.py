import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import tempfile
import CurveMaker
import numpy
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
    self.parent.contributors = ["Junichi Tokuda (BWH)"] # replace with "Firstname Lastname (Organization)"
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

    ####################
    # For debugging
    #
    # Reload and Test area
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)
    
    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "VentriculostomyPlanning Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)
    #
    ####################

    #
    # Lines Area
    #
    referenceLinesCollapsibleButton = ctk.ctkCollapsibleButton()
    referenceLinesCollapsibleButton.text = "Reference Lines"
    self.layout.addWidget(referenceLinesCollapsibleButton)

    # Layout within the dummy collapsible button
    referenceLinesFormLayout = qt.QFormLayout(referenceLinesCollapsibleButton)

    #
    # Mid-sagitalReference line
    #
    sagitalReferenceLineLayout = qt.QHBoxLayout()

    #-- Curve length
    self.lengthSagitalReferenceLineEdit = qt.QLineEdit()
    self.lengthSagitalReferenceLineEdit.text = '--'
    self.lengthSagitalReferenceLineEdit.readOnly = True
    self.lengthSagitalReferenceLineEdit.frame = True
    self.lengthSagitalReferenceLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthSagitalReferenceLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    sagitalReferenceLineLayout.addWidget(self.lengthSagitalReferenceLineEdit)
    lengthSagitalReferenceLineUnitLabel = qt.QLabel('mm  ')
    sagitalReferenceLineLayout.addWidget(lengthSagitalReferenceLineUnitLabel)

    #-- Add Point
    self.addPointForSagitalReferenceLineButton = qt.QPushButton("Add Points")
    self.addPointForSagitalReferenceLineButton.toolTip = "Add points for mid-sagital reference line"
    self.addPointForSagitalReferenceLineButton.enabled = True
    self.addPointForSagitalReferenceLineButton.checkable = True    
    sagitalReferenceLineLayout.addWidget(self.addPointForSagitalReferenceLineButton)

    #-- Clear Point
    self.clearPointForSagitalReferenceLineButton = qt.QPushButton("Clear")
    self.clearPointForSagitalReferenceLineButton.toolTip = "Remove all points for mid-sagital reference line"
    self.clearPointForSagitalReferenceLineButton.enabled = True
    sagitalReferenceLineLayout.addWidget(self.clearPointForSagitalReferenceLineButton)

    #-- Move the slice to the curve
    self.moveSliceSagitalReferenceLineButton = qt.QPushButton("Slice")
    self.moveSliceSagitalReferenceLineButton.toolTip = "Move the slice to the mid-sagital reference line"
    self.moveSliceSagitalReferenceLineButton.enabled = True
    sagitalReferenceLineLayout.addWidget(self.moveSliceSagitalReferenceLineButton)

    referenceLinesFormLayout.addRow("Mid-Sagital Reference Line:", sagitalReferenceLineLayout)

    #
    # CoronalReference line
    #
    coronalReferenceLineLayout = qt.QHBoxLayout()

    #-- Curve length
    self.lengthCoronalReferenceLineEdit = qt.QLineEdit()
    self.lengthCoronalReferenceLineEdit.text = '--'
    self.lengthCoronalReferenceLineEdit.readOnly = True
    self.lengthCoronalReferenceLineEdit.frame = True
    self.lengthCoronalReferenceLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthCoronalReferenceLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    coronalReferenceLineLayout.addWidget(self.lengthCoronalReferenceLineEdit)
    lengthCoronalReferenceLineUnitLabel = qt.QLabel('mm  ')
    coronalReferenceLineLayout.addWidget(lengthCoronalReferenceLineUnitLabel)

    #-- Add Point
    self.addPointForCoronalReferenceLineButton = qt.QPushButton("Add Points")
    self.addPointForCoronalReferenceLineButton.toolTip = "Add points for coronal reference line"
    self.addPointForCoronalReferenceLineButton.enabled = True
    self.addPointForCoronalReferenceLineButton.checkable = True    
    coronalReferenceLineLayout.addWidget(self.addPointForCoronalReferenceLineButton)

    #-- Clear Point
    self.clearPointForCoronalReferenceLineButton = qt.QPushButton("Clear")
    self.clearPointForCoronalReferenceLineButton.toolTip = "Remove all points for coronal reference line"
    self.clearPointForCoronalReferenceLineButton.enabled = True
    coronalReferenceLineLayout.addWidget(self.clearPointForCoronalReferenceLineButton)

    #-- Move the slice to the curve
    self.moveSliceCoronalReferenceLineButton = qt.QPushButton("Slice")
    self.moveSliceCoronalReferenceLineButton.toolTip = "Move the slice to the coronal reference line"
    self.moveSliceCoronalReferenceLineButton.enabled = True
    coronalReferenceLineLayout.addWidget(self.moveSliceCoronalReferenceLineButton)

    referenceLinesFormLayout.addRow("CoronalReference Line:", coronalReferenceLineLayout)

    self.lockReferenceLinesCheckBox = qt.QCheckBox()
    self.lockReferenceLinesCheckBox.checked = 0
    self.lockReferenceLinesCheckBox.setToolTip("If checked, the lines will be locked.")
    referenceLinesFormLayout.addRow("Lock:", self.lockReferenceLinesCheckBox)
    
    #
    # Trajectory
    #
    trajectoryCollapsibleButton = ctk.ctkCollapsibleButton()
    trajectoryCollapsibleButton.text = "Trajectory"
    self.layout.addWidget(trajectoryCollapsibleButton)
    
    # Layout within the dummy collapsible button
    trajectoryFormLayout = qt.QFormLayout(trajectoryCollapsibleButton)
    
    #
    # Trajectory
    #
    trajectoryLayout = qt.QHBoxLayout()

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

    #-- Add Point
    self.addTrajectoryButton = qt.QPushButton("Add Trajectory")
    self.addTrajectoryButton.toolTip = "Add Trajectory"
    self.addTrajectoryButton.enabled = True
    self.addTrajectoryButton.checkable = True    
    trajectoryLayout.addWidget(self.addTrajectoryButton)

    #-- Clear Point
    self.clearTrajectoryButton = qt.QPushButton("Clear")
    self.clearTrajectoryButton.toolTip = "Remove Trajectory"
    self.clearTrajectoryButton.enabled = True
    trajectoryLayout.addWidget(self.clearTrajectoryButton)

    trajectoryFormLayout.addRow("Trajectory:", trajectoryLayout)
    
    createPlanningLineHorizontalLayout = qt.QHBoxLayout()
    self.lockTrajectoryCheckBox = qt.QCheckBox()
    self.lockTrajectoryCheckBox.checked = 0
    self.lockTrajectoryCheckBox.setToolTip("If checked, the trajectory will be locked.")
    createPlanningLineHorizontalLayout.addWidget(self.lockTrajectoryCheckBox)
    self.createPlanningLineButton = qt.QPushButton("Create planning Line")
    self.createPlanningLineButton.toolTip = "Create the planning line."
    self.createPlanningLineButton.enabled = True
    createPlanningLineHorizontalLayout.addWidget(self.createPlanningLineButton)
    trajectoryFormLayout.addRow("Lock: ", createPlanningLineHorizontalLayout)
    
    self.createPlanningLineButton.connect('clicked(bool)', self.onCreatePlanningLine)
    
    #
    # Planning Lines
    #
    planningLinesCollapsibleButton = ctk.ctkCollapsibleButton()
    planningLinesCollapsibleButton.text = "Planning Lines"
    self.layout.addWidget(planningLinesCollapsibleButton)
    
    # Layout within the dummy collapsible button
    planningLinesFormLayout = qt.QFormLayout(planningLinesCollapsibleButton)
    
    #
    # CoronalPlanning line
    #
    coronalPlanningLineLayout = qt.QHBoxLayout()

    #-- Curve length
    self.lengthCoronalPlanningLineEdit = qt.QLineEdit()
    self.lengthCoronalPlanningLineEdit.text = '--'
    self.lengthCoronalPlanningLineEdit.readOnly = True
    self.lengthCoronalPlanningLineEdit.frame = True
    self.lengthCoronalPlanningLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthCoronalPlanningLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    coronalPlanningLineLayout.addWidget(self.lengthCoronalPlanningLineEdit)
    lengthCoronalPlanningLineUnitLabel = qt.QLabel('mm  ')
    coronalPlanningLineLayout.addWidget(lengthCoronalPlanningLineUnitLabel)

    #-- Add Point
    self.addPointForCoronalPlanningLineButton = qt.QPushButton("Add Points")
    self.addPointForCoronalPlanningLineButton.toolTip = "Add points for coronal planning line"
    self.addPointForCoronalPlanningLineButton.enabled = True
    self.addPointForCoronalPlanningLineButton.checkable = True    
    coronalPlanningLineLayout.addWidget(self.addPointForCoronalPlanningLineButton)

    #-- Clear Point
    self.clearPointForCoronalPlanningLineButton = qt.QPushButton("Clear")
    self.clearPointForCoronalPlanningLineButton.toolTip = "Remove all points for coronal planning line"
    self.clearPointForCoronalPlanningLineButton.enabled = True
    coronalPlanningLineLayout.addWidget(self.clearPointForCoronalPlanningLineButton)

    #-- Move the slice to the curve
    self.moveSliceCoronalPlanningLineButton = qt.QPushButton("Slice")
    self.moveSliceCoronalPlanningLineButton.toolTip = "Move the slice to the coronal planning line"
    self.moveSliceCoronalPlanningLineButton.enabled = True
    coronalPlanningLineLayout.addWidget(self.moveSliceCoronalPlanningLineButton)

    planningLinesFormLayout.addRow("CoronalPlanning Line:", coronalPlanningLineLayout)

    #
    # Mid-sagital planning line
    #
    sagitalPlanningLineLayout = qt.QHBoxLayout()

    #-- Curve length
    self.lengthSagitalPlanningLineEdit = qt.QLineEdit()
    self.lengthSagitalPlanningLineEdit.text = '--'
    self.lengthSagitalPlanningLineEdit.readOnly = True
    self.lengthSagitalPlanningLineEdit.frame = True
    self.lengthSagitalPlanningLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthSagitalPlanningLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    sagitalPlanningLineLayout.addWidget(self.lengthSagitalPlanningLineEdit)
    lengthSagitalPlanningLineUnitLabel = qt.QLabel('mm  ')
    sagitalPlanningLineLayout.addWidget(lengthSagitalPlanningLineUnitLabel)

    #-- Add Point
    self.addPointForSagitalPlanningLineButton = qt.QPushButton("Add Points")
    self.addPointForSagitalPlanningLineButton.toolTip = "Add points for mid-sagital planning line"
    self.addPointForSagitalPlanningLineButton.enabled = True
    self.addPointForSagitalPlanningLineButton.checkable = True    
    sagitalPlanningLineLayout.addWidget(self.addPointForSagitalPlanningLineButton)

    #-- Clear Point
    self.clearPointForSagitalPlanningLineButton = qt.QPushButton("Clear")
    self.clearPointForSagitalPlanningLineButton.toolTip = "Remove all points for mid-sagital planning line"
    self.clearPointForSagitalPlanningLineButton.enabled = True
    sagitalPlanningLineLayout.addWidget(self.clearPointForSagitalPlanningLineButton)

    #-- Move the slice to the curve
    self.moveSliceSagitalPlanningLineButton = qt.QPushButton("Slice")
    self.moveSliceSagitalPlanningLineButton.toolTip = "Move the slice to the mid-sagital planning line"
    self.moveSliceSagitalPlanningLineButton.enabled = True
    sagitalPlanningLineLayout.addWidget(self.moveSliceSagitalPlanningLineButton)

    planningLinesFormLayout.addRow("Mid-Sagital Planning Line:", sagitalPlanningLineLayout)

    self.lockPlanningLinesCheckBox = qt.QCheckBox()
    self.lockPlanningLinesCheckBox.checked = 0
    self.lockPlanningLinesCheckBox.setToolTip("If checked, the lines will be locked.")
    planningLinesFormLayout.addRow("Lock:", self.lockPlanningLinesCheckBox)
    

    # PatientModel Area
    #
    patientModelCollapsibleButton = ctk.ctkCollapsibleButton()
    patientModelCollapsibleButton.text = "Patient Model"
    self.layout.addWidget(patientModelCollapsibleButton)
    
    # Layout within the dummy collapsible button
    patientModelFormLayout = qt.QFormLayout(patientModelCollapsibleButton)
    
    #
    # input volume selector
    #
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
    patientModelFormLayout.addRow("Input Volume: ", self.inputVolumeSelector)
    
    #
    # output volume selector
    #
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
    patientModelFormLayout.addRow("Output Model: ", self.outputModelSelector)
    
    
    #
    # Create Model Button
    #
    self.createModelButton = qt.QPushButton("Create Model")
    self.createModelButton.toolTip = "Create a surface model."
    self.createModelButton.enabled = True
    patientModelFormLayout.addRow(self.createModelButton)

    self.createModelButton.connect('clicked(bool)', self.onCreateModel)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    
    # Automatic entry point Area
    #
    automaticEntryPointCollapsibleButton = ctk.ctkCollapsibleButton()
    automaticEntryPointCollapsibleButton.text = "CreateEntry"
    self.layout.addWidget(automaticEntryPointCollapsibleButton)
    
    # Layout within the dummy collapsible button
    automaticEntryPointFormLayout = qt.QFormLayout(automaticEntryPointCollapsibleButton)
    
    #
    # output volume selector
    #
    self.inputModelSelector = slicer.qMRMLNodeComboBox()
    self.inputModelSelector.nodeTypes = ["vtkMRMLModelNode"]
    self.inputModelSelector.selectNodeUponCreation = True
    self.inputModelSelector.addEnabled = True
    self.inputModelSelector.removeEnabled = True
    self.inputModelSelector.noneEnabled = True
    self.inputModelSelector.showHidden = False
    self.inputModelSelector.showChildNodeTypes = False
    self.inputModelSelector.setMRMLScene( slicer.mrmlScene )
    self.inputModelSelector.setToolTip( "Pick the input to the algorithm." )
    automaticEntryPointFormLayout.addRow("Input Model: ", self.inputModelSelector)
    
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
    
    automaticEntryPointFormLayout.addRow("Automatic Entry Point: ", automaticEntryHorizontalLayout)
    self.selectNasionButton.connect('clicked(bool)', self.onSelectnasionPointNode)
    self.createEntryPointButton.connect('clicked(bool)', self.onCreateEntryPoint)
    self.inputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectModelForEntryPoint)
    
    #end of GUI section
    #####################################
    
    

    # SagitalReference line
    self.addPointForSagitalReferenceLineButton.connect('toggled(bool)', self.onEditSagitalReferenceLine)
    self.clearPointForSagitalReferenceLineButton.connect('clicked(bool)', self.onClearSagitalReferenceLine)
    self.moveSliceSagitalReferenceLineButton.connect('clicked(bool)', self.onMoveSliceSagitalReferenceLine)
    self.logic.setSagitalReferenceLineModifiedEventHandler(self.onSagitalReferenceLineModified)

    # CoronalReference line
    self.addPointForCoronalReferenceLineButton.connect('toggled(bool)', self.onEditCoronalReferenceLine)
    self.clearPointForCoronalReferenceLineButton.connect('clicked(bool)', self.onClearCoronalReferenceLine)
    self.moveSliceCoronalReferenceLineButton.connect('clicked(bool)', self.onMoveSliceCoronalReferenceLine)
    self.logic.setCoronalReferenceLineModifiedEventHandler(self.onCoronalReferenceLineModified)

    self.lockReferenceLinesCheckBox.connect('toggled(bool)', self.onLock)

    # Needle trajectory
    self.addTrajectoryButton.connect('toggled(bool)', self.onEditTrajectory)
    self.clearTrajectoryButton.connect('clicked(bool)', self.onClearTrajectory)
    self.logic.setTrajectoryModifiedEventHandler(self.onTrajectoryModified)
    self.lockTrajectoryCheckBox.connect('toggled(bool)', self.onLock)


    # SagitalPlanning line
    self.addPointForSagitalPlanningLineButton.connect('toggled(bool)', self.onEditSagitalPlanningLine)
    self.clearPointForSagitalPlanningLineButton.connect('clicked(bool)', self.onClearSagitalPlanningLine)
    self.moveSliceSagitalPlanningLineButton.connect('clicked(bool)', self.onMoveSliceSagitalPlanningLine)
    self.logic.setSagitalPlanningLineModifiedEventHandler(self.onSagitalPlanningLineModified)

    # CoronalPlanning line
    self.addPointForCoronalPlanningLineButton.connect('toggled(bool)', self.onEditCoronalPlanningLine)
    self.clearPointForCoronalPlanningLineButton.connect('clicked(bool)', self.onClearCoronalPlanningLine)
    self.moveSliceCoronalPlanningLineButton.connect('clicked(bool)', self.onMoveSliceCoronalPlanningLine)
    self.logic.setCoronalPlanningLineModifiedEventHandler(self.onCoronalPlanningLineModified)

    self.lockPlanningLinesCheckBox.connect('toggled(bool)', self.onLock)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    pass
  
  def onSelect(self):
    pass

  def onSelectModelForEntryPoint(self):
    #self.createModelButton.enabled =  self.inputVolumeSelector.currentNode() and self.outputModelSelector.currentNode()
    self.logic.inputModel = self.inputModelSelector.currentNode()
    pass
    
  def onCreatePlanningLine(self):
    self.logic.creatPlanningLine()  
    self.lengthSagitalPlanningLineEdit.text = '%.2f' % self.logic.getSagitalPlanningLineLength()
    self.lengthCoronalPlanningLineEdit.text = '%.2f' % self.logic.getCoronalPlanningLineLength()
    pass 
    
  def onCreateModel(self):
    #logic = VentriculostomyPlanningLogic()
    threshold = -500.0
    self.logic.createModel(self.inputVolumeSelector.currentNode(), self.outputModelSelector.currentNode(), threshold)
  
  def onSelectnasionPointNode(self):
    self.logic.selectnasionPointNode(self.inputModelSelector.currentNode())     
  
  def onCreateEntryPoint(self):
    self.logic.creatEntryPoint()
    self.lengthSagitalReferenceLineEdit.text = '%.2f' % self.logic.getSagitalReferenceLineLength()
    self.lengthCoronalReferenceLineEdit.text = '%.2f' % self.logic.getCoronalReferenceLineLength()
    

  # Event handlers for sagitalReference line
  def onEditSagitalReferenceLine(self, switch):

    if switch == True:
      self.addPointForCoronalReferenceLineButton.checked = False
      self.addTrajectoryButton.checked = False
      self.logic.startEditSagitalReferenceLine()
    else:
      self.logic.endEditSagitalReferenceLine()

  def onClearSagitalReferenceLine(self):
    
    self.logic.clearSagitalReferenceLine()

  def onSagitalReferenceLineModified(self, caller, event):
    self.lengthSagitalReferenceLineEdit.text = '%.2f' % self.logic.getSagitalReferenceLineLength()

  def onMoveSliceSagitalReferenceLine(self):
    self.logic.moveSliceSagitalReferenceLine()

  # Event handlers for coronalReference line
  def onEditCoronalReferenceLine(self, switch):

    if switch == True:
      self.addPointForSagitalReferenceLineButton.checked = False
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
  def onEditTrajectory(self, switch):

    if switch == True:
      self.addPointForSagitalReferenceLineButton.checked = False
      self.addPointForCoronalReferenceLineButton.checked = False
      self.logic.startEditTrajectory()
    else:
      self.logic.endEditCoronalReferenceLine()
    
  def onClearTrajectory(self):
    self.logic.clearTrajectory()
    
  def onTrajectoryModified(self, caller, event):
    self.lengthTrajectoryEdit.text = '%.2f' % self.logic.getTrajectoryLength()

  # Event handlers for sagitalPlanning line
  def onEditSagitalPlanningLine(self, switch):

    if switch == True:
      self.addPointForCoronalPlanningLineButton.checked = False
      self.addTrajectoryButton.checked = False
      self.logic.startEditSagitalPlanningLine()
    else:
      self.logic.endEditSagitalPlanningLine()

  def onClearSagitalPlanningLine(self):
    
    self.logic.clearSagitalPlanningLine()

  def onSagitalPlanningLineModified(self, caller, event):
    self.lengthSagitalPlanningLineEdit.text = '%.2f' % self.logic.getSagitalPlanningLineLength()

  def onMoveSliceSagitalPlanningLine(self):
    self.logic.moveSliceSagitalPlanningLine()

  # Event handlers for coronalPlanning line
  def onEditCoronalPlanningLine(self, switch):

    if switch == True:
      self.addPointForSagitalPlanningLineButton.checked = False
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
    if self.lockReferenceLinesCheckBox.checked == 1:
      self.addPointForSagitalReferenceLineButton.enabled = False
      self.clearPointForSagitalReferenceLineButton.enabled = False
      self.addPointForCoronalReferenceLineButton.enabled = False
      self.clearPointForCoronalReferenceLineButton.enabled = False
      self.logic.lockReferenceLine()
    else:
      self.addPointForSagitalReferenceLineButton.enabled = True
      self.clearPointForSagitalReferenceLineButton.enabled = True
      self.addPointForCoronalReferenceLineButton.enabled = True
      self.clearPointForCoronalReferenceLineButton.enabled = True
      self.logic.unlockReferenceLine()

    if self.lockTrajectoryCheckBox.checked == 1:
      self.addTrajectoryButton.enabled = False
      self.clearTrajectoryButton.enabled = False
      self.logic.lockTrajectoryLine()
    else:
      self.addTrajectoryButton.enabled = True
      self.clearTrajectoryButton.enabled = True
      self.logic.unlockTrajectoryLine()

    if self.lockPlanningLinesCheckBox.checked == 1:
      self.addPointForSagitalPlanningLineButton.enabled = False
      self.clearPointForSagitalPlanningLineButton.enabled = False
      self.addPointForCoronalPlanningLineButton.enabled = False
      self.clearPointForCoronalPlanningLineButton.enabled = False
      self.logic.lockPlanningLine()
    else:
      self.addPointForSagitalPlanningLineButton.enabled = True
      self.clearPointForSagitalPlanningLineButton.enabled = True
      self.addPointForCoronalPlanningLineButton.enabled = True
      self.clearPointForCoronalPlanningLineButton.enabled = True
      self.logic.unlockPlanningLine()

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

    selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    if (selectionNode == None) or (interactionNode == None):
      return

    selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode");
    selectionNode.SetActivePlaceNodeID(self.curveFiducials.GetID())

    interactionNode.SwitchToPersistentPlaceMode()
    interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place)

  def endEditLine(self):

    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)  ## Turn off
    
  def clearLine(self):

    if self.curveFiducials:
      self.curveFiducials.RemoveAllMarkups()
      slicer.mrmlScene.RemoveNode(self.curveFiducials)
      self.curveFiducials = None
      #To trigger the initializaton, when the user clear the trajectory and restart the planning, 
      #the last point of the coronal reference line should be added to the trajectory

    self.cmLogic.updateCurve()

    if self.curveModel:
      pdata = self.curveModel.GetPolyData()
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
    self.sagitalReferenceCurveManager = CurveManager()
    self.sagitalReferenceCurveManager.setName("SR1")
    self.sagitalReferenceCurveManager.setSliceID("vtkMRMLSliceNodeYellow")
    self.sagitalReferenceCurveManager.setDefaultSlicePositionToFirstPoint()
    self.sagitalReferenceCurveManager.curveModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
    self.sagitalReferenceCurveManager.curveModel.SetName(self.sagitalReferenceCurveManager.curveModelName)
    slicer.mrmlScene.AddNode(self.sagitalReferenceCurveManager.curveModel)
    self.sagitalReferenceCurveManager.setModelColor(1.0, 1.0, 0.5)
    
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

    self.sagitalPlanningCurveManager = CurveManager()
    self.sagitalPlanningCurveManager.setName("SP1")
    self.sagitalPlanningCurveManager.setSliceID("vtkMRMLSliceNodeYellow")
    self.sagitalPlanningCurveManager.setDefaultSlicePositionToFirstPoint()
    self.sagitalPlanningCurveManager.curveModel = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
    self.sagitalPlanningCurveManager.curveModel.SetName(self.sagitalPlanningCurveManager.curveModelName)
    slicer.mrmlScene.AddNode(self.sagitalPlanningCurveManager.curveModel)
    self.sagitalPlanningCurveManager.setModelColor(1.0, 1.0, 0.0)
    
    self.nasionPointNode = None
    self.inputModel = None
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

  def startEditSagitalReferenceLine(self):

    self.sagitalReferenceCurveManager.startEditLine()
    
  def endEditSagitalReferenceLine(self):

    self.sagitalReferenceCurveManager.endEditLine()

  def clearSagitalReferenceLine(self):
    
    self.sagitalReferenceCurveManager.clearLine()

  def setSagitalReferenceLineModifiedEventHandler(self, handler):

    self.sagitalReferenceCurveManager.setModifiedEventHandler(handler)

  def getSagitalReferenceLineLength(self):
    return self.sagitalReferenceCurveManager.getLength()

  def moveSliceSagitalReferenceLine(self):
    self.sagitalReferenceCurveManager.moveSliceToLine()

  def startEditCoronalReferenceLine(self):

    pos = [0.0] * 3
    self.sagitalReferenceCurveManager.getLastPoint(pos)
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
    self.sagitalReferenceCurveManager.lockLine()
    self.coronalReferenceCurveManager.lockLine()

  def unlockReferenceLine(self):
    self.sagitalReferenceCurveManager.unlockLine()
    self.coronalReferenceCurveManager.unlockLine()

  def startEditTrajectory(self):
    pos = [0.0] * 3
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
    self.sagitalPlanningCurveManager.lockLine()
    self.coronalPlanningCurveManager.lockLine()

  def unlockPlanningLine(self):
    self.sagitalPlanningCurveManager.unlockLine()
    self.coronalPlanningCurveManager.unlockLine()


  def startEditSagitalPlanningLine(self):

    pos = [0.0] * 3

    self.coronalPlanningCurveManager.getLastPoint(pos)
    self.sagitalPlanningCurveManager.startEditLine(pos)
    
  def endEditSagitalPlanningLine(self):

    self.sagitalPlanningCurveManager.endEditLine()

  def clearSagitalPlanningLine(self):
    
    self.sagitalPlanningCurveManager.clearLine()

  def setSagitalPlanningLineModifiedEventHandler(self, handler):

    self.sagitalPlanningCurveManager.setModifiedEventHandler(handler)

  def getSagitalPlanningLineLength(self):
    return self.sagitalPlanningCurveManager.getLength()

  def moveSliceSagitalPlanningLine(self):
    self.sagitalPlanningCurveManager.moveSliceToLine()



  def createModel(self, inputVolumeNode, outputModelNode, thresholdValue):

    Decimate = 0.05

    if inputVolumeNode == None:
      return
    
    inputImageData = inputVolumeNode.GetImageData()    
    threshold = vtk.vtkImageThreshold()
    threshold.SetInputData(inputImageData)
    threshold.ThresholdByLower(thresholdValue)
    threshold.SetInValue(0)
    threshold.SetOutValue(1)
    threshold.ReleaseDataFlagOff()
    threshold.Update()
    dilateErode = vtk.vtkImageDilateErode3D()
    dilateErode.SetInputData(threshold.GetOutput()) 
    dilateErode.SetDilateValue(1)
    dilateErode.SetErodeValue(0)
    dilateErode.SetKernelSize(50, 50, 15)
    dilateErode.ReleaseDataFlagOff()
    dilateErode.Update()
    erode = vtk.vtkImageDilateErode3D()
    erode.SetInputData(dilateErode.GetOutput())
    erode.SetDilateValue(0)
    erode.SetErodeValue(1)
    erode.SetKernelSize(50, 50, 15)
    erode.ReleaseDataFlagOff()
    erode.Update()
    #for i in range(1):
    #  dilateErode.SetInputData(erode.GetOutput()) 
    #  dilateErode.Update()
    #  erode.SetInputData(dilateErode.GetOutput())
    #  erode.Update()
    
    cast = vtk.vtkImageCast()
    cast.SetInputData(erode.GetOutput())
    cast.SetOutputScalarTypeToUnsignedChar()
    cast.Update()

    labelVolumeNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLLabelMapVolumeNode")
    slicer.mrmlScene.AddNode(labelVolumeNode)
    labelVolumeNode.SetName("Threshold")
    labelVolumeNode.SetSpacing(inputVolumeNode.GetSpacing())
    labelVolumeNode.SetOrigin(inputVolumeNode.GetOrigin())

    matrix = vtk.vtkMatrix4x4()
    inputVolumeNode.GetIJKToRASDirectionMatrix(matrix)
    labelVolumeNode.SetIJKToRASDirectionMatrix(matrix)

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

    modelDisplayNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelDisplayNode")
    ModelColor = [0.0, 0.0, 1.0]
    modelDisplayNode.SetColor(ModelColor)
    modelDisplayNode.SetOpacity(0.5)
    slicer.mrmlScene.AddNode(modelDisplayNode)
    outputModelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
  
  def cutSkullModel(self, inputModelNode, posNasion):
    pass
    
    
  def updatePosition(self, nasionNode, eventID):
    pos = [0.0]*4
    nasionNode.GetNthFiducialWorldCoordinates(0,pos)
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
    
  def selectnasionPointNode(self, inputCreatedModel, initPoint = None):
    if self.nasionPointNode:
      slicer.mrmlScene.RemoveNode(self.nasionPointNode)
      self.nasionPointNode = None
    self.inputModel= inputCreatedModel
    self.nasionPointNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
    self.nasionPointNode.SetName("nasionPointNode")
    slicer.mrmlScene.AddNode(self.nasionPointNode)
    self.nasionPointNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.updatePosition)
    dnode = self.nasionPointNode.GetMarkupsDisplayNode()
    if dnode:
      rgbColor = [1.0, 0.0, 1.0]
      dnode.SetSelectedColor(rgbColor)
    pos = [0.0] * 3
    if initPoint != None:
      self.nasionPointNode.AddFiducial(initPoint[0],initPoint[1],initPoint[2])
      pos = initPoint
    viewerRed = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeRed")
    viewerRed.SetOrientationToAxial()
    viewerRed.SetSliceOffset(pos[2])
    viewerYellow = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeYellow")
    viewerYellow.SetOrientationToSagittal()
    viewerYellow.SetSliceOffset(pos[0])
    viewerBlue = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeGreen")
    viewerBlue.SetOrientationToCoronal()
    viewerBlue.SetSliceOffset(pos[1])
    selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    if (selectionNode == None) or (interactionNode == None):
      return

    selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode");
    selectionNode.SetActivePlaceNodeID(self.nasionPointNode.GetID())

    interactionNode.SwitchToSinglePlaceMode ()
    interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.Place) 
    
    interactionNode.AddObserver(interactionNode.EndPlacementEvent, self.endPlacement) 
    
  
  def endPlacement(self, interactionNode, selectednasionPointNode):
    interactionNode.SetCurrentInteractionMode(slicer.vtkMRMLInteractionNode.ViewTransform)
    #self.creatEntryPoint() 
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
      
  def constructCurveReference(self, CurveManager,points, axis):
    step = 20 
    ApproximityPos = 25.0
    DestiationPos = 30.0
    if axis == 0:
      step = 50
      ApproximityPos = 85.0
      DestiationPos = 100.0
  
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
    for iPos in range(step,points.GetNumberOfPoints(),step):
      posModel = numpy.array(points.GetPoint(iPos))
      posModelValid = numpy.array(points.GetPoint(iPosValid))
      if  numpy.linalg.norm(posModel-posModelValid)> 50.0:
        continue
      iPosValid = iPos
      CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2]) #adding fiducials takes too long, check the event triggered by this operation
      CurveManager.cmLogic.SourceNode = CurveManager.curveFiducials
      CurveManager.cmLogic.updateCurve()
      print CurveManager.cmLogic.CurveLength
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
    if axis == 0:
      self.topPoint = points.GetPoint(jPos)
    else:
      self.topPoint = []
  
  def constructCurvePlanning(self, CurveManager,points, axis):
    if self.nasionPointNode:
      posNasion = numpy.array([0.0,0.0,0.0])
      self.nasionPointNode.GetNthFiducialPosition(0,posNasion)
      step = 20 
      if axis == 0:
        step = 50
    
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
      for iPos in range(step,points.GetNumberOfPoints(),step):
        posModel = numpy.array(points.GetPoint(iPos))
        posModelValid = numpy.array(points.GetPoint(iPosValid))
        if  numpy.linalg.norm(posModel-posModelValid)> 50.0:
          continue
        if axis == 0 and posModel[2]<posNasion[2]:
          break
        if axis == 1 and posModel[0]<posNasion[0]:
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
        if  axis == 0 and posModel[2]<posNasion[2]:
          break
        if  axis == 1 and posModel[0]<posNasion[0]:
          break
        jPosValid = jPos
      posModel = numpy.array(points.GetPoint(jPosValid))  
      CurveManager.curveFiducials.AddFiducial(posModel[0],posModel[1],posModel[2]) 
      
      CurveManager.cmLogic.SourceNode = CurveManager.curveFiducials
      CurveManager.cmLogic.updateCurve()
      CurveManager.cmLogic.SourceNode.SetAttribute('CurveMaker.CurveModel', CurveManager.cmLogic.DestinationNode.GetID())  
      CurveManager.cmLogic.enableAutomaticUpdate(1)
      CurveManager.cmLogic.setInterpolationMethod(1)
      CurveManager.cmLogic.setTubeRadius(0.5)  
    if axis == 1:
      self.topPoint = points.GetPoint(jPosValid)
    else:
      self.topPoint = []
      
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
  
  def creatEntryPoint(self) :
    ###All calculation is based on the RAS coordinates system
    if self.inputModel and (self.inputModel.GetClassName() == "vtkMRMLModelNode") and self.nasionPointNode:
      polyData = self.inputModel.GetPolyData()
      if polyData: 
        posNasion = numpy.array([0.0,0.0,0.0])
        self.nasionPointNode.GetNthFiducialPosition(0,posNasion)
        #self.cutSkullModel(self.inputModel, posNasion)
        plane = vtk.vtkPlane()
        plane.SetOrigin(posNasion[0],0,0)
        plane.SetNormal(1,0,0)
        sagittalPoints = vtk.vtkPoints()
        self.getIntersectPoints(polyData, plane, posNasion, 100, 0, sagittalPoints)
              
        ## Sorting   
        self.sortPoints(sagittalPoints, posNasion)   
        self.constructCurveReference(self.sagitalReferenceCurveManager, sagittalPoints, 0)  
            
        ##To do, calculate the curvature value points by point might be necessary to exclude the outliers   
        if self.topPoint:
          posNasionBack100 = self.topPoint
          coronalPoints = vtk.vtkPoints() 
          plane.SetOrigin(0,posNasionBack100[1],0)
          plane.SetNormal(0,1,0)
          self.getIntersectPoints(polyData, plane, posNasionBack100, 30, 1, coronalPoints) 
                    
          ## Sorting      
          self.sortPoints(coronalPoints, posNasionBack100)  
          self.constructCurveReference(self.coronalReferenceCurveManager, coronalPoints, 1)    
    pass
   
  def creatPlanningLine(self):
    ###All calculation is based on the RAS coordinates system
    if self.inputModel and (self.inputModel.GetClassName() == "vtkMRMLModelNode") and self.nasionPointNode:
      polyData = self.inputModel.GetPolyData()
      if polyData: 
        posNasion = numpy.array([0.0,0.0,0.0])
        self.nasionPointNode.GetNthFiducialPosition(0,posNasion)
        posTrajectory = numpy.array([0.0,0.0,0.0])
        self.trajectoryManager.getFirstPoint(posTrajectory)
        #self.cutSkullModel(self.inputModel, posNasion)
        plane = vtk.vtkPlane()
        plane.SetOrigin(0,posTrajectory[1],0)
        plane.SetNormal(0,1,0)
        coronalPoints = vtk.vtkPoints()
        self.getIntersectPointsPlanning(polyData, plane, posTrajectory, 1 , coronalPoints)
              
        ## Sorting   
        self.sortPoints(coronalPoints, posTrajectory)   
        
        self.constructCurvePlanning(self.coronalPlanningCurveManager, coronalPoints, 1)  
            
        ##To do, calculate the curvature value points by point might be necessary to exclude the outliers   
        if self.topPoint:
          posTractoryBack = self.topPoint
          saggitalPoints = vtk.vtkPoints() 
          plane.SetOrigin(posTractoryBack[0],0,0)
          plane.SetNormal(1,0,0)
          self.getIntersectPointsPlanning(polyData, plane, posTractoryBack, 0, saggitalPoints) 
                    
          ## Sorting      
          self.sortPoints(saggitalPoints, posTractoryBack)  
          self.constructCurvePlanning(self.sagitalPlanningCurveManager, saggitalPoints, 0)
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
