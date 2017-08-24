import vtk, qt, ctk, slicer

class SerialAssignMessageBox(qt.QMessageBox):
  def __init__(self):
    qt.QMessageBox.__init__(self)
    #self.setSizeGripEnabled(True)
    self.setWindowTitle ('SerialAssignTable')
    self.volumesCheckedDict = dict()
    self.volumesCheckedDictPre = dict()  # Store the previous selected item. if the user click the cancel button. all value should be reset.
    self.serialCheckboxVenous = []
    self.serialCheckboxVentricle = []
    self.volumeNames = []
    self.importedVolumeIDs = []
    self.volumes = []
    self.mainGUILayout = self.layout()
    self.mainGUILayout.setAlignment(qt.Qt.AlignCenter)
    
    self.addTableWidget ()
    #Create QPushButton in QMessageBox
    self.confirmButton = qt.QPushButton('Confirm')
    self.cancelButton = qt.QPushButton('Cancel')
    self.addButton(self.confirmButton, qt.QMessageBox.YesRole)
    self.addButton(self.cancelButton, qt.QMessageBox.RejectRole)
    self.confirmButton.setEnabled(False)
    
    self.buttonBox = qt.QGroupBox()
    buttonLayout = qt.QHBoxLayout()
    buttonLayout.setSizeConstraint(buttonLayout.SetMinAndMaxSize)
    self.buttonBox.setLayout(buttonLayout)
    self.buttonBox.setStyleSheet('QGroupBox{border:0;}')
    buttonLayout.addWidget(self.confirmButton)
    buttonLayout.addWidget(self.cancelButton)
    self.mainGUILayout.addWidget(self.buttonBox,1,0,1,1)
    self.tableHeight = 0
    self.tableWidth = 0
  #Create TableWidget
  def addTableWidget (self) :
    self.tableWidgetBox = qt.QGroupBox()
    layout = qt.QHBoxLayout()
    self.tableWidgetBox.setLayout(layout)
    self.tableWidgetBox.setStyleSheet('QGroupBox{border:0;}')
    self.tableWidget = qt.QTableWidget()
    self.tableWidget.setStyleSheet('QGroupBox{border:0;}')
    self.tableWidget.horizontalScrollBar().setEnabled(True)
    self.tableWidget.setHorizontalScrollBarPolicy(1)
    self.tableWidget.setVerticalScrollBarPolicy(1)
    #layout.setColumnMinimumWidth(0,340)
    #layout.setRowMinimumHeight(0,100)
    #layout.setGeometry (qt.QRect(0, 0, 340, 100))
    layout.addWidget(self.tableWidget)
    #self.tableWidget.setGeometry (qt.QRect(0, 0, 400, 200))
    #self.tableWidget.setMinimumHeight(200)
    #self.tableWidget.setMinimumWidth(300)
    self.tableWidget.setObjectName ('tableWidget')
    self.tableWidget.setColumnCount(2)
    self.tableWidget.setRowCount(2)
    #self.tableWidget.resizeRowsToContents()
    #self.tableWidget.resizeColumnsToContents()
    self.tableWidget.setHorizontalHeaderLabels("IsVenousType;IsVentricleType".split(";"))
    self.tableWidget.setVerticalHeaderLabels("Serial1;Serial2".split(";"))
    #self.tableWidget.horizontalHeader().setStretchLastSection(True)
    #self.tableWidget.verticalHeader().setStretchLastSection(True)
  def AppendVolumeNode(self, addedVolumeNode):
    if addedVolumeNode not in self.volumes:
      self.volumes.append(addedVolumeNode)
      self.SetAssignTableWithVolumes(self.volumes)

  def Clear(self):
    self.volumesCheckedDict = dict()
    self.volumesCheckedDictPre = dict()  # Store the previous selected item. if the user click the cancel button. all value should be reset.
    self.serialCheckboxVenous = []
    self.serialCheckboxVentricle = []
    self.volumeNames = []
    self.importedVolumeIDs = []
    self.volumes = []
    self.tableWidget.setRowCount(0)

  def SetAssignTableWithVolumes(self, addedVolumeNodes):
    self.volumes = addedVolumeNodes
    if self.volumes:
      self.tableWidget.setColumnCount(2)
      self.tableWidget.setRowCount(len(self.volumes))
      self.tableHeight = 0
      for counter, volume in enumerate(self.volumes):
        if not volume.GetID() in self.importedVolumeIDs:
          self.importedVolumeIDs.append(volume.GetID())
          self.volumeNames.append(volume.GetName())
          tableItemVenous = qt.QCheckBox()
          tableItemVenous.setCheckState(False)
          tableItemVenous.setCheckable(True)
          itemWidgetVenous = qt.QWidget()
          itemLayoutVenous = qt.QVBoxLayout()
          itemLayoutVenous.setAlignment(qt.Qt.AlignCenter)
          itemWidgetVenous.setLayout(itemLayoutVenous)
          itemLayoutVenous.addWidget(tableItemVenous)
          self.tableWidget.setCellWidget(counter,0,itemWidgetVenous)
          tableItemVentricle = qt.QCheckBox()
          tableItemVentricle.setCheckState(False)
          tableItemVentricle.setCheckable(True)
          itemWidgetVentricle = qt.QWidget()
          itemLayoutVentricle = qt.QVBoxLayout()
          itemLayoutVentricle.setAlignment(qt.Qt.AlignCenter)
          itemWidgetVentricle.setLayout(itemLayoutVentricle)
          itemLayoutVentricle.addWidget(tableItemVentricle)
          self.serialCheckboxVenous.append(tableItemVenous)
          self.serialCheckboxVentricle.append(tableItemVentricle)
          if self.volumesCheckedDict.get("Venous") and volume.GetID() == self.volumesCheckedDict.get("Venous").GetID():
            tableItemVenous.setCheckState(True)
          if self.volumesCheckedDict.get("Ventricle") and volume.GetID() == self.volumesCheckedDict.get("Ventricle").GetID():
            tableItemVentricle.setCheckState(True)
          tableItemVenous.stateChanged.connect(lambda checked, i=counter: self.VenousStateChanged(checked, self.serialCheckboxVenous[i]))
          tableItemVentricle.stateChanged.connect(lambda checked, i=counter: self.VentricleStateChanged(checked, self.serialCheckboxVentricle[i]))
          self.tableWidget.setCellWidget(counter, 1, itemWidgetVentricle)
        self.tableHeight = self.tableHeight + self.tableWidget.cellWidget(counter, 1).geometry.height()
    self.tableWidget.setVerticalHeaderLabels(self.volumeNames)
    #self.tableWidget.setFixedSize(self.tableWidget.verticalHeader().width + self.tableWidth, self.tableWidget.horizontalHeader().height + self.tableHeight)
    self.mainGUILayout.addWidget(self.tableWidgetBox, 0, 0, 1, 3)
    self.ConfirmButtonValid()
  def ConfirmButtonValid(self):
    checkedNum = 0
    for count, box in enumerate(self.serialCheckboxVenous):
      if box.checkState():
        checkedNum = checkedNum + 1
        self.volumesCheckedDict["Venous"] = self.volumes[count]
    for count, box in enumerate(self.serialCheckboxVentricle):
      if box.checkState():
        checkedNum = checkedNum + 1
        self.volumesCheckedDict["Ventricle"] = self.volumes[count]
    if checkedNum == 2:
      self.confirmButton.setEnabled(True)
    elif checkedNum == 1 and len(self.volumes) == 1:
      self.confirmButton.setEnabled(True)
    else:
      self.confirmButton.setEnabled(False)
  def ShowVolumeTable(self):
    self.volumesCheckedDictPre = self.volumesCheckedDict.copy()
    self.show()
    self.close() # show and close to get the width of the header
    if self.tableWidget.cellWidget(0,0) and self.tableWidget.cellWidget(0,1):
      self.tableWidth = self.tableWidget.cellWidget(0,0).geometry.width() + self.tableWidget.cellWidget(0,1).geometry.width()
    self.tableWidget.setFixedSize(self.tableWidget.verticalHeader().width + self.tableWidth+6, self.tableWidget.horizontalHeader().height + self.tableHeight+6)
    return self.exec_()
  def CancelUserChanges(self):
    self.volumesCheckedDict = self.volumesCheckedDictPre.copy()
    self.SetCheckBoxAccordingToAssignment()
  def ConfirmUserChanges(self):
    self.volumesCheckedDictPre = self.volumesCheckedDict.copy()
  def BlockCheckboxSignal(self):
    for box in self.serialCheckboxVenous:
      box.blockSignals(True)
    for box in self.serialCheckboxVentricle:
      box.blockSignals(True)
  def UnblockCheckboxSignal(self):
    for box in self.serialCheckboxVenous:
      box.blockSignals(False)
    for box in self.serialCheckboxVentricle:
      box.blockSignals(False)
  def SetCheckBoxAccordingToAssignment(self):
    self.BlockCheckboxSignal()
    ventricleVolume = self.volumesCheckedDict.get("Ventricle")
    venousVolume = self.volumesCheckedDict.get("Venous")
    for count, checkbox in enumerate(self.serialCheckboxVentricle):
      checkbox.setCheckState(False)
      if ventricleVolume and self.volumes[count].GetID() == ventricleVolume.GetID():
        checkbox.setCheckState(True)
    for count, checkbox in enumerate(self.serialCheckboxVenous):
      checkbox.setCheckState(False)
      if venousVolume and self.volumes[count].GetID() == venousVolume.GetID():
        checkbox.setCheckState(True)
    self.UnblockCheckboxSignal()
  def CheckBoxStatusChanged(self, checked, checkBox, workingSerialCheckbox, otherSerialCheckbox):
    self.BlockCheckboxSignal()
    if checkBox in workingSerialCheckbox:
      for count, box in enumerate(workingSerialCheckbox):
        if not box == checkBox:
          box.setCheckState(False)
        else:
          box.setCheckState(checked)
          otherSerialCheckbox[count].setCheckState(False)
    self.ConfirmButtonValid()
    self.UnblockCheckboxSignal()
  def VenousStateChanged(self, checked, checkBox):
    self.CheckBoxStatusChanged(checked, checkBox, self.serialCheckboxVenous, self.serialCheckboxVentricle)
  def VentricleStateChanged(self,checked, checkBox):
    self.CheckBoxStatusChanged(checked, checkBox, self.serialCheckboxVentricle,self.serialCheckboxVenous)

#volumes = [slicer.mrmlScene.GetNodeByID("vtkMRMLScalarVolumeNode1"), slicer.mrmlScene.GetNodeByID("vtkMRMLScalarVolumeNode2")]
#a = SerialAssignMessageBox()
#a.SetAssignTableWithVolumes(volumes)
#a.ShowVolumeTable()