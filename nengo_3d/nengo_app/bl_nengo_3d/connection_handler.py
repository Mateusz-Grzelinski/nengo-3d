import logging
import os
import socket
import struct
from collections import defaultdict
from functools import partial

import bmesh
import bpy
import networkx as nx
from mathutils import Vector

import bl_nengo_3d.schemas as schemas
from bl_nengo_3d import nx_layouts
from bl_nengo_3d.bl_properties import Nengo3dProperties
from bl_nengo_3d.share_data import share_data

logger = logging.getLogger(__file__)

update_interval = 0.1


def redraw_all():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def handle_data(nengo_3d: Nengo3dProperties):
    # In non-blocking mode blocking operations error out with OS specific errors.
    # https://docs.python.org/3/library/socket.html#notes-on-socket-timeouts
    if not share_data.client:
        return None
    try:
        size = struct.unpack("i", share_data.client.recv(struct.calcsize("i")))[0]
        data = ""
        while len(data) < size:
            msg = share_data.client.recv(size - len(data))
            if not msg:
                return None
            data += msg.decode('utf-8')
    except socket.timeout:
        return update_interval
    except (ConnectionAbortedError, ConnectionResetError) as e:
        logger.exception(e)
        return None
    except Exception as e:
        logger.exception(e)
        return None  # unregisters handler

    if data:
        message = data
        logger.debug(f'Incoming: {message}')
        handle_single_packet(message, nengo_3d)

    return update_interval


def handle_single_packet(message: str, nengo_3d: Nengo3dProperties):
    answer_schema = schemas.Message()
    incoming_answer: dict = answer_schema.loads(message)  # json.loads(message)
    if incoming_answer['schema'] == schemas.NetworkSchema.__name__:
        data_scheme = schemas.NetworkSchema()
        g, data = data_scheme.load(data=incoming_answer['data'])
        handle_network_model(g=g, nengo_3d=nengo_3d)

        file_path = data['file']

        t = bpy.data.texts.get(os.path.basename(file_path))
        if t:
            t.clear()
        else:
            t = bpy.data.texts.new(os.path.basename(file_path))
        for area in bpy.context.screen.areas:
            if area.type == 'TEXT_EDITOR':
                area.spaces[0].text = t  # make loaded text file visible
        with open(file_path, 'r') as f:
            while line := f.read():
                t.write(line)
    elif incoming_answer['schema'] == schemas.SimulationSteps.__name__:
        data_scheme = schemas.SimulationSteps(many=True)
        data = data_scheme.load(data=incoming_answer['data'])

        # logger.debug(sorted(data, key=lambda sim_step: sim_step['step']))
        for simulation_step in sorted(data, key=lambda sim_step: sim_step['step']):
            step = simulation_step['step']
            node_name = simulation_step['node_name']
            if not share_data.simulation_cache.get(node_name):
                share_data.simulation_cache[node_name] = defaultdict(list)
            for param, value in simulation_step['parameters'].items():
                assert step == len(share_data.simulation_cache[node_name][param]), \
                    (step, len(share_data.simulation_cache[node_name][param]))
                share_data.simulation_cache[node_name][param].append((step, *[float(i) for i in value]))

        if share_data.step_when_ready != 0 and not nengo_3d.is_realtime:
            bpy.context.scene.frame_current += share_data.step_when_ready
            share_data.step_when_ready = 0

        if share_data.resume_playback_on_steps:
            if not bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()  # start playback
            share_data.resume_playback_on_steps = False
    else:
        logger.error(f'Unknown schema: {incoming_answer["schema"]}')


verts = [(0, -0.125, 0), (0.5, -0.25, 0),
         (0, 0.125, 0), (0.5, 0.25, 0),
         (0.5, -0.125, 0), (0.5, 0.125, 0),
         (1, 0, 0), ]
edges = [(2, 0), (3, 5), (5, 2), (0, 4), (4, 1), (4, 5), (6, 3), (1, 6), ]
faces = [(0, 4, 5, 2), (1, 6, 3, 5, 4), ]

_PRIMITIVES = {}


def get_primitive(type_name: str) -> bpy.types.Object:
    global _PRIMITIVES

    if not _PRIMITIVES:
        collection_name = 'Nengo primitives'
        collection = bpy.data.collections.get(collection_name)

        if not collection:
            collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(collection)
            collection.hide_viewport = True

        name = 'Node primitive'
        if not _PRIMITIVES.get(name):
            obj = bpy.data.objects.get(name)
            if not obj:
                primitive_mesh = bpy.data.meshes.get(name)
                if not primitive_mesh:
                    primitive_mesh = bpy.data.meshes.new(name)
                    bm = bmesh.new()
                    bmesh.ops.create_cube(bm, size=0.4)
                    bm.to_mesh(primitive_mesh)
                    bm.free()
                obj = bpy.data.objects.new(name=name, object_data=primitive_mesh)
            _PRIMITIVES[name] = obj
            collection.objects.link(obj)

        name = 'Ensemble primitive'
        if not _PRIMITIVES.get(name):
            obj = bpy.data.objects.get(name)
            if not obj:
                primitive_mesh = bpy.data.meshes.get(name)
                if not primitive_mesh:
                    primitive_mesh = bpy.data.meshes.new(name)
                    bm = bmesh.new()
                    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=16, diameter=0.5)
                    for f in bm.faces:
                        f.smooth = True
                    bm.to_mesh(primitive_mesh)
                    bm.free()
                obj = bpy.data.objects.new(name=name, object_data=primitive_mesh)
            _PRIMITIVES[name] = obj
            collection.objects.link(obj)

    if obj := _PRIMITIVES.get(f'{type_name} primitive'):
        return obj.copy()
    else:
        logger.error(f'Unknown type: {type_name}')
        return None


