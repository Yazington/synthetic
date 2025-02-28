# Copyright 2022 the Regents of the University of California, Nerfstudio Team and contributors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Additional rich ui components"""

import sys
from .getters import get_preferences

import logging

logging.basicConfig(format='Gscatter %(levelname)s: %(message)s', level=logging.DEBUG)


def try_catch(function):

    def protected(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            logging.warning("FAILED TO RUN %s \n %s" % (str(function), str(e)))
            return None

    return protected


def annotate(f):
    name = str(f).split(' ')[1]

    def f2(*args, **kwargs):
        debug_print(f"{name}(...): ==>")
        ret = f(*args, **kwargs)
        debug_print(f"    {name} <== {ret}")
        return ret

    return f2


def debug_print(msg):
    prefs = get_preferences()
    DEBUG_ENABLED = prefs.enable_developer_mode
    if DEBUG_ENABLED:
        logging.debug(msg)


def info(msg):
    logging.info(msg)


def error(msg, debug=False):
    prefs = get_preferences()
    DEBUG_ENABLED = prefs.enable_developer_mode
    code = sys._getframe().f_back.f_code
    if (debug and DEBUG_ENABLED) or not debug:
        logging.error(f"{code.co_name} in {code.co_filename}:{code.co_firstlineno}>:",
                        msg)


def warn(msg):
    logging.warning(msg)


def success(msg):
    logging.log(msg)


def debug(msg):
    debug_print(msg)
