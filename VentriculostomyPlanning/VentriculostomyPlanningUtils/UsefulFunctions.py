import vtk, qt, ctk, slicer
import numpy
import SimpleITK as sitk
import sitkUtils
import math

class UsefulFunctions(object):

  def __init__(self):
    pass

  def clipVolumeWithModelNode(self, inputVolume, clippingModelNode, clipOutsideSurface, fillValue):
    """
    Fill voxels of the input volume inside/outside the clipping model with the provided fill value
    """
    # Determine the transform between the box and the image IJK coordinate systems
    rasToModel = vtk.vtkMatrix4x4()
    if clippingModelNode.GetTransformNodeID() != None:
      modelTransformNode = slicer.mrmlScene.GetNodeByID(clippingModelNode.GetTransformNodeID())
      boxToRas = vtk.vtkMatrix4x4()
      modelTransformNode.GetMatrixTransformToWorld(boxToRas)
      rasToModel.DeepCopy(boxToRas)
      rasToModel.Invert()
    polyData = clippingModelNode.GetPolyData()
    return self.clipVolumeWithPolyData(inputVolume, polyData, clipOutsideSurface, fillValue, rasToModel)

  def clipVolumeWithPolyData(self, inputVolume, polyData, clipOutsideSurface, fillValue, leftTransformMatrix = None):
    leftMatrix = vtk.vtkMatrix4x4()
    leftMatrix.Identity()
    if leftTransformMatrix:
      leftMatrix.DeepCopy(leftTransformMatrix)
    ijkToRas = vtk.vtkMatrix4x4()
    inputVolume.GetIJKToRASMatrix(ijkToRas)
    ijkToModel = vtk.vtkMatrix4x4()
    vtk.vtkMatrix4x4.Multiply4x4(leftMatrix, ijkToRas, ijkToModel)
    modelToIjkTransform = vtk.vtkTransform()
    modelToIjkTransform.SetMatrix(ijkToModel)
    modelToIjkTransform.Inverse()
    transformModelToIjk = vtk.vtkTransformPolyDataFilter()
    transformModelToIjk.SetTransform(modelToIjkTransform)
    transformModelToIjk.SetInputData(polyData)
    transformModelToIjk.Update()

    # Use the stencil to fill the volume

    # Convert model to stencil
    polyToStencil = vtk.vtkPolyDataToImageStencil()
    polyToStencil.SetInputConnection(transformModelToIjk.GetOutputPort())
    polyToStencil.SetOutputSpacing(inputVolume.GetImageData().GetSpacing())
    polyToStencil.SetOutputOrigin(inputVolume.GetImageData().GetOrigin())
    polyToStencil.SetOutputWholeExtent(inputVolume.GetImageData().GetExtent())

    # Apply the stencil to the volume
    stencilToImage = vtk.vtkImageStencil()
    stencilToImage.SetInputConnection(inputVolume.GetImageDataConnection())
    stencilToImage.SetStencilConnection(polyToStencil.GetOutputPort())
    if clipOutsideSurface:
      stencilToImage.ReverseStencilOff()
    else:
      stencilToImage.ReverseStencilOn()
    stencilToImage.SetBackgroundValue(fillValue)
    stencilToImage.Update()

    # Update the volume with the stencil operation result
    outputImageData = vtk.vtkImageData()
    outputImageData.DeepCopy(stencilToImage.GetOutput())
    return outputImageData

  def createHoleFilledVolumeNode(self, ventricleVolume, thresholdValue, samplingFactor, morphologyParameters):
    holeFillKernelSize = morphologyParameters[0]
    maskKernelSize = morphologyParameters[1]
    resampleFilter = sitk.ResampleImageFilter()
    ventricleImage = sitk.Cast(sitkUtils.PullFromSlicer(ventricleVolume.GetID()), sitk.sitkInt16)
    resampleFilter.SetSize(numpy.array(ventricleImage.GetSize()) / samplingFactor)
    resampleFilter.SetOutputSpacing(numpy.array(ventricleImage.GetSpacing()) * samplingFactor)
    resampleFilter.SetOutputDirection(ventricleImage.GetDirection())
    resampleFilter.SetOutputOrigin(numpy.array(ventricleImage.GetOrigin()))
    resampledImage = resampleFilter.Execute(ventricleImage)
    thresholdFilter = sitk.BinaryThresholdImageFilter()
    thresholdImage = thresholdFilter.Execute(resampledImage, thresholdValue, 10000, 1, 0)
    padFilter = sitk.ConstantPadImageFilter()
    padFilter.SetPadLowerBound(holeFillKernelSize)
    padFilter.SetPadUpperBound(holeFillKernelSize)
    paddedImage = padFilter.Execute(thresholdImage)
    dilateFilter = sitk.BinaryDilateImageFilter()
    dilateFilter.SetKernelRadius(holeFillKernelSize)
    dilateFilter.SetBackgroundValue(0)
    dilateFilter.SetForegroundValue(1)
    dilatedImage = dilateFilter.Execute(paddedImage)
    erodeFilter = sitk.BinaryErodeImageFilter()
    erodeFilter.SetKernelRadius(holeFillKernelSize)
    erodeFilter.SetBackgroundValue(0)
    erodeFilter.SetForegroundValue(1)
    erodedImage = erodeFilter.Execute(dilatedImage)
    fillHoleFilter = sitk.BinaryFillholeImageFilter()
    holefilledImage = fillHoleFilter.Execute(erodedImage)
    dilateFilter = sitk.BinaryDilateImageFilter()
    dilateFilter.SetKernelRadius(maskKernelSize)
    dilateFilter.SetBackgroundValue(0)
    dilateFilter.SetForegroundValue(1)
    dilatedImage = dilateFilter.Execute(holefilledImage)
    subtractFilter = sitk.SubtractImageFilter()
    subtractedImage = subtractFilter.Execute(dilatedImage, holefilledImage)
    holefilledImageNode = sitkUtils.PushToSlicer(holefilledImage, "holefilledImage", 0, False)
    subtractedImageNode = sitkUtils.PushToSlicer(subtractedImage, "subtractedImage", 0, False)
    return holefilledImageNode, subtractedImageNode

  def createModelBaseOnVolume(self, holefilledImageNode, outputModelNode):
    if holefilledImageNode:
      holefilledImageData = holefilledImageNode.GetImageData()
      cast = vtk.vtkImageCast()
      cast.SetInputData(holefilledImageData)
      cast.SetOutputScalarTypeToUnsignedChar()
      cast.Update()
      labelVolumeNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLLabelMapVolumeNode")
      slicer.mrmlScene.AddNode(labelVolumeNode)
      labelVolumeNode.SetName("Threshold")
      labelVolumeNode.SetSpacing(holefilledImageData.GetSpacing())
      labelVolumeNode.SetOrigin(holefilledImageData.GetOrigin())
      matrix = vtk.vtkMatrix4x4()
      holefilledImageNode.GetIJKToRASMatrix(matrix)
      labelVolumeNode.SetIJKToRASMatrix(matrix)
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
      smoother.BoundarySmoothingOn()
      smoother.FeatureEdgeSmoothingOff()
      smoother.SetFeatureAngle(120.0)
      smoother.SetPassBand(0.001)
      smoother.NonManifoldSmoothingOn()
      smoother.NormalizeCoordinatesOn()
      smoother.Update()

      pthreshold = vtk.vtkThreshold()
      pthreshold.SetInputConnection(smoother.GetOutputPort())
      pthreshold.ThresholdBetween(1, 1) ## Label 1
      pthreshold.ReleaseDataFlagOn()

      geometryFilter = vtk.vtkGeometryFilter()
      geometryFilter.SetInputConnection(pthreshold.GetOutputPort())
      geometryFilter.ReleaseDataFlagOn()

      decimator = vtk.vtkDecimatePro()
      decimator.SetInputConnection(geometryFilter.GetOutputPort())
      decimator.SetFeatureAngle(60)
      decimator.SplittingOff()
      decimator.PreserveTopologyOn()
      decimator.SetMaximumError(1)
      decimator.SetTargetReduction(0.5) #0.001 only reduce the points by 0.1%, 0.5 is 50% off
      decimator.ReleaseDataFlagOff()
      decimator.Update()

      smootherPoly = vtk.vtkSmoothPolyDataFilter()
      smootherPoly.SetRelaxationFactor(0.33)
      smootherPoly.SetFeatureAngle(60)
      smootherPoly.SetConvergence(0)

      if transformIJKtoRAS.GetMatrix().Determinant() < 0:
        reverser = vtk.vtkReverseSense()
        reverser.SetInputConnection(decimator.GetOutputPort())
        reverser.ReverseNormalsOn()
        reverser.ReleaseDataFlagOn()
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
      outputModelNode.SetAttribute("vtkMRMLModelNode.modelCreated","True")
      outputModelNode.GetDisplayNode().SetVisibility(1)
      slicer.mrmlScene.RemoveNode(labelVolumeNode)
    pass

  def getClosedCuttedModel(self, cutPlanes, polyData):
    clipper = vtk.vtkClipClosedSurface()
    clipper.SetClippingPlanes(cutPlanes)
    clipper.SetActivePlaneId(2)
    clipper.SetInputData(polyData)
    clipper.Update()
    cuttedPolyData = clipper.GetOutput()
    return cuttedPolyData

  def sortVTKPoints(self, inputPointVector, referencePoint):
    minDistanceIndex = 0
    minDistance = 1e10
    for iPos in range(inputPointVector.GetNumberOfPoints()):
      currentPos = numpy.array(inputPointVector.GetPoint(iPos))
      minDistance = numpy.linalg.norm(currentPos-referencePoint)
      minDistanceIndex = iPos
      for jPos in range(iPos, inputPointVector.GetNumberOfPoints()):
        posModelPost = numpy.array(inputPointVector.GetPoint(jPos))
        distanceModelPostNasion = numpy.linalg.norm(posModelPost-referencePoint)
        if distanceModelPostNasion <  minDistance:
          minDistanceIndex = jPos
          minDistance = distanceModelPostNasion
      inputPointVector.SetPoint(iPos,inputPointVector.GetPoint(minDistanceIndex))
      inputPointVector.SetPoint(minDistanceIndex,currentPos)
    pass

  def calculateLineModelIntersect(self, polyData, posFirst, posSecond, intersectionNode=None):
    if polyData:
      obbTree = vtk.vtkOBBTree()
      obbTree.SetDataSet(polyData)
      obbTree.BuildLocator()
      pointsVTKintersection = vtk.vtkPoints()
      hasIntersection = obbTree.IntersectWithLine(posFirst, posSecond, pointsVTKintersection, None)
      if hasIntersection>0:
        pointsVTKIntersectionData = pointsVTKintersection.GetData()
        numPointsVTKIntersection = pointsVTKIntersectionData.GetNumberOfTuples()
        if intersectionNode:
          validPosIndex = intersectionNode.GetNumberOfFiducials()
          for idx in range(numPointsVTKIntersection):
            posTuple = pointsVTKIntersectionData.GetTuple3(idx)
            if ((posTuple[0]-posFirst[0])*(posSecond[0]-posFirst[0])>0) and abs(posTuple[0]-posFirst[0])<abs(posSecond[0]-posFirst[0]):
              # check if the intersection if within the posFist and posSecond
              intersectionNode.AddFiducial(0,0,0)
              intersectionNode.SetNthFiducialPositionFromArray(validPosIndex,posTuple)
              intersectionNode.SetNthFiducialLabel(validPosIndex,"")
              intersectionNode.SetNthFiducialVisibility(validPosIndex,True)
              validPosIndex = validPosIndex + 1
        return numPointsVTKIntersection
      else:
        if intersectionNode:
          numOfFiducial = intersectionNode.GetNumberOfFiducials()
          for idx in range(1, numOfFiducial):
            intersectionNode.SetNthFiducialLabel(idx,"invalid")
    return 0

  def generateCubeModelWithYawAngle(self, centerPoint, sagittalYawAngle, dimension):
    cube = vtk.vtkCubeSource()
    fullMatrix = self.calculateMatrixBasedPos(centerPoint, sagittalYawAngle, 0.0, 0.0)
    cube.SetCenter(centerPoint[0], centerPoint[1], centerPoint[2])
    cube.SetXLength(dimension[0])
    cube.SetYLength(dimension[1])
    cube.SetZLength(dimension[2])
    cube.Update()
    sagittalTransform = vtk.vtkTransform()
    sagittalTransform.SetMatrix(fullMatrix)
    sagittalTransform.Inverse()
    sagittalTransformFilter = vtk.vtkTransformPolyDataFilter()
    sagittalTransformFilter.SetTransform(sagittalTransform)
    sagittalTransformFilter.SetInputData(cube.GetOutput())
    sagittalTransformFilter.Update()
    return sagittalTransformFilter.GetOutput()

  def generateConeModel(self, tipPos, basePos, radius, height):
    cone = vtk.vtkConeSource()
    ventricleDirect = (basePos - tipPos) / numpy.linalg.norm(
      tipPos - basePos)
    coneTipPoint = tipPos - numpy.linalg.norm(basePos - tipPos) / 2.0 * ventricleDirect
    angle = 180.0 / math.pi * math.atan(2 * radius / numpy.linalg.norm(
      tipPos - basePos))
    coneCenter = height / 2.0 * ventricleDirect + coneTipPoint
    cone.SetHeight(height)
    cone.SetResolution(60)
    cone.SetCenter(coneCenter)
    cone.SetDirection(-1.0 * ventricleDirect)  # we want the open end of the cone towards outside
    cone.SetAngle(angle)
    cone.Update()
    return cone.GetOutput()

  def generateCylinderModelWithTransform(self, radius, height, transform):
    cylinderTop = vtk.vtkCylinderSource()
    cylinderTop.SetCenter(numpy.array([0.0, 0.0, 0.0]))
    cylinderTop.SetRadius(radius)
    cylinderTop.SetHeight(height)
    cylinderTop.SetResolution(200)
    cylinderTop.Update()
    transformFilter = vtk.vtkTransformPolyDataFilter()
    transformFilter.SetInputConnection(cylinderTop.GetOutputPort())
    transformFilter.SetTransform(transform)
    transformFilter.ReleaseDataFlagOn()
    transformFilter.Update()
    return transformFilter.GetOutput()

  def calculateMatrixBasedPos(self, pos, yaw, pitch, roll):
    tempMatrix = vtk.vtkMatrix4x4()
    tempMatrix.Identity()
    tempMatrix.SetElement(0, 3, -pos[0])
    tempMatrix.SetElement(1, 3, -pos[1])
    tempMatrix.SetElement(2, 3, -pos[2])
    yawMatrix = vtk.vtkMatrix4x4()
    yawMatrix.Identity()
    yawMatrix.SetElement(0, 0, math.cos(yaw))
    yawMatrix.SetElement(0, 1, math.sin(yaw))
    yawMatrix.SetElement(1, 0, -math.sin(yaw))
    yawMatrix.SetElement(1, 1, math.cos(yaw))
    pitchMatrix = vtk.vtkMatrix4x4()
    pitchMatrix.Identity()
    pitchMatrix.SetElement(1, 1, math.cos(pitch))
    pitchMatrix.SetElement(1, 2, math.sin(pitch))
    pitchMatrix.SetElement(2, 1, -math.sin(pitch))
    pitchMatrix.SetElement(2, 2, math.cos(pitch))
    rollMatrix = vtk.vtkMatrix4x4()
    rollMatrix.Identity()
    rollMatrix.SetElement(0, 0, math.cos(roll))
    rollMatrix.SetElement(0, 2, -math.sin(roll))
    rollMatrix.SetElement(2, 0, math.sin(roll))
    rollMatrix.SetElement(2, 2, math.cos(roll))
    rollMatrix.SetElement(0, 3, pos[0])
    rollMatrix.SetElement(1, 3, pos[1])
    rollMatrix.SetElement(2, 3, pos[2])
    totalMatrix = vtk.vtkMatrix4x4()
    totalMatrix.Multiply4x4(yawMatrix, tempMatrix, totalMatrix)
    totalMatrix.Multiply4x4(pitchMatrix, totalMatrix, totalMatrix)
    totalMatrix.Multiply4x4(rollMatrix, totalMatrix, totalMatrix)
    return totalMatrix

  def inverseVTKImage(self, inputImageData):
    imgvtk = vtk.vtkImageData()
    imgvtk.DeepCopy(inputImageData)
    imgvtk.GetPointData().GetScalars().FillComponent(0, 1)
    subtractFilter = vtk.vtkImageMathematics()
    subtractFilter.SetInput1Data(imgvtk)
    subtractFilter.SetInput2Data(inputImageData)
    subtractFilter.SetOperationToSubtract()  # performed inverse operation on the
    subtractFilter.Update()
    return subtractFilter.GetOutput()

  def getClosedCuttedModel(self, cutPlanes, polyData):
    clipper = vtk.vtkClipClosedSurface()
    clipper.SetClippingPlanes(cutPlanes)
    clipper.SetActivePlaneId(2)
    clipper.SetInputData(polyData)
    clipper.Update()
    cuttedPolyData = clipper.GetOutput()
    return cuttedPolyData