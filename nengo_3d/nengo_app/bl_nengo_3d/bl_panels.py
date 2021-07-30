from __future__ import annotations

import logging

import bpy

from bl_nengo_3d import bl_operators, bl_context_menu
from bl_nengo_3d.bl_properties import Nengo3dProperties
from bl_nengo_3d.share_data import share_data

logger = logging.getLogger(__name__)


def connected():
    return share_data.client is not None  # and share_data.client.is_connected()


class NengoSettingsPanel(bpy.types.Panel):
    bl_label = 'Nengo 3d'
    bl_idname = 'NENGO_PT_settings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw_header_preset(self, context):
        layout = self.layout
        layout.emboss = 'NONE'
        cached_frames = share_data.simulation_cache_steps()
        if cached_frames:
            layout.label(text=f'Cached: {cached_frames}')

    def draw(self, context):
        layout = self.layout.column()

        layout.label(text='localhost:6001')
        if not connected():
            row = layout.row()
            row.scale_y = 1.5
            row.operator(bl_operators.ConnectOperator.bl_idname, text='Connect')
        else:
            row = layout.row()
            row.scale_y = 1.5
            row.operator(bl_operators.DisconnectOperator.bl_idname, text='Disconnect')

        win_man = context.window_manager

        nengo_3d = win_man.nengo_3d
        row = layout.row()
        row.active = not connected()
        row.prop(nengo_3d, 'collection')
        screen = context.screen
        col = layout.column(align=True)
        col.active = connected()
        col.prop(nengo_3d, 'is_realtime')
        col.prop(context.scene.render, 'fps')
        col.prop(context.scene, 'frame_end')

        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator(bl_operators.NengoSimulateOperator.bl_idname, text='Step', icon='FRAME_NEXT').action = 'step'
        row.operator(bl_operators.NengoSimulateOperator.bl_idname, text='Step x10',
                     icon='FRAME_NEXT').action = 'stepx10'
        col.operator(bl_operators.NengoSimulateOperator.bl_idname, text='Reset',
                     icon='CANCEL').action = 'reset'

        nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
        col = layout.column()
        row = layout.row(align=True)
        col = row.column()
        col.prop(nengo_3d, 'show_whole_simulation', text='', invert_checkbox=True)
        col = row.column()
        col.active = not nengo_3d.show_whole_simulation
        col.prop(nengo_3d, 'show_n_last_steps', text=f'Show last {nengo_3d.show_n_last_steps} steps')


class NengoAlgorithmPanel(bpy.types.Panel):
    bl_label = 'Nengo Algorithms'
    bl_idname = 'NENGO_PT_algorithms'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout.column()
        win_man = context.window_manager
        layout.operator(bl_operators.NengoCalculateOperator.bl_idname)

        nengo_3d = win_man.nengo_3d
        layout.prop(nengo_3d, 'spacing')
        layout.use_property_split = False
        row = layout.row()
        row.prop(nengo_3d, 'algorithm_dim', expand=True)
        if nengo_3d.algorithm_dim == '2D':
            layout.prop(nengo_3d, 'layout_algorithm_2d')
        else:
            layout.prop(nengo_3d, 'layout_algorithm_3d')


class NengoContextPanel(bpy.types.Panel):
    bl_label = 'Context Actions'
    bl_idname = 'NENGO_PT_context'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout.column()
        if bl_context_menu.CreatePlotLineOperator.poll(context):
            obj_name = context.active_object.name
            node = share_data.model_graph.nodes.get(obj_name)
            e_source, e_target, edge = share_data.model_get_edge_by_name(obj_name)

            if node:
                col = layout.column(align=True)
                col.operator_context = 'EXEC_DEFAULT'
                size_out = node['size_out'] + 1
                if node['type'] == 'Ensemble':
                    col = layout.column(align=True)
                    col.operator_context = 'EXEC_DEFAULT'
                    neurons = node['neurons']
                    op = col.operator(bl_context_menu.CreatePlotLineOperator.bl_idname,
                                      text=f'Plot Neuron Spikes',
                                      icon='ORIENTATION_VIEW')
                    op.probe_neurons = 'output'
                    op.neurons = True
                    op.dim = 2
                    op.xlabel = 'Step'
                    op.ylabel = 'Spikes'
                    op.xindex = 0
                    op.yindex = 1
                    op.title = f'{obj_name}: Spikes'

                    if size_out == 3:
                        op = col.operator(bl_context_menu.CreatePlotLineOperator.bl_idname,
                                          text=f'Plot {size_out}d output',
                                          icon='ORIENTATION_VIEW')
                        op.probe = 'decoded_output'
                        op.dim = size_out
                        op.xlabel = 'X'
                        op.ylabel = 'Y'
                        op.zlabel = 'Step'
                        op.xindex = 1
                        op.yindex = 2
                        op.zindex = 0
                        op.title = f'{obj_name} 2d: decoded output'

                        op = col.operator(bl_context_menu.CreatePlotLineOperator.bl_idname,
                                          text=f'Plot 2d ouput',
                                          icon='ORIENTATION_VIEW')
                        op.probe = 'decoded_output'
                        op.dim = node['size_out']
                        op.xlabel = 'X'
                        op.xindex = 1
                        op.yindex = 2
                        op.ylabel = 'Y'
                        op.title = f'{obj_name} 3d: output'
                    else:
                        op = col.operator(bl_context_menu.CreatePlotLineOperator.bl_idname,
                                          text=f'Plot {size_out}d decoded ouput',
                                          icon='ORIENTATION_VIEW')
                        op.probe = 'decoded_output'
                        op.dim = node['size_out']
                        op.xlabel = 'Step'
                        op.ylabel = 'Voltage'
                        op.xindex = 0
                        op.yindex = 1
                        op.title = f'{obj_name}: output'
                elif node['type'] == 'Node':
                    op = col.operator(bl_context_menu.CreatePlotLineOperator.bl_idname, text=f'Plot {size_out}d output',
                                      icon='ORIENTATION_VIEW')
                    op.probe = 'output'
                    op.dim = node['size_out']
                    op.xlabel = 'Step'
                    op.ylabel = 'Voltage'
                    op.xindex = 0
                    op.yindex = 1
                    op.title = f'{obj_name}: output'
            if edge:
                # todo check format of weights
                col = layout.column(align=True)
                col.operator_context = 'EXEC_DEFAULT'
                size_out = edge['size_out']
                op = col.operator(bl_context_menu.CreatePlotLineOperator.bl_idname, text=f'Plot {size_out}d Weights',
                                  icon='ORIENTATION_VIEW')
                op.probe = 'weights'
                op.dim = size_out
                op.xlabel = 'Step'
                op.ylabel = 'Voltage'
                op.xindex = 0
                op.yindex = 1
                op.title = f'{e_source} -> {e_target}: output'
        else:
            layout.label(text='No actions available')


