#-----------------------------------------------------------------------------
set(MODULE_NAME VentriculostomyPlanning)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  SlicerCaseManager.py
  ${MODULE_NAME}.py
  ${MODULE_NAME}Utils/__init__.py
  ${MODULE_NAME}Utils/UserEvents.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )
