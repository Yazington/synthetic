import bpy
from bpy.app.handlers import persistent

from ..utils.getters import get_addon_dir, get_version, get_allow_networking
from .callbacks import (
    update_cancel_handler,
    update_complete_handler,
    update_error_handler,
    update_info_handler,
    update_progress_handler,
    update_start_handler,
)
from .graswald_updater import Updater
from .graswald_updater.auth import HTTPS

UPDATE_INTERVAL = 300.0  # Update interval in seconds (e.g., 300 seconds = 5 minutes)


class InitUpdater:

    def __init__(self) -> None:
        self.auth_method = HTTPS(
            url="https://asset-downloads.gscatter.com/file-downloads/gscatter/latest_versions",
            headers={},
        )
        self.updater = Updater(
            version=".".join(map(str, get_version())),
            host_app_version=".".join(map(str, bpy.app.version)),
            auth_method=self.auth_method,
        )

        self.updater.on_update_info.add_handler(update_info_handler)
        self.update_info = None

        self.updater.on_update_progress.add_handler(update_progress_handler)
        self.updater.on_start.add_handler(update_start_handler)
        self.updater.on_complete.add_handler(update_complete_handler)
        self.updater.on_cancel.add_handler(update_cancel_handler)
        self.updater.on_error.add_handler(update_error_handler)

    def cancel(self):
        self.updater.cancel()

    def install_update(self):
        addon_path = get_addon_dir()
        # addon_path = get_addon_dir().parent.joinpath("test", "gscatter")
        files_to_update = {
            "gscatter/": addon_path.as_posix(),
        }
        self.updater.update(self.update_info, files_to_update, dry_run=False)

updater: InitUpdater = None


def handle_update_info(update_info):
    updater.update_info = update_info


@persistent
def check_update_handler():
    allow_networking = get_allow_networking()
    if allow_networking:
        global updater
        updater.updater.check_for_update(handle_update_info)
    return UPDATE_INTERVAL


def register():
    global updater
    updater = InitUpdater()
    bpy.app.timers.register(check_update_handler, first_interval=30, persistent=True)


def unregister():
    global updater
    updater = None
    # del updater

    # Remove the check_update_handler from the load_post handler
    bpy.app.timers.unregister(check_update_handler)
