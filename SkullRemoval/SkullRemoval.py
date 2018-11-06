# -*- coding: utf-8 -*-
from __main__ import vtk, qt, ctk, slicer
import time

class SkullRemoval:
  def __init__(self, parent):
    parent.title = "Skull Removal"
    parent.categories = ["Filtering"]
    parent.contributors = ["Franklin King"]
    
    parent.helpText = """
    Add help text
    """
    parent.acknowledgementText = """
""" 
    # module build directory is not the current directory when running the python script, hence why the usual method of finding resources didn't work ASAP
    self.parent = parent

class SkullRemovalWidget:
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
    self.nodeSelector.setToolTip( "Pick Volume" )
    controlLayout.addRow("Volume Node:", self.nodeSelector)    
  
    self.applyButton = qt.QPushButton("Apply")
    controlLayout.addRow(self.applyButton)
    self.applyButton.connect('clicked(bool)', self.onApply)
    
  def runMask(self, volume, maskVolume, maskedVolume):
    maskScalar = slicer.modules.maskscalarvolume
    parameters = {}
    parameters["InputVolume"] = volume.GetID()
    parameters["MaskVolume"] = maskVolume.GetID()
    parameters["OutputVolume"] = maskedVolume.GetID()
    return slicer.cli.runSync(maskScalar, None, parameters)

  def runSubtract(self, volume, maskedVolume, subtractedVolume):
    subScalar = slicer.modules.subtractscalarvolumes
    parameters = {}
    parameters["inputVolume1"] = volume.GetID()
    parameters["inputVolume2"] = maskedVolume.GetID()

    parameters["outputVolume"] = subtractedVolume.GetID()
    return slicer.cli.runSync(subScalar, None, parameters)
    
    
  def onApply(self):   
    volume = self.nodeSelector.currentNode()
    segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    segmentationNode.CreateDefaultDisplayNodes()
    segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(volume)
    addedSegmentID = segmentationNode.GetSegmentation().AddEmptySegment("Skull")

    segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
    segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
    segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
    segmentEditorWidget.setSegmentationNode(segmentationNode)
    segmentEditorWidget.setMasterVolumeNode(volume)

    segmentEditorWidget.setActiveEffectByName("Threshold")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("MinimumThreshold","550")
    effect.setParameter("MaximumThreshold","3000")
    effect.self().onApply()

    segmentEditorWidget.setActiveEffectByName("Islands")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("Operation","KEEP_LARGEST_ISLAND")
    effect.self().onApply()

    segmentEditorWidget.setActiveEffectByName("Margin")
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("MarginSizeMm","3.5")
    effect.self().onApply()

    labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
    labelmapVolumeNode.SetName("MaskVolume")
    slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(segmentationNode, labelmapVolumeNode)

    maskedVolume = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode')
    maskedVolume.SetName("MaskedVolume")    
    self.runMask(volume, labelmapVolumeNode, maskedVolume)
    
    subtractedVolume = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode')
    subtractedVolume.SetName("Cropped_volume_sub")    
    self.runSubtract(volume, maskedVolume, subtractedVolume)

class SkullRemovalLogic:
  def __init__(self):
    pass
 
  


