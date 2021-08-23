import logging
import os
import socket
import struct
import time
from functools import partial

import bpy
import networkx as nx
import numpy as np
from mathutils import Vector

import bl_nengo_3d.schemas as schemas
from bl_nengo_3d import nx_layouts, bl_operators
from bl_nengo_3d.bl_nengo_primitives import get_primitive_material, get_primitive
from bl_nengo_3d.bl_properties import Nengo3dProperties
from bl_nengo_3d.charts import normalize
from bl_nengo_3d.share_data import share_data
from bl_nengo_3d.time_utils import ExecutionTimes

logger = logging.getLogger(__file__)

update_interval = 0.1

execution_times = ExecutionTimes(max_items=10)


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
        logger.debug(f'Incoming: {message[:1000]}')
        start = time.time()
        handle_single_packet(message, nengo_3d)
        end = time.time()
        execution_times.append(end - start)

    return update_interval


def handle_single_packet(message: str, nengo_3d: Nengo3dProperties):
    from bl_nengo_3d.digraph_model import DiGraphModel
    answer_schema = schemas.Message()
    incoming_answer: dict = answer_schema.loads(message)  # json.loads(message)
    if incoming_answer['schema'] == schemas.NetworkSchema.__name__:
        data_scheme = schemas.NetworkSchema()
        g, data = data_scheme.load(data=incoming_answer['data'])
        g: DiGraphModel
        share_data.model_graph = g

        # nengo_3d.expand_subnetworks.clear()
        for subnet in g.list_subnetworks():
            # logger.debug(subnet)
            item = nengo_3d.expand_subnetworks.add()
            item.name = subnet.name
            item.network = subnet.name
            item.expand = False  # bool(g.networks.get(subnet.name))
        nengo_3d.expand_subnetworks['model'].expand = True

        share_data.model_graph_view = g.get_graph_view(nengo_3d)

        handle_network_model(g=share_data.model_graph_view, nengo_3d=nengo_3d)

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
        for simulation_step in sorted(data, key=lambda sim_step: sim_step['step']):
            share_data.current_step = simulation_step['step']
            parameters = simulation_step.get('parameters')
            if not parameters:
                continue
            node_name = simulation_step['node_name']
            for access_path, value in parameters.items():
                share_data.simulation_cache[node_name, access_path].append(np.array(value))

        if share_data.step_when_ready != 0 and not nengo_3d.is_realtime:
            bpy.context.scene.frame_current += share_data.step_when_ready
            share_data.step_when_ready = 0
        # bl_operators.NengoColorNodesOperator.recolor_nodes(nengo_3d)
    elif incoming_answer['schema'] == schemas.PlotLines.__name__:
        data_scheme = schemas.PlotLines()
        data = data_scheme.load(data=incoming_answer['data'])
        plot_id = data['plot_id']
        access_path = data['access_path']
        source = data['source']
        axes = share_data.get_chart(source, access_path=access_path)
        ax = None
        for _ax in axes:
            if _ax.root.name == plot_id and _ax.parameter == access_path:
                ax = _ax
                break
        datax = np.array(data['x'])
        datay = np.array(data['y'])
        if access_path == 'neurons.response_curves':
            for i in range(datay.shape[1]):
                ax.plot(datax, datay[:, i], label=f'Neuron {i}')
        elif access_path == 'neurons.tuning_curves':  # todo handle higher dim
            for i in range(datay.shape[-1]):
                ax.plot(datax[:, 0], datay[:, i], label=f'Neuron {i}')
        ax.relim()
        ax.draw()
    else:
        logger.error(f'Unknown schema: {incoming_answer["schema"]}')


