from __future__ import annotations

import logging
import time
from typing import Any

import bpy

from bl_nengo_3d import bl_operators, bl_plot_operators, frame_change_handler
from bl_nengo_3d.bl_properties import Nengo3dProperties, Nengo3dShowNetwork, draw_axes_properties_template, \
    AxesProperties, LineProperties, LineSourceProperties, draw_color_generator_properties_template
from bl_nengo_3d.charts import Axes
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

    def draw_header_preset(self, context):
        layout = self.layout
        layout.emboss = 'NONE'
        cached_frames = share_data.current_step
        if cached_frames > -1:
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
        col = layout.column(align=True)
        col.prop(nengo_3d, 'sample_every')
        col.prop(nengo_3d, 'dt')

        row = layout.row()
        row.active = not connected()
        col = layout.column()
        col.operator(bl_operators.NengoSimulateOperator.bl_idname,
                     text='!Reset!' if nengo_3d.requires_reset else 'Reset',
                     icon='CANCEL').action = 'reset'

        col = layout.column()
        col.active = connected() and not nengo_3d.requires_reset
        row = col.row(align=True)
        op = row.operator(bl_operators.NengoSimulateOperator.bl_idname, text=f'Step x{nengo_3d.step_n}',
                          icon='FRAME_NEXT')
        op.action = 'step'
        row.prop(nengo_3d, 'step_n', text='')

        row = col.row(align=True)
        if context.scene.is_simulation_playing:
            op = row.operator(bl_operators.NengoSimulateOperator.bl_idname, text='Stop',
                              icon='PAUSE')
        else:
            op = row.operator(bl_operators.NengoSimulateOperator.bl_idname, text='Play',
                              icon='PLAY')
        row.prop(nengo_3d, 'speed', text='')
        op.action = 'continuous'

        nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
        layout.prop(nengo_3d, 'allow_scrubbing')
        layout.label(text=f'Switching frame took: {frame_change_handler.execution_times.average():.2f} sec')
        row = layout.row(align=True)
        col = row.column(align=True)
        col.prop(nengo_3d, 'show_whole_simulation', text='', invert_checkbox=True)
        col = row.column(align=True)
        col.active = not nengo_3d.show_whole_simulation
        col.prop(nengo_3d, 'show_n_last_steps', text=f'Show n last steps')
        layout.prop(nengo_3d, 'select_edges')
        layout.prop(nengo_3d, 'draw_labels')


