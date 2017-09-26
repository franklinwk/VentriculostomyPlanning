import vtk, slicer

class VentriculostomyUserEvents(object):
  ResetButtonEvent = vtk.vtkCommand.UserEvent + 150
  LoadParametersToScene = vtk.vtkCommand.UserEvent + 151
  TriggerDistalSelectionEvent = vtk.vtkCommand.UserEvent + 152
  UpdateCannulaTargetPoint = vtk.vtkCommand.UserEvent + 153
  SetSliceViewerEvent = vtk.vtkCommand.UserEvent + 154
  SaveModifiedFiducialEvent = vtk.vtkCommand.UserEvent + 155
  VentricleCylinderModified = vtk.vtkCommand.UserEvent + 156
  ReverseViewClicked = vtk.vtkCommand.UserEvent + 157