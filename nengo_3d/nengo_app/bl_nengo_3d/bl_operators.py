import logging
import socket
import time
from functools import partial

import bpy

import bl_nengo_3d.schemas as schemas
from bl_nengo_3d.bl_properties import Nengo3dProperties, node_color_single_update, \
    node_attributes_update
from bl_nengo_3d.connection_handler import handle_data, handle_network_model
from bl_nengo_3d.frame_change_handler import frame_change_pre
from bl_nengo_3d.share_data import share_data

message = schemas.Message()
simulation_scheme = schemas.Simulation()


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
        for source_name, params in share_data.charts.items():
            for access_path, _axes in params.items():
                data = data_scheme.dump(
                    obj={'source': source_name, 'access_path': access_path})
                mess = message.dumps({'schema': schemas.Observe.__name__, 'data': data})
                logging.debug(f'Sending: {mess}')
                share_data.sendall(mess.encode('utf-8'))

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
        share_data.current_step = -1
        share_data.resume_playback_on_steps = False
        # share_data.simulation_cache_step.clear()
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
            ('continuous', 'continuous', ''),
        ], name='Action')

    _timer = None
    _end_now = False

    @classmethod
    def poll(cls, context):
        return share_data.client is not None

    def execute(self, context):
        if self.action == 'reset':
            context.scene.frame_current = 0
            share_data.step_when_ready = 0
            share_data.requested_steps_until = -1
            share_data.current_step = -1
            share_data.resume_playback_on_steps = False
            # share_data.simulation_cache_step.clear()
            share_data.simulation_cache.clear()
            mess = message.dumps(
                {'schema': schemas.Simulation.__name__,
                 'data': simulation_scheme.dump({'action': 'reset'})
                 })
            share_data.sendall(mess.encode('utf-8'))
            return {'FINISHED'}
        elif self.action == 'step':
            self.simulation_step(context, 1, 1)
            return {'FINISHED'}
        elif self.action == 'stepx10':
            self.simulation_step(context, 10, 10)
            return {'FINISHED'}
        elif self.action == 'continuous':
            wm = context.window_manager
            if context.scene.is_simulation_playing:
                context.scene.is_simulation_playing = False
                return {'CANCELLED'}
            else:
                context.scene.is_simulation_playing = True
                self._timer = wm.event_timer_add(1 / 24, window=context.window)
                wm.modal_handler_add(self)
                return {'RUNNING_MODAL'}
        else:
            raise TypeError(self.action)
        return {'CANCELLED'}

    @staticmethod
    def simulation_step(context, step_num: int, prefetch: int = 0):
        # cached_steps = share_data.simulation_cache_steps()
        cached_steps = share_data.current_step
        if cached_steps and context.scene.frame_current < cached_steps:
            context.scene.frame_current += step_num
        else:
            data = {'action': 'step',
                    'until': context.scene.frame_current + step_num + prefetch}
            mess = message.dumps({'schema': schemas.Simulation.__name__,
                                  'data': simulation_scheme.dump(data)
                                  })
            share_data.step_when_ready += step_num
            share_data.sendall(mess.encode('utf-8'))

    def modal(self, context, event):
        if not context.scene.is_simulation_playing or event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if share_data.current_step >= context.scene.frame_current:
                self.simulation_step(context, step_num=1, prefetch=0)
            elif share_data.requested_steps_until <= context.scene.frame_current:
                self.simulation_step(context, step_num=0, prefetch=2)

        return {'PASS_THROUGH'}

    def cancel(self, context):
        context.scene.is_simulation_playing = False
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        self._timer = None


class NengoColorNodesOperator(bpy.types.Operator):
    """Calculate graph drawing"""
    bl_idname = 'nengo_3d.color_nodes'
    bl_label = 'Recolor nodes'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return bool(share_data.model_graph)

    def execute(self, context):
        self.recolor_nodes(context.window_manager.nengo_3d)
        return {'FINISHED'}

    @staticmethod
    def recolor_nodes(nengo_3d: Nengo3dProperties):
        # if nengo_3d.node_color_map == 'ENUM'
        if nengo_3d.node_color_source == 'SINGLE':
            node_color_single_update(nengo_3d, None)
        elif nengo_3d.node_color_source == 'MODEL':
            node_attributes_update(nengo_3d, None)
        elif nengo_3d.node_color_source == 'MODEL_DYNAMIC':
            share_data.simulation_cache  # todo
        else:
            assert False, nengo_3d.node_color_source


classes = (
    ConnectOperator,
    DisconnectOperator,
    NengoCalculateOperator,
    NengoSimulateOperator,
    SimpleSelectOperator,
    NengoColorNodesOperator,
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    bpy.types.Scene.is_simulation_playing = bpy.props.BoolProperty()
    register_factory()


def unregister():
    del bpy.types.Scene.is_simulation_playing
    if share_data.handle_data and bpy.app.timers.is_registered(share_data.handle_data):
        bpy.app.timers.unregister(share_data.handle_data)
        share_data.handle_data = None
    if share_data.client:
        share_data.client.shutdown(socket.SHUT_RDWR)
        share_data.client.close()
        share_data.client = None
    unregister_factory()
