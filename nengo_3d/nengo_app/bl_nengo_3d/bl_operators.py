import logging
import socket
import time
import typing
from functools import partial

import bpy

import bl_nengo_3d.schemas as schemas
from bl_nengo_3d import colors
from bl_nengo_3d.bl_depsgraph_handler import graph_edges_recalculate_handler
from bl_nengo_3d.frame_change_handler import frame_change_handler, execution_times, recolor_dynamic_node_attributes
from bl_nengo_3d.bl_properties import Nengo3dProperties, node_color_single_update, \
    node_attribute_with_types_update, Nengo3dShowNetwork, ColorGeneratorProperties
from bl_nengo_3d.axes import Axes
from bl_nengo_3d.connection_handler import handle_data, handle_network_model
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
        for source_name, axes in share_data.charts.items():
            for ax in axes:
                ax: Axes
                data = data_scheme.dump(
                    obj={'source': source_name,
                         'access_path': ax.parameter,
                         'sample_every': context.window_manager.nengo_3d.sample_every,
                         'dt': context.window_manager.nengo_3d.dt})
                mess = message.dumps({'schema': schemas.Observe.__name__, 'data': data})
                logging.debug(f'Sending: {mess}')
                share_data.sendall(mess.encode('utf-8'))

        bpy.app.handlers.frame_change_pre.append(frame_change_handler)
        bpy.app.handlers.depsgraph_update_post.append(graph_edges_recalculate_handler)
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
        bpy.app.handlers.frame_change_pre.remove(frame_change_handler)
        bpy.app.handlers.depsgraph_update_post.remove(graph_edges_recalculate_handler)
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


