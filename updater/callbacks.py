from typing import Any

from ..utils.logger import info
from ..utils import getters
from .utils import update_viewport, show_message
import bpy


def update_viewport_timer():
    wm_props = getters.get_wm_props(bpy.context)
    update_viewport()
    if wm_props.updater_properties.update_start:
        return 0.3


def update_start_handler(*args: Any, **kwargs: Any) -> None:
    wm_props = getters.get_wm_props(bpy.context)
    wm_props.updater_properties.update_start = True
    bpy.app.timers.register(update_viewport_timer)
    info("Update started")


def update_progress_handler(progress_current: int, progress_total: int) -> None:
    percent = (progress_current / progress_total) * 100
    wm_props = getters.get_wm_props(bpy.context)
    wm_props.updater_properties.update_progress = percent


def update_complete_handler(*args: Any, **kwargs: Any) -> None:
    wm_props = getters.get_wm_props(bpy.context)
    wm_props.updater_properties.update_start = False
    wm_props.updater_properties.update_progress = 0
    wm_props.updater_properties.cancelling = False
    wm_props.updater_properties.update_available = False

    global can_refresh
    can_refresh = True

    update_viewport()
    show_message("Update Complete. Restart blender to see changes", 300)
    info("Update complete")


def update_cancel_handler(*args: Any, **kwargs: Any) -> None:
    wm_props = getters.get_wm_props(bpy.context)
    wm_props.updater_properties.update_start = False
    wm_props.updater_properties.update_progress = 0
    wm_props.updater_properties.cancelling = False
    update_viewport()
    info(" Update cancelled")


def update_error_handler(error: Exception) -> None:
    info(f"Update error: {str(error)}")


def update_info_handler(update_info) -> None:
    if not bpy.app.background and hasattr(bpy.context.window_manager, "gscatter") and update_info is not None:
        wm_props = getters.get_wm_props(bpy.context)
        wm_props.updater_properties.update_available = True


def register():
    pass


def unregister():
    pass
