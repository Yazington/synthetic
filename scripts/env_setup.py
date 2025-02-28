import os
import sys
import bpy


def find_project_root():
    """Find the project root directory containing blender_scripts."""
    # First try the current working directory
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, "blender_scripts")):
        return cwd

    # Try specific known path
    known_path = r"C:\Users\Yaz\Workspace\tcv\synthetic-data-gen"
    if os.path.exists(os.path.join(known_path, "blender_scripts")):
        return known_path

    # If running from Blender text editor
    if not "__file__" in globals():
        # Try to get path from text block
        for text in bpy.data.texts:
            if text.name == "create_synthetic.py" and text.filepath:
                project_root = os.path.dirname(os.path.abspath(text.filepath))
                if os.path.exists(os.path.join(project_root, "blender_scripts")):
                    return project_root

    raise RuntimeError(
        "Could not find project root. Please ensure you're running this script from the correct directory."
    )


def setup_environment():
    """Setup the Python environment."""
    try:
        # Find project root containing blender_scripts
        project_root = find_project_root()
        print(f"Project root: {project_root}")

        # Set current working directory to project root
        os.chdir(project_root)
        print(f"Set working directory to: {os.getcwd()}")

        # Add project root to Python path if needed
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
            print(f"Added to Python path: {project_root}")

        print("Environment setup completed successfully")
    except Exception as e:
        print(f"Environment setup failed: {str(e)}")
        raise

def clean_scene():
    """Remove all objects and data from the Blender scene"""
    print("\nPerforming complete scene cleanup...")
    
    # Deselect all objects first
    if bpy.context.selected_objects:
        bpy.ops.object.select_all(action='DESELECT')
    
    # Remove objects directly
    for obj in list(bpy.data.objects):  # Create a list to avoid modification during iteration
        print(f"Removing object: {obj.name}")
        bpy.data.objects.remove(obj, do_unlink=True)
    
    # Clear all collections
    for collection in list(bpy.data.collections):  # Create a list to avoid modification during iteration
        print(f"Removing collection: {collection.name}")
        bpy.data.collections.remove(collection)
    
    # Clear all scene data
    data_types = [
        (bpy.data.meshes, "mesh"),
        (bpy.data.materials, "material"),
        (bpy.data.textures, "texture"),
        (bpy.data.images, "image"),
        (bpy.data.node_groups, "node group"),
        (bpy.data.actions, "action"),
        (bpy.data.particles, "particle system")
    ]
    
    for data_container, type_name in data_types:
        for item in list(data_container):  # Create a list to avoid modification during iteration
            print(f"Removing {type_name}: {item.name}")
            data_container.remove(item)
    
    print("Complete scene cleanup completed")