class NengoGraphOperator(bpy.types.Operator):
    """Calculate graph drawing"""
    bl_idname = 'nengo_3d.draw_graph'
    bl_label = 'Recalculate'
    bl_options = {'REGISTER'}

    regenerate: bpy.props.BoolProperty(default=False, options={'SKIP_SAVE'})
    expand: bpy.props.StringProperty(default='', options={'SKIP_SAVE'})
    collapse: bpy.props.StringProperty(default='', options={'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        return share_data.model_graph is not None

    def execute(self, context):
        nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
        if self.expand:
            # todo select new nodes when expanding
            # obj = share_data.model_graph_view.nodes[self.expand]['_blender_object']
            # handle_network_model(
            #     g=share_data.model_graph.get_subnetwork(self.expand).get_graph_view(nengo_3d),
            #     nengo_3d=nengo_3d,
            #     bounding_box=tuple((i/2 for i in obj.dimensions)),
            #     center=tuple(obj.location),
            #     select=True)
            nengo_3d.expand_subnetworks[self.expand].expand = True
            # return {'FINISHED'}
        if self.collapse:
            nengo_3d.expand_subnetworks[self.collapse].expand = False
        if self.regenerate:
            for node, node_data in share_data.model_graph_view.nodes(data=True):
                node_data['_blender_object'].hide_viewport = True
                node_data['_blender_object'].hide_render = True
            for e_s, e_v, e_data in share_data.model_graph_view.edges(data=True):
                e_data['_blender_object'].hide_viewport = True
                e_data['_blender_object'].hide_render = True
            share_data.model_graph_view = share_data.model_graph.get_graph_view(nengo_3d)

        # logging.debug(share_data.model_graph_view.nodes(data=False))
        # logging.debug(share_data.model_graph_view.nodes['model.cortical'])
        handle_network_model(g=share_data.model_graph_view, nengo_3d=nengo_3d, select=True)
        bpy.ops.view3d.view_selected()

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
            ('reset', 'reset', ''),
            ('continuous', 'continuous', ''),
        ], name='Action')

    _timer = None
    _end_now = False

    @classmethod
    def poll(cls, context):
        return share_data.client is not None

    def execute(self, context):
        nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
        if nengo_3d.requires_reset and self.action != 'reset':
            return {'CANCELLED'}
        if self.action == 'reset':
            nengo_3d.requires_reset = False
            context.scene.frame_current = 0
            share_data.step_when_ready = 0
            share_data.requested_steps_until = -1
            share_data.current_step = -1
            share_data.resume_playback_on_steps = False
            # share_data.simulation_cache_step.clear()
            share_data.simulation_cache.clear()

            observe, plot = share_data.get_all_sources(nengo_3d)

            self.simulation_step(context.scene, action='reset', step_num=nengo_3d.step_n,
                                 sample_every=nengo_3d.sample_every,
                                 dt=nengo_3d.dt, prefetch=0, observe=observe, plot=plot)
            return {'FINISHED'}
        elif self.action == 'step':
            self.simulation_step(context.scene, action='step', step_num=nengo_3d.step_n,
                                 sample_every=nengo_3d.sample_every, dt=nengo_3d.dt, prefetch=0)
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
    def simulation_step(scene, action: str, step_num: int, sample_every: int, dt: float, prefetch: int = 0,
                        observe: list = None, plot: list = None):
        observe = observe or []
        plot = plot or []
        observables = []
        plotable = []
        for i in observe:
            observables.append({'source': i[0],
                                'access_path': i[1],
                                'sample_every': sample_every,
                                'dt': dt})
        for i in plot:
            plotable.append({
                'source': i[0],
                'access_path': i[1],
                'step': i[2],
            })

        cached_steps = share_data.current_step
        if cached_steps and scene.frame_current < cached_steps:
            scene.frame_current += step_num
        else:
            data = {'action': action,
                    'until': scene.frame_current + step_num + prefetch,
                    'dt': dt,
                    'sample_every': sample_every,
                    'observe': observables,
                    'plot_lines': plotable}
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
            nengo_3d = context.window_manager.nengo_3d
            speed = nengo_3d.speed
            if share_data.current_step >= context.scene.frame_current:
                frame_change_time = execution_times.average()
                dropped_frames = frame_change_time * 24
                self.simulation_step(context.scene, action='step', step_num=int((1 + dropped_frames) * speed),
                                     sample_every=nengo_3d.sample_every, dt=nengo_3d.dt, prefetch=min(24 * speed, 24))
            elif share_data.requested_steps_until <= context.scene.frame_current:
                self.simulation_step(context.scene, action='step', step_num=0, sample_every=nengo_3d.sample_every,
                                     dt=nengo_3d.dt, prefetch=min(24 * speed, 24))
        return {'PASS_THROUGH'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        context.scene.is_simulation_playing = False
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
        self.recolor_nodes(context.window_manager.nengo_3d, context.scene.frame_current)
        return {'FINISHED'}

    @staticmethod
    def recolor_nodes(nengo_3d: Nengo3dProperties, frame_current):
        if nengo_3d.node_color == 'SINGLE':
            node_color_single_update(nengo_3d, None)
        elif nengo_3d.node_color == 'MODEL':
            node_attribute_with_types_update(nengo_3d, None)
        elif nengo_3d.node_color == 'MODEL_DYNAMIC':
            recolor_dynamic_node_attributes(nengo_3d, int(frame_current / nengo_3d.sample_every))
            # share_data.simulation_cache  # todo
        else:
            assert False, nengo_3d.node_color


class NengoColorLinesOperator(bpy.types.Operator):
    """Calculate graph drawing"""
    bl_idname = 'nengo_3d.color_lines'
    bl_label = 'Recolor lines'
    bl_options = {'REGISTER'}

    axes_obj: bpy.props.StringProperty()

    def execute(self, context):
        ax_obj = bpy.data.objects.get(self.axes_obj)
        if not ax_obj:
            return {'CANCELLED'}
        color_gen: ColorGeneratorProperties = ax_obj.nengo_axes.color_gen
        gen = colors.cycle_color(color_gen.initial_color, color_gen.shift, color_gen.max_colors)
        for line in ax_obj.nengo_axes.lines:
            line_obj = bpy.data.objects[line.name]
            line_obj.nengo_colors.color = next(gen)
            line_obj.update_tag()
        return {'FINISHED'}


classes = (
    ConnectOperator,
    DisconnectOperator,
    NengoGraphOperator,
    NengoSimulateOperator,
    SimpleSelectOperator,
    NengoColorNodesOperator,
    NengoColorLinesOperator,
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
