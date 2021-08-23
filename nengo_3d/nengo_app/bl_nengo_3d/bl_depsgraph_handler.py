import logging
import bpy

from bl_nengo_3d import connection_handler
from bl_nengo_3d.share_data import share_data


def graph_edges_recalculate_handler(scene: bpy.types.Scene):
    # must be 3d viewport
    if not hasattr(bpy.context, 'selected_objects'):
        return
    nodes_to_update = []
    g_view = share_data.model_graph_view
    for obj in bpy.context.selected_objects:
        if not share_data.model_graph_view.nodes.get(obj.name):
            continue
        data = share_data.model_graph.get_node_or_subnet_data(obj.name)
        # must be element of network
        if not data:
            continue
        # can not be edge
        if data['type'] not in {'Node', 'Ensemble', 'Network'}:
            continue
        # only when position changed
        if obj.before_loc == obj.location:
            continue

        nodes_to_update.append(obj.name)
        nodes_to_update.extend(g_view.successors(obj.name))
        nodes_to_update.extend(g_view.predecessors(obj.name))
        obj.before_loc = obj.location

    pos = {}
    for node in nodes_to_update:
        _obj = g_view.nodes[node]['_blender_object']
        pos[_obj.name] = _obj.location
    connection_handler.regenerate_edges(
        g=g_view,
        nengo_3d=bpy.context.window_manager.nengo_3d,
        pos=pos
    )


def register():
    # bpy.app.handlers.depsgraph_update_post.append(graph_edges_recalculate_handler)
    bpy.types.Object.before_loc = bpy.props.FloatVectorProperty(name='before_loc', subtype='TRANSLATION')


def unregister():
    del bpy.types.Object.before_loc
    if graph_edges_recalculate_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(graph_edges_recalculate_handler)


if __name__ == '__main__':
    register()

    import bpy

    # Any Python object can act as the subscription's owner.
    owner = object()

    subscribe_to = bpy.context.object.location


    def msgbus_callback(*args):
        # This will print:
        # Something changed! (1, 2, 3)
        print("Something changed!", args)


    bpy.msgbus.subscribe_rna(
        key=subscribe_to,
        owner=owner,
        args=(1, 2, 3),
        notify=msgbus_callback,
    )
