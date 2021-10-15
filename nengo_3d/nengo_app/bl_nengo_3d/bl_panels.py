from __future__ import annotations

import logging
import time
from typing import Any

import bpy

from bl_nengo_3d import bl_operators, bl_plot_operators, frame_change_handler
from bl_nengo_3d.bl_properties import Nengo3dProperties, Nengo3dShowNetwork, draw_axes_properties_template, \
    AxesProperties, LineProperties, LineSourceProperties, draw_color_generator_properties_template
from bl_nengo_3d.axes import Axes
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
        nengo_3d = context.scene.nengo_3d
        cached_frames = share_data.current_step * nengo_3d.sample_every
        until = share_data.requested_steps_until
        layout.label(
            text=f'Cached: {cached_frames if cached_frames >= 0 else -1}/{until - 1 if until >= 0 else -1:.0f}')

    def draw(self, context):
        layout = self.layout.column()

        layout.label(text='localhost:6001')
        is_connected = connected()
        if not is_connected:
            row = layout.row()
            row.scale_y = 1.5
            row.operator(bl_operators.ConnectOperator.bl_idname, text='Connect')
        else:
            row = layout.row()
            row.scale_y = 1.5
            row.operator(bl_operators.DisconnectOperator.bl_idname, text='Disconnect')

        layout.operator(bl_operators.NengoQuickSaveOperator.bl_idname,
                        text='Quick save!' if bpy.data.is_dirty else 'Quick save')

        nengo_3d = context.scene.nengo_3d
        col = layout.column(align=True)
        col.prop(nengo_3d, 'sample_every')
        col.prop(nengo_3d, 'dt')

        row = layout.row()
        row.active = not is_connected
        col = layout.column()
        col.operator(bl_operators.NengoSimulateOperator.bl_idname,
                     text='!Reset!' if nengo_3d.requires_reset else 'Reset',
                     icon='CANCEL').action = 'reset'

        col = layout.column()
        col.active = is_connected and not nengo_3d.requires_reset
        row = col.row(align=True)
        subrow = row.row(align=True)
        subrow.operator(bl_operators.NengoSimulateOperator.bl_idname, text=f'Step x{nengo_3d.step_n}',
                        icon='FRAME_NEXT').action = 'step'
        subrow = row.row(align=True)
        subrow.prop(nengo_3d, 'step_n', text='')

        row = col.row(align=True)
        subrow = row.row(align=True)
        if context.scene.is_simulation_playing:
            subrow.operator(bl_operators.NengoSimulateOperator.bl_idname, text='Stop',
                            icon='PAUSE').action = 'continuous'
        else:
            subrow.operator(bl_operators.NengoSimulateOperator.bl_idname, text='Play',
                            icon='PLAY').action = 'continuous'
        subrow = row.row(align=True)
        subrow.prop(nengo_3d, 'speed', text='')

        nengo_3d: Nengo3dProperties = context.scene.nengo_3d
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
        layout.prop(nengo_3d, 'force_one_connection_per_edge')


class NengoSubnetworksPanel(bpy.types.Panel):
    bl_label = 'Subnetworks'
    bl_idname = 'NENGO_PT_subnetworks'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_options = {'DEFAULT_CLOSED'}
    bl_parent_id = 'NENGO_PT_layout'

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        box = layout.box()
        if not connected():
            layout.active = False
            # return
        nengo_3d = context.scene.nengo_3d
        box.label(text='Expand subnetworks')
        col = box.column(align=True)
        for net in sorted(nengo_3d.expand_subnetworks, key=lambda net: net.name):
            row = col.row(align=True)
            net: Nengo3dShowNetwork
            row.prop(net, 'expand', text=net.network)
            # row.prop(net, 'draw_bounded', text='')
            # row.label(text=net.network)


