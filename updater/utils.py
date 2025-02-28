import bpy, blf
from typing import List
from functools import partial


def _refresh():
    bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)


def _show_message(message, width):
    bpy.ops.gscatter.popup_message('INVOKE_DEFAULT', message=message, width=width)


def update_viewport():
    bpy.app.timers.register(_refresh)


def show_message(message, width):
    bpy.app.timers.register(partial(_show_message, message, width))
