import json
import socket

import bmesh

import nengo_3d_schemas
import networkx as nx

import bpy
from bl_nengo_3d.share_data import share_data
import logging

logger = logging.getLogger(__file__)

collection_name = 'Sockets'
update_interval = 1


def redraw_all():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def handle_data():
    # In non-blocking mode blocking operations error out with OS specific errors.
    # https://docs.python.org/3/library/socket.html#notes-on-socket-timeouts
    try:
        data = share_data.client.recv(1024)
    except socket.timeout:
        return update_interval
    except (ConnectionAbortedError, ConnectionResetError):
        return None
    except Exception as e:
        logger.exception(e)
        return None  # unregisters handler

    if not data:
        pass
    else:
        message = data.decode("utf-8")
        logger.debug(f'Incoming: {message}')
        incoming_json: dict = json.loads(message)
        s = nengo_3d_schemas.NetworkSchema()
        network = s.load(data=incoming_json)

        g = nx.DiGraph()
        for node_name, attributes in network['nodes'].items():
            g.add_node(node_name)
        for conn_name, attributes in network['connections'].items():
            g.add_edge(attributes['pre'], attributes['post'])
        pos = nx.spring_layout(g)
        logger.debug(pos)

        # Fetch the 'Sockets' collection or create one. Anything created via sockets will be linked
        # to that collection.
        try:
            collection = bpy.data.collections[collection_name]
        except KeyError:
            collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(collection)
            collection.hide_viewport = False

        node_primitive_mesh = bpy.data.meshes.get('node_primitive')
        if not node_primitive_mesh:
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, diameter=1)
            node_primitive_mesh = bpy.data.meshes.new(name='node_primitive')
            bm.to_mesh(node_primitive_mesh)
            bm.free()

        for node_name, position in pos.items():
            node_obj = bpy.data.objects.get(node_name)
            if not node_obj:
                # bpy.ops.mesh.primitive_ico_sphere_add(radius=0.2, calc_uvs=False, location=(position[0], position[1], 0.0))
                node_obj = bpy.data.objects.new(name=node_name, object_data=node_primitive_mesh)
                collection.objects.link(node_obj)
            node_obj.location = (position[0], position[1], 0.0)

        # if objects := incoming.get('objects'):
        #     objects: dict
        #     for uuid, object in objects.items():
        #         object: dict
        # if object['type'] == 'Connection':  # nengo.Connection
        #     pass
        # object.pre
        # object.post
        # elif object['type'] in {'Node', 'Ensemble'}:
        #     import random
        #     mesh_data = bpy.data.meshes.new(name=uuid)
        #     obj = bpy.data.objects.new('cube', mesh_data)
        #     obj.location = (random.random(), random.random(), random.random())
        #     collection.objects.link(obj)

        # if 'cube' in data.decode('utf-8'):
        #     mesh_data = bpy.data.meshes.new(name='m_cube')
        #     obj = bpy.data.objects.new('cube', mesh_data)
        #     collection.objects.link(obj)
        #
        # if 'empty' in data.decode('utf-8'):
        #     empty = bpy.data.objects.new('empty', None)
        #     empty.empty_display_size = 2
        #     empty.empty_display_type = 'PLAIN_AXES'
        #     collection.objects.link(empty)

        if 'quit' in data.decode('utf-8'):
            share_data.client.close()
            share_data.client = None
            return None  # unregisters handler

    return update_interval
