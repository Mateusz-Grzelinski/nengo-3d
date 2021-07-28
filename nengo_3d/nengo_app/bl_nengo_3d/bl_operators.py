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
            # share_data.requested_until_step = until_step
            mess = message.dumps(
                {'schema': schemas.Simulation.__name__,
                 'data': simulation_scheme.dump({'action': 'step', 'until': until_step})
                 })
            share_data.sendall(mess.encode('utf-8'))

        if not share_data.simulation_cache or frame_current > share_data.simulation_cache_steps():
            # there is missing data in cache, wait for it to arrive
            if bpy.context.screen.is_animation_playing:
                bpy.ops.screen.animation_play()  # stop playback
                share_data.resume_playback_on_steps = True
                return

    nengo_3d: Nengo3dProperties = bpy.context.window_manager.nengo_3d
    for obj, params in share_data.simulation_cache.items():
        charts = share_data.charts[obj]
        for param, data in params.items():
            ax: Axes = charts[param]
            # logging.debug(f'{ax.title_text}: {scene.frame_current}:{data[0]}')
            # todo handle 2 dim data
            if not nengo_3d.show_whole_simulation:
                start_entries = max(frame_current - nengo_3d.show_n_last_steps, 0)
                ydata = [i[0] for i in data[start_entries:frame_current + 1]]
                xdata = list(range(start_entries, start_entries + len(ydata)))
                if frame_current <= share_data.simulation_cache_steps():
                    ax.xlim_min = start_entries
                    ax.xlim_max = start_entries + len(ydata)
                    ax.ylim_max = max(i[0] for i in data)
                    ax.ylim_min = min(i[0] for i in data)
                    ax.set_data(X=xdata, Y=ydata)
            else:
                ydata = [i[0] for i in data]
                xdata = list(range(0, len(ydata)))
                ax.set_data(X=xdata, Y=ydata, auto_range=True)


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
        for obj, params in share_data.charts.items():
            for param, ax in params.items():
                data = data_scheme.dump(
                    obj={'source': obj, 'parameter': ax.parameter})
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
            share_data.resume_playback_on_steps = False
            share_data.simulation_cache.clear()
        elif self.action == 'step':
            step_num = 1
            mess = message.dumps(
                {'schema': schemas.Simulation.__name__,
                 'data': simulation_scheme.dump({'action': 'step', 'until': context.scene.frame_current + 1})
                 })
            share_data.step_when_ready += step_num
        elif self.action == 'stepx10':
            step_num = 10

            until_step = context.scene.frame_current + step_num

            mess = message.dumps(
                {'schema': schemas.Simulation.__name__,
                 'data': simulation_scheme.dump({'action': 'step', 'until': until_step})
                 })
            share_data.step_when_ready += step_num
        else:
            raise TypeError(self.action)
        share_data.sendall(mess.encode('utf-8'))
        context.area.tag_redraw()  # todo not needed here?
        return {'FINISHED'}


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
