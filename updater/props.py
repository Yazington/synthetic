import bpy
from ..common.props import WindowManagerProps


class UpdaterProperties(bpy.types.PropertyGroup):
    update_progress: bpy.props.FloatProperty(default=0.0, min=0.0, max=100.0, subtype="PERCENTAGE")
    update_start: bpy.props.BoolProperty(name="Start")
    update_cancel: bpy.props.BoolProperty(name="Cancel")
    update_complete: bpy.props.BoolProperty(name="Complete")
    update_available: bpy.props.BoolProperty(name="Update Available")
    cancelling: bpy.props.BoolProperty(name="Cancelling")

    def draw_progress_panel(self, layout):
        layout.label(text='Downloading Update...')
        layout.prop(self, 'update_progress', text='Progress', slider=True, emboss=True)


def register():
    bpy.utils.register_class(UpdaterProperties)
    WindowManagerProps.updater_properties = bpy.props.PointerProperty(type=UpdaterProperties)


def unregister():
    bpy.utils.unregister_class(UpdaterProperties)
    del WindowManagerProps.updater_properties
