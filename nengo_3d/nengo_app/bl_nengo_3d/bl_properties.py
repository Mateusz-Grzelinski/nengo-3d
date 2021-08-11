import logging
import math

import bpy

from bl_nengo_3d import colors
from bl_nengo_3d.share_data import share_data


class Nengo3dChartProperties(bpy.types.PropertyGroup):
    parent: bpy.props.StringProperty(name='')
    auto_range: bpy.props.BoolProperty(default=True)
    x_min: bpy.props.FloatProperty()
    x_max: bpy.props.FloatProperty()
    y_min: bpy.props.FloatProperty()
    y_max: bpy.props.FloatProperty()
    z_min: bpy.props.FloatProperty()
    z_max: bpy.props.FloatProperty()

    simplify: bpy.props.BoolProperty()
    threshold: bpy.props.FloatProperty(default=0.01,
                                       description='If delta is than threshold, vertex will not be added to plot',
                                       min=0.0, max=1.0, subtype='PERCENTAGE')
    # n_step: bpy.props.IntProperty()


def recurse_dict(prefix: str, value: dict):
    for k, v in value.items():
        if k.startswith('_'):
            continue
        elif isinstance(v, list):
            continue
        elif isinstance(v, tuple):
            continue
        elif isinstance(v, dict):
            yield from recurse_dict(prefix=k, value=v)
        yield prefix + '.' + k, v


_node_anti_crash = None


def node_attributes(self, context):
    global _node_anti_crash
    g = share_data.model_graph
    if not g:
        return [(':', '--no data--', '')]
    used = {}
    for _node, data in g.nodes(data=True):
        for k, v in data.items():
            if k.startswith('_'):
                continue
            if used.get(k):
                if used[k] is None:
                    used[k] = v
                continue
            elif isinstance(v, list):
                continue
            elif isinstance(v, tuple):
                continue
            elif isinstance(v, dict):
                for i, _v in recurse_dict(prefix=k, value=v):
                    if used.get(i):
                        if used[i] is None:
                            used[i] = _v
                        continue
                    used[i] = _v
            elif v is None:
                continue
            else:
                used[k] = v
    _node_anti_crash = [(':', '--Choose an attribute--', '')]
    for k, v in sorted(used.items()):
        _node_anti_crash.append((f'{k}:{type(v).__name__}', f'{k}: {type(v).__name__}', f''))
    return _node_anti_crash


def node_attributes_update(self: Nengo3dChartProperties, context):
    from bl_nengo_3d.bl_operators import get_from_path
    nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
    access_path, attr_type = nengo_3d.node_attribute.split(':')
    nengo_3d.node_mapped_colors.clear()
    access_path = access_path.split('.')
    share_data.color_gen = colors.cycle_color(nengo_3d.node_initial_color, shift_type=nengo_3d.node_color_shift)
    is_numerical = attr_type in {'int', 'float'}
    min, max = math.inf, -math.inf
    for node, data in share_data.model_graph.nodes(data=True):
        value = get_from_path(data, access_path)
        mapped_color = nengo_3d.node_mapped_colors.get(str(value))
        if not mapped_color:
            mapped_color: Nengo3dMappedColor = nengo_3d.node_mapped_colors.add()
            mapped_color.name = str(value)
            mapped_color.color = next(share_data.color_gen)
        if is_numerical and value is not None:
            if min > value:
                min = value
            elif max < value:
                max = value

    if is_numerical:
        if min == max:
            min -= 1
            max += 1
        nengo_3d.node_attr_min = min
        nengo_3d.node_attr_max = max

        for node, data in share_data.model_graph.nodes(data=True):
            value = get_from_path(data, access_path)
            obj = data['_blender_object']
            if value is None:
                obj.nengo_colors.weight = 0
            else:
                # must be normalized for color ramp to work
                obj.nengo_colors.weight = float(value) - min / (max - min)


_edge_anti_crash = None


def edge_attributes(self, context):
    global _edge_anti_crash
    g = share_data.model_graph
    if not g:
        return [(':', '--no data--', '')]
    used = {}
    for _e_src, _e_t, data in g.edges(data=True):
        for k, v in data.items():
            if k.startswith('_'):
                continue
            if used.get(k):
                if used[k] is None:
                    used[k] = v
                continue
            elif isinstance(v, list):
                continue
            elif isinstance(v, tuple):
                continue
            elif isinstance(v, dict):
                for i, _v in recurse_dict(prefix=k, value=v):
                    if used.get(i):
                        if used[i] is None:
                            used[i] = _v
                        continue
                    used[i] = _v
            elif v is None:
                continue
            else:
                used[k] = v
    _edge_anti_crash = [(':', '--Choose an attribute--', '')]
    for k, v in sorted(used.items()):
        _edge_anti_crash.append((k, f'{k}: {type(v).__name__}', f''))
    return _edge_anti_crash


def edge_attributes2(self, context):
    global _edge_anti_crash
    g = share_data.model_graph
    used = set()
    for _edge_s, _e_t, edge_data in g.edges(data=True):
        for k, v in edge_data.items():
            if k in used:
                continue
            if isinstance(v, list):
                continue
            if isinstance(v, tuple):
                continue
            if isinstance(v, dict):
                for i, _v in recurse_dict(prefix=k, value=v):
                    if i in used:
                        continue
                    yield i, i, f'{type(_v)}:{_v}'
                    used.add(i)
            yield k, k, f'{type(v)}:{v}'
            used.add(k)


