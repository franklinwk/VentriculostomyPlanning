import vtk, slicer

class VentriculostomyUserEvents(object):
  ResetButtonEvent = vtk.vtkCommand.UserEvent + 100
  CloseCaseEvent = vtk.vtkCommand.UserEvent + 101
  LoadCaseCompletedEvent = vtk.vtkCommand.UserEvent + 102
  LoadParametersToScene = vtk.vtkCommand.UserEvent + 103
  TriggerDistalSelectionEvent = vtk.vtkCommand.UserEvent + 104
