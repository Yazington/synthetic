# Synthetic Lawn Data Generation

This Blender-based project provides tools for generating synthetic lawn/grass surface data with advanced asset management and scattering capabilities. It creates realistic, natural-looking lawn surfaces with customizable parameters for terrain variation and detail. The project can be used either as a Blender addon or by directly using the source code, providing flexibility for different integration needs.

The source code approach allows direct access to the underlying functionality without requiring addon installation, making it ideal for custom pipeline integration and automated workflows.

## Core Features

### 1. Grass Surface Generation

- Creates natural-looking lawn surfaces with organic borders
- Configurable parameters for size, detail level, and terrain variation
- Multi-layered noise generation for realistic terrain:
  - Base terrain features (hills and depressions)
  - Medium-scale variations (bumps and dips)
  - Micro-detail for soil texture
- Enhanced edge handling with organic curves
- Automatic smoothing and detail enhancement through Blender modifiers

### 2. Asset Management

- Asset installation and synchronization
- Asset browser integration
- Library management for reusable assets
- Support for custom asset catalogs

### 3. Environment Management

- Create and manage environment configurations
- Environment property handling
- Environment installation and synchronization
- Support for environment templates

### 4. Scatter System

- Scatter objects across surfaces with customizable patterns
- Preset management for scatter configurations
- Advanced scatter item manipulation
- Support for linked and unique scatter systems

## Usage

### Basic Surface Generation

```python
from blender_scripts import surface

# Create a grass surface with default parameters
surface.create_grass_surface()

# Create a customized grass surface
surface.create_grass_surface(
    size=10.0,              # Size of the grass surface
    subdivisions=16,        # Detail level
    noise_scale=0.7,        # Amount of surface irregularity
    edge_randomness=0.2,    # Border irregularity
    terrain_complexity=0.9, # Overall terrain features
    micro_detail=0.3        # Fine detail level
)
```

### Parameters

- `size` (float, 0.1-20.0): Controls the width and length of the grass surface
- `subdivisions` (int, 1-20): Number of subdivisions for detail
- `noise_scale` (float, 0.0-1.0): Amount of surface irregularity
- `edge_randomness` (float, 0.0-1.0): Amount of border irregularity
- `terrain_complexity` (float, 0.0-1.0): Intensity of terrain features
- `micro_detail` (float, 0.0-1.0): Level of fine surface detail

### Asset Management Usage

The project can be used either as a Blender addon or by using the source code directly. Here's how to use it with the source code:

```python
from asset_manager.utils import create_asset_browser_entry
from pathlib import Path

# Import grass assets
def import_grass_assets():
    # Read the product.json file
    product_json_path = "path/to/asset/product.json"
    with open(product_json_path, "r") as f:
        product_data = json.loads(f.read())

    # Create asset browser entry
    result = create_asset_browser_entry(
        bpy.context,
        name="GrassAsset",
        product_data=product_data,
        asset_type="3D_PLANT",
        asset_dir=Path("path/to/asset"),
        create_object_entry=True,
        create_lod_collection_entry=True,
    )
```

### Scatter System Usage

The scatter system implements a dual-particle system approach for realistic lawn generation:

1. **Main Grass System**

   - High density (3000 instances) for primary grass coverage
   - Consistent size variation (base: 1.0, random: 0.3)
   - Uses true grass species (DactylisGlomerata, LoliumPerenne, etc.)
   - Natural clustering through reduced randomization

2. **Weed System**
   - Low density (150 instances, ~5% of grass density)
   - More varied sizes (base: 1.2, random: 0.4)
   - Includes weeds and flowers (PlantagoLanceolata, TaraxacumOfficinale, etc.)
   - Scattered naturally throughout the grass

The system can be used directly through the source code:

```python
from scatter import functions
from scatter.store import scattersystempresetstore

def setup_scatter_system(surface_obj):
    # Set scatter surface
    bpy.context.scene.gscatter.scatter_surface = surface_obj

    # Create separate collections for grasses and weeds
    grass_collection = bpy.data.collections.new("True Grasses")
    weed_collection = bpy.data.collections.new("Weeds")

    # Sort assets into appropriate collections
    for obj in grass_objects:
        if is_true_grass(obj):  # Based on asset name/type
            grass_collection.objects.link(obj)
        else:
            weed_collection.objects.link(obj)

    # Create particle systems with natural distribution
    create_grass_system(surface_obj, grass_collection,
        count=3000,
        size_base=1.0,
        size_random=0.3,
        clustering=0.8  # Reduced randomization for natural grouping
    )

    create_weed_system(surface_obj, weed_collection,
        count=150,
        size_base=1.2,
        size_random=0.4,
        normal_align=0.2  # Slight alignment for better ground contact
    )
```

Distribution Features:

- Separate particle systems for grasses and weeds
- Realistic density ratios (20:1 grass to weed ratio)
- Natural clustering through reduced randomization
- Ground-aware placement with slight normal alignment
- Size variation tailored to vegetation type
- Full utilization of all available grass and weed assets

