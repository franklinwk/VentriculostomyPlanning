class EndPlacementModes(object):
  NotSpecifiedMode = "None"
  VesselSeeds = "vesselSeeds"
  VentricleTarget = "target"
  VentricleDistal = "distal"
  Nasion = "nasion"
  SagittalPoint = "sagittalPoint"

class SagittalCorrectionStatus(object):
  NotYetChecked = 1
  NeedCorrection = 2
  NoNeedForCorrection = 3

class CandidatePathStatus(object):
  NoPosteriorAndNoWithinKocherPoint = 1
  NoPosteriorPoint = 2
  NoWithinKocherPoint = 3
