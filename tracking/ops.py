import bpy
from bpy.props import BoolProperty

from ..utils.getters import get_preferences

from .core import createUidFile, removeUidFile, uidFileExists


class RemoveUidFileOperator(bpy.types.Operator):
    """Remove local data"""

    bl_label = "Remove User ID"
    bl_idname = "gscatter.remove_uid"

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return uidFileExists()

    def execute(self, context: bpy.types.Context) -> set:
        removeUidFile()
        return {"FINISHED"}


class ConsentOperator(bpy.types.Operator):
    """Accept Data Collection"""

    bl_label = "Sounds good!"
    bl_idname = "gscatter.consent"

    consent: BoolProperty(default=False)

    def execute(self, context: bpy.types.Context) -> set:
        if not uidFileExists():
            createUidFile()
        prefs = get_preferences()
        prefs.tracking_interaction = self.consent
        prefs.tracking_errors = self.consent
        bpy.ops.wm.save_userpref()
        return {"FINISHED"}


classes = (
    ConsentOperator,
    RemoveUidFileOperator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
