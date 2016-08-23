import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import tempfile

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
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

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
    parametersFormLayout.addRow("Input Volume: ", self.inputVolumeSelector)

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
    parametersFormLayout.addRow("Output Model: ", self.outputModelSelector)

    
    #
    # output volume selector
    #
    self.outputSelector = slicer.qMRMLNodeComboBox()
    self.outputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.outputSelector.selectNodeUponCreation = True
    self.outputSelector.addEnabled = True
    self.outputSelector.removeEnabled = True
    self.outputSelector.noneEnabled = True
    self.outputSelector.showHidden = False
    self.outputSelector.showChildNodeTypes = False
    self.outputSelector.setMRMLScene( slicer.mrmlScene )
    self.outputSelector.setToolTip( "Pick the output to the algorithm." )
    parametersFormLayout.addRow("Output Volume: ", self.outputSelector)

    #
    # threshold value
    #
    self.imageThresholdSliderWidget = ctk.ctkSliderWidget()
    self.imageThresholdSliderWidget.singleStep = 0.1
    self.imageThresholdSliderWidget.minimum = -100
    self.imageThresholdSliderWidget.maximum = 100
    self.imageThresholdSliderWidget.value = 0.5
    self.imageThresholdSliderWidget.setToolTip("Set threshold value for computing the output image. Voxels that have intensities lower than this value will set to zero.")
    parametersFormLayout.addRow("Image threshold", self.imageThresholdSliderWidget)

    #
    # check box to trigger taking screen shots for later use in tutorials
    #
    self.enableScreenshotsFlagCheckBox = qt.QCheckBox()
    self.enableScreenshotsFlagCheckBox.checked = 0
    self.enableScreenshotsFlagCheckBox.setToolTip("If checked, take screen shots for tutorials. Use Save Data to write them to disk.")
    parametersFormLayout.addRow("Enable Screenshots", self.enableScreenshotsFlagCheckBox)

    #
    # Create Model Button
    #
    self.createModelButton = qt.QPushButton("Crete Model")
    self.createModelButton.toolTip = "Create a surface model."
    self.createModelButton.enabled = False
    parametersFormLayout.addRow(self.createModelButton)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)



    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.createModelButton.connect('clicked(bool)', self.onCreateModel)
    self.inputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onSelect()

  def cleanup(self):
    pass

  def onSelect(self):
    self.applyButton.enabled = self.inputVolumeSelector.currentNode() and self.outputSelector.currentNode()
    self.createModelButton.enabled =  self.inputVolumeSelector.currentNode() and self.outputModelSelector.currentNode()
    
    
  def onApplyButton(self):
    logic = VentriculostomyPlanningLogic()
    enableScreenshotsFlag = self.enableScreenshotsFlagCheckBox.checked
    imageThreshold = self.imageThresholdSliderWidget.value
    logic.run(self.inputVolumeSelector.currentNode(), self.outputSelector.currentNode(), imageThreshold, enableScreenshotsFlag)

  def onCreateModel(self):
    logic = VentriculostomyPlanningLogic()
    threshold = -500.0
    logic.createModel(self.inputVolumeSelector.currentNode(), self.outputModelSelector.currentNode(), threshold)
    

  def onReload(self,moduleName="VentriculostomyPlanning"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)
    

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

  def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
    """Validates if the output is not the same as input
    """
    if not inputVolumeNode:
      logging.debug('isValidInputOutputData failed: no input volume node defined')
      return False
    if not outputVolumeNode:
      logging.debug('isValidInputOutputData failed: no output volume node defined')
      return False
    if inputVolumeNode.GetID()==outputVolumeNode.GetID():
      logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
      return False
    return True

  def takeScreenshot(self,name,description,type=-1):
    # show the message even if not taking a screen shot
    slicer.util.delayDisplay('Take screenshot: '+description+'.\nResult is available in the Annotations module.', 3000)

    lm = slicer.app.layoutManager()
    # switch on the type to get the requested window
    widget = 0
    if type == slicer.qMRMLScreenShotDialog.FullLayout:
      # full layout
      widget = lm.viewport()
    elif type == slicer.qMRMLScreenShotDialog.ThreeD:
      # just the 3D window
      widget = lm.threeDWidget(0).threeDView()
    elif type == slicer.qMRMLScreenShotDialog.Red:
      # red slice window
      widget = lm.sliceWidget("Red")
    elif type == slicer.qMRMLScreenShotDialog.Yellow:
      # yellow slice window
      widget = lm.sliceWidget("Yellow")
    elif type == slicer.qMRMLScreenShotDialog.Green:
      # green slice window
      widget = lm.sliceWidget("Green")
    else:
      # default to using the full window
      widget = slicer.util.mainWindow()
      # reset the type so that the node is set correctly
      type = slicer.qMRMLScreenShotDialog.FullLayout

    # grab and convert to vtk image data
    qpixMap = qt.QPixmap().grabWidget(widget)
    qimage = qpixMap.toImage()
    imageData = vtk.vtkImageData()
    slicer.qMRMLUtils().qImageToVtkImageData(qimage,imageData)

    annotationLogic = slicer.modules.annotations.logic()
    annotationLogic.CreateSnapShot(name, description, type, 1, imageData)

  def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
    """
    Run the actual algorithm
    """

    if not self.isValidInputOutputData(inputVolume, outputVolume):
      slicer.util.errorDisplay('Input volume is the same as output volume. Choose a different output volume.')
      return False

    logging.info('Processing started')

    # Compute the thresholded output volume using the Threshold Scalar Volume CLI module
    cliParams = {'InputVolume': inputVolume.GetID(), 'OutputVolume': outputVolume.GetID(), 'ThresholdValue' : imageThreshold, 'ThresholdType' : 'Above'}
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True)

    # Capture screenshot
    if enableScreenshots:
      self.takeScreenshot('VentriculostomyPlanningTest-Start','MyScreenshot',-1)

    logging.info('Processing completed')

    return True


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
