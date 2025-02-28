# coding: utf-8
""" Find compiled module linking to Tcl / Tk libraries
"""
from __future__ import annotations
import sys
import tkinter
tk = getattr(tkinter, '_tkinter')
try:
    if hasattr(sys, 'pypy_find_executable'):
        TKINTER_LIB = tk.tklib_cffi.__file__
    else:
        TKINTER_LIB = tk.__file__
except AttributeError:
    TKINTER_LIB = None
tk_version = str(tkinter.TkVersion)