color_map_items = [
    ('ENUM', 'Enum', ''),
    ('GRADIENT', 'Gradient', ''),
]


def color_map_node_update(self: 'Nengo3dProperties', context):
    material = bpy.data.materials['NengoNodeMaterial']
    mix = material.node_tree.nodes['Mix']
    if self.node_color_map == 'ENUM':
        mix.inputs[0].default_value = 1.0
    elif self.node_color_map == 'GRADIENT':
        mix.inputs[0].default_value = 0.0
    else:
        logging.error(f'Unknown value: {self.node_color_map}')


def color_map_edge_update(self, context):
    material = bpy.data.materials['NengoEdgeMaterial']
    mix = material.node_tree.nodes['Mix']
    if self.edge_color_map == 'ENUM':
        mix.inputs[0].default_value = 1.0
    elif self.edge_color_map == 'GRADIENT':
        mix.inputs[0].default_value = 0.0
    else:
        logging.error(f'Unknown value: {self.edge_color_map}')


def color_update(self, context):
    from bl_nengo_3d.bl_operators import get_from_path
    nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
    access_path, attr_type = nengo_3d.node_attribute.split(':')
    access_path = access_path.split('.')
    for node, data in share_data.model_graph.nodes(data=True):
        value = get_from_path(data, access_path)
        mapped_color = nengo_3d.node_mapped_colors.get(str(value))
        if not mapped_color:
            continue  # update only selected nodes
        obj = data['_blender_object']
        assert mapped_color, (node, str(value), list(nengo_3d.node_mapped_colors.keys()))
        obj.nengo_colors.color = mapped_color.color
        obj.update_tag()


class Nengo3dMappedColor(bpy.types.PropertyGroup):
    # id: bpy.props.StringProperty()
    color: bpy.props.FloatVectorProperty(subtype='COLOR', default=[1.0, 1.0, 1.0], update=color_update)
    # tags: bpy.props.StringProperty()


class Nengo3dProperties(bpy.types.PropertyGroup):
    show_whole_simulation: bpy.props.BoolProperty(name='Show all steps', default=False)
    show_n_last_steps: bpy.props.IntProperty(name='Show last n steps', default=100, min=0, soft_min=0)
    is_realtime: bpy.props.BoolProperty(name='Live simulate when playback')
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
            ("RANDOM_LAYOUT", "Random", "Position nodes uniformly at random in the unit square"),
            ("SPRING_LAYOUT", "Spring", "Position nodes using Fruchterman-Reingold force-directed algorithm"),
            ("SPECTRAL_LAYOUT", "Spectral", "Position nodes using the eigenvectors of the graph Laplacian"),
        ], name='Layout', description='', default='SPRING_LAYOUT')
    spacing: bpy.props.FloatProperty(name='spacing', description='', default=2, min=0)

    node_attribute: bpy.props.EnumProperty(name='Attribute', items=node_attributes, update=node_attributes_update)
    node_attr_min: bpy.props.FloatProperty(name='Min')
    node_attr_max: bpy.props.FloatProperty(name='Max')
    node_color_map: bpy.props.EnumProperty(items=color_map_items, update=color_map_node_update)
    node_mapped_colors: bpy.props.CollectionProperty(type=Nengo3dMappedColor)
    node_initial_color: bpy.props.FloatVectorProperty(name='Initial color', subtype='COLOR',
                                                      default=[0.099202, 1.000000, 0.217183])
    node_color_shift: bpy.props.EnumProperty(name='Shift type', items=[
        ('H', 'Shift hue', ''),
        ('S', 'Shift saturation', ''),
        ('V', 'Shift value', ''),
    ])

    edge_attribute: bpy.props.EnumProperty(name='Attribute', items=edge_attributes)
    edge_color_map: bpy.props.EnumProperty(items=color_map_items, update=color_map_edge_update)
    # max_colors: bpy.props.IntProperty(min=1)
    # gradient_start: bpy.props.FloatVectorProperty(subtype='COLOR', default=[0.099202, 1.000000, 0.217183])
    # gradient_end: bpy.props.FloatVectorProperty(subtype='COLOR', default=[0.099202, 1.000000, 0.217183])


class Nengo3dColors(bpy.types.PropertyGroup):
    color: bpy.props.FloatVectorProperty(subtype='COLOR', default=[1.0, 1.0, 1.0])
    weight: bpy.props.FloatProperty(default=0.0)


classes = (
    Nengo3dMappedColor,
    Nengo3dProperties,
    Nengo3dChartProperties,
    Nengo3dColors,
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()
    bpy.types.WindowManager.nengo_3d = bpy.props.PointerProperty(type=Nengo3dProperties)
    bpy.types.Object.figure = bpy.props.PointerProperty(type=Nengo3dChartProperties)
    bpy.types.Object.nengo_colors = bpy.props.PointerProperty(type=Nengo3dColors)


def unregister():
    del bpy.types.WindowManager.nengo_3d
    del bpy.types.Object.figure
    del bpy.types.Object.nengo_colors
    unregister_factory()