class NengoInfoPanel(bpy.types.Panel):
    bl_label = 'Info'
    bl_idname = 'NENGO_PT_info'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw_header_preset(self, context):
        layout = self.layout
        layout.emboss = 'NONE'
        row = layout.row(align=True)
        obj: bpy.types.Object = context.active_object
        if not obj:
            return
        if share_data.model_graph:
            node = share_data.model_graph.nodes.get(obj.name)
            if node:
                row.label(text=f'Node: {obj.name}')
                return
            e_source, _, _edge = share_data.model_get_edge_by_name(obj.name)
            if e_source:
                row.label(text=f'Edge: {obj.name}')
                return

            chart = None
            for source, charts in share_data.charts.items():
                for ax in charts:
                    if ax.root == obj:
                        chart = ax
            if chart:
                row.label(text=f'Plot: {obj.name}')

    def draw(self, context):
        layout = self.layout.column()
        obj: bpy.types.Object = context.active_object
        if not obj:
            layout.label(text='No active object')
            return

        node = None
        edge = None
        if share_data.model_graph:
            node = share_data.model_graph.nodes.get(obj.name)
            e_source, e_target, edge = share_data.model_get_edge_by_name(obj.name)
        else:
            layout.label(text='No active model')
            return

        chart = None
        for source, charts in share_data.charts.items():
            # for charts in params.values():
            for ax in charts:
                if ax.root == obj:
                    chart = ax
        if chart:
            indices = share_data.charts_sources[chart]
            layout.label(text=f'{obj.name}:  {chart.title_text}')
            col = layout.box().column(align=True)
            row = col.row()
            row.label(text='Parameter:')
            row.label(text=f'{chart.parameter}')
            row = col.row()
            row.label(text='Source:')
            row.label(text=f'{source}')
            row = col.row()
            ind_str = 'Indices: '
            if indices[0] == 0:
                ind_str += 'x=step, '
            else:
                ind_str += f'x={indices[0]}, '
            if indices[1] == 0:
                ind_str += 'y=step'
            else:
                ind_str += f'y={indices[1]}, '
            if len(indices) == 3:
                if indices[2] == 0:
                    ind_str += ', z=step'
                else:
                    ind_str += f', z={indices[1]}'
            row.label(text=ind_str)

        if node:
            layout.label(text=f'Node: {obj.name}')
            col = layout.box().column(align=True)
            self._draw_expand(col, node)
        elif edge:
            layout.label(text=f'Edge: {obj.name}, {e_source} -> {e_target}')
            col = layout.box().column(align=True)
            self._draw_expand(col, edge)
        else:
            layout.label(text=f'Not a network element')

    def _draw_expand(self, col, items: dict, tab=0):
        edge = items
        for param, value in sorted(edge.items()):
            if value is None: continue
            row = col.row()
            row.separator(factor=tab)
            if isinstance(value, dict):
                row.label(text=param + ':')
                self._draw_expand(col.box().column(align=True), value, tab + 1.4)
            else:
                row.label(text=param)
                row.label(text=str(value))

    # def _draw_expand_list(self, col, items: list):


classes = (
    NengoSettingsPanel,
    NengoContextPanel,
    NengoInfoPanel,
    NengoAlgorithmPanel,
)
register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()


def unregister():
    unregister_factory()