class NengoLayoutPanel(bpy.types.Panel):
    bl_label = 'Nengo layout'
    bl_idname = 'NENGO_PT_layout'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout.column()

        nengo_3d = context.scene.nengo_3d

        layout.operator(bl_operators.NengoGraphOperator.bl_idname)
        layout.prop(nengo_3d, 'spacing')
        layout.use_property_split = False
        row = layout.row()
        row.prop(nengo_3d, 'algorithm_dim', expand=True)
        if nengo_3d.algorithm_dim == '2D':
            layout.prop(nengo_3d, 'layout_algorithm_2d')
        else:
            layout.prop(nengo_3d, 'layout_algorithm_3d')


class NengoContextPanel(bpy.types.Panel):
    bl_label = 'Context actions'
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
        if not share_data.model_graph:
            return

        obj_name = obj.name
        node = share_data.model_graph.get_node_or_subnet_data(obj_name)
        # layout.operator(bl_plot_operators.PlotLineOperator.bl_idname, text=f'Plot 2d anything',
        #                 icon='FORCE_HARMONIC')

        if node:
            nengo_3d = context.scene.nengo_3d
            self.draw_node_actions(layout, obj_name, nengo_3d.select_edges)

            col = layout.column()
            if node['type'] == 'Ensemble':
                self.draw_ensemble_type_actions(col, node, obj_name, context.scene.frame_current)
            elif node['type'] == 'Node':
                self.draw_node_type_actions(col, obj_name, node)
            elif node['type'] == 'Network':
                self.draw_network_type_actions(col, node)
            return

        e_source, e_target, edge = share_data.model_graph.get_edge_by_name(obj_name)
        if edge:
            self.draw_edge_actions(layout, obj_name, e_source, e_target, edge)
            return

        if obj.nengo_axes.object == obj_name:
            layout.operator(bl_plot_operators.RemoveAxOperator.bl_idname).axes_obj = obj.nengo_axes.object

    def draw_node_actions(self, layout, obj_name: str, selectable_edges: bool):
        layout.label(text='Select')
        layout.operator(bl_operators.GrowSelectOperator.bl_idname, text='Grow selection')
        row = layout.row()
        op = row.operator(bl_operators.SimpleSelectOperator.bl_idname, text=f'Predecessors')
        for _node in share_data.model_graph_view.predecessors(obj_name):
            item = op.objects.add()
            item.object = _node
        op = row.operator(bl_operators.SimpleSelectOperator.bl_idname, text=f'Successors')
        for _node in share_data.model_graph_view.successors(obj_name):
            item = op.objects.add()
            item.object = _node

        if not selectable_edges:
            return
        layout.label(text='Select edges')
        row = layout.row()
        op = row.operator(bl_operators.SimpleSelectOperator.bl_idname, text=f'In')
        for e_source, e_target, key, e_data in share_data.model_graph_view.in_edges(obj_name, data=True, keys=True):
            item = op.objects.add()
            item.object = key
        op = row.operator(bl_operators.SimpleSelectOperator.bl_idname, text=f'Out')
        for e_source, e_target, key, e_data in share_data.model_graph_view.out_edges(obj_name, data=True, keys=True):
            item = op.objects.add()
            item.object = key

    @staticmethod
    def draw_node_type_actions(layout: bpy.types.UILayout, obj_name, node: dict[str, Any]):
        col = layout
        if node['network_name'] != 'model':
            layout.label(text='Subnetworks:')
            op = col.operator(bl_operators.NengoGraphOperator.bl_idname,
                              text=f'Collapse {node["network_name"]}')
            op.collapse = node['network_name']

        layout.label(text='Plot 2d lines:')

        box = layout.box()
        col = box.column(align=True)
        if node['has_vocabulary']:
            op = col.operator(bl_plot_operators.PlotByRowSimilarityOperator.bl_idname,
                              text=f'Similarity (dim {node["vocabulary_size"]})',
                              icon='ORIENTATION_VIEW')
            op.object = obj_name
            op.access_path = 'probeable.output.similarity'
            op.dimensions = node['vocabulary_size']
            op.axes: AxesProperties
            op.axes.xlabel = 'Step'
            op.axes.ylabel = 'Similarity'
            op.axes.xlocator = 'IntegerLocator'
            op.axes.xformat = '{:.0f}'
            op.axes.yformat = '{:.2f}'
            op.axes.title = f'{obj_name}: output (similarity)'

        col = box.column(align=True)
        op = col.operator(bl_plot_operators.PlotByRowOperator.bl_idname,
                          text=f'Output (dim {node["size_out"]})', icon='ORIENTATION_VIEW')
        op.object = obj_name
        op.access_path = 'probeable.output'
        op.dimensions = node['size_out']
        op.axes: AxesProperties
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: output'

    @staticmethod
    def draw_ensemble_type_actions(layout: bpy.types.UILayout, ensemble: dict[str, Any], obj_name: str,
                                   frame_current: int):
        node = ensemble
        if node['network_name'] != 'model':
            layout.label(text='Subnetworks:')
            op = layout.operator(bl_operators.NengoGraphOperator.bl_idname,
                                 text=f'Collapse {node["network_name"]}')
            op.collapse = node['network_name']

        layout.label(text='Plot 2d lines:')
        box = layout.box().column(align=True)
        box.label(text='Ensemble:')

        op = box.operator(bl_plot_operators.PlotByRowOperator.bl_idname,
                          text=f'Decoded output (dim {ensemble["size_out"]})',
                          icon='ORIENTATION_VIEW')
        op.object = obj_name
        op.access_path = 'probeable.decoded_output'
        op.dimensions = ensemble['size_out']
        op.axes: AxesProperties
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: decoded_output'

        op = box.operator(bl_plot_operators.PlotByRowOperator.bl_idname,
                          text=f'Input (dim {ensemble["size_in"]})',
                          icon='ORIENTATION_VIEW')
        op.object = obj_name
        op.access_path = 'probeable.input'
        op.dimensions = ensemble['size_in']
        op.axes: AxesProperties
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: input'

        op = box.operator(bl_plot_operators.PlotByRowOperator.bl_idname,
                          text=f'Scaled encoders (dim {ensemble["size_out"]})',
                          icon='ORIENTATION_VIEW')
        op.object = obj_name
        op.access_path = 'probeable.scaled_encoders'
        op.dimensions = ensemble['size_out']
        op.axes: AxesProperties
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: scaled_encoders'

        neurons = ensemble['neurons']

        box = layout.box().column(align=True)
        box.label(text=f'Neurons (in: {neurons["size_in"]}, out: {neurons["size_out"]}):')
        op = box.operator(bl_plot_operators.PlotBy2dColumnOperator.bl_idname,
                          text=f'Response curves at {frame_current} step',
                          icon='ORIENTATION_VIEW')
        op.object = obj_name
        op.n_neurons = neurons['size_in']
        op.access_path = 'neurons.response_curves'
        op.axes.xlabel = 'Input signal'
        op.axes.ylabel = 'Firing rate (Hz)'
        op.axes.title = f'{obj_name}: Neuron response curves\n' \
                        f'(step {frame_current}, {ensemble["neuron_type"]["name"]})'

        op = box.operator(bl_plot_operators.PlotBy2dColumnOperator.bl_idname,
                          text=f'Tuning curves at {frame_current} step',
                          icon='ORIENTATION_VIEW')
        op.object = obj_name
        op.n_neurons = neurons['size_in']
        op.access_path = 'neurons.tuning_curves'
        op.axes.xlabel = 'Input signal'
        op.axes.ylabel = 'Firing rate (Hz)'
        op.axes.title = f'{obj_name}: Neuron tuning curves\n' \
                        f'(step {frame_current}, {ensemble["neuron_type"]["name"]})'

        op = box.operator(bl_plot_operators.PlotByRowOperator.bl_idname,
                          text=f'Output (spikes)',
                          icon='ORIENTATION_VIEW')
        op.object = obj_name
        op.dimensions = neurons['size_out']
        op.access_path = 'neurons.probeable.output'
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Spikes'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: Neurons output (spikes)'

        op = box.operator(bl_plot_operators.PlotByRowOperator.bl_idname,
                          text=f'Input',
                          icon='ORIENTATION_VIEW')
        op.object = obj_name
        op.dimensions = neurons['size_out']
        op.access_path = 'neurons.probeable.input'
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Input'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: Neurons input'

        op = box.operator(bl_plot_operators.PlotByRowOperator.bl_idname,
                          text=f'Voltage',
                          icon='ORIENTATION_VIEW')
        op.object = obj_name
        op.dimensions = neurons['size_out']
        op.access_path = 'neurons.probeable.voltage'
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: Neurons voltage'

        op = box.operator(bl_plot_operators.PlotByRowOperator.bl_idname,
                          text=f'Refractory time',
                          icon='ORIENTATION_VIEW')
        op.object = obj_name
        op.dimensions = neurons['size_out']
        op.access_path = 'neurons.probeable.refractory_time'
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Refractory time'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{obj_name}: Neurons refractory time'

        # 3d plots
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
        #                       text=f'Ouput',
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
    def draw_network_type_actions(layout: bpy.types.UILayout, node: dict[str, Any]):
        layout.label(text='Subnetworks:')
        if node.get('parent_network'):
            row = layout.row()
            op = row.operator(bl_operators.NengoGraphOperator.bl_idname,
                              text=f'Collapse {node["parent_network"]}')
            op.collapse = node['parent_network']
        else:
            row = layout
        op = row.operator(bl_operators.NengoGraphOperator.bl_idname, text=f'Expand {node["name"]}')
        op.expand = node['name']

    @staticmethod
    def draw_edge_actions(layout: bpy.types.UILayout, obj_name: str, e_source: str, e_target: str,
                          e_data: dict[str, Any]):
        layout.label(text='Select')
        row = layout.row()
        op = row.operator(bl_operators.SelectByEdgeOperator.bl_idname, text=f'Source')
        op.edge_name = obj_name
        op.select_source = True
        op = row.operator(bl_operators.SelectByEdgeOperator.bl_idname, text=f'Target')
        op.edge_name = obj_name
        op.select_target = True

        layout.label(text='Plot 2d:')
        box = layout.box()

        col = box.column(align=True)

        source_node = share_data.model_graph.get_node_data(e_data['pre'])  # model_graph.nodes[e_target]
        if source_node['has_vocabulary']:
            node = source_node
            obj_name = source_node['name']
            op = col.operator(bl_plot_operators.PlotByRowSimilarityOperator.bl_idname,
                              text=f'{obj_name}  similarity (dim {node["vocabulary_size"]}) - source node',
                              icon='ORIENTATION_VIEW')
            op.object = obj_name
            op.access_path = 'probeable.output.similarity'
            op.dimensions = node['vocabulary_size']
            op.axes: AxesProperties
            op.axes.xlabel = 'Step'
            op.axes.ylabel = 'Similarity'
            op.axes.xlocator = 'IntegerLocator'
            op.axes.xformat = '{:.0f}'
            op.axes.yformat = '{:.2f}'
            op.axes.title = f'{obj_name}: output (similarity)'

        target_node = share_data.model_graph.get_node_data(e_data['post'])
        if target_node['has_vocabulary']:
            node = target_node
            obj_name = target_node['name']
            op = col.operator(bl_plot_operators.PlotByRowSimilarityOperator.bl_idname,
                              text=f'{obj_name}  similarity (dim {node["vocabulary_size"]}) - target node',
                              icon='ORIENTATION_VIEW')
            op.object = obj_name
            op.access_path = 'probeable.output.similarity'
            op.dimensions = node['vocabulary_size']
            op.axes: AxesProperties
            op.axes.xlabel = 'Step'
            op.axes.ylabel = 'Similarity'
            op.axes.xlocator = 'IntegerLocator'
            op.axes.xformat = '{:.0f}'
            op.axes.yformat = '{:.2f}'
            op.axes.title = f'{obj_name}: output (similarity)'

        col = box.column(align=True)

        op = col.operator(bl_plot_operators.PlotByRowOperator.bl_idname,
                          text=f'Input (dim {e_data["size_in"]})',
                          icon='ORIENTATION_VIEW')
        op.object = e_data['name']
        op.access_path = 'probeable.input'
        op.dimensions = e_data['size_in']
        op.axes: AxesProperties
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{e_data["name"]}: input'

        op = col.operator(bl_plot_operators.PlotByRowOperator.bl_idname,
                          text=f'Output (dim {e_data["size_out"]})',
                          icon='ORIENTATION_VIEW')
        op.object = e_data['name']
        op.access_path = 'probeable.output'
        op.dimensions = e_data['size_out']
        op.axes: AxesProperties
        op.axes.xlabel = 'Step'
        op.axes.ylabel = 'Voltage'
        op.axes.xlocator = 'IntegerLocator'
        op.axes.xformat = '{:.0f}'
        op.axes.yformat = '{:.2f}'
        op.axes.title = f'{e_data["name"]}: output'

        if e_data['has_weights']:
            # Weights are usually solved once. They are used to approximate function given in connection
            if source_node['type'] == 'Node':
                op = col.operator(
                    bl_plot_operators.PlotBy2dRowOperator.bl_idname,
                    text=f'Weights ({e_data["size_out"]} dim * {source_node["size_out"]} neurons) '
                         f'= {e_data["size_out"] * source_node["size_out"]})',
                    icon='ORIENTATION_VIEW')
                op.object = e_data['name']
                op.access_path = 'probeable.weights'
                # dimension 1 weight [neuron1, neuron2, ...]
                # dimension 2 weight [neuron1, neuron2, ...], ...
                op.dimension1 = source_node['size_out']
                op.dimension2 = e_data['size_out']
                op.axes.xlabel = 'Step'
                op.axes.ylabel = 'Weight'
                op.axes.xlocator = 'IntegerLocator'
                op.axes.xformat = '{:.0f}'
                op.axes.yformat = '{:.4f}'
                op.axes.title = f'{e_data["name"]}: weights'
            else:
                op = col.operator(
                    bl_plot_operators.PlotBy2dRowOperator.bl_idname,
                    text=f'Weights ({e_data["size_out"]} dim * {source_node["neurons"]["size_out"]} neurons '
                         f'= {e_data["size_out"] * source_node["neurons"]["size_out"]})',
                    icon='ORIENTATION_VIEW')
                op.object = e_data['name']
                op.access_path = 'probeable.weights'
                # dimension 1 weight [neuron1, neuron2, ...]
                # dimension 2 weight [neuron1, neuron2, ...], ...
                op.dimension1 = source_node['neurons']['size_out']
                op.dimension2 = e_data['size_out']
                op.axes.xlabel = 'Step'
                op.axes.ylabel = 'Neuron weight'
                op.axes.xlocator = 'IntegerLocator'
                op.axes.xformat = '{:.0f}'
                op.axes.yformat = '{:.4f}'
                op.axes.title = f'{e_data["name"]}: weights'
                # target_node = share_data.model_graph.get_node_data(e_data['post'])  # model_graph.nodes[e_target]


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
        # col.enabled = False
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


