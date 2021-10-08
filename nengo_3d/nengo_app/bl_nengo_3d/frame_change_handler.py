import logging
import time
from typing import Iterable, Union

import bpy

import numpy as np
from bl_nengo_3d import bl_properties, schemas
from bl_nengo_3d.bl_properties import LineProperties, LineSourceProperties, Nengo3dProperties, \
    NodeMappedColor
from bl_nengo_3d.axes import Axes
from bl_nengo_3d.share_data import share_data
from bl_nengo_3d.time_utils import ExecutionTimes

execution_times = ExecutionTimes(max_items=3)

message = schemas.Message()
simulation_scheme = schemas.Simulation()

_last_update = -1


def frame_change_handler(scene: bpy.types.Scene):
    """Updates scene for running nenego simulation"""
    start = time.time()
    frame_current = scene.frame_current
    nengo_3d: Nengo3dProperties = bpy.context.scene.nengo_3d

    if nengo_3d.requires_reset:
        return  # todo allow scrubbing existing data

    # support for nengo_3d.sample_every:
    global _last_update
    if abs(_last_update - frame_current) < nengo_3d.sample_every:
        # logging.debug(f'Aborted: abs({_last_update}-{frame_current}) < {nengo_3d.sample_every}')
        return

    if nengo_3d.allow_scrubbing:
        if not share_data.simulation_cache or frame_current > share_data.simulation_cache_steps():
            if frame_current > share_data.requested_steps_until:
                from bl_nengo_3d.bl_operators import NengoSimulateOperator
                NengoSimulateOperator.simulation_step(scene=scene, action='step', step_num=nengo_3d.step_n,
                                                      sample_every=nengo_3d.sample_every, dt=nengo_3d.dt, prefetch=0)
                # share_data.requested_steps_until = frame_current
    else:
        if frame_current > (share_data.simulation_cache_steps() or 0) * nengo_3d.sample_every:
            scene.frame_current = (share_data.simulation_cache_steps() or 0) * nengo_3d.sample_every
            frame_current = scene.frame_current

    if not share_data.simulation_cache_steps() or frame_current > 1 + share_data.simulation_cache_steps() * nengo_3d.sample_every:
        # logging.debug(f'Aborted: {frame_current}, {share_data.simulation_cache_steps()}')
        return

    _last_update = frame_current - frame_current % nengo_3d.sample_every

    # calculate data range:
    if nengo_3d.show_whole_simulation:
        start_entries = 0
    else:
        start_entries = max(frame_current - nengo_3d.show_n_last_steps, 0)
    start_entries = int(start_entries / nengo_3d.sample_every)
    end_entries = int(frame_current / nengo_3d.sample_every)
    steps = list(range(start_entries, end_entries))

    if nengo_3d.node_color == 'MODEL_DYNAMIC':
        recolor_dynamic_node_attributes(nengo_3d, steps[-1] if steps else 0)

    if nengo_3d.edge_color == 'MODEL_DYNAMIC':
        # logging.debug((frame_current, start_entries, end_entries))
        # logging.debug(list(steps))
        recolor_dynamic_edge_attributes(nengo_3d, steps[-1] if steps else 0)

    # update plots
    update_plots(nengo_3d, start_entries, end_entries, steps)
    end = time.time()
    execution_times.append(end - start)


def update_plots(nengo_3d: Nengo3dProperties, start_entries: int, end_entries: int, steps: list[int]):
    debugged = False
    for (obj_name, access_path), _data in share_data.simulation_cache.items():
        data = _data[start_entries:end_entries]  # ugh, copy
        if not debugged:
            # logging.debug((start_entries, end_entries, steps, len(data)))
            debugged = True
        for ax in share_data.charts[obj_name]:
            ax: Axes
            for line_prop in ax.lines:
                line_prop: LineProperties
                line_source: LineSourceProperties = line_prop.source
                if not line_prop.update or line_source.access_path != access_path:
                    continue
                l = ax.get_line(line_prop)
                xdata, ydata, zdata = get_xyzdata(data, steps, line_prop, nengo_3d)
                l.set_data(X=xdata, Y=ydata, Z=zdata)
            if ax.auto_range:
                ax.relim()
            ax.draw()


