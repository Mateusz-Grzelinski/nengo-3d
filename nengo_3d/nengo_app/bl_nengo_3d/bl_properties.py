import logging

import bpy


# class Nengo3dChartProperties(bpy.types.PropertyGroup):
#     parent: bpy.props.StringProperty(name='')


class Nengo3dProperties(bpy.types.PropertyGroup):
    show_whole_simulation: bpy.props.BoolProperty(name='Show all steps', default=False)
    show_n_last_steps: bpy.props.IntProperty(name='Show last n steps', default=100, min=0, soft_min=0)
    is_realtime: bpy.props.BoolProperty(name='Live simulate playback')
    collection: bpy.props.StringProperty(name='Collection', default='Nengo Model')
    algorithm_dim: bpy.props.EnumProperty(
        items=[
            ('2D', '2d', 'Use 2d graph drawing algorithm'),
            ('3D', '3d', 'Use 3d graph drawing algorithm'),
        ], name='Algorithm 2d/3d', description='')
    layout_algorithm_2d: bpy.props.EnumProperty(
        items=[
            ("HIERARCHICAL", "Hierarchical", ""),
            ("BIPARTITE_LAYOUT", "Bipartite", "Position nodes in two straight lines"),
            ("MULTIPARTITE_LAYOUT", "Multipartite", "Position nodes in layers of straight lines"),
            ("CIRCULAR_LAYOUT", "Circular", "Position nodes on a circle"),
            ("KAMADA_KAWAI_LAYOUT", "Kamada kawai", "Position nodes using Kamada-Kawai path-length cost-function"),
            ("PLANAR_LAYOUT", "Planar", "Position nodes without edge intersections"),
            ("RANDOM_LAYOUT", "Random", "Position nodes uniformly at random in the unit square"),
            ("SHELL_LAYOUT", "Shell", "Position nodes in concentric circles"),
            ("SPRING_LAYOUT", "Spring", "Position nodes using Fruchterman-Reingold force-directed algorithm"),
            ("SPECTRAL_LAYOUT", "Spectral", "Position nodes using the eigenvectors of the graph Laplacian"),
            ("SPIRAL_LAYOUT", "Spiral", "Position nodes in a spiral layout"),
        ], name='Layout', description='', default='SPRING_LAYOUT')
    layout_algorithm_3d: bpy.props.EnumProperty(
        items=[
            ("CIRCULAR_LAYOUT", "Circular", "Position nodes on a circle"),
            ("KAMADA_KAWAI_LAYOUT", "Kamada kawai", "Position nodes using Kamada-Kawai path-length cost-function"),
            ("PLANAR_LAYOUT", "Planar", "Position nodes without edge intersections"),
            ("RANDOM_LAYOUT", "Random", "Position nodes uniformly at random in the unit square"),
            ("SHELL_LAYOUT", "Shell", "Position nodes in concentric circles"),
            ("SPRING_LAYOUT", "Spring", "Position nodes using Fruchterman-Reingold force-directed algorithm"),
            ("SPECTRAL_LAYOUT", "Spectral", "Position nodes using the eigenvectors of the graph Laplacian"),
            ("SPIRAL_LAYOUT", "Spiral", "Position nodes in a spiral layout"),
        ], name='Layout', description='', default='SPRING_LAYOUT')
    spacing: bpy.props.FloatProperty(name='spacing', description='', default=2, min=0)


# ("RESCALE_LAYOUT", "Rescale", "Returns scaled position array to (-scale  scale) in all axes"),
# ("RESCALE_LAYOUT_DICT", "Rescale dict", "Return a dictionary of scaled positions keyed by node"),

classes = (
    Nengo3dProperties,
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()
    bpy.types.WindowManager.nengo_3d = bpy.props.PointerProperty(type=Nengo3dProperties)
    bpy.types.Object


def unregister():
    del bpy.types.WindowManager.nengo_3d
    unregister_factory()
