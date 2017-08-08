import vtk, slicer

class VentriculostomyUserEvents(object):
  ResetButtonEvent = vtk.vtkCommand.UserEvent + 150
  CloseCaseEvent = vtk.vtkCommand.UserEvent + 151
  LoadCaseCompletedEvent = vtk.vtkCommand.UserEvent + 152
  LoadParametersToScene = vtk.vtkCommand.UserEvent + 153
  TriggerDistalSelectionEvent = vtk.vtkCommand.UserEvent + 154
  UpdateCannulaTargetPoint = vtk.vtkCommand.UserEvent + 155
  SetSliceViewerEvent = vtk.vtkCommand.UserEvent + 156
  StartCaseImportEvent = vtk.vtkCommand.UserEvent + 157
  SaveModifiedFiducialEvent = vtk.vtkCommand.UserEvent + 158