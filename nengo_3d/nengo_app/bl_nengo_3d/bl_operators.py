import logging
import socket
from functools import partial

import bpy

import bl_nengo_3d.schemas as schemas
from bl_nengo_3d import bl_properties
from bl_nengo_3d.bl_properties import Nengo3dProperties
from bl_nengo_3d.charts import Axes
from bl_nengo_3d.connection_handler import handle_data, handle_network_model
from bl_nengo_3d.share_data import share_data

message = schemas.Message()
simulation_scheme = schemas.Simulation()


def frame_change_pre(scene: bpy.types.Scene):
    """Updates scene for running nenego simulation"""
    # dict[frame / step, dict[object, dict[param, list[data]]]]

    frame_current = scene.frame_current
    nengo_3d: bl_properties.Nengo3dProperties = bpy.context.window_manager.nengo_3d
    if nengo_3d.is_realtime:
        # make sure you have 1 second of cache
        if not share_data.simulation_cache or frame_current + int(
                scene.render.fps) > share_data.simulation_cache_steps():
            until_step = frame_current + int(scene.render.fps)
            if until_step > share_data.requested_steps_until:
                mess = message.dumps(
                    {'schema': schemas.Simulation.__name__,
                     'data': simulation_scheme.dump({'action': 'step', 'until': until_step})
                     })
                share_data.requested_steps_until = until_step
                share_data.sendall(mess.encode('utf-8'))

        if not share_data.simulation_cache or frame_current > share_data.simulation_cache_steps():
            # there is missing data in cache, wait for it to arrive
            if bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()  # stop playback
                share_data.resume_playback_on_steps = True
                return

    nengo_3d: Nengo3dProperties = bpy.context.window_manager.nengo_3d
    for (obj_name, param, is_neuron), data in share_data.simulation_cache.items():
        charts = share_data.get_chart(obj_name, is_neurons=is_neuron)
        for ax in charts:
            if ax.parameter != param:
                continue
            # logging.debug(f'{ax.title_text}: {scene.frame_current}:{data}')
            indices = share_data.charts_sources[ax]
            try:
                if nengo_3d.show_whole_simulation:
                    xdata = [i[indices[0]] for i in data]
                    ydata = [i[indices[1]] for i in data]
                    if len(indices) == 3:
                        zdata = [i[indices[2]] for i in data]
                        ax.set_data(X=xdata, Y=ydata, Z=zdata, auto_range=True)
                    else:
                        ax.set_data(X=xdata, Y=ydata, auto_range=True)
                else:
                    if frame_current <= share_data.simulation_cache_steps():
                        start_entries = max(frame_current - nengo_3d.show_n_last_steps, 0)
                        xdata = [i[indices[0]] for i in data[start_entries:frame_current + 1]]
                        ax.xlim_min = min(i[indices[0]] for i in data[start_entries:frame_current + 1])
                        ax.xlim_max = max(i[indices[0]] for i in data[start_entries:frame_current + 1])
                        ydata = [i[indices[1]] for i in data[start_entries:frame_current + 1]]
                        ax.ylim_max = max(i[indices[1]] for i in data)
                        ax.ylim_min = min(i[indices[1]] for i in data)
                        if len(indices) == 3:
                            zdata = [i[indices[2]] for i in data[start_entries:frame_current + 1]]
                            ax.zlim_max = max(i[indices[2]] for i in data[start_entries:frame_current + 1])
                            ax.zlim_min = min(i[indices[2]] for i in data[start_entries:frame_current + 1])
                            ax.set_data(X=xdata, Y=ydata, Z=zdata)
                        else:
                            ax.set_data(X=xdata, Y=ydata)
            except IndexError as e:
                logging.error(f'Invalid indexes for data: {indices} in {ax} of {(obj_name, param, is_neuron)}: {e}')


class SimpleSelectOperator(bpy.types.Operator):
    bl_idname = "object.simple_select"
    bl_label = "Simple Object Operator"

    object_name: bpy.props.StringProperty(name='Select')

    def execute(self, context):
        ob = bpy.data.objects.get(self.object_name)
        if ob is not None:
            ob.select_set(True)
            context.view_layer.objects.active = ob
        return {'FINISHED'}


