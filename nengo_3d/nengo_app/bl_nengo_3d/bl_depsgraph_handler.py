import logging
import bpy

from bl_nengo_3d import connection_handler
from bl_nengo_3d.share_data import share_data


def graph_edges_recalculate_handler(scene: bpy.types.Scene):
    # must be 3d viewport
    if not hasattr(bpy.context, 'selected_objects'):
        return
    g_view = share_data.model_graph_view
    if g_view is None:
        return
    nodes_to_update = []
    for obj in bpy.context.selected_objects:
        # must be node
        if share_data.model_graph_view.nodes.get(obj.name) is None:
            continue
        # only when position changed
        if obj.before_loc == obj.location:
            continue

        nodes_to_update.append(obj.name)
        nodes_to_update.extend(g_view.successors(obj.name))
        nodes_to_update.extend(g_view.predecessors(obj.name))
        obj.before_loc = obj.location

    g = share_data.model_graph
    pos = {}
    for node in nodes_to_update:
        node_data = g.get_node_or_subnet_data(node)
        _obj = bpy.data.objects[node_data['_blender_object_name']]
        pos[_obj.name] = _obj.location
    connection_handler.regenerate_edges(
        g=g,
        g_view=g_view,
        nengo_3d=bpy.context.scene.nengo_3d,
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
