import vtk, slicer

class VentriculostomyUserEvents(object):
  ResetButtonEvent = vtk.vtkCommand.UserEvent + 100
  CloseCaseEvent = vtk.vtkCommand.UserEvent + 101
  LoadCaseCompletedEvent = vtk.vtkCommand.UserEvent + 102
  LoadParametersToScene = vtk.vtkCommand.UserEvent + 103
  TriggerDistalSelectionEvent = vtk.vtkCommand.UserEvent + 104
  UpdateCannulaTargetPoint = vtk.vtkCommand.UserEvent + 105
  SetSliceViewerEvent = vtk.vtkCommand.UserEvent + 106
  StartCaseImportEvent = vtk.vtkCommand.UserEvent + 107
  SaveModifiedFiducialEvent = vtk.vtkCommand.UserEvent + 108