def draw_node_enum(layout: bpy.types.UILayout, nengo_3d: Nengo3dProperties):
    row = layout.row(align=True)
    draw_color_generator_properties_template(row, nengo_3d.node_color_gen)
    row.operator(bl_operators.NengoColorNodesOperator.bl_idname, text='', icon='FILE_REFRESH')
    box = layout.box()
    col = box.column()
    if len(nengo_3d.node_mapped_colors) > 0 and str(nengo_3d.node_mapped_colors[0].name).isnumeric():
        key = lambda key_value: float(key_value[0])
    else:
        key = lambda key_value: key_value[0]
    for name, data in sorted(nengo_3d.node_mapped_colors.items(), key=key):
        row = col.row(align=True)
        # todo add filters for hiding and selecting nodes and edges
        row.prop(data, 'color', text=name)


def draw_edge_enum(layout: bpy.types.UILayout, nengo_3d: Nengo3dProperties):
    row = layout.row(align=True)
    draw_color_generator_properties_template(row, nengo_3d.edge_color_gen)
    row.operator(bl_operators.NengoColorEdgesOperator.bl_idname, text='', icon='FILE_REFRESH')
    box = layout.box()
    col = box.column()
    if len(nengo_3d.edge_mapped_colors) > 0 and str(nengo_3d.edge_mapped_colors[0].name).isnumeric():
        key = lambda key_value: float(key_value[0])
    else:
        key = lambda key_value: key_value[0]
    for name, data in sorted(nengo_3d.edge_mapped_colors.items(), key=key):
        row = col.row(align=True)
        # todo add filters for hiding and selecting nodes and edges
        row.prop(data, 'color', text=name)


