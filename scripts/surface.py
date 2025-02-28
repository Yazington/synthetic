import bpy
import bmesh
import random
from math import cos
from mathutils import Vector


def create_grass_surface(
    size=10.0,  # Increased default size for larger lawn
    subdivisions=16,  # Increased for better detail at larger scale
    noise_scale=0.7,  # Increased for more dramatic height variation
    edge_randomness=0.2,
    terrain_complexity=0.9,  # Increased for more pronounced features
    micro_detail=0.3,  # Slightly increased for proportional detail
):
    """Creates an irregular grass surface with natural-looking borders.

    Args:
        size (float): Size of the grass surface (width and length)
        subdivisions (int): Number of subdivisions for detail (1-10)
        noise_scale (float): Amount of surface irregularity (0.0-1.0)
        edge_randomness (float): Amount of border irregularity (0.0-1.0)

    Returns:
        bpy.types.Object: The created grass surface object

    Raises:
        ValueError: If parameters are out of valid ranges
    """
    try:
        # Validate parameters
        if not (0.1 <= size <= 20.0):
            raise ValueError("Size must be between 0.1 and 20.0")
        if not (1 <= subdivisions <= 20):
            raise ValueError("Subdivisions must be between 1 and 20")
        if not (0.0 <= noise_scale <= 1.0):
            raise ValueError("Noise scale must be between 0.0 and 1.0")
        if not (0.0 <= edge_randomness <= 1.0):
            raise ValueError("Edge randomness must be between 0.0 and 1.0")
        if not (0.0 <= terrain_complexity <= 1.0):
            raise ValueError("Terrain complexity must be between 0.0 and 1.0")
        if not (0.0 <= micro_detail <= 1.0):
            raise ValueError("Micro detail must be between 0.0 and 1.0")

        # Create a new plane mesh
        bpy.ops.mesh.primitive_plane_add(size=size)
        obj = bpy.context.active_object

        # Enter edit mode and get the bmesh
        if obj.mode != "EDIT":
            bpy.ops.object.mode_set(mode="EDIT")

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        try:
            # Subdivide the plane for more detail
            for face in bm.faces[:]:  # Create a copy of the list to iterate
                bmesh.ops.subdivide_edges(
                    bm,
                    edges=face.edges[:],  # Create a copy of the edges list
                    cuts=subdivisions,
                    use_grid_fill=True,
                )

            # Generate random phase offsets for terrain variation
            base_phase_x = random.uniform(0, 6.28)  # 0 to 2π
            base_phase_y = random.uniform(0, 6.28)
            med_phase_x1 = random.uniform(0, 6.28)
            med_phase_y1 = random.uniform(0, 6.28)
            med_phase_x2 = random.uniform(0, 6.28)
            med_phase_y2 = random.uniform(0, 6.28)
            micro_phase_x1 = random.uniform(0, 6.28)
            micro_phase_y1 = random.uniform(0, 6.28)
            micro_phase_x2 = random.uniform(0, 6.28)
            micro_phase_y2 = random.uniform(0, 6.28)

            # Create more natural terrain variation
            for v in bm.verts[:]:
                # Scale coordinates for proper detail distribution at larger sizes
                scaled_x = v.co.x * (
                    5.0 / size
                )  # Maintain detail density at larger scales
                scaled_y = v.co.y * (5.0 / size)

                # Base terrain features (hills and depressions)
                base_noise = (
                    cos(scaled_x * 1.2 + base_phase_x)
                    * cos(scaled_y * 1.2 + base_phase_y)
                    * 1.2  # Increased from 0.8 for more dramatic hills
                    * noise_scale
                    * terrain_complexity
                )

                # Medium-scale variations (bumps and dips)
                medium_noise = (
                    cos(scaled_x * 2.5 + med_phase_x1)
                    * cos(scaled_y * 2.5 + med_phase_y1)
                    * 0.6  # Increased from 0.4
                    * noise_scale
                    + cos(scaled_x * 3.5 + med_phase_x2)
                    * cos(scaled_y * 3.5 + med_phase_y2)
                    * 0.35  # Increased from 0.25
                    * noise_scale
                ) * terrain_complexity

                # Micro-detail for soil texture
                micro_noise = (
                    (
                        cos(scaled_x * 8.0 + micro_phase_x1)
                        * cos(scaled_y * 8.0 + micro_phase_y1)
                        * 0.15
                        + cos(scaled_x * 12.0 + micro_phase_x2)
                        * cos(scaled_y * 12.0 + micro_phase_y2)
                        * 0.08
                    )
                    * micro_detail
                    * noise_scale
                )

                # Combine all noise layers
                total_noise = base_noise + medium_noise + micro_noise

                # Apply height-based scaling for more natural look
                height_scale = 1.0 - (abs(v.co.x) + abs(v.co.y)) / (size * 1.2)
                v.co.z += total_noise * max(0.2, height_scale)

                # Enhanced edge handling with organic curves
                if v.is_boundary:
                    # Calculate angle for smooth periodic variation
                    angle = (
                        random.uniform(0, 6.28)  # Random phase offset per vertex
                        + cos(v.co.x * 0.8) * 2.0  # Slower frequency for larger curves
                        + cos(v.co.y * 0.8) * 2.0
                    )

                    # Create smooth, organic edge curves
                    edge_curve = (
                        cos(angle) * cos(v.co.x * 0.4)  # Large, smooth curves
                        + cos(angle + 1.5) * cos(v.co.y * 0.4) * 0.8
                        + cos(v.co.x * 0.8) * cos(v.co.y * 0.8) * 0.4  # Medium details
                    )

                    # Calculate radial distance for edge variation
                    radial_pos = Vector((v.co.x, v.co.y)).normalized()
                    edge_dist = Vector((v.co.x, v.co.y)).length / (size * 0.5)

                    # Apply larger, smoother edge deformation
                    deform_amount = edge_randomness * 2.0  # Increased deformation
                    v.co.x += radial_pos.x * edge_curve * deform_amount
                    v.co.y += radial_pos.y * edge_curve * deform_amount

                    # Smooth height transition at edges
                    falloff = 1.0 - min(1.0, edge_dist)
                    v.co.z *= falloff
                    # Add subtle height variation at edges
                    v.co.z += (
                        (
                            cos(angle * 2.0) * 0.05  # Smooth height variation
                            + random.uniform(-0.02, 0.02)  # Tiny random detail
                        )
                        * noise_scale
                        * falloff
                    )

            # Ensure normals are consistent
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

            # Update the mesh
            bmesh.update_edit_mesh(obj.data)
        finally:
            # Clean up bmesh
            bm.free()

        # Return to object mode
        if obj.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        # Add smooth shading
        bpy.ops.object.shade_smooth()

        # Add modifiers for enhanced detail
        # Bevel modifier for smoother edges
        bevel = obj.modifiers.new(name="Bevel", type="BEVEL")
        bevel.width = 0.03
        bevel.segments = 3
        bevel.limit_method = "ANGLE"
        bevel.angle_limit = 0.785398  # 45 degrees

        # Subdivision surface for smoother overall shape
        subsurf = obj.modifiers.new(name="Subsurf", type="SUBSURF")
        subsurf.levels = 1
        subsurf.render_levels = 2

        return obj

    except Exception as e:
        # Ensure we're in object mode even if an error occurs
        if bpy.context.active_object and bpy.context.active_object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        raise RuntimeError(f"Failed to create grass surface: {str(e)}")
