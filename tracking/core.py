import atexit
import os
import platform
import threading
import uuid

import bpy
from requests.sessions import Session

from ..utils.logger import debug, error

from .. import bl_info, utils
from ..vendor.mixpanel import BufferedConsumer, Mixpanel, MixpanelException

_UID_FILE = "uid"
_UID_PATH = ".config/gscatter/"
_TOKEN = os.getenv("MIXPANELTOKEN") or '0ddbe286d4b214f3d70f79d3ad5601c5'
_BUFSIZE = 20
_API_HOST = "api-eu.mixpanel.com"
_DEFAULT_PROPS = {
    'Addon Version': str(bl_info.get('version')),
    'Blender Version': bpy.app.version_string,
    'OS': platform.system(),
}


class _SessionWithIpOverride:

    def __init__(self, session: Session):
        self._session = session

    def post(self, url: str, data: dict, auth: dict, timeout: float, verify: bool):
        data['ip'] = 1
        return self._session.post(url=url, data=data, auth=auth, timeout=500, verify=verify)


_mp_consumer = BufferedConsumer(_BUFSIZE, api_host=_API_HOST)
_mp_consumer._consumer._session = _SessionWithIpOverride(_mp_consumer._consumer._session)
_mp = Mixpanel(_TOKEN, consumer=_mp_consumer)


def track_event(event: str, properties: dict = {}, ignorePrefs: bool = False):
    try:
        if uidFileExists():
            if properties is None:
                properties = {}

            uid = readUidFile()
            properties.update(_DEFAULT_PROPS)

            prefs = utils.getters.get_preferences()
            allow_networking = utils.getters.get_allow_networking()
            if (prefs.tracking_interaction or ignorePrefs) and allow_networking:
                _mp.track(uid, event, properties)
    except Exception:
        error(debug=True)
        debug("Failed to send tracking event.")


def track(event: str, properties: dict = None, ignorePrefs: bool = False):
    tracking_thread = threading.Thread(target=track_event, args=(event, properties, ignorePrefs), daemon=True)
    tracking_thread.start()
    if not tracking_thread.is_alive():
        tracking_thread.join()


def getAbsoluteUidFilename() -> str:
    userdir = os.path.expanduser("~")
    absUidFilename = os.path.join(userdir, _UID_PATH, _UID_FILE)
    return absUidFilename


def uidFileExists() -> bool:
    return os.path.exists(getAbsoluteUidFilename())


def createUidFile(uid: str = None):
    if uidFileExists():
        removeUidFile()

    if uid is None:
        uid = str(uuid.uuid4())

    userdir = os.path.expanduser("~")
    path = os.path.join(userdir, _UID_PATH)
    if not os.path.exists(path):
        os.makedirs(path)

    with open(getAbsoluteUidFilename(), 'w') as f:
        f.write(uid)

    track("newUser")


def readUidFile() -> str:
    uid = ''
    with open(getAbsoluteUidFilename(), 'r') as f:
        uid = f.readline().strip("\n")
    return uid


def removeUidFile():
    absUidFilename = getAbsoluteUidFilename()
    os.remove(absUidFilename)


def getUid() -> str:
    prefs = utils.getters.get_preferences()
    return prefs.uid


def setUid(uid: str):
    prefs = utils.getters.get_preferences()
    prefs.uid = uid
    bpy.ops.wm.save_userpref()


def uidIsSet() -> bool:
    prefs = utils.getters.get_preferences()
    if prefs.uid == '':
        return False
    return True


def finalize():
    try:
        _mp._consumer.flush()
    except MixpanelException as e:
        error(e, debug=True)


atexit.register(finalize)
