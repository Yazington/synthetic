import bpy
from bpy.types import Context
from .ops import StartUpdateOperator, CancelUpdateOperator
from .updater import updater
from ..common.ui import BasePanel
from ..utils.getters import get_allow_networking, get_wm_props, get_version
from ..utils import wrap_text


class UpdatePanel(BasePanel):
    bl_idname = 'GSCATTER_PT_Update'
    bl_label = "Update"
    bl_order = 1
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        wm_scene_props = get_wm_props()
        updater_properties = wm_scene_props.updater_properties
        return updater and updater.update_info and updater.update_info.get('update_version') and updater_properties.update_available and get_allow_networking()

    def draw_header_preset(self, context: Context):
        layout = self.layout
        row = layout.row(align=True)
        if updater.update_info:
            row.label(text='v' + '.'.join(map(str, get_version())))
            row.label(text='v' + updater.update_info['update_version']['version_number'], icon="FORWARD")

    def draw(self, context):
        layout = self.layout
        wm_scene_props = get_wm_props()
        updater_properties = wm_scene_props.updater_properties
        if updater.update_info:
            col = layout.column()
            col.label(text="Compatibility: " + updater.update_info['update_version']['compatibility_range'])

            for text in wrap_text(updater.update_info['update_version']['description'], context.region.width - 50):
                col.label(text=text)

            changelog = updater.update_info['update_version'].get("changelogs")
            if changelog:
                col = layout.box().column()
                col.label(text="Changelog")
                for log in changelog:
                    sub_col = col.column(align=True)
                    for idx, text in enumerate(wrap_text(log, context.region.width)  ):
                        sub_col.label(text=text, icon="DOT" if idx == 0 else "BLANK1")

        if updater.update_info.get('is_update_available') and not updater_properties.update_start:
            row = layout.row()
            row.operator(StartUpdateOperator.bl_idname)

        elif updater_properties.update_start:
            row = layout.row()
            row.enabled = not updater_properties.cancelling
            row.operator(CancelUpdateOperator.bl_idname,
                         text="Cancel Update" if not updater_properties.cancelling else "Cancelling")

            col = layout.column()
            col.enabled = False
            updater_properties.draw_progress_panel(col)


def register():
    bpy.utils.register_class(UpdatePanel)


def unregister():
    bpy.utils.unregister_class(UpdatePanel)
