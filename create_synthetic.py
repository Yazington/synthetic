import bpy
import json
from pathlib import Path

# Relative imports from your add-on
from ..scripts import env_setup, surface
from ..asset_manager.utils import create_asset_browser_entry
from ..scatter import functions

def load_strand_asset(asset_folder, asset_name):
    folder_path = Path(asset_folder)
    product_json_path = folder_path / "product.json"
    if not product_json_path.exists():
        print(f"Error: product.json not found in {asset_folder}")
        return None

    with open(product_json_path, "r") as f:
        product_data = json.load(f)

    asset_obj = create_asset_browser_entry(
        bpy.context,
        name=asset_name,
        product_data=product_data,
        asset_type="3D_PLANT",
        asset_dir=folder_path,
        create_object_entry=True,
        create_lod_collection_entry=True,
    )
    return asset_obj

def scatter_single_strand(emitter_obj, strand_asset):
    single_strand_collection = bpy.data.collections.new("Single Strand")
    bpy.context.scene.collection.children.link(single_strand_collection)

    if strand_asset.name not in single_strand_collection.objects:
        single_strand_collection.objects.link(strand_asset)

    scatter_system = functions.create_grass_system(
        emitter=emitter_obj,
        asset_collection=single_strand_collection,
        count=1,
        size_base=1.0,
        size_random=0.3,
        clustering=0.5
    )
    return scatter_system

def main():
    env_setup.clean_scene()
    lawn_surface = surface.create_grass_surface()

    asset_folder = r"C:\Users\yazan\Workspace\tcv\assets\FieldMeadowPathside_lms82_FadedDandelionMeadow\Faded Dandelion Meadow\Assets\DactylisGlomerata_bb1ly"
    strand_asset = load_strand_asset(asset_folder, "DactylisGlomerata")

    if strand_asset is None:
        print("Failed to load the strand asset.")
    else:
        scatter_system = scatter_single_strand(lawn_surface, strand_asset)
        print("Scatter system created:", scatter_system)
