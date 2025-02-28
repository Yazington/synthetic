from . import updater, callbacks, ops, props, ui

modules = (
    props,
    updater,
    callbacks,
    ops,
    ui,
)


def register():
    for module in modules:
        module.register()


def unregister():
    for module in reversed(modules):
        module.unregister()
