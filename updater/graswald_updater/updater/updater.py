"""
    This is the Main updater class which contains methods for:
    checking for updates
    download that update
    unzipping, deleting and moving files
"""

from ..auth.auth import Authentication
#from .events import UpdateEvent

import os
import shutil
import tempfile
import zipfile

import threading

class UpdateEvent:

    def __init__(self, *args, **kwargs):
        self._handlers = []

    def __call__(self, *args, **kwargs):
        for handler in self._handlers:
            handler(*args, **kwargs)

    def add_handler(self, handler):
        self._handlers.append(handler)


class Updater:
    """
        ### Usage
            from updater import Updater \n
            from auth import HTTPS, AWS \n
            auth_method = HTTPS() # or AWS()\n
            updater = Updater( current_version, host_app_version, auth_method) \n
            new_version_info = updater.check_for_update()\n
            if new_version:\n
                files_to_update = {\n
                    'Update_v1.0.0/update.zip': 'Current_myapp/update',\n
                    'Update_v1.0.0/scripts': 'Current_myapp/scripts'\n
                }\n
            updater.install_update(files_to_update)\n
        """

    def __init__(
            self,
            version=str,
            host_app_version=str(""),
            auth_method=Authentication, 
            **args):
        self.on_update_info = UpdateEvent()
        self.on_start = UpdateEvent()
        self.on_update_progress = UpdateEvent()
        self.on_complete = UpdateEvent()
        self.on_cancel = UpdateEvent()
        self.on_error = UpdateEvent()

        self._cancel_update = UpdateEvent()

        self.current_version = version
        self.host_app_version = host_app_version
        self.auth_method = auth_method

    def check_for_update(self, callback_function=None):
        """
        ### Usage 
        update_info = updater.check_for_update()\n
        -> returns update_info object, and uses initialized url from auth_method\n
        """

        # Get versions_info.json from remote
        def get_update_info():
            json = self.auth_method.get_versions_info()
            #print(self.current_version)
            update_info = self.__get_latest_compatible_version(json, self.current_version, self.host_app_version)
            self.on_update_info(update_info)
            if callback_function:
                callback_function(update_info)

        thread = threading.Thread(target=get_update_info)
        thread.start()
        if not thread.is_alive():
            thread.join()

        return

    def update(self, update_info, files, dry_run=False):
        # Perform the update download asynchronously
        #print("Downloading & installing update...")
        thread = self.update_thread
        thread = threading.Thread(target=self.__download_install_update_thread, args=(update_info, files, dry_run))
        self.update_thread.start()
        if not thread.is_alive():
            thread.join()

    def cancel(self):
        self._cancel_update()

    def __download_install_update_thread(self, update_info, files, dry_run):
        """
        returns True if sucecessful, RaisesException if not, please try, except this method!
        """

        def progress_handler(current, total):
            self.on_update_progress(current, total)

        if dry_run:
            self.on_start()
            try:
                downloadUpdate = Authentication._sim_download_file(self,progress_handler=progress_handler, cancelled_event=self._cancel_update)
            except Exception as e:
                self.on_error(error = {e})
                raise RuntimeError(f"Error installing update: {e}")
            finally:
                if not downloadUpdate:
                    self.on_cancel()
                else: 
                    self.on_complete()
                return

        if "is_update_available" not in update_info or "is_update_compatible" not in update_info or "update_version" not in update_info:
            self.on_error(error = {"message": "Invalid update info, please try again."})
            raise RuntimeError("Invalid update info, please try again.")

        # Trigger the on_start event
        self.on_start()
        try:
            temp_dir = tempfile.mkdtemp()
            temp_update_file_path = os.path.join(str(temp_dir),
                                                 str(update_info["update_version"]["version_number"]) + ".zip")
            url = update_info["update_version"]["url"]

            #Downloading the update from the remote
            #self.auth_method._sim_download_file(progress_handler)
            downloadUpdate = self.auth_method.download_file(url, temp_update_file_path, progress_handler,
                                                            self._cancel_update)

            if downloadUpdate is not False:
                if zipfile.is_zipfile(temp_update_file_path):
                    with zipfile.ZipFile(temp_update_file_path, "r") as zip_ref:
                        zip_ref.extractall(temp_dir)

                # Installing/Moving Files according to files dict given
                for src, dest in files.items():
                    temp_file_path = os.path.join(temp_dir, src)
                    #print(f"Move from: {temp_file_path} to: {dest}")
                    #print(temp_file_path)
                    if os.path.exists(dest):
                        shutil.rmtree(dest, ignore_errors=True)
                    os.makedirs(temp_file_path, exist_ok=True)
                    shutil.move(temp_file_path, dest)
        except Exception as e:
            self.on_error(error={e})
            raise RuntimeError(f"Error installing update: {e}")
        finally:
            shutil.rmtree(temp_dir)
            if downloadUpdate is False:
                self.on_cancel()
            else:
                self.on_complete()
            return

    def __get_latest_compatible_version(self, versions, current_version, host_app_version):
        #print('\nApp-ver: ' + current_version)
        #print('Host_app_ver: ' + host_app_version)

        def convert_to_tuple(version):
            if version == "":
                return (-1,)
            return tuple(map(int, version.split('.')))

        def _is_compatible(host_app_version, compatibility_range):
            # compatibility_range is a space separated string, e.g. "2.8 - 2.9"
            # or is simply a minimum required version, e.g. "3.0+"
            host_components = convert_to_tuple(host_app_version)
            if "-" in compatibility_range:
                # Range format: "1.20 - 1.21.2"
                lower_bound, upper_bound = compatibility_range.split("-")
                lower_bound_components = convert_to_tuple(lower_bound)
                upper_bound_components = convert_to_tuple(upper_bound)
                return lower_bound_components <= host_components <= upper_bound_components
            elif "+" in compatibility_range:
                # Range format: "1.22+"
                lower_bound = compatibility_range.rstrip("+")
                lower_bound_components = convert_to_tuple(lower_bound)
                return host_components >= lower_bound_components
            else:
                # Invalid range format
                return False

        update_info = {
            "is_update_available": False,
            "is_update_compatible": False,
            "is_update_latest": False,
            "update_version": None,
            "latest_version": None
        }

        if not versions:
            return update_info

        latest_version = max(versions, key=lambda v: convert_to_tuple(v["version_number"]))
        #print("\nOverall latest/most recent version")
        #print(latest_version["version_number"] + " | compatible with: " + latest_version["compatibility_range"])

        # If the latest version is already installed, just return the latest versions up-to-date version info
        if current_version == max([latest_version["version_number"], current_version],
                                  key=lambda v: convert_to_tuple(v)):
            #print("Current version is the latest update available!")
            update_info["latest_version"] = latest_version
            return update_info

        # Otherwise, check if the host app is compatible with the latest version
        if _is_compatible(host_app_version, latest_version["compatibility_range"]):
            update_info["is_update_available"] = True
            update_info["is_update_compatible"] = True
            update_info["is_update_latest"] = True
            update_info["update_version"] = latest_version
            return update_info
        else:
            update_info["latest_version"] = latest_version

        # Get all Compatible versions
        compatible_versions = []
        for version in versions:
            compatibility_range = version["compatibility_range"]
            if _is_compatible(host_app_version, compatibility_range):
                compatible_versions.append(version)

        # If there are no compatible versions, but there was a latest_version ->
        if compatible_versions == []:
            update_info["is_update_available"] = True
            update_info["is_update_compatible"] = False
            update_info["is_update_latest"] = True
            update_info["update_version"] = latest_version
            return update_info

        # Get the latest compatible version
        latest_compatible_version = max(compatible_versions, key=lambda v: convert_to_tuple(v["version_number"]))
        #print("\nMost recent compatible version")
        #print(latest_version["version_number"] + " | compatible with: " + latest_version["compatibility_range"])

        if latest_compatible_version["version_number"] == max(
            [latest_compatible_version["version_number"], current_version], key=lambda v: convert_to_tuple(v)):
            update_info["is_update_available"] = True
            update_info["is_update_compatible"] = True
            update_info["update_version"] = latest_compatible_version

        return update_info
