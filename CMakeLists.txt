cmake_minimum_required(VERSION 2.8.9)

project(VentriculostomyPlanning)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/VentriculostomyPlanning")
set(EXTENSION_CATEGORY "IGT")
set(EXTENSION_CONTRIBUTORS "Longquan Chen (BWH), Junichi Tokuda (BWH), Franklin King (BWH)")
set(EXTENSION_DESCRIPTION "This is an extension to support Ventriculostomy planning.")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/VentriculostomyPlanning.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/VentriculostomyPlanning/Screenshots/1.png")
set(EXTENSION_DEPENDS "CurveMaker PercutaneousApproachAnalysis SlicerDevelopmentToolbox") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(VentriculostomyPlanning)
add_subdirectory(LabelMapBinning)
add_subdirectory(SkullRemoval)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
