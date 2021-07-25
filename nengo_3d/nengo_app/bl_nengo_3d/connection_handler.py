import logging
import socket
from functools import partial

import bmesh
import bpy
import networkx as nx
from mathutils import Vector

import bl_nengo_3d.schemas as schemas
from bl_nengo_3d.bl_properties import Nengo3dProperties
from bl_nengo_3d.share_data import share_data

logger = logging.getLogger(__file__)

update_interval = 0.1


def redraw_all():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


def handle_step_update(simulation_steps: list[dict]):
    # simulation_steps: schemas.SimulationSteps
    # logger.debug(share_data.charts)
    for simulation_step in simulation_steps:
        step = simulation_step['step']
        node_name = simulation_step['node_name']
        axes_list = share_data.charts[node_name]
        for param, value in simulation_step['parameters'].items():
            used = False
            for ax in axes_list:
                # logger.debug(f'{ax.parameter}')
                if ax.parameter == param:
                    ax.append_data(X=[step, ], Y=[value[0], ], truncate=10, auto_range=True)
                    used = True
            if not used:
                logger.warning(f'{node_name}: {param} was not used for any chart')


def handle_data(nengo_3d: Nengo3dProperties):
    # In non-blocking mode blocking operations error out with OS specific errors.
    # https://docs.python.org/3/library/socket.html#notes-on-socket-timeouts
    if not share_data.client:
        return None
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
        pass  # ???
    else:
        message = data.decode("utf-8")
        logger.debug(f'Incoming: {message}')
        answer_schema = schemas.Message()
        incoming_answer: dict = answer_schema.loads(message)  # json.loads(message)
        if incoming_answer['schema'] == schemas.NetworkSchema.__name__:
            data_scheme = schemas.NetworkSchema()
            data = data_scheme.load(data=incoming_answer['data'])
            handle_network_model(g=data, nengo_3d=nengo_3d)
        elif incoming_answer['schema'] == schemas.SimulationSteps.__name__:
            data_scheme = schemas.SimulationSteps(many=True)
            data = data_scheme.load(data=incoming_answer['data'])
            handle_step_update(simulation_steps=data)
        else:
            logger.error(f'Unknown schema: {incoming_answer["schema"]}')

    return update_interval


verts = [(0, -0.125, 0), (0.5, -0.25, 0),
         (0, 0.125, 0), (0.5, 0.25, 0),
         (0.5, -0.125, 0), (0.5, 0.125, 0),
         (1, 0, 0), ]
edges = [(2, 0), (3, 5), (5, 2), (0, 4), (4, 1), (4, 5), (6, 3), (1, 6), ]
faces = [(0, 4, 5, 2), (1, 6, 3, 5, 4), ]


def handle_network_model(g: nx.DiGraph, nengo_3d: Nengo3dProperties) -> None:
    pos = calculate_layout(nengo_3d, g)
    pos = nx.rescale_layout_dict(pos=pos, scale=nengo_3d.spacing)
    collection = bpy.data.collections.get(nengo_3d.use_collection)
    if not collection:
        collection = bpy.data.collections.new(nengo_3d.use_collection)
        bpy.context.scene.collection.children.link(collection)
        # collection.hide_viewport = False
    node_primitive_mesh = bpy.data.meshes.get('node_primitive')
    if not node_primitive_mesh:
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=16, diameter=0.5)
        node_primitive_mesh = bpy.data.meshes.new(name='node_primitive')
        for f in bm.faces:
            f.smooth = True
        bm.to_mesh(node_primitive_mesh)
        bm.free()
    for node_name, position in pos.items():
        node_obj = bpy.data.objects.get(node_name)
        if not node_obj:
            # bpy.ops.mesh.primitive_ico_sphere_add(radius=0.2, calc_uvs=False, location=(position[0], position[1], 0.0))
            node_obj = bpy.data.objects.new(name=node_name, object_data=node_primitive_mesh)
            collection.objects.link(node_obj)
        node_obj.location = (position[0], position[1], 0.0 if nengo_3d.algorithm_dim == '2D' else position[2])

    for connection in g.edges:
        source_pos = pos[connection[0]]
        target_pos = pos[connection[1]]
        if nengo_3d.algorithm_dim == '2D':
            source_pos = [source_pos[0], source_pos[1], 0.0]
            target_pos = [target_pos[0], target_pos[1], 0.0]
        target_pos_vector = Vector(target_pos)
        source_pos_vector = Vector(source_pos)
        vector_difference: Vector = target_pos_vector - source_pos_vector

        connection_name = f'{connection[0]}-{connection[1]}'
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


Positions = dict[str, tuple]  # node: (float, float[, float]), depending on dimension


def calculate_layout(nengo_3d: Nengo3dProperties, g: nx.Graph) -> Positions:
    dim = 2 if nengo_3d.algorithm_dim == '2D' else 3
    # not the most efficient...
    maping = {  # both 3d and 2d algorithms
        "BIPARTITE_LAYOUT": partial(nx.bipartite_layout, nodes=[]),
        "CIRCULAR_LAYOUT": partial(nx.circular_layout, dim=dim),
        "KAMADA_KAWAI_LAYOUT": partial(nx.kamada_kawai_layout, dim=dim),
        "PLANAR_LAYOUT": partial(nx.planar_layout, dim=dim),
        "RANDOM_LAYOUT": partial(nx.random_layout, dim=dim),
        # "RESCALE_LAYOUT": nx.rescale_layout,
        # "RESCALE_LAYOUT_DICT": nx.rescale_layout_dict,
        "SHELL_LAYOUT": partial(nx.shell_layout, dim=dim),
        "SPRING_LAYOUT": partial(nx.spring_layout, dim=dim),
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
