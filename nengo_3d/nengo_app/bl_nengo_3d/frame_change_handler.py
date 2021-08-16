import logging
import time

import bpy

from bl_nengo_3d import bl_properties, schemas as schemas
# from bl_nengo_3d.bl_operators import message, simulation_scheme
from bl_nengo_3d.bl_properties import Nengo3dProperties
from bl_nengo_3d.share_data import share_data, Indices
from bl_nengo_3d.time_utils import ExecutionTimes

execution_times = ExecutionTimes(max_items=3)

message = schemas.Message()
simulation_scheme = schemas.Simulation()


def frame_change_pre(scene: bpy.types.Scene):
    """Updates scene for running nenego simulation"""
    start = time.time()
    frame_current = scene.frame_current
    nengo_3d: bl_properties.Nengo3dProperties = bpy.context.window_manager.nengo_3d
    if nengo_3d.is_realtime:
        if not share_data.simulation_cache or frame_current  > share_data.simulation_cache_steps():
            if frame_current > share_data.requested_steps_until:
                mess = message.dumps(
                    {'schema': schemas.Simulation.__name__,
                     'data': simulation_scheme.dump({'action': 'step', 'until': frame_current, 'dt': nengo_3d.dt})
                     })
                share_data.requested_steps_until = frame_current
                share_data.sendall(mess.encode('utf-8'))

    for (obj_name, access_path), data in share_data.simulation_cache.items():
        charts = share_data.get_chart(obj_name, access_path=access_path)
        for ax in charts:
            if ax.parameter != access_path:
                continue
            for line in ax.plot_lines:
                # logging.debug(f'{ax.title_text}: {scene.frame_current}:{data}')
                indices: Indices = share_data.plot_line_sources[line]
                try:
                    if nengo_3d.show_whole_simulation:
                        start_entries = 0
                    else:
                        start_entries = max(frame_current - nengo_3d.show_n_last_steps, 0)
                    _data = data[start_entries:frame_current]

                    if indices.x_is_step:
                        xdata = range(start_entries, len(_data)+start_entries)
                    else:
                        xdata = [row[indices.x] for row in _data]

                    if indices.y_multi_dim:
                        ydata = [eval(f'row{indices.y_multi_dim}') for row in _data]
                    else:
                        ydata = [row[indices.y] for row in _data]
                    if indices.z:
                        if indices.z_is_step:
                            zdata = range(start_entries, frame_current)
                        else:
                            zdata = [row[indices.z] for row in _data]
                        line.set_data(X=xdata, Y=ydata, Z=zdata)
                    else:
                        line.set_data(X=xdata, Y=ydata)
                except IndexError as e:
                    logging.error(f'Invalid indexes for data: {indices} in {ax} of {(obj_name, access_path)}: {e}')
                ax.relim()
                ax.draw()
    end = time.time()
    execution_times.append(end - start)
