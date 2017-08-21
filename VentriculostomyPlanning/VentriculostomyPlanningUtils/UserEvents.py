import vtk, slicer

class VentriculostomyUserEvents(object):
  ResetButtonEvent = vtk.vtkCommand.UserEvent + 150
  LoadParametersToScene = vtk.vtkCommand.UserEvent + 153
  TriggerDistalSelectionEvent = vtk.vtkCommand.UserEvent + 154
  UpdateCannulaTargetPoint = vtk.vtkCommand.UserEvent + 155
  SetSliceViewerEvent = vtk.vtkCommand.UserEvent + 156
  SaveModifiedFiducialEvent = vtk.vtkCommand.UserEvent + 158
  VentricleCylinderModified = vtk.vtkCommand.UserEvent + 159