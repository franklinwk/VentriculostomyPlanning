import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import tempfile
import CurveMaker

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
    linesCollapsibleButton = ctk.ctkCollapsibleButton()
    linesCollapsibleButton.text = "Lines"
    self.layout.addWidget(linesCollapsibleButton)

    # Layout within the dummy collapsible button
    linesFormLayout = qt.QFormLayout(linesCollapsibleButton)

    #
    # Mid-sagittal line
    #
    sagittalLineLayout = qt.QHBoxLayout()

    #-- Curve length
    self.lengthSagittalLineEdit = qt.QLineEdit()
    self.lengthSagittalLineEdit.text = '--'
    self.lengthSagittalLineEdit.readOnly = True
    self.lengthSagittalLineEdit.frame = True
    self.lengthSagittalLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthSagittalLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    sagittalLineLayout.addWidget(self.lengthSagittalLineEdit)
    lengthSagittalLineUnitLabel = qt.QLabel('mm  ')
    sagittalLineLayout.addWidget(lengthSagittalLineUnitLabel)

    #-- Add Point
    self.addPointForSagittalLineButton = qt.QPushButton("Add Points")
    self.addPointForSagittalLineButton.toolTip = "Add points for mid-sagittal line"
    self.addPointForSagittalLineButton.enabled = True
    self.addPointForSagittalLineButton.checkable = True    
    sagittalLineLayout.addWidget(self.addPointForSagittalLineButton)

    #-- Clear Point
    self.clearPointForSagittalLineButton = qt.QPushButton("Clear")
    self.clearPointForSagittalLineButton.toolTip = "Remove all points for mid-sagittal line"
    self.clearPointForSagittalLineButton.enabled = True
    sagittalLineLayout.addWidget(self.clearPointForSagittalLineButton)

    #-- Move the slice to the curve
    self.moveSliceSagittalLineButton = qt.QPushButton("Slice")
    self.moveSliceSagittalLineButton.toolTip = "Move the slice to the mid-sagittal line"
    self.moveSliceSagittalLineButton.enabled = True
    sagittalLineLayout.addWidget(self.moveSliceSagittalLineButton)

    linesFormLayout.addRow("Mid-Sagittal Line:", sagittalLineLayout)

    #
    # Coronal line
    #
    coronalLineLayout = qt.QHBoxLayout()

    #-- Curve length
    self.lengthCoronalLineEdit = qt.QLineEdit()
    self.lengthCoronalLineEdit.text = '--'
    self.lengthCoronalLineEdit.readOnly = True
    self.lengthCoronalLineEdit.frame = True
    self.lengthCoronalLineEdit.styleSheet = "QLineEdit { background:transparent; }"
    self.lengthCoronalLineEdit.cursor = qt.QCursor(qt.Qt.IBeamCursor)
    coronalLineLayout.addWidget(self.lengthCoronalLineEdit)
    lengthCoronalLineUnitLabel = qt.QLabel('mm  ')
    coronalLineLayout.addWidget(lengthCoronalLineUnitLabel)

    #-- Add Point
    self.addPointForCoronalLineButton = qt.QPushButton("Add Points")
    self.addPointForCoronalLineButton.toolTip = "Add points for coronal line"
    self.addPointForCoronalLineButton.enabled = True
    self.addPointForCoronalLineButton.checkable = True    
    coronalLineLayout.addWidget(self.addPointForCoronalLineButton)

    #-- Clear Point
    self.clearPointForCoronalLineButton = qt.QPushButton("Clear")
    self.clearPointForCoronalLineButton.toolTip = "Remove all points for coronal line"
    self.clearPointForCoronalLineButton.enabled = True
    coronalLineLayout.addWidget(self.clearPointForCoronalLineButton)

    #-- Move the slice to the curve
    self.moveSliceCoronalLineButton = qt.QPushButton("Slice")
    self.moveSliceCoronalLineButton.toolTip = "Move the slice to the coronal line"
    self.moveSliceCoronalLineButton.enabled = True
    coronalLineLayout.addWidget(self.moveSliceCoronalLineButton)

    linesFormLayout.addRow("Coronal Line:", coronalLineLayout)

    self.lockInitialLinesCheckBox = qt.QCheckBox()
    self.lockInitialLinesCheckBox.checked = 0
    self.lockInitialLinesCheckBox.setToolTip("If checked, the lines will be locked.")
    linesFormLayout.addRow("Lock:", self.lockInitialLinesCheckBox)
    
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

    self.lockTrajectoryCheckBox = qt.QCheckBox()
    self.lockTrajectoryCheckBox.checked = 0
    self.lockTrajectoryCheckBox.setToolTip("If checked, the trajectory will be locked.")
    trajectoryFormLayout.addRow("Lock:", self.lockTrajectoryCheckBox)
    
    #
    # Inverse Lines
    #
    inverseLinesCollapsibleButton = ctk.ctkCollapsibleButton()
    inverseLinesCollapsibleButton.text = "InverseLines"
    self.layout.addWidget(inverseLinesCollapsibleButton)
    
    # Layout within the dummy collapsible button
    inverseLinesFormLayout = qt.QFormLayout(inverseLinesCollapsibleButton)

    self.lockInverseLinesCheckBox = qt.QCheckBox()
    self.lockInverseLinesCheckBox.checked = 0
    self.lockInverseLinesCheckBox.setToolTip("If checked, the lines will be locked.")
    inverseLinesFormLayout.addRow("Lock:", self.lockInverseLinesCheckBox)
    

    ## PatientModel Area
    ##
    #patientModelCollapsibleButton = ctk.ctkCollapsibleButton()
    #patientModelCollapsibleButton.text = "Patient Model"
    #self.layout.addWidget(patientModelCollapsibleButton)
    #
    ## Layout within the dummy collapsible button
    #patientModelFormLayout = qt.QFormLayout(patientModelCollapsibleButton)
    #
    ##
    ## input volume selector
    ##
    #self.inputVolumeSelector = slicer.qMRMLNodeComboBox()
    #self.inputVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    #self.inputVolumeSelector.selectNodeUponCreation = True
    #self.inputVolumeSelector.addEnabled = False
    #self.inputVolumeSelector.removeEnabled = False
    #self.inputVolumeSelector.noneEnabled = False
    #self.inputVolumeSelector.showHidden = False
    #self.inputVolumeSelector.showChildNodeTypes = False
    #self.inputVolumeSelector.setMRMLScene( slicer.mrmlScene )
    #self.inputVolumeSelector.setToolTip( "Pick the input to the algorithm." )
    #patientModelFormLayout.addRow("Input Volume: ", self.inputVolumeSelector)
    #
    ##
    ## output volume selector
    ##
    #self.outputModelSelector = slicer.qMRMLNodeComboBox()
    #self.outputModelSelector.nodeTypes = ["vtkMRMLModelNode"]
    #self.outputModelSelector.selectNodeUponCreation = True
    #self.outputModelSelector.addEnabled = True
    #self.outputModelSelector.removeEnabled = True
    #self.outputModelSelector.noneEnabled = True
    #self.outputModelSelector.showHidden = False
    #self.outputModelSelector.showChildNodeTypes = False
    #self.outputModelSelector.setMRMLScene( slicer.mrmlScene )
    #self.outputModelSelector.setToolTip( "Pick the output to the algorithm." )
    #patientModelFormLayout.addRow("Output Model: ", self.outputModelSelector)
    #
    #
    ##
    ## Create Model Button
    ##
    #self.createModelButton = qt.QPushButton("Crete Model")
    #self.createModelButton.toolTip = "Create a surface model."
    #self.createModelButton.enabled = False
    #patientModelFormLayout.addRow(self.createModelButton)

    # connections
    #self.createModelButton.connect('clicked(bool)', self.onCreateModel)
    #self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    #self.outputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Sagittal line
    self.addPointForSagittalLineButton.connect('toggled(bool)', self.onEditSagittalLine)
    self.clearPointForSagittalLineButton.connect('clicked(bool)', self.onClearSagittalLine)
    self.moveSliceSagittalLineButton.connect('clicked(bool)', self.onMoveSliceSagittalLine)
    self.logic.setSagittalLineModifiedEventHandler(self.onSagittalLineModified)

    # Coronal line
    self.addPointForCoronalLineButton.connect('toggled(bool)', self.onEditCoronalLine)
    self.clearPointForCoronalLineButton.connect('clicked(bool)', self.onClearCoronalLine)
    self.moveSliceCoronalLineButton.connect('clicked(bool)', self.onMoveSliceCoronalLine)
    self.logic.setCoronalLineModifiedEventHandler(self.onCoronalLineModified)

    self.lockInitialLinesCheckBox.connect('toggled(bool)', self.onLock)

    # Needle trajectory
    self.addTrajectoryButton.connect('toggled(bool)', self.onEditTrajectory)
    self.clearTrajectoryButton.connect('clicked(bool)', self.onClearTrajectory)
    self.logic.setTrajectoryModifiedEventHandler(self.onTrajectoryModified)
    self.lockTrajectoryCheckBox.connect('toggled(bool)', self.onLock)


    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    pass

  def onSelect(self):
    #self.createModelButton.enabled =  self.inputVolumeSelector.currentNode() and self.outputModelSelector.currentNode()
    pass
    
    
  #def onCreateModel(self):
  #  #logic = VentriculostomyPlanningLogic()
  #  threshold = -500.0
  #  self.logic.createModel(self.inputVolumeSelector.currentNode(), self.outputModelSelector.currentNode(), threshold)


  # Event handlers for sagittal line
  def onEditSagittalLine(self, switch):

    if switch == True:
      self.addPointForCoronalLineButton.checked = False
      self.addTrajectoryButton.checked = False
      self.logic.startEditSagittalLine()
    else:
      self.logic.endEditSagittalLine()

  def onClearSagittalLine(self):
    
    self.logic.clearSagittalLine()

  def onSagittalLineModified(self, caller, event):
    self.lengthSagittalLineEdit.text = '%.2f' % self.logic.getSagittalLineLength()

  def onMoveSliceSagittalLine(self):
    self.logic.moveSliceSagittalLine()

  # Event handlers for coronal line
  def onEditCoronalLine(self, switch):

    if switch == True:
      self.addPointForSagittalLineButton.checked = False
      self.addTrajectoryButton.checked = False
      self.logic.startEditCoronalLine()
    else:
      self.logic.endEditCoronalLine()

  def onClearCoronalLine(self):
    
    self.logic.clearCoronalLine()

  def onCoronalLineModified(self, caller, event):
    self.lengthCoronalLineEdit.text = '%.2f' % self.logic.getCoronalLineLength()
    
  def onMoveSliceCoronalLine(self):
    self.logic.moveSliceCoronalLine()

  # Event handlers for trajectory
  def onEditTrajectory(self, switch):

    if switch == True:
      self.addPointForSagittalLineButton.checked = False
      self.addPointForCoronalLineButton.checked = False
      self.logic.startEditTrajectory()
    else:
      self.logic.endEditCoronalLine()
    
  def onClearTrajectory(self):
    self.logic.clearTrajectory()
    
  def onTrajectoryModified(self, caller, event):
    self.lengthTrajectoryEdit.text = '%.2f' % self.logic.getTrajectoryLength()

  def onLock(self):
    if self.lockInitialLinesCheckBox.checked == 1:
      self.addPointForSagittalLineButton.enabled = False
      self.clearPointForSagittalLineButton.enabled = False
      self.addPointForCoronalLineButton.enabled = False
      self.clearPointForCoronalLineButton.enabled = False
      self.logic.lockInitialLine()
    else:
      self.addPointForSagittalLineButton.enabled = True
      self.clearPointForSagittalLineButton.enabled = True
      self.addPointForCoronalLineButton.enabled = True
      self.clearPointForCoronalLineButton.enabled = True
      self.logic.unlockInitialLine()

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
    
    self.sagittalCurveManager = CurveManager()
    self.sagittalCurveManager.setName("S1")
    self.sagittalCurveManager.setSliceID("vtkMRMLSliceNodeYellow")
    self.sagittalCurveManager.setDefaultSlicePositionToFirstPoint()
    self.sagittalCurveManager.setModelColor(1.0, 1.0, 0.0)
    
    self.coronalCurveManager = CurveManager()
    self.coronalCurveManager.setName("C1")
    self.coronalCurveManager.setSliceID("vtkMRMLSliceNodeGreen")
    self.coronalCurveManager.setDefaultSlicePositionToLastPoint()
    self.coronalCurveManager.setModelColor(0.0, 1.0, 0.0)

    self.trajectoryManager = CurveManager()
    self.trajectoryManager.setName("T")
    self.trajectoryManager.setDefaultSlicePositionToLastPoint()
    self.trajectoryManager.setModelColor(0.0, 1.0, 1.0)

    
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


  def startEditSagittalLine(self):

    self.sagittalCurveManager.startEditLine()
    
  def endEditSagittalLine(self):

    self.sagittalCurveManager.endEditLine()

  def clearSagittalLine(self):
    
    self.sagittalCurveManager.clearLine()

  def setSagittalLineModifiedEventHandler(self, handler):

    self.sagittalCurveManager.setModifiedEventHandler(handler)

  def getSagittalLineLength(self):
    return self.sagittalCurveManager.getLength()

  def moveSliceSagittalLine(self):
    self.sagittalCurveManager.moveSliceToLine()

  def startEditCoronalLine(self):

    pos = [0.0] * 3
    self.sagittalCurveManager.getLastPoint(pos)
    self.coronalCurveManager.startEditLine(pos)
    
  def endEditCoronalLine(self):

    self.coronalCurveManager.endEditLine()

  def clearCoronalLine(self):
    
    self.coronalCurveManager.clearLine()

  def setCoronalLineModifiedEventHandler(self, handler):

    self.coronalCurveManager.setModifiedEventHandler(handler)

  def getCoronalLineLength(self):
    return self.coronalCurveManager.getLength()

  def moveSliceCoronalLine(self):
    self.coronalCurveManager.moveSliceToLine()

  def lockInitialLine(self):
    self.sagittalCurveManager.lockLine()
    self.coronalCurveManager.lockLine()

  def unlockInitialLine(self):
    self.sagittalCurveManager.unlockLine()
    self.coronalCurveManager.unlockLine()

  def startEditTrajectory(self):
    self.trajectoryManager.startEditLine()

  def endEditTrajectory(self):
    self.trajectoryManager.endEditLine()

  def clearTrajectory(self):
    self.trajectoryManager.clearLine()

  def setTrajectoryModifiedEventHandler(self, handler):
    self.trajectoryManager.setModifiedEventHandler(handler)

  def getTrajectoryLength(self):
    return self.trajectoryManager.getLength()

  def createModel(self, inputVolumeNode, outputModelNode, thresholdValue):

    Decimate = 0.25

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

    cast = vtk.vtkImageCast()
    cast.SetInputConnection(threshold.GetOutputPort())
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
    decimator.SetTargetReduction(0.001)
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
    slicer.mrmlScene.AddNode(modelDisplayNode)
    outputModelNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())

  
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
