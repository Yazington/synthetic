import bpy
from ..utils import getters
from .updater import updater


class StartUpdateOperator(bpy.types.Operator):
    bl_idname = 'app_updater.start_update'
    bl_label = 'Update Addon'
    bl_description = 'Download and install the latest addon update'

    @classmethod
    def poll(cls, context):
        return updater.update_info and updater.update_info['is_update_available'] and updater.update_info[
            'is_update_compatible']

    def execute(self, context: bpy.types.Context) -> set:
        updater.install_update()
        return {'FINISHED'}


class CancelUpdateOperator(bpy.types.Operator):
    bl_idname = 'app_updater.cancel_update'
    bl_label = 'Cancel Update'
    bl_description = 'Cancel the downlaod and isntallation process'

    def execute(self, context: bpy.types.Context) -> set:
        wm_props = getters.get_wm_props(bpy.context)
        wm_props.updater_properties.cancelling = True
        updater.cancel()
        return {'CANCELLED'}


def register():
    bpy.utils.register_class(StartUpdateOperator)
    bpy.utils.register_class(CancelUpdateOperator)


def unregister():
    bpy.utils.unregister_class(StartUpdateOperator)
    bpy.utils.unregister_class(CancelUpdateOperator)
