# -*- coding: utf-8 -*-
from __main__ import vtk, qt, ctk, slicer
import time

class LabelMapBinning:
  def __init__(self, parent):
    parent.title = "Label Map Binning"
    parent.categories = ["Filtering"]
    parent.contributors = ["Franklin King"]
    
    parent.helpText = """
    Add help text
    """
    parent.acknowledgementText = """
""" 
    # module build directory is not the current directory when running the python script, hence why the usual method of finding resources didn't work ASAP
    self.parent = parent

class LabelMapBinningWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    self.lastCommandId = 0
    self.timeoutCounter = 0
    if not parent:
      self.setup()
      self.parent.show()
  
  def setup(self):
    # Point Distance
    controlCollapseButton = ctk.ctkCollapsibleButton()
    controlCollapseButton.text = "Control"
    self.layout.addWidget(controlCollapseButton)

    controlLayout = qt.QFormLayout(controlCollapseButton)    
  
    self.nodeSelector = slicer.qMRMLNodeComboBox()
    self.nodeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.nodeSelector.selectNodeUponCreation = False
    self.nodeSelector.noneEnabled = False
    self.nodeSelector.addEnabled = False
    self.nodeSelector.showHidden = False
    self.nodeSelector.setMRMLScene( slicer.mrmlScene )
    self.nodeSelector.setToolTip( "Pick Continuous Label Map" )
    controlLayout.addRow("LabelMap Node:", self.nodeSelector)

    self.newNodeSelector = slicer.qMRMLNodeComboBox()
    self.newNodeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.newNodeSelector.selectNodeUponCreation = True
    self.newNodeSelector.noneEnabled = False
    self.newNodeSelector.addEnabled = True
    self.newNodeSelector.showHidden = False
    self.newNodeSelector.setMRMLScene( slicer.mrmlScene )
    self.newNodeSelector.setToolTip( "Pick Node for Binned Label Map" )
    controlLayout.addRow("New Node:", self.newNodeSelector)    

    self.lowLabelSpinBox = qt.QSpinBox()
    self.lowLabelSpinBox.setSingleStep(1)
    self.lowLabelSpinBox.setValue(1)
    controlLayout.addRow("Label under threshold value:", self.lowLabelSpinBox)

    self.thresholdSpinBox = qt.QDoubleSpinBox()
    self.thresholdSpinBox.setSingleStep(0.01)
    self.thresholdSpinBox.setValue(0.7)
    controlLayout.addRow("Threshold value:", self.thresholdSpinBox)

    self.highLabelSpinBox = qt.QSpinBox()
    self.highLabelSpinBox.setSingleStep(1)
    self.highLabelSpinBox.setValue(0)
    controlLayout.addRow("Label over threshold value:", self.highLabelSpinBox)

    self.applyButton = qt.QPushButton("Apply")
    controlLayout.addRow(self.applyButton)
    self.applyButton.connect('clicked(bool)', self.onApply)
    

  def onApply(self):   
    oldNode = self.nodeSelector.currentNode()
    newNode = self.newNodeSelector.currentNode()

    self.runThreshold(oldNode.GetID(), newNode.GetID(), "Below", self.thresholdSpinBox.value, 999999.0) #temporary outside value
    self.runThreshold(newNode.GetID(), newNode.GetID(), "Below", 999999.0, self.highLabelSpinBox.value)
    self.runThreshold(newNode.GetID(), newNode.GetID(), "Above", 999998.0, self.lowLabelSpinBox.value)
    
    self.convertToLabelMap(newNode, (newNode.GetName() + "_label"))


  def runThreshold(self, oldNodeID, newNodeID, thresholdType, thresholdValue, outsideValue):
    thresholdScalar = slicer.modules.thresholdscalarvolume

    parameters = {}
    parameters["InputVolume"] = oldNodeID
    parameters["OutputVolume"] = newNodeID

    parameters["ThresholdType"] = thresholdType
    parameters["ThresholdValue"] = thresholdValue
    parameters["OutsideValue"] = outsideValue
    
    return (slicer.cli.runSync(thresholdScalar, None, parameters))


  def convertToLabelMap(self, volumeNode, name):
    volumesLogic = slicer.modules.volumes.logic()

    newLabelNode = slicer.vtkMRMLLabelMapVolumeNode()
    newLabelNode.SetName(volumeNode.GetName())
    newLabelNode.SetHideFromEditors(volumeNode.GetHideFromEditors())
    newLabelNode.SetSaveWithScene(volumeNode.GetSaveWithScene())
    newLabelNode.SetSelectable(volumeNode.GetSelectable())
    newLabelNode.SetSingletonTag(volumeNode.GetSingletonTag())
    newLabelNode.SetDescription(volumeNode.GetDescription())
    #TODO: Attributes
    slicer.mrmlScene.AddNode(newLabelNode)
    
    volumesLogic.CreateLabelVolumeFromVolume(slicer.mrmlScene, newLabelNode, volumeNode)
    slicer.mrmlScene.RemoveNode(volumeNode)  

    
  
class LabelMapBinningLogic:
  def __init__(self):
    pass
 
  