class ConnectOperator(bpy.types.Operator):
    """Connect to the Nengo 3d server"""

    bl_idname = 'nengo_3d.connect'
    bl_label = 'Connect to server'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return share_data.client is None

    def execute(self, context):
        global message
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect(('localhost', 6001))
        except Exception as e:
            self.report({'ERROR'}, f'Nengo 3d connection failed: {e}')
            return {'CANCELLED'}
        client.setblocking(False)
        client.settimeout(0.01)
        share_data.client = client
        mess = message.dumps({'schema': schemas.NetworkSchema.__name__})

        logging.debug(f'Sending: {mess}')
        share_data.sendall(mess.encode('utf-8'))

        data_scheme = schemas.Observe()
        for (source_name, is_neurons), params in share_data.charts.items():
            for param, _axes in params.items():
                data = data_scheme.dump(
                    obj={'source': source_name, 'parameter': param, 'neurons': is_neurons})
                mess = message.dumps({'schema': schemas.Observe.__name__, 'data': data})
                share_data.sendall(mess.encode('utf-8'))
        logging.debug(f'Sending: {mess}')

        bpy.app.handlers.frame_change_pre.append(frame_change_pre)
        context.scene.frame_current = 0

        handle_data_function = partial(handle_data, nengo_3d=context.window_manager.nengo_3d)
        share_data.handle_data = handle_data_function
        bpy.app.timers.register(function=handle_data_function, first_interval=0.01)
        self.report({'INFO'}, 'Connected to localhost:6001')
        return {'FINISHED'}


class DisconnectOperator(bpy.types.Operator):
    """Disconnect from the Nengo 3d server"""

    bl_idname = 'nengo_3d.disconnect'
    bl_label = 'Disconnect from server'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return share_data.client is not None

    def execute(self, context):
        bpy.app.handlers.frame_change_pre.remove(frame_change_pre)
        share_data.client.shutdown(socket.SHUT_RDWR)
        share_data.client.close()
        share_data.client = None
        context.scene.frame_current = 0
        share_data.step_when_ready = 0
        share_data.requested_steps_until = -1
        share_data.resume_playback_on_steps = False
        share_data.simulation_cache.clear()
        self.report({'INFO'}, 'Disconnected')
        return {'FINISHED'}


class NengoCalculateOperator(bpy.types.Operator):
    """Calculate graph drawing"""
    bl_idname = 'nengo_3d.calculate'
    bl_label = 'Recalculate'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return share_data.model_graph

    def execute(self, context):
        nengo_3d = context.window_manager.nengo_3d
        handle_network_model(g=share_data.model_graph, nengo_3d=nengo_3d)
        context.area.tag_redraw()
        return {'FINISHED'}


class NengoSimulateOperator(bpy.types.Operator):
    """Calculate graph drawing"""
    bl_idname = 'nengo_3d.simulate'
    bl_label = 'Recalculate'
    bl_options = {'REGISTER'}

    action: bpy.props.EnumProperty(
        items=[
            ('step', 'step', ''),
            ('stepx10', 'step x10', ''),
            ('reset', 'reset', ''),
        ], name='Action', description='')

    @classmethod
    def poll(cls, context):
        return share_data.client is not None

    def execute(self, context):
        if self.action == 'reset':
            mess = message.dumps(
                {'schema': schemas.Simulation.__name__,
                 'data': simulation_scheme.dump({'action': 'reset'})
                 })
            context.scene.frame_current = 0
            share_data.step_when_ready = 0
            share_data.requested_steps_until = -1
            share_data.resume_playback_on_steps = False
            share_data.simulation_cache.clear()
            share_data.sendall(mess.encode('utf-8'))
            return {'FINISHED'}
        elif self.action == 'step':
            cached_steps = share_data.simulation_cache_steps()
            if cached_steps and context.scene.frame_current < cached_steps:
                context.scene.frame_current += 1
            else:
                step_num = 1
                mess = message.dumps(
                    {'schema': schemas.Simulation.__name__,
                     'data': simulation_scheme.dump({'action': 'step', 'until': context.scene.frame_current + 1})
                     })
                share_data.step_when_ready += step_num
                share_data.sendall(mess.encode('utf-8'))
                return {'FINISHED'}
        elif self.action == 'stepx10':
            cached_steps = share_data.simulation_cache_steps()
            if cached_steps and context.scene.frame_current + 10 < cached_steps:
                context.scene.frame_current += 10
            else:
                step_num = 10

                until_step = context.scene.frame_current + step_num

                mess = message.dumps(
                    {'schema': schemas.Simulation.__name__,
                     'data': simulation_scheme.dump({'action': 'step', 'until': until_step})
                     })
                share_data.step_when_ready += step_num
                share_data.sendall(mess.encode('utf-8'))
                return {'FINISHED'}
        else:
            raise TypeError(self.action)
        # context.area.tag_redraw()  # todo not needed here?
        return {'CANCELLED'}


classes = (
    ConnectOperator,
    DisconnectOperator,
    NengoCalculateOperator,
    NengoSimulateOperator,
    SimpleSelectOperator
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()


def unregister():
    if share_data.handle_data and bpy.app.timers.is_registered(share_data.handle_data):
        bpy.app.timers.unregister(share_data.handle_data)
        share_data.handle_data = None
    if share_data.client:
        share_data.client.shutdown(socket.SHUT_RDWR)
        share_data.client.close()
        share_data.client = None
    unregister_factory()
