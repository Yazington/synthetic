import bpy

# Import your modules (env_setup, surface, create_synthetic)
from . import env_setup
from . import surface
from . import create_synthetic


def register():
    """
    Called automatically when the add-on is enabled,
    because we listed `scripts` in modules in the root __init__.py.
    """
    # If you have custom operators or classes in create_synthetic.py,
    # you can register them here.
    pass

def unregister():
    """
    Called automatically when the add-on is disabled/uninstalled.
    """
    pass
