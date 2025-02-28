import bpy
from pathlib import Path
from asset_manager.utils import create_asset_browser_entry
from scatter import functions

def setup_grass_scatter():
    # Get the surface object (Plane)
    surface = bpy.data.objects.get("Plane")
    if not surface:
        raise Exception("Plane object not found")

    # Set it as the scatter surface
    bpy.context.scene.gscatter.scatter_surface = surface

    # Create a collection for grass assets
    grass_collection = bpy.data.collections.new("Grass Assets")
    bpy.context.scene.collection.children.link(grass_collection)

    # Import main grass asset (DactylisGlomerata)
    grass_path = Path("assets/FieldMeadowPathside_lms82_FadedDandelionMeadow/Faded Dandelion Meadow/Assets/DactylisGlomerata_bb1ly")
    
    # Create scatter system with default preset
    scatter_item, main_tree = functions.create_new_system("Grass System", surface)

    # Configure distribution settings for natural look
    distribution_node = main_tree.nodes['GScatter'].node_tree.nodes["DISTRIBUTION"]
    if distribution_node:
        # Set moderate density for better performance
        distribution_node.inputs["Density"].default_value = 1000
        # Add some randomness to positions
        distribution_node.inputs["Position Random"].default_value = 0.2
        # Vary the scale slightly
        distribution_node.inputs["Scale Random"].default_value = 0.3
        # Random rotation for natural look
        distribution_node.inputs["Rotation Random"].default_value = 1.0

    return scatter_item

if __name__ == "__main__":
    setup_grass_scatter()