def recolor_dynamic_node_attributes(nengo_3d: Nengo3dProperties, step: int):
    from bl_nengo_3d import colors
    # node_color_source: NodeColorSourceProperties = nengo_3d.node_color_source
    get = compile(nengo_3d.node_dynamic_get, filename='get', mode='eval')
    share_data.color_gen = colors.cycle_color(nengo_3d.node_color_gen.initial_color,
                                              shift_type=nengo_3d.node_color_gen.shift,
                                              max_colors=nengo_3d.node_color_gen.max_colors)
    nengo_3d.node_mapped_colors.clear()
    for node, node_data in share_data.model_graph_view.nodes(data=True):
        obj: bpy.types.Object = node_data['_blender_object']
        all_data = share_data.simulation_cache.get((node, nengo_3d.node_dynamic_access_path))
        if not all_data:
            obj.nengo_colors.color = (0.0, 0.0, 0.0)
            obj.update_tag()
            continue
        data = all_data[step]
        value = eval(get)
        # logging.debug((node, value, data, all_data, step))
        if isinstance(value, (float, int)):
            if nengo_3d.node_attr_auto_range:
                nengo_3d.node_attr_min = min(nengo_3d.node_attr_min, value)
                nengo_3d.node_attr_max = max(nengo_3d.node_attr_max, value)
            obj.nengo_colors.weight = value
        # todo mapped color or gradient
        mapped_color = nengo_3d.node_mapped_colors.get(str(value))
        if not mapped_color:
            mapped_color: NodeMappedColor = nengo_3d.node_mapped_colors.add()
            mapped_color.name = str(value)
            mapped_color.color = next(share_data.color_gen)
        obj.nengo_colors.color = mapped_color.color

    if nengo_3d.node_attr_min == nengo_3d.node_attr_max:
        nengo_3d.node_attr_min = 0
        nengo_3d.node_attr_max = 1

    minimum = nengo_3d.node_attr_min
    maximum = nengo_3d.node_attr_max

    for node, node_data in share_data.model_graph_view.nodes(data=True):
        obj: bpy.types.Object = node_data['_blender_object']
        value = obj.nengo_colors.weight
        obj.nengo_colors.weight = (float(value) - minimum) / (maximum - minimum)
        obj.update_tag()


def recolor_dynamic_edge_attributes(nengo_3d: Nengo3dProperties, step: int):
    from bl_nengo_3d import colors
    # edge_color_source: NodeColorSourceProperties = nengo_3d.edge_color_source
    get = compile(nengo_3d.edge_dynamic_get, filename='get', mode='eval')
    share_data.color_gen = colors.cycle_color(nengo_3d.edge_color_gen.initial_color,
                                              shift_type=nengo_3d.edge_color_gen.shift,
                                              max_colors=nengo_3d.edge_color_gen.max_colors)
    nengo_3d.edge_mapped_colors.clear()
    for e_source, e_target, e_data in share_data.model_graph_view.edges(data=True):
        obj: bpy.types.Object = e_data['_blender_object']
        all_data = share_data.simulation_cache.get((e_data['name'], nengo_3d.edge_dynamic_access_path))
        if not all_data:
            obj.nengo_colors.color = (0.0, 0.0, 0.0)
            obj.update_tag()
            continue
        # logging.debug((len(all_data), step))
        # if len(all_data) >= step:
        #     step = len(all_data) - 1  # workaround...
        # logging.debug((len(all_data), step))
        data = all_data[step]
        value = eval(get)
        # logging.debug((e_source, e_target, value, data, all_data, step))
        if isinstance(value, (float, int)):
            if nengo_3d.edge_attr_auto_range:
                nengo_3d.edge_attr_min = min(nengo_3d.edge_attr_min, value)
                nengo_3d.edge_attr_max = max(nengo_3d.edge_attr_max, value)
            obj.nengo_colors.weight = value
        # todo mapped color not needed when using gradient
        mapped_color = nengo_3d.edge_mapped_colors.get(str(value))
        if not mapped_color:
            mapped_color: NodeMappedColor = nengo_3d.edge_mapped_colors.add()
            mapped_color.name = str(value)
            mapped_color.color = next(share_data.color_gen)
        obj.nengo_colors.color = mapped_color.color

    if nengo_3d.edge_attr_min == nengo_3d.edge_attr_max:
        nengo_3d.edge_attr_min = 0
        nengo_3d.edge_attr_max = 1

    minimum = nengo_3d.edge_attr_min
    maximum = nengo_3d.edge_attr_max

    for e_source, e_target, e_data in share_data.model_graph_view.edges(data=True):
        obj: bpy.types.Object = e_data['_blender_object']
        value = obj.nengo_colors.weight
        obj.nengo_colors.weight = (float(value) - minimum) / (maximum - minimum)
        obj.update_tag()


def get_xyzdata(data: Union[np.array, list[np.array]], steps: Iterable[int], line: LineProperties,
                nengo_3d: Nengo3dProperties):
    line_source: LineSourceProperties = line.source
    # logging.debug(f'{ax.title_text}: {scene.frame_current}:{data}')
    if line_source.iterate_step:
        xdata = []
        ydata = []
        get_x = compile(line_source.get_x, filename='get_x', mode='eval')
        get_y = compile(line_source.get_y, filename='get_y', mode='eval')
        if line_source.get_z:
            zdata = []
            get_z = compile(line_source.get_z, filename='get_z', mode='eval')
            for step, row in zip(steps, data):
                step: int = step * nengo_3d.sample_every
                row: np.array
                xdata.append(eval(get_x))
                ydata.append(eval(get_y))
                zdata.append(eval(get_z))
            return xdata, ydata, zdata
        else:
            # logging.debug((line_source.get_x, line_source.get_y, len(data)))
            for step, row in zip(steps, data):
                step: int = step * nengo_3d.sample_every
                row: np.array
                xdata.append(eval(get_x))
                ydata.append(eval(get_y))
            return xdata, ydata, None
    else:
        get_x = compile(line_source.get_x, filename='get_x', mode='eval')
        get_y = compile(line_source.get_y, filename='get_y', mode='eval')
        xdata = eval(get_x)
        ydata = eval(get_y)
        if line_source.get_z:
            get_z = compile(line_source.get_z, filename='get_z', mode='eval')
            zdata = eval(get_z)
            return xdata, ydata, zdata
        return xdata, ydata, None
