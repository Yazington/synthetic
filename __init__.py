bl_info = {
    "name": "GScatter by Graswald",
    "description": "The Graswald Scattering Tools",
    "location": "View3D > Sidebar > GScatter & Geo-Nodes > Sidebar > GScatter",
    "author": "Graswald",
    "version": (0, 11, 8),
    "blender": (3, 5, 0),
    "support": "COMMUNITY",
    "category": "",
}

from . import (
    asset_manager,
    common,
    slow_task_manager,
    effects,
    environment,
    icon_viewer,
    icons,
    info,
    extras,
    scatter,
    tracking,
    utils,
    updater,
    # <--- Add scripts here
    scripts
)

modules = (
    common,
    slow_task_manager,
    tracking,
    icons,
    scatter,
    icon_viewer,
    asset_manager,
    effects,
    utils,
    environment,
    extras,
    info,
    updater,
    # <--- Also add scripts here
    scripts
)

def register():
    for module in modules:
        module.register()

def unregister():
    tracking.core.finalize()
    for module in reversed(modules):
        module.unregister()
