import vtk, slicer

class VentriculostomyUserEvents(object):
  LoadParametersToScene = vtk.vtkCommand.UserEvent + 150
  CheckSagittalCorrectionEvent = vtk.vtkCommand.UserEvent + 151
  TriggerDistalSelectionEvent = vtk.vtkCommand.UserEvent + 152
  UpdateCannulaTargetPoint = vtk.vtkCommand.UserEvent + 153
  SetSliceViewerEvent = vtk.vtkCommand.UserEvent + 154
  SaveModifiedFiducialEvent = vtk.vtkCommand.UserEvent + 155
  VentricleCylinderModified = vtk.vtkCommand.UserEvent + 156
  ReverseViewClicked = vtk.vtkCommand.UserEvent + 157
  CheckCurrentProgressEvent = vtk.vtkCommand.UserEvent + 158
  ResetButtonEvent = vtk.vtkCommand.UserEvent + 159
  SegmentVesselWithSeedsEvent = vtk.vtkCommand.UserEvent + 160
  SagittalCorrectionFinishedEvent = vtk.vtkCommand.UserEvent + 161