class NengoSubnetworksPanel(bpy.types.Panel):
    bl_label = 'Subnetworks'
    bl_idname = 'NENGO_PT_subnetworks'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = 'NENGO_PT_algorithms'

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        box = layout.box()
        if not connected():
            layout.active = False
            return
        nengo_3d = context.window_manager.nengo_3d
        box.label(text='Expand subnetworks')
        col = box.column(align=True)
        for net in sorted(nengo_3d.expand_subnetworks, key=lambda net: net.name):
            row = col.row(align=True)
            net: Nengo3dShowNetwork
            row.prop(net, 'expand', text='')
            # row.prop(net, 'draw_bounded', text='')
            row.label(text=net.name)


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
        nengo_3d = win_man.nengo_3d

        layout.operator(bl_operators.NengoGraphOperator.bl_idname).regenerate = True
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

    def draw(self, context):
        layout = self.layout.column()
        obj = context.active_object
        if not obj:
            layout.label(text='No active object')
            return

        obj_name = obj.name
        if not bl_plot_operators.PlotLineOperator.poll(context):
            layout.label(text='No actions available')
            return
        node = share_data.model_graph.get_node_or_subnet_data(obj_name)
        # layout.operator(bl_plot_operators.PlotLineOperator.bl_idname, text=f'Plot 2d anything',
        #                 icon='FORCE_HARMONIC')

        if node:
            if node['type'] in {'Ensemble', 'Node'} and node['network_name'] != 'model':
                op = layout.operator(bl_operators.NengoGraphOperator.bl_idname,
                                     text=f'Collapse {node["network_name"]}')
                op.regenerate = True
                op.collapse = node['network_name']
            if node['type'] == 'Network' and node.get('parent_network'):
                op = layout.operator(bl_operators.NengoGraphOperator.bl_idname,
                                     text=f'Collapse {node["parent_network"]}')
                op.regenerate = True
                op.collapse = node['parent_network']

            col = layout.column()
            if node['type'] == 'Ensemble':
                self.draw_ensemble_actions(col, node, obj_name, context.scene.frame_current)
            elif node['type'] == 'Node':
                self.draw_node_actions(col, obj_name, node)
            elif node['type'] == 'Network':
                self.draw_network_actions(layout, node)
            return

        e_source, e_target, edge = share_data.model_graph.get_edge_by_name(obj_name)
        if edge:
            pass
            # self.draw_edge_actions(layout, e_source, e_target, edge)
            return

    @staticmethod
    def draw_node_actions(layout: bpy.types.UILayout, obj_name, node: dict[str, Any]):
        layout.label(text='Plot 2d lines:')
        layout.operator_context = 'EXEC_DEFAULT'
        op = layout.operator(
            operator=bl_plot_operators.PlotLineOperator.bl_idname,
            text=f'Plot 2d output',
            icon='ORIENTATION_VIEW')
        op: bl_plot_operators.PlotLineOperator
        op.axes: AxesProperties
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: output'
        for i in range(node['size_out']):
            line: LineProperties = op.axes.lines.add()
            line.source: LineSourceProperties
            line.source.source_obj = obj_name
            line.source.access_path = 'probeable.output'
            line.source.iterate_step = True
            line.source.get_x = 'step'
            line.source.get_y = f'row[{i}]'
            line.label = f'Dimension {i}'

    @staticmethod
    def draw_ensemble_actions(layout: bpy.types.UILayout, ensemble: dict[str, Any], obj_name: str, frame_current: int):
        layout.label(text='Plot 2d lines:')
        box = layout.box().column(align=True)
        box.label(text='Ensemble:')
        box.operator_context = 'EXEC_DEFAULT'
        op = box.operator(
            operator=bl_plot_operators.PlotLineOperator.bl_idname,
            text=f'Decoded output',
            icon='ORIENTATION_VIEW')
        op: bl_plot_operators.PlotLineOperator
        op.axes: AxesProperties
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: decoded_output'
        for i in range(ensemble['size_out']):
            line: LineProperties = op.axes.lines.add()
            line.label = f'Dimension {i}'
            line.source: LineSourceProperties
            line.source.source_obj = obj_name
            line.source.access_path = 'probeable.decoded_output'
            line.source.iterate_step = True
            line.source.get_x = 'step'
            line.source.get_y = f'row[{i}]'

        box.operator_context = 'EXEC_DEFAULT'
        op = box.operator(
            operator=bl_plot_operators.PlotLineOperator.bl_idname,
            text=f'Input',
            icon='ORIENTATION_VIEW')
        op: bl_plot_operators.PlotLineOperator
        op.axes: AxesProperties
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: input'
        for i in range(ensemble['size_out']):
            line: LineProperties = op.axes.lines.add()
            line.label = f'Dimension {i}'
            line.source: LineSourceProperties
            line.source.source_obj = obj_name
            line.source.access_path = 'probeable.input'
            line.source.iterate_step = True
            line.source.get_x = 'step'
            line.source.get_y = f'row[{i}]'

        box.operator_context = 'EXEC_DEFAULT'
        op = box.operator(
            operator=bl_plot_operators.PlotLineOperator.bl_idname,
            text=f'Scaled encoders',
            icon='ORIENTATION_VIEW')
        op: bl_plot_operators.PlotLineOperator
        op.axes: AxesProperties
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: scaled_encoders'
        for i in range(ensemble['size_out']):
            line: LineProperties = op.axes.lines.add()
            line.label = f'Dimension {i}'
            line.source: LineSourceProperties
            line.source.source_obj = obj_name
            line.source.access_path = 'probeable.scaled_encoders'
            line.source.iterate_step = True
            line.source.get_x = 'step'
            line.source.get_y = f'row[{i}]'
            box.operator_context = 'EXEC_DEFAULT'

        box = layout.box().column(align=True)
        box.label(text='Neurons:')
        neurons = ensemble['neurons']
        max_neurons = 50  # todo raise neurons limit
        box.operator_context = 'EXEC_DEFAULT'
        # layout.active = share_data.current_step > 0
        op = box.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                          text=f'Response curves at {frame_current}',
                          icon='ORIENTATION_VIEW')
        op: bl_plot_operators.PlotLineOperator
        op.axes: AxesProperties
        op.axes.xlabel = 'Input signal'
        op.axes.ylabel = 'Firing rate (Hz)'
        op.axes.title = f'{obj_name}: Neuron response curves\n' \
                        f'(step {frame_current}, {ensemble["neuron_type"]["name"]})'
        op.axes.line_offset = -0.05
        for i in range(min(neurons['size_out'], max_neurons)):
            line: LineProperties = op.axes.lines.add()
            line.label = f'Neuron {i}'
            line.update = False
            line_source = line.source
            line_source: LineSourceProperties
            line_source.source_obj = obj_name
            line_source.iterate_step = False
            line_source.fixed_step = frame_current  # todo do we need to calculate nengo.sample_step here?
            line_source.access_path = 'neurons.response_curves'
            line_source.get_x = 'data[:, 0]'
            line_source.get_y = f'data[:, {i + 1}]'

        # layout = layout.column(align=True)
        box.operator_context = 'EXEC_DEFAULT'
        # layout.active = share_data.current_step > 0 and ensemble['size_out'] < 2
        op = box.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                          text=f'Tuning curves at {frame_current}',
                          icon='ORIENTATION_VIEW')
        op.axes.xlabel = 'Input signal'
        op.axes.ylabel = 'Firing rate (Hz)'
        op.axes.title = f'{obj_name}: Neuron tuning curves\n' \
                        f'(step {frame_current}, {ensemble["neuron_type"]["name"]})'
        op.axes.line_offset = -0.05
        for i in range(min(neurons['size_out'], max_neurons)):
            line: LineProperties = op.axes.lines.add()
            line.label = f'Neuron {i}'
            line.update = False
            line_source = line.source
            line_source: LineSourceProperties
            line_source.source_obj = obj_name
            line_source.iterate_step = False
            line_source.fixed_step = frame_current  # todo do we need to calculate nengo.sample_step here?
            line_source.access_path = 'neurons.tuning_curves'
            line_source.get_x = 'data[:, 0]'
            line_source.get_y = f'data[:, {i + 1}]'

        box.operator_context = 'EXEC_DEFAULT'
        op = box.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                          text=f'Output (spikes)',
                          icon='ORIENTATION_VIEW')
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Spikes'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.line_offset = -0.05
        op.axes.title = f'{obj_name}: Neurons output (spikes)'
        for i in range(min(neurons['size_out'], max_neurons)):
            line: LineProperties = op.axes.lines.add()
            line.label = f'Neuron {i}'
            line_source = line.source
            line_source: LineSourceProperties
            line_source.source_obj = obj_name
            line_source.access_path = 'neurons.probeable.output'
            line_source.iterate_step = True
            line_source.get_x = 'step'
            line_source.get_y = f'row[{i}]'

        box.operator_context = 'EXEC_DEFAULT'
        op = box.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                          text=f'Input',
                          icon='ORIENTATION_VIEW')
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Input'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.line_offset = -0.05
        op.axes.title = f'{obj_name}: Neurons input'
        for i in range(min(neurons['size_out'], max_neurons)):
            line: LineProperties = op.axes.lines.add()
            line.label = f'Neuron {i}'
            line_source = line.source
            line_source: LineSourceProperties
            line_source.source_obj = obj_name
            line_source.access_path = 'neurons.probeable.input'
            line_source.iterate_step = True
            line_source.get_x = 'step'
            line_source.get_y = f'row[{i}]'

        box.operator_context = 'EXEC_DEFAULT'
        op = box.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                          text=f'Voltage',
                          icon='ORIENTATION_VIEW')
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.line_offset = -0.05
        op.axes.title = f'{obj_name}: Neurons voltage'
        for i in range(min(neurons['size_out'], max_neurons)):
            line: LineProperties = op.axes.lines.add()
            line.label = f'Neuron {i}'
            line_source = line.source
            line_source: LineSourceProperties
            line_source.source_obj = obj_name
            line_source.access_path = 'neurons.probeable.voltage'
            line_source.iterate_step = True
            line_source.get_x = 'step'
            line_source.get_y = f'row[{i}]'


        box.operator_context = 'EXEC_DEFAULT'
        op = box.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                          text=f'Refractory time',
                          icon='ORIENTATION_VIEW')
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Refractory time'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.line_offset = -0.05
        op.axes.title = f'{obj_name}: Neurons refractory time'
        for i in range(min(neurons['size_out'], max_neurons)):
            line: LineProperties = op.axes.lines.add()
            line.label = f'Neuron {i}'
            line_source = line.source
            line_source: LineSourceProperties
            line_source.source_obj = obj_name
            line_source.access_path = 'neurons.probeable.refractory_time'
            line_source.iterate_step = True
            line_source.get_x = 'step'
            line_source.get_y = f'row[{i}]'

        # if node['size_out'] == 2:
        #     op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname,
        #                       text=f'Plot 3d output',
        #                       icon='ORIENTATION_GLOBAL')
        #     op.probe = 'probeable.decoded_output'
        #     op.axes.xlabel = 'X'
        #     op.axes.ylabel = 'Y'
        #     op.axes.zlabel = 'Step'
        #     op.axes.xformat = '{:.2f}'
        #     op.axes.yformat = '{:.2f}'
        #     op.axes.zformat = '{:.0f}'
        #     op.axes.zlocator = 'IntegerLocator'
        #     op.axes.title = f'{obj_name} 3d: decoded output'
        #     item = op.indices.add()
        #     item.xindex = 0
        #     item.yindex = 1
        #     item.use_z = True
        #     item.z_is_step = True
        #
        #     op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname,
        #                       text=f'Plot 2d ouput',
        #                       icon='ORIENTATION_VIEW')
        #     op.probe = 'probeable.decoded_output'
        #     op.axes.xlabel = 'X'
        #     op.axes.ylabel = 'Y'
        #     op.axes.xformat = '{:.2f}'
        #     op.axes.yformat = '{:.2f}'
        #     op.axes.title = f'{obj_name} 2d: output'
        #     item = op.indices.add()
        #     item.xindex = 0
        #     item.yindex = 1
        # else:
        #     op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname,
        #                       text=f'Plot 2d decoded ouput',
        #                       icon='ORIENTATION_VIEW')
        #     op.probe = 'probeable.decoded_output'
        #     op.axes.xlabel = 'Step'
        #     op.axes.ylabel = 'Voltage'
        #     op.axes.xlocator = 'IntegerLocator'
        #     op.axes.xformat = '{:.0f}'
        #     op.axes.yformat = '{:.2f}'
        #     op.axes.title = f'{obj_name}: output'
        #     item = op.indices.add()
        #     item.x_is_step = True
        #     item.yindex = 0

    @staticmethod
    def draw_network_actions(layout: bpy.types.UILayout, node: dict[str, Any]):
        # nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
        # layout.prop(nengo_3d.expand_subnetworks[node['name']], 'expand', text=f'Expand {node["name"]}')
        op = layout.operator(bl_operators.NengoGraphOperator.bl_idname, text=f'Expand {node["name"]}')
        op.regenerate = True
        op.expand = node['name']

    @staticmethod
    def draw_edge_actions(layout: bpy.types.UILayout, e_source: str, e_target: str, edge: dict[str, Any]):
        col = layout.column(align=True)
        col.operator_context = 'EXEC_DEFAULT'
        op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname, text=f'Plot 2d input',
                          icon='ORIENTATION_VIEW')
        op.probe = 'probeable.input'
        op.xlabel = 'Step'
        op.ylabel = 'Input'
        op.xlocator = 'IntegerLocator'
        op.xformat = '{:.0f}'
        op.yformat = '{:.2f}'
        op.line_offset = -0.05
        op.title = f'{e_source} -> {e_target}: input'
        source_node = share_data.model_graph.get_node_data(e_source)
        if source_node['type'] == 'Ensemble':
            for i in range(source_node['neurons']['size_out']):
                item = op.indices.add()
                item.x_is_step = True
                item.yindex = i
                item.label = f'Neuron {i}'
        elif source_node['type'] == 'Node':
            # todo check
            for i in range(source_node['size_out']):
                item = op.indices.add()
                item.x_is_step = True
                item.yindex = i
                item.label = f'Neuron {i}'
        col.operator_context = 'EXEC_DEFAULT'
        op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname, text=f'Plot 2d output',
                          icon='ORIENTATION_VIEW')
        op.probe = 'probeable.output'
        op.xlabel = 'Step'
        op.ylabel = 'Output'
        op.xlocator = 'IntegerLocator'
        op.xformat = '{:.0f}'
        op.yformat = '{:.2f}'
        op.title = f'{e_source} -> {e_target}: output'
        item = op.indices.add()
        item.x_is_step = True
        item.yindex = 0
        if edge['has_weights']:
            # todo check format of weights
            col.operator_context = 'EXEC_DEFAULT'
            op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname, text=f'Plot 2d Weights',
                              icon='ORIENTATION_VIEW')
            """Weights are solved once. They are used to approximate function given in connection"""
            # op.probe = 'probeable.weights'
            op.xlabel = 'Step'
            op.ylabel = 'Neuron Weight'
            op.xlocator = 'IntegerLocator'
            op.xformat = '{:.0f}'
            op.yformat = '{:.4f}'
            op.title = f'{e_source} -> {e_target}: weights'
            op.line_offset = -0.05
            target_node = share_data.model_graph.get_node_data(
                e_target)  # model_graph.nodes[e_target]
            # dimension 1 weight [neuron1, neuron2, ...]
            # dimension 2 weight [neuron1, neuron2, ...], ...
            for d in range(target_node['size_in']):
                # todo connection to node can also have weights?
                if source_node['type'] == 'Node':
                    logging.warning(f'Not implemented: {source_node}')
                    break
                for i in range(source_node['neurons']['size_out']):
                    item = op.indices.add()
                    item.x_is_step = True
                    item.yindex_multi_dim = f'[{d}, {i}]'  # same as numpy array slice. Must return single value
                    item.label = f'Neuron {item.yindex_multi_dim}'


