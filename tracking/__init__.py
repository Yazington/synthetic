from . import core, ops, sentry, ui
from .core import track

modules = (
    sentry,
    ops,
    ui,
)


def register():
    for m in modules:
        m.register()


def unregister():
    for m in modules:
        m.unregister()