def handle_network_model(g: nx.DiGraph, nengo_3d: Nengo3dProperties) -> None:
    pos = calculate_layout(nengo_3d, g)
    pos = nx.rescale_layout_dict(pos=pos, scale=nengo_3d.spacing)
    collection = bpy.data.collections.get(nengo_3d.collection)
    if not collection:
        collection = bpy.data.collections.new(nengo_3d.collection)
        bpy.context.scene.collection.children.link(collection)

    for node_name, position in pos.items():
        node_obj = get_primitive(g.nodes[node_name]['type']).copy()
        node_obj.name = node_name
        collection.objects.link(node_obj)
        node_obj.location = (position[0], position[1], 0.0 if nengo_3d.algorithm_dim == '2D' else position[2])
        g.nodes[node_name]['blender_object'] = node_obj

    for node_source, node_target, edge_data in g.edges.data():
        source_pos = pos[node_source]
        target_pos = pos[node_target]
        if nengo_3d.algorithm_dim == '2D':
            source_pos = [source_pos[0], source_pos[1], 0.0]
            target_pos = [target_pos[0], target_pos[1], 0.0]
        target_pos_vector = Vector(target_pos)
        source_pos_vector = Vector(source_pos)
        vector_difference: Vector = target_pos_vector - source_pos_vector

        connection_name = edge_data['name']
        connection_obj = bpy.data.objects.get(connection_name)
        connection_primitive = bpy.data.meshes.get(connection_name)
        if connection_obj and connection_primitive:
            for i, v in enumerate(connection_obj.data.vertices):
                if i in {0, 2}: continue
                # logger.debug(f'{connection_name}: {verts[i][0]} + {vector_difference.length}')
                x = verts[i][0] + vector_difference.length - 0.5 - 1
                v.co.x = x
        elif connection_obj and not connection_primitive:
            assert False
        elif not connection_obj and not connection_primitive:
            connection_primitive = bpy.data.meshes.new(connection_name)
            # make arrow longer
            _verts = verts.copy()
            for i in range(len(verts)):
                # skip vert 0 and 2 - they are the base of arrow
                if i in {0, 2}: continue
                # logger.debug(f'{connection_name}: {verts[i][0]} + {vector_difference.length}')
                x = verts[i][0] + vector_difference.length - 0.5 - 1
                """x = original x position - node size - initial arrow length"""
                _verts[i] = (x, verts[i][1], verts[i][2])
            connection_primitive.from_pydata(_verts, edges, faces)
            connection_obj = bpy.data.objects.new(name=connection_name, object_data=connection_primitive)
            connection_obj.rotation_mode = 'QUATERNION'
            collection.objects.link(connection_obj)
        elif not connection_obj and connection_primitive:
            assert False, 'Object was deleted by hand, and mesh is still not deleted'
        else:
            assert False, 'Should never happen'
        connection_obj.location = source_pos
        connection_obj.rotation_quaternion = vector_difference.to_track_quat('X', 'Z')
        g.edges[node_source, node_target]['blender_object'] = connection_obj
    share_data.model_graph = g


Positions = dict[str, tuple]  # node: (float, float[, float]), depending on dimension


def calculate_layout(nengo_3d: Nengo3dProperties, g: nx.Graph) -> Positions:
    dim = 2 if nengo_3d.algorithm_dim == '2D' else 3
    # not the most efficient...
    maping = {  # both 3d and 2d algorithms
        "HIERARCHICAL": nx_layouts.hierarchy_pos,
        "BIPARTITE_LAYOUT": partial(nx.bipartite_layout, nodes=[]),
        "CIRCULAR_LAYOUT": partial(nx.circular_layout, dim=dim),
        "KAMADA_KAWAI_LAYOUT": partial(nx.kamada_kawai_layout, dim=dim),
        "PLANAR_LAYOUT": partial(nx.planar_layout, dim=dim),
        "RANDOM_LAYOUT": partial(nx.random_layout, dim=dim),
        # "RESCALE_LAYOUT": nx.rescale_layout,
        # "RESCALE_LAYOUT_DICT": nx.rescale_layout_dict,
        "SHELL_LAYOUT": partial(nx.shell_layout, dim=dim),
        "SPRING_LAYOUT": partial(nx.spring_layout, dim=dim, seed=0),
        "SPECTRAL_LAYOUT": partial(nx.spectral_layout, dim=dim),
        "SPIRAL_LAYOUT": partial(nx.spiral_layout, dim=dim),
        "MULTIPARTITE_LAYOUT": nx.multipartite_layout,
    }

    if dim == 2:
        return maping[nengo_3d.layout_algorithm_2d](G=g)
    else:
        return maping[nengo_3d.layout_algorithm_3d](G=g)
    # if 'SPRING_LAYOUT' == nengo_3d.layout_algorithm:
    #     return nx.spring_layout(g, dim=dim)
    logger.error(f'not implemented algorithm: {nengo_3d.layout_algorithm}')
    return {}