class NengoInfoPanel(bpy.types.Panel):
    bl_label = 'Info'
    bl_idname = 'NENGO_PT_info'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    def draw_header_preset(self, context):
        layout = self.layout
        layout.emboss = 'NONE'
        row = layout.row(align=True)
        obj: bpy.types.Object = context.active_object
        if not obj:
            return
        if share_data.model_graph is not None:
            node = share_data.model_graph.get_node_or_subnet_data(obj.name)
            if node:
                row.label(text=node['type'])  #: {obj.name}')
                return
            e_source, _, _edge = share_data.model_graph.get_edge_by_name(obj.name)
            if e_source:
                row.label(text=f'Edge')  #: {obj.name}')
                return

            chart = None
            for source, charts in share_data.charts.items():
                for ax in charts:
                    if ax.root == obj:
                        chart = ax
            if chart:
                row.label(text=f'Plot')  #: {obj.name}')

    def draw(self, context):
        layout = self.layout.column()
        obj: bpy.types.Object = context.active_object
        if not obj:
            layout.label(text='No active object')
            return

        if share_data.model_graph is None:
            layout.label(text='No active model')
            return

        node = share_data.model_graph.get_node_or_subnet_data(obj.name)
        e_source, e_target, edge = share_data.model_graph.get_edge_by_name(obj.name)

        chart = None
        for source, charts in share_data.charts.items():
            for ax in charts:
                if ax.root == obj:
                    chart = ax
        if chart:
            self.draw_info_chart(chart, layout, obj)
        elif node:
            layout.label(text=f'Node: {obj.name}')
            col = layout.box().column(align=True)
            self._draw_expand(col, node)
        elif edge:
            layout.label(text=f'Edge: {obj.name}')
            layout.label(text=f'{e_source} -> {e_target}')
            col = layout.box().column(align=True)
            self._draw_expand(col, edge)
        else:
            layout.label(text=f'Not a network element')

    @staticmethod
    def draw_info_chart(ax: Axes, layout, obj: bpy.types.Object):
        col = layout.column()
        col.enabled = False
        # todo edition is not supported yet
        draw_axes_properties_template(col, ax.root.nengo_axes)

    def _draw_expand(self, col, item: dict, tab=0):
        for param, value in sorted(item.items()):
            if param.startswith('_'):
                continue
            if value is None:
                continue
            row = col.row()
            if tab:
                row.separator(factor=tab)
            row = row.split(factor=0.25)
            if isinstance(value, dict):
                if value:
                    row.label(text=param + ':')
                    self._draw_expand(col.box().column(align=True), value, tab + 1.4)
                else:
                    row.label(text=param + ':')
                    row.label(text=str(value))
            else:
                row.label(text=param)
                row.label(text=str(value))


