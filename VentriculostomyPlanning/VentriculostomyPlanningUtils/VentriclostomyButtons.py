import slicer, vtk
from ctk import ctkAxesWidget
from SlicerDevelopmentToolboxUtils.buttons import LayoutButton, CheckableIconButton

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

  _ICON_FILENAME = 'LayoutOneUpGreenSliceView.png'
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

  _ICON_FILENAME = 'LayoutConventionalSliceView.png'
  LAYOUT = slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalView

  def __init__(self, text="", parent=None, **kwargs):
    super(ConventionalSliceLayoutButton, self).__init__(text, parent, **kwargs)
    self.toolTip = "Conventional Slice Only Layout"


class ReverseViewOnCannulaButton(CheckableIconButton):
  _ICON_FILENAME = 'ReverseView.png'

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