def draw_edge_gradient(layout, nengo_3d):
    cr_node = bpy.data.materials['NengoEdgeMaterial'].node_tree.nodes['ColorRamp']
    row = layout.row(align=True)
    row.prop(nengo_3d, 'edge_attr_auto_range', text='')
    subrow = row.row(align=True)
    subrow.active = not nengo_3d.edge_attr_auto_range
    subrow.prop(nengo_3d, 'edge_attr_min')
    subrow.prop(nengo_3d, 'edge_attr_max')
    subrow.operator(bl_operators.NengoColorEdgesOperator.bl_idname, icon='FILE_REFRESH', text='')

    box = layout.box()
    box.template_color_ramp(cr_node, 'color_ramp', expand=True)


def draw_node_gradient(layout, nengo_3d):
    cr_node = bpy.data.materials['NengoNodeMaterial'].node_tree.nodes['ColorRamp']
    row = layout.row(align=True)
    row.prop(nengo_3d, 'node_attr_auto_range', text='')
    subrow = row.row(align=True)
    subrow.active = not nengo_3d.node_attr_auto_range
    subrow.prop(nengo_3d, 'node_attr_min')
    subrow.prop(nengo_3d, 'node_attr_max')
    subrow.operator(bl_operators.NengoColorNodesOperator.bl_idname, icon='FILE_REFRESH', text='')

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
        nengo_3d: Nengo3dProperties = context.scene.nengo_3d
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
        nengo_3d: Nengo3dProperties = context.scene.nengo_3d
        layout.active = bool(share_data.model_graph) and context.area.type == 'VIEW_3D' and \
                        context.space_data.shading.type in {'MATERIAL', 'RENDERED'}
        layout.prop(nengo_3d, 'node_color', expand=True)

        if nengo_3d.node_color == 'SINGLE':
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
        layout.prop(nengo_3d, 'node_color_map', expand=True)
        if nengo_3d.node_color_map == 'GRADIENT':
            draw_node_gradient(layout, nengo_3d)
        elif nengo_3d.node_color_map == 'ENUM':
            draw_node_enum(layout, nengo_3d)
        else:
            logging.error(f'Unknown value: {nengo_3d.node_color_map}')

    @staticmethod
    def draw_model(layout: bpy.types.UILayout, nengo_3d: Nengo3dProperties):
        layout.prop(nengo_3d, 'node_attribute_with_type', text='')
        if nengo_3d.node_attribute_with_type == ':':
            return
        if nengo_3d.node_attribute_with_type.endswith(':str'):
            draw_node_enum(layout, nengo_3d)
        elif nengo_3d.node_attribute_with_type.endswith(':int'):
            layout.prop(nengo_3d, 'node_color_map', expand=True)
            if nengo_3d.node_color_map == 'GRADIENT':
                draw_node_gradient(layout, nengo_3d)
            elif nengo_3d.node_color_map == 'ENUM':
                draw_node_enum(layout, nengo_3d)
            else:
                logging.error(f'Unknown value: {nengo_3d.node_color_map}')
        elif nengo_3d.node_attribute_with_type.endswith(':float'):
            draw_node_gradient(layout, nengo_3d)
        elif nengo_3d.node_attribute_with_type.endswith(':bool'):
            draw_node_enum(layout, nengo_3d)
        else:
            logging.error(f'Unknown type: "{nengo_3d.node_attribute_with_type}"')