def draw_enum(layout, nengo_3d):
    row = layout.row(align=True)
    draw_color_generator_properties_template(layout, nengo_3d.node_color_gen)
    box = layout.box()
    col = box.column()
    for name, data in sorted(nengo_3d.node_mapped_colors.items()):
        row = col.row(align=True)
        # todo add filters for hiding and selecting nodes and edges
        row.prop(data, 'color', text=name)


def draw_gradient(layout, nengo_3d):
    cr_node = bpy.data.materials['NengoNodeMaterial'].node_tree.nodes['ColorRamp']
    row = layout.row(align=True)
    row.label(text=f'Min: {nengo_3d.node_attr_min}')
    row.label(text=f'Max: {nengo_3d.node_attr_max}')

    box = layout.box()
    box.template_color_ramp(cr_node, 'color_ramp', expand=True)


class NengoColorsPanel(bpy.types.Panel):
    bl_label = 'Colors'
    bl_idname = 'NENGO_PT_colors'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    def draw(self, context):
        layout = self.layout
        nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
        layout.active = bool(share_data.model_graph)


class NengoNodeColorsPanel(bpy.types.Panel):
    bl_label = 'Node'
    bl_idname = 'NENGO_PT_node_colors'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_parent_id = NengoColorsPanel.bl_idname

    def draw(self, context):
        layout = self.layout
        nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
        layout.active = bool(share_data.model_graph) and context.area.type == 'VIEW_3D' and \
                        context.space_data.shading.type in {'MATERIAL', 'RENDERED'}
        layout.prop(nengo_3d, 'node_color', expand=True)

        if nengo_3d.node_color == 'SINGLE':
            nengo_3d.node_color_map = 'ENUM'
            layout.prop(nengo_3d, 'node_color_single', text='')
        elif nengo_3d.node_color == 'GRAPH':
            pass
        elif nengo_3d.node_color == 'MODEL':
            self.draw_model(layout, nengo_3d)
        elif nengo_3d.node_color == 'MODEL_DYNAMIC':
            self.draw_model_dynamic(layout, nengo_3d)
        else:
            assert False, nengo_3d.node_color

    @staticmethod
    def draw_model_dynamic(layout: bpy.types.UILayout, nengo_3d: Nengo3dProperties):
        layout.prop(nengo_3d, 'node_dynamic_access_path')
        if nengo_3d.node_dynamic_access_path == ':':
            return
        layout.label(text='data: np.array = data[node, access_path][step]')
        layout.prop(nengo_3d, 'node_dynamic_get', text='Get')
        # draw_color_source_properties_template(layout, nengo_3d.node_color_source)
        layout.prop(nengo_3d, 'node_color_map', expand=True)
        if nengo_3d.node_color_map == 'GRADIENT':
            draw_gradient(layout, nengo_3d)
        elif nengo_3d.node_color_map == 'ENUM':
            layout.operator(bl_operators.NengoColorNodesOperator.bl_idname)
            draw_enum(layout, nengo_3d)
        else:
            logging.error(f'Unknown value: {nengo_3d.node_color_map}')

    @staticmethod
    def draw_model(layout: bpy.types.UILayout, nengo_3d: Nengo3dProperties):
        layout.prop(nengo_3d, 'node_attribute_with_type', text='')
        if nengo_3d.node_attribute_with_type == ':':
            return
        if nengo_3d.node_attribute_with_type.endswith(':str'):
            nengo_3d.node_color_map = 'ENUM'
            layout.operator(bl_operators.NengoColorNodesOperator.bl_idname)
            draw_enum(layout, nengo_3d)
        elif nengo_3d.node_attribute_with_type.endswith(':int'):
            layout.prop(nengo_3d, 'node_color_map', expand=True)
            if nengo_3d.node_color_map == 'GRADIENT':
                draw_gradient(layout, nengo_3d)
            elif nengo_3d.node_color_map == 'ENUM':
                layout.operator(bl_operators.NengoColorNodesOperator.bl_idname)
                draw_enum(layout, nengo_3d)
            else:
                logging.error(f'Unknown value: {nengo_3d.node_color_map}')
        elif nengo_3d.node_attribute_with_type.endswith(':float'):
            nengo_3d.node_color_map = 'GRADIENT'
            draw_gradient(layout, nengo_3d)
        elif nengo_3d.node_attribute_with_type.endswith(':bool'):
            layout.operator(bl_operators.NengoColorNodesOperator.bl_idname)
            draw_enum(layout, nengo_3d)
        else:
            logging.error(f'Unknown type: "{nengo_3d.node_attribute_with_type}"')


class NengoStylePanel(bpy.types.Panel):
    bl_label = 'Arrow Style'
    bl_idname = 'NENGO_PT_style'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_parent_id = 'NENGO_PT_settings'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        nengo_3d = context.window_manager.nengo_3d
        col = layout.column(align=True)
        col.prop(nengo_3d, 'arrow_length')
        col.prop(nengo_3d, 'arrow_back_length')
        col.prop(nengo_3d, 'arrow_width')
        layout.prop(nengo_3d, 'edge_width')


classes = (
    NengoSettingsPanel,
    NengoContextPanel,
    NengoInfoPanel,
    NengoAlgorithmPanel,
    NengoColorsPanel,
    NengoNodeColorsPanel,
    NengoSubnetworksPanel,
    NengoStylePanel,
)

register, unregister = bpy.utils.register_classes_factory(classes)
