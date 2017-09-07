import slicer, vtk
from ctk import ctkAxesWidget
from SlicerDevelopmentToolboxUtils.buttons import LayoutButton, CheckableIconButton, BasicIconButton
import os
import qt

class GreenSliceLayoutButton(LayoutButton):
  """ LayoutButton inherited class which represents a button for the SlicerLayoutOneUpGreenSliceView including the icon.

  Args:
    text (str, optional): text to be displayed for the button
    parent (qt.QWidget, optional): parent of the button

  .. code-block:: python

    from VentriculostomyPlanningUtils.buttons import GreenSliceLayoutButton

    button = GreenSliceLayoutButton()
    button.show()
  """

  iconFileName=os.path.join(os.path.dirname(os.path.normpath(os.path.dirname(os.path.realpath(__file__)))),'Resources','Icons','LayoutOneUpGreenSliceView.png')
  _ICON = qt.QIcon(iconFileName)
  LAYOUT = slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpGreenSliceView

  def __init__(self, text="", parent=None, **kwargs):
    super(GreenSliceLayoutButton, self).__init__(text, parent, **kwargs)
    self.toolTip = "Green Slice Only Layout"


class ConventionalSliceLayoutButton(LayoutButton):
  """ LayoutButton inherited class which represents a button for the ConventionalSliceLayoutButton including the icon.

  Args:
    text (str, optional): text to be displayed for the button
    parent (qt.QWidget, optional): parent of the button

  .. code-block:: python

    from VentriculostomyPlanningUtils.buttons import ConventionalSliceLayoutButton

    button = ConventionalSliceLayoutButton()
    button.show()
  """
  iconFileName=os.path.join(os.path.dirname(os.path.normpath(os.path.dirname(os.path.realpath(__file__)))),'Resources','Icons','LayoutConventionalSliceView.png')
  _ICON = qt.QIcon(iconFileName)
  LAYOUT = slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalView

  def __init__(self, text="", parent=None, **kwargs):
    super(ConventionalSliceLayoutButton, self).__init__(text, parent, **kwargs)
    self.toolTip = "Conventional Slice Only Layout"


class ScreenShotButton(BasicIconButton):
  
  iconFileName=os.path.join(os.path.dirname(os.path.normpath(os.path.dirname(os.path.realpath(__file__)))),'Resources','Icons','screenShot.png')
  _ICON = qt.QIcon(iconFileName)
  
  @property
  def caseResultDir(self):
    return self._caseResultDir

  @caseResultDir.setter
  def caseResultDir(self, value):
    self._caseResultDir = value
    self.imageIndex = 0

  def __init__(self, text="", parent=None, **kwargs):
    super(ScreenShotButton, self).__init__(text, parent, **kwargs)
    import ScreenCapture
    self.cap = ScreenCapture.ScreenCaptureLogic()
    self.checkable = False
    self._caseResultDir = ""
    self.imageIndex = 0

  def _connectSignals(self):
    super(ScreenShotButton, self)._connectSignals()
    self.clicked.connect(self.onClicked)

  def onClicked(self):
    if self.caseResultDir:
      self.cap.showViewControllers(False)
      fileName = os.path.join(self._caseResultDir, 'Results', 'screenShot'+str(self.imageIndex)+'.png')
      if os.path.exists(fileName):
        self.imageIndex = self.imageIndex + 1
        fileName = os.path.join(self._caseResultDir, 'Results', 'screenShot' + str(self.imageIndex) + '.png')
      self.cap.captureImageFromView(None, fileName)
      self.cap.showViewControllers(True)
      self.imageIndex = self.imageIndex + 1
    else:
      slicer.util.warningDisplay("Case was not created, create a case first")
    pass

class ReverseViewOnCannulaButton(CheckableIconButton):
  
  iconFileName=os.path.join(os.path.dirname(os.path.normpath(os.path.dirname(os.path.realpath(__file__)))),'Resources','Icons','ReverseView.png')
  _ICON = qt.QIcon(iconFileName)
  
  @property
  def cannulaNode(self):
    return self._cannulaNode

  @cannulaNode.setter
  def cannulaNode(self,value):
    self._cannulaNode = value

  def __init__(self, text="", parent=None, **kwargs):
    super(ReverseViewOnCannulaButton, self).__init__(text, parent, **kwargs)
    self._cannulaNode = None
    self.cameraPos = [0.0] * 3
    self.cameraReversePos = None
    self.camera = None
    layoutManager = slicer.app.layoutManager()
    threeDView = layoutManager.threeDWidget(0).threeDView()
    displayManagers = vtk.vtkCollection()
    threeDView.getDisplayableManagers(displayManagers)
    for index in range(displayManagers.GetNumberOfItems()):
      if displayManagers.GetItemAsObject(index).GetClassName() == 'vtkMRMLCameraDisplayableManager':
        self.camera = displayManagers.GetItemAsObject(index).GetCameraNode().GetCamera()
        self.cameraPos = self.camera.GetPosition()
    self.toolTip = "Reverse the view of the cannula from the other end"

  def _onToggled(self, checked):
    if self.cannulaNode:
      layoutManager = slicer.app.layoutManager()
      threeDView = layoutManager.threeDWidget(0).threeDView()
      if checked == True:
        #self.setReverseViewButton.setText("  Reset View     ")
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
            threeDView.setPitchRollYawIncrement(360 - self.logic.yawAngle)
          threeDView.yaw()
          if self.cannulaNode and self.cannulaNode.GetNumberOfFiducials() >= 2:
            posSecond = [0.0] * 3
            self.cannulaNode.GetNthFiducialPosition(1, posSecond)
            threeDView.setFocalPoint(posSecond[0], posSecond[1], posSecond[2])
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
        threeDView.zoomIn()  # to refresh the 3D viewer, when the view position is inside the skull model, the model is not rendered,
        threeDView.zoomOut()  # Zoom in and out will refresh the viewer