class NengoEdgeColorsPanel(bpy.types.Panel):
    bl_label = 'Edge'
    bl_idname = 'NENGO_PT_edge_colors'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_parent_id = NengoColorsPanel.bl_idname

    def draw(self, context):
        layout = self.layout
        nengo_3d: Nengo3dProperties = context.scene.nengo_3d
        layout.active = bool(share_data.model_graph) and context.area.type == 'VIEW_3D' and \
                        context.space_data.shading.type in {'MATERIAL', 'RENDERED'}
        layout.prop(nengo_3d, 'edge_color', expand=True)

        if nengo_3d.edge_color == 'SINGLE':
            layout.prop(nengo_3d, 'edge_color_single', text='')
        elif nengo_3d.edge_color == 'GRAPH':
            pass
        elif nengo_3d.edge_color == 'MODEL':
            self.draw_model(layout, nengo_3d)
        elif nengo_3d.edge_color == 'MODEL_DYNAMIC':
            self.draw_model_dynamic(layout, nengo_3d)
        else:
            assert False, nengo_3d.edge_color

    @staticmethod
    def draw_model_dynamic(layout: bpy.types.UILayout, nengo_3d: Nengo3dProperties):
        layout.prop(nengo_3d, 'edge_dynamic_access_path')
        if nengo_3d.edge_dynamic_access_path == ':':
            return
        layout.label(text='data: np.array = data[node, access_path][step]')
        layout.prop(nengo_3d, 'edge_dynamic_get', text='Get')
        layout.prop(nengo_3d, 'edge_color_map', expand=True)
        if nengo_3d.edge_color_map == 'GRADIENT':
            draw_edge_gradient(layout, nengo_3d, )
        elif nengo_3d.edge_color_map == 'ENUM':
            draw_edge_enum(layout, nengo_3d)
        else:
            logging.error(f'Unknown value: {nengo_3d.edge_color_map}')

    @staticmethod
    def draw_model(layout: bpy.types.UILayout, nengo_3d: Nengo3dProperties):
        layout.prop(nengo_3d, 'edge_attribute_with_type', text='')
        if nengo_3d.edge_attribute_with_type == ':':
            return
        if nengo_3d.edge_attribute_with_type.endswith(':str'):
            draw_edge_enum(layout, nengo_3d)
        elif nengo_3d.edge_attribute_with_type.endswith(':int'):
            layout.prop(nengo_3d, 'edge_color_map', expand=True)
            if nengo_3d.edge_color_map == 'GRADIENT':
                draw_edge_gradient(layout, nengo_3d)
            elif nengo_3d.edge_color_map == 'ENUM':
                draw_edge_enum(layout, nengo_3d)
            else:
                logging.error(f'Unknown value: {nengo_3d.edge_color_map}')
        elif nengo_3d.edge_attribute_with_type.endswith(':float'):
            draw_edge_gradient(layout, nengo_3d)
        elif nengo_3d.edge_attribute_with_type.endswith(':bool'):
            draw_edge_enum(layout, nengo_3d)
        else:
            logging.error(f'Unknown type: "{nengo_3d.edge_attribute_with_type}"')


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
        nengo_3d = context.scene.nengo_3d
        col = layout.column(align=True)
        col.prop(nengo_3d, 'arrow_length')
        col.prop(nengo_3d, 'arrow_back_length')
        col.prop(nengo_3d, 'arrow_width')
        layout.prop(nengo_3d, 'edge_width')


classes = (
    NengoSettingsPanel,
    NengoContextPanel,
    NengoInfoPanel,
    NengoLayoutPanel,
    NengoColorsPanel,
    NengoNodeColorsPanel,
    NengoEdgeColorsPanel,
    NengoSubnetworksPanel,
    NengoStylePanel,
)

register, unregister = bpy.utils.register_classes_factory(classes)
