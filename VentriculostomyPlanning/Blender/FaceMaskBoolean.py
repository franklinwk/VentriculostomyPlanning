import bpy

def reset_blend():
    bpy.ops.wm.read_factory_settings()

    for scene in bpy.data.scenes:
        for obj in scene.objects:
            scene.objects.unlink(obj)

    # only worry about data in the startup scene
    for bpy_data_iter in (
            bpy.data.objects,
            bpy.data.meshes,
            bpy.data.lamps,
            bpy.data.cameras,
    ):
        for id_data in bpy_data_iter:
            bpy_data_iter.remove(id_data)

reset_blend()

bpy.ops.import_mesh.stl(filepath="./faceMask.STL")
bpy.ops.import_mesh.stl(filepath="./guidePlatform.STL")
bpy.ops.import_mesh.stl(filepath="./holeCylinder.STL")
bpy.ops.import_mesh.stl(filepath="./skullModel.STL")
bpy.ops.import_mesh.stl(filepath="./pilotHoles1.STL")
bpy.ops.import_mesh.stl(filepath="./pilotHoles2.STL")
bpy.ops.import_mesh.stl(filepath="./pilotHoles3.STL")
bpy.ops.import_mesh.stl(filepath="./pilotHoles4.STL")

objects = bpy.data.objects
faceMask = objects['faceMask']
guidePlatform = objects['guidePlatform']
holeCylinder = objects['holeCylinder']
skullModel = objects['skullModel']
pilotHole1 = objects['pilotHoles1']
pilotHole2 = objects['pilotHoles2']
pilotHole3 = objects['pilotHoles3']
pilotHole4 = objects['pilotHoles4']

guidePlatform_d_skullModel = guidePlatform.modifiers.new(type="BOOLEAN", name="bool_1")
guidePlatform_d_skullModel.object = skullModel
guidePlatform_d_skullModel.operation = 'DIFFERENCE'
skullModel.hide = True
bpy.context.scene.objects.active = bpy.data.objects['guidePlatform']
bpy.ops.object.modifier_apply(apply_as='DATA', modifier=guidePlatform_d_skullModel.name)

faceMask_u_guidePlatform = faceMask.modifiers.new(type="BOOLEAN", name="bool_2")
faceMask_u_guidePlatform.object = guidePlatform
faceMask_u_guidePlatform.operation = 'UNION'
guidePlatform.hide = True
bpy.context.scene.objects.active = bpy.data.objects['faceMask']
bpy.ops.object.modifier_apply(apply_as='DATA', modifier=faceMask_u_guidePlatform.name)

faceMask_d_holeCylinder = faceMask.modifiers.new(type="BOOLEAN", name="bool_3")
faceMask_d_holeCylinder.object = holeCylinder
faceMask_d_holeCylinder.operation = 'DIFFERENCE'
holeCylinder.hide = True
bpy.context.scene.objects.active = bpy.data.objects['faceMask']
bpy.ops.object.modifier_apply(apply_as='DATA', modifier=faceMask_d_holeCylinder.name)

faceMask_d_pilotHole1 = faceMask.modifiers.new(type="BOOLEAN", name="bool_4")
faceMask_d_pilotHole1.object = pilotHole1
faceMask_d_pilotHole1.operation = 'DIFFERENCE'
pilotHole1.hide = True
bpy.context.scene.objects.active = bpy.data.objects['faceMask']
bpy.ops.object.modifier_apply(apply_as='DATA', modifier=faceMask_d_pilotHole1.name)

faceMask_d_pilotHole2 = faceMask.modifiers.new(type="BOOLEAN", name="bool_5")
faceMask_d_pilotHole2.object = pilotHole2
faceMask_d_pilotHole2.operation = 'DIFFERENCE'
pilotHole2.hide = True
bpy.context.scene.objects.active = bpy.data.objects['faceMask']
bpy.ops.object.modifier_apply(apply_as='DATA', modifier=faceMask_d_pilotHole2.name)

faceMask_d_pilotHole3 = faceMask.modifiers.new(type="BOOLEAN", name="bool_6")
faceMask_d_pilotHole3.object = pilotHole3
faceMask_d_pilotHole3.operation = 'DIFFERENCE'
pilotHole3.hide = True
bpy.context.scene.objects.active = bpy.data.objects['faceMask']
bpy.ops.object.modifier_apply(apply_as='DATA', modifier=faceMask_d_pilotHole3.name)

faceMask_d_pilotHole4 = faceMask.modifiers.new(type="BOOLEAN", name="bool_7")
faceMask_d_pilotHole4.object = pilotHole4
faceMask_d_pilotHole4.operation = 'DIFFERENCE'
pilotHole4.hide = True
bpy.context.scene.objects.active = bpy.data.objects['faceMask']
bpy.ops.object.modifier_apply(apply_as='DATA', modifier=faceMask_d_pilotHole4.name)

faceMask.select = False
skullModel.select = True
guidePlatform.select = True
holeCylinder.select = True
pilotHole1.select = True
pilotHole2.select = True
pilotHole3.select = True
pilotHole4.select = True
bpy.ops.object.delete()
faceMask.select = True
bpy.ops.export_mesh.stl(filepath="./outputBlenderModel.STL")

#bpy.ops.wm.quit_blender()
