from typing import Optional

import bpy


def copy_property_group(src: bpy.types.PropertyGroup, dst: bpy.types.PropertyGroup):
    """dst collections should be empty"""
    for name, prop in src.rna_type.properties.items():
        if name == 'rna_type':
            continue
        value_src = getattr(src, name)
        value_dst = getattr(dst, name)
        if isinstance(prop, bpy.types.CollectionProperty):
            # logging.debug(f'Name: {name}, Value: {prop}, Type:{type(prop)}')
            for iname, i in value_src.items():
                # item = value_dst.get(iname)  # unreliable, names does not need to be set
                # if not item:
                item = value_dst.add()
                item.name = iname
                copy_property_group(i, item)
            assert len(value_src) == len(value_dst), (value_src, value_dst)
        elif isinstance(prop, bpy.types.PointerProperty):
            copy_property_group(value_src, value_dst)
        else:
            setattr(dst, name, value_src)


def probeable_recurse_dict(prefix: Optional[str], value: dict):
    probeable = value.get('probeable') or []
    for param in probeable:
        yield prefix + '.probeable.' + param if prefix else 'probeable.' + param

    for k, v in value.items():
        if k.startswith('_'):
            continue
        elif isinstance(v, list):
            continue
        elif isinstance(v, tuple):
            continue
        elif isinstance(v, dict):
            yield from probeable_recurse_dict(prefix=prefix + '.' + k if prefix else k, value=v)
        # yield prefix + '.' + k if prefix else k


_probeable_nodes_anti_crash = None
_probeable_nodes_cache = None


def probeable_nodes(self, context):
    global _probeable_nodes_anti_crash, _probeable_nodes_cache
    from bl_nengo_3d.share_data import share_data
    g = share_data.model_graph_view
    if not g:
        return [(':', '--no data--', '')]
    if _probeable_nodes_cache == g and _probeable_nodes_anti_crash:
        return _probeable_nodes_anti_crash
    else:
        _probeable_nodes_cache = g
    _probeable_nodes_anti_crash = [(':', '--Choose an attribute--', '')]
    probeables = set()
    for node in g.nodes:
        node = share_data.model_graph.get_node_or_subnet_data(node)
        probeables.update(list(probeable_recurse_dict(prefix=None, value=node)))
        if node.get('type') == 'Ensemble':
            probeables.add('neurons.response_curves')
            probeables.add('neurons.tuning_curves')
    for param in sorted(probeables):
        _probeable_nodes_anti_crash.append((param, param, ''))
    return _probeable_nodes_anti_crash


def probeable(self, context):
    from bl_nengo_3d.share_data import share_data
    from bl_nengo_3d.bl_properties import LineSourceProperties
    yield ':', '--Choose--', ''
    if isinstance(self, LineSourceProperties):
        obj_name = self.source_obj
    else:
        obj_name = context.active_object
    if not obj_name:
        return
    if share_data.model_graph_view is None:
        return
    item = None
    node = share_data.model_graph.get_node_or_subnet_data(obj_name)
    _, _, edge = share_data.model_graph.get_edge_by_name(obj_name)
    if node:
        item = node
    elif edge:
        item = edge
    else:
        return

    for param in probeable_recurse_dict(prefix=None, value=item):
        yield param, param, ''

    if item.get('type') == 'Ensemble':
        yield 'neurons.response_curves', 'Response Curves', ''
        yield 'neurons.tuning_curves', 'Tuning Curves', ''


def redraw_all():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