def handle_network_model(g: 'DiGraphModel', nengo_3d: Nengo3dProperties,
                         bounding_box: tuple[float, float, float] = None,
                         center: tuple[float, float, float] = None,
                         select: bool = False):
    # logger.debug((g, nengo_3d, bounding_box))
    pos = calculate_layout(nengo_3d, g)
    dim = 2 if nengo_3d.algorithm_dim == '2D' else 3
    if bounding_box:
        norm_pos_x, _, _ = normalize(list(i[0] for i in pos.values()))
        norm_pos_y, _, _ = normalize(list(i[1] for i in pos.values()))
        if dim == 3:
            norm_pos_z, _, _ = normalize(list(i[2] for i in pos.values()))
            for node_name, pos_x, pos_y, pos_z in zip(pos.keys(), norm_pos_x, norm_pos_y, norm_pos_z):
                pos[node_name] = (pos_x * bounding_box[0], pos_y * bounding_box[1], pos_z * bounding_box[2])
        else:
            for node_name, pos_x, pos_y in zip(pos.keys(), norm_pos_x, norm_pos_y):
                pos[node_name] = (pos_x * bounding_box[0], pos_y * bounding_box[1], 0.0)
    else:
        pos = nx.rescale_layout_dict(pos=pos, scale=nengo_3d.spacing)
        if dim == 2:
            for node_name, position in pos.items():
                pos[node_name] = tuple((*position, 0.0))
    if center:
        for node_name, position in pos.items():
            pos[node_name] = (position[0] + center[0], position[1] + center[1], position[2] + center[2])

    collection = bpy.data.collections.get(nengo_3d.collection)
    if not collection:
        collection = bpy.data.collections.new(nengo_3d.collection)
        bpy.context.scene.collection.children.link(collection)

    # logger.debug(pos)
    regenerate_nodes(g, nengo_3d, pos, select=select)
    regenerate_edges(g, nengo_3d, pos, select=select)
    bl_operators.NengoColorNodesOperator.recolor_nodes(nengo_3d)


class Arrow:
    """Flat arrow encoded as geometry"""

    @classmethod
    @property
    def arrow_radius(cls) -> float:
        return bpy.context.window_manager.nengo_3d.arrow_radius

    @classmethod
    @property
    def arrow_length(cls) -> float:
        return bpy.context.window_manager.nengo_3d.arrow_length

    @classmethod
    @property
    def arrow_back_length(cls) -> float:
        return bpy.context.window_manager.nengo_3d.arrow_back_length

    @classmethod
    @property
    def arrow_width(cls) -> float:
        return bpy.context.window_manager.nengo_3d.arrow_width

    @classmethod
    @property
    def original_len(cls) -> float:
        return max(v[0] for v in cls.verts)

    @classmethod
    @property
    def verts(cls) -> list[tuple[float, float, float]]:
        _verts = [
            (0, -0.125 * cls.arrow_width, 0),
            (cls.arrow_length + cls.arrow_back_length, -0.25 * cls.arrow_radius, 0),
            (0, 0.125 * cls.arrow_width, 0),
            (cls.arrow_length + cls.arrow_back_length, 0.25 * cls.arrow_radius, 0),
            (cls.arrow_length, -0.125 * cls.arrow_width, 0),
            (cls.arrow_length, 0.125 * cls.arrow_width, 0),
            (1, 0, 0),
        ]
        return _verts

    @classmethod
    @property
    def edges(cls) -> list[tuple[float, float]]:
        _edges = [(2, 0), (3, 5), (5, 2), (0, 4), (4, 1), (4, 5), (6, 3), (1, 6), ]
        return _edges

    @classmethod
    @property
    def faces(cls) -> list[tuple[float]]:
        _faces = [(0, 4, 5, 2), (1, 6, 3, 5, 4), ]
        return _faces


