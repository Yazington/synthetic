import bpy

from ..utils import wrap_text
from .core import uidFileExists
from .ops import ConsentOperator

_TRACKING_MSG = "In order to fix bugs faster and learn more about how we can improve GScatter, we are collecting anonymous information about how you use the add-on. You can disable/enable data collection in the add-on preferences at any time. Please consider participating since it helps us tremendously to make GScatter better!"


class ConsentPanel(bpy.types.Panel):
    bl_idname = "GSCATTER_PT_consent"
    bl_label = "Data Collection Notice"
    bl_order = 80
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "GScatter"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return not uidFileExists()

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        box = layout.box()
        text_col = box.column(align=True)
        text_col.scale_y = 0.8
        width = context.region.width
        for text in wrap_text(_TRACKING_MSG, width):
            text_col.label(text=text)
        row = layout.row()
        row.scale_y = 1.5

        op = row.operator(ConsentOperator.bl_idname, text="Sounds good!")
        op.consent = True
        op = row.operator(ConsentOperator.bl_idname, text="Rather not.")
        op.consent = False


classes = (ConsentPanel,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