#### Complete Grass Scattering Workflow

1. Create a lawn surface:

```python
from blender_scripts import surface

# Generate the base lawn surface with natural terrain
lawn_surface = surface.create_grass_surface(
    size=10.0,              # Size of the grass surface
    terrain_complexity=0.9, # Natural terrain variation
    micro_detail=0.4        # Fine surface detail
)
```

2. Import grass assets:

```python
# Import grass assets using asset manager
from asset_manager.utils import create_asset_browser_entry

# Import each grass variety
grass_types = [
    "DactylisGlomerata",  # Orchard Grass
    "LoliumPerenne",      # Perennial Ryegrass
    "PlantagoLanceolata", # Ribwort Plantain
    "TaraxacumOfficinale",# Dandelion
    "TrisetumFlavescens"  # Yellow Oat Grass
]

for grass in grass_types:
    create_asset_browser_entry(
        bpy.context,
        name=grass,
        product_data=product_data,  # From product.json
        asset_type="3D_PLANT",
        asset_dir=Path(asset_path)
    )
```

3. Set up scatter system:

```python
# Create and configure scatter system
scatter_system = setup_scatter_system(lawn_surface)

# Configure natural distribution
if scatter_system:
    distribution_node = scatter_system.obj.modifiers[0].node_group.nodes["GScatter"].node_tree.nodes["DISTRIBUTION"]
    if distribution_node:
        distribution_node.inputs["Density"].default_value = 1200     # Dense coverage
        distribution_node.inputs["Scale Random"].default_value = 0.4  # Natural size variation
        distribution_node.inputs["Rotation Random"].default_value = 1.0  # Random orientation
        distribution_node.inputs["Position Random"].default_value = 0.15 # Slight position variation
```

Tips for realistic grass scattering:

- Use multiple grass variations for natural diversity
- Apply random rotation for organic appearance
- Vary scale slightly between instances
- Consider terrain height for density distribution
- Use environment templates for proven grass setups

## Project Structure

### Core Files

- `create_synthetic.py`: Entry point script that initializes the synthetic data generation
- `blender_manifest.toml`: Project configuration file

### Blender Scripts Module

The `blender_scripts/` directory contains the core implementation split into logical components:

- `main.py`: Orchestrates the overall execution flow and module reloading
- `environment_setup.py`: Handles environment setup and Python path configuration
- `scene_cleanup.py`: Manages scene cleanup operations (removing existing grass, planes, etc.)
- `asset_importer.py`: Handles grass asset importing from blend files
- `scatter_setup.py`: Configures the particle system for grass distribution
- `surface.py`: Core implementation of grass surface generation

### Supporting Modules

- `asset_manager/`: Asset management and library functionality
- `environment/`: Environment creation and management
- `scatter/`: Scatter system implementation
- `effects/`: Effect management for scatter systems
- `common/`: Shared utilities and base functionality

### Module Details

#### environment_setup.py

Handles Python path configuration and environment setup to ensure proper module imports.

#### scene_cleanup.py

Manages scene cleanup by:

- Removing existing particle systems
- Cleaning up grass-related collections
- Removing plane objects
- Cleaning orphaned data

#### asset_importer.py

Handles grass asset importing with features like:

- Support for multiple asset paths
- Separation of grass types and weeds
- Organized collection hierarchy
- Duplicate asset prevention

#### scatter_setup.py

Configures the particle system for grass distribution with:

- Basic particle settings (count, length)
- Distribution settings (jittering, spacing)
- Rotation and scale randomization
- Display and rendering settings

#### surface.py

Core surface generation implementation with:

- Terrain generation
- Edge treatment
- Post-processing

## Features in Detail

### Terrain Generation

The surface generation uses multiple layers of noise to create realistic terrain:

1. **Base Terrain Layer**

   - Creates fundamental hills and depressions
   - Controlled by terrain_complexity parameter

2. **Medium-scale Variations**

   - Adds natural bumps and dips
   - Two frequency layers for varied detail

3. **Micro-detail Layer**
   - Adds fine soil texture
   - Multiple high-frequency noise layers

### Edge Treatment

- Organic, natural-looking borders
- Smooth height transitions
- Enhanced edge deformation for realistic boundary conditions

### Post-processing

- Automatic smooth shading
- Bevel modifier for enhanced edge detail
- Subdivision surface modifier for overall smoothness

## System Requirements

### Blender Requirements

- Blender version 4.2.0 or higher
- Python support enabled in Blender
- Must be run from within Blender's Python environment

### Permissions Required

- Network access for updates, downloads, and anonymous tracking
- File system access for installing/loading/saving assets, presets, and node groups

### Supported Features

- 3D View integration
- Geometry Nodes support
- Cross-platform compatibility (Windows, macOS, Linux)

## Notes

- The script automatically handles environment setup and module reloading
- All parameters are validated to ensure they fall within acceptable ranges
- Error handling is implemented throughout the generation process