def regenerate_edges(g: 'DiGraphModel', nengo_3d: Nengo3dProperties, pos: dict[str, tuple[float, float, float]],
                     select: bool = False):
    collection = bpy.data.collections.get(nengo_3d.collection)
    material = get_primitive_material('NengoEdgeMaterial')
    for node_source, node_target, edge_data in g.edges.data():  # todo iterate pos, not edges?
        source_pos = pos.get(node_source)
        if not source_pos:
            continue
        target_pos = pos.get(node_target)
        if not target_pos:
            continue
        target_pos_vector = Vector(target_pos)
        source_pos_vector = Vector(source_pos)
        vector_difference: Vector = target_pos_vector - source_pos_vector

        src_dim = max(g.nodes[node_target]['_blender_object'].dimensions) / 2
        target_dim = max(g.nodes[node_target]['_blender_object'].dimensions) / 2
        # arrow_height = 1  # 0.5

        connection_name = edge_data['name']
        connection_obj = bpy.data.objects.get(connection_name)
        connection_primitive = bpy.data.meshes.get(connection_name)
        if connection_obj and connection_primitive:
            regenerate_edge_mesh(connection_primitive,
                                 length=vector_difference.length - Arrow.original_len - target_dim)
        elif connection_obj and not connection_primitive:
            assert False
        elif not connection_obj and not connection_primitive:
            connection_primitive = bpy.data.meshes.new(connection_name)
            # make arrow longer
            regenerate_edge_mesh(connection_primitive,
                                 length=vector_difference.length - Arrow.original_len - target_dim)
            connection_obj = bpy.data.objects.new(name=connection_name, object_data=connection_primitive)
            connection_obj.rotation_mode = 'QUATERNION'
            collection.objects.link(connection_obj)
        elif not connection_obj and connection_primitive:
            assert False, 'Object was deleted by hand, and mesh is still not deleted'
        else:
            assert False, 'Should never happen'
        connection_obj.select_set(select)
        connection_obj.hide_viewport = False
        connection_obj.hide_select = not nengo_3d.select_edges
        connection_obj.location = source_pos
        connection_obj.nengo_colors.color = [0.011030, 0.011030, 0.011030]
        connection_obj.active_material = material
        connection_obj.rotation_quaternion = vector_difference.to_track_quat('X', 'Z')
        g.edges[node_source, node_target]['_blender_object'] = connection_obj


def regenerate_edge_mesh(connection_primitive: bpy.types.Mesh, length: float):
    connection_primitive.clear_geometry()
    _verts = Arrow.verts
    for i in range(len(Arrow.verts)):
        # skip vert 0 and 2 - they are the base of arrow
        if i in {0, 2}:
            continue
        x = Arrow.verts[i][0] + length
        """x = original x position - node size - initial arrow length"""
        _verts[i] = (x, Arrow.verts[i][1], Arrow.verts[i][2])
    connection_primitive.from_pydata(_verts, Arrow.edges, Arrow.faces)


def regenerate_nodes(g: 'DiGraphModel', nengo_3d: Nengo3dProperties, pos: dict[str, tuple[float, float, float]],
                     select: bool = False):
    material = get_primitive_material('NengoNodeMaterial')
    collection = bpy.data.collections.get(nengo_3d.collection)
    for node_name, position in pos.items():
        node_obj = bpy.data.objects.get(node_name)
        node = share_data.model_graph.get_node_or_subnet_data(node_name)
        if not node_obj:
            # logger.debug((node_name, node, node['type'] if node else '?'))
            node_type = node['type']
            node_obj = get_primitive(type_name=node_type).copy()
            if node_type == 'Network':
                mod = node_obj.modifiers.new('Wireframe', 'WIREFRAME')
                mod.thickness = 0.05
            node_obj.name = node_name
            collection.objects.link(node_obj)
            node_obj.active_material = material
            node_obj.select_set(select)
        node_obj.hide_viewport = False
        node_obj.location = position
        node['_blender_object'] = node_obj
        g.nodes[node_name]['_blender_object'] = node_obj


Positions = dict[str, tuple]  # node: (float, float[, float]), depending on dimension


def calculate_layout(nengo_3d: Nengo3dProperties, g: nx.Graph) -> Positions:
    dim = 2 if nengo_3d.algorithm_dim == '2D' else 3
    # not the most efficient...
    maping = {  # both 3d and 2d algorithms
        "HIERARCHICAL": partial(nx_layouts.hierarchy_pos, seed=0),
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
        "MULTIPARTITE_LAYOUT": partial(nx.multipartite_layout, subset_key='_type'),
    }

    if 'MULTIPARTITE_LAYOUT' in {nengo_3d.layout_algorithm_2d, nengo_3d.layout_algorithm_3d} and \
            not next(iter(g.nodes.values())).get('_type'):
        cache = {}
        i = 0

        def gen_id(name: str):
            nonlocal i
            if id := cache.get(name):
                return id
            else:
                i += 1
                cache[name] = i
                return i

        for node, node_data in g.nodes(data=True):
            node_data['_type'] = gen_id(node_data['type'])
    if dim == 2:
        return maping[nengo_3d.layout_algorithm_2d](G=g)
    else:
        return maping[nengo_3d.layout_algorithm_3d](G=g)
    logger.error(f'not implemented algorithm: {nengo_3d.layout_algorithm}')
    return {}
