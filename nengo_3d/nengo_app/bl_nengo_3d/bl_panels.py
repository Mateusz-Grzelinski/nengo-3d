from __future__ import annotations

import logging

import bpy

from bl_nengo_3d import bl_operators, bl_plot_operators
from bl_nengo_3d.bl_properties import Nengo3dProperties
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

    @classmethod
    def poll(cls, context):
        return True

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
        nengo_3d = win_man.nengo_3d

        layout.operator(bl_operators.NengoCalculateOperator.bl_idname)
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

        obj_name = context.active_object.name
        if bl_plot_operators.PlotLineOperator.poll(context):
            node = share_data.model_graph.nodes.get(obj_name)
            e_source, e_target, edge = share_data.model_get_edge_by_name(obj_name)
            op = layout.operator(bl_plot_operators.PlotLineOperator.bl_idname, text=f'Plot 2d anything',
                                 icon='FORCE_HARMONIC')

            if node:
                # op = layout.operator(bl_plot_operators.PlotLineOperator.bl_idname, text=f'Plot 2d anything',
                #                      icon='FORCE_HARMONIC')
                col = layout.column(align=True)
                if node['type'] == 'Ensemble':
                    col.operator_context = 'EXEC_DEFAULT'
                    col.active = share_data.current_step > 0
                    op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                                      text=f'Plot 2d Response curves',
                                      icon='ORIENTATION_VIEW')
                    op.probe_now = 'neurons.response_curves'
                    op.xlabel = 'Input signal'
                    op.ylabel = 'Firing rate (Hz)'
                    # op.xformat = '{:.2f}'
                    # op.yformat = '{:.2f}'
                    op.title = f'{obj_name}: Neuron response curves\n' \
                               f'(step {share_data.current_step}, {node["neuron_type"]["name"]})'
                    # todo iterate
                    item = op.indices.add()
                    item.x_is_step = True
                    item.yindex = 0

                    col = col.column(align=True)
                    col.operator_context = 'EXEC_DEFAULT'
                    col.active = share_data.current_step > 0 and node['size_out'] < 2
                    op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                                      text=f'Plot 2d Tuning curves',
                                      icon='ORIENTATION_VIEW')
                    op.probe_now = 'neurons.tuning_curves'
                    op.xlabel = 'Input signal'
                    op.ylabel = 'Firing rate (Hz)'
                    # op.xformat = '{:.2f}'
                    # op.yformat = '{:.2f}'
                    op.title = f'{obj_name}: Neuron tuning curves\n' \
                               f'(step {share_data.current_step}, {node["neuron_type"]["name"]})'
                    op.line_offset = -0.05

                    col = layout.column(align=True)
                    col.operator_context = 'EXEC_DEFAULT'
                    neurons = node['neurons']
                    op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                                      text=f'Plot 2d Neuron Spikes',
                                      icon='ORIENTATION_VIEW')
                    op.probe = 'neurons.probeable.output'
                    op.xlabel = 'Step'
                    op.ylabel = 'Spikes'
                    op.xlocator = 'IntegerLocator'
                    op.xformat = '{:.0f}'
                    op.yformat = '{:.2f}'
                    op.line_offset = -0.05
                    op.title = f'{obj_name}: Spikes'
                    for i in range(neurons['size_out']):
                        item = op.indices.add()
                        item.x_is_step = True
                        item.yindex = i
                        item.label = f'Neuron {i}'

                    if node['size_out'] == 2:
                        op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                                          text=f'Plot 3d output',
                                          icon='ORIENTATION_GLOBAL')
                        op.probe = 'probeable.decoded_output'
                        op.xlabel = 'X'
                        op.ylabel = 'Y'
                        op.zlabel = 'Step'
                        op.xformat = '{:.2f}'
                        op.yformat = '{:.2f}'
                        op.zformat = '{:.0f}'
                        op.zlocator = 'IntegerLocator'
                        op.title = f'{obj_name} 3d: decoded output'
                        item = op.indices.add()
                        item.xindex = 0
                        item.yindex = 1
                        item.use_z = True
                        item.z_is_step = True

                        op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                                          text=f'Plot 2d ouput',
                                          icon='ORIENTATION_VIEW')
                        op.probe = 'probeable.decoded_output'
                        op.xlabel = 'X'
                        op.ylabel = 'Y'
                        op.xformat = '{:.2f}'
                        op.yformat = '{:.2f}'
                        op.title = f'{obj_name} 2d: output'
                        item = op.indices.add()
                        item.xindex = 0
                        item.yindex = 1
                    else:
                        op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname,
                                          text=f'Plot 2d decoded ouput',
                                          icon='ORIENTATION_VIEW')
                        op.probe = 'probeable.decoded_output'
                        op.xlabel = 'Step'
                        op.ylabel = 'Voltage'
                        op.xlocator = 'IntegerLocator'
                        op.xformat = '{:.0f}'
                        op.yformat = '{:.2f}'
                        op.title = f'{obj_name}: output'
                        item = op.indices.add()
                        item.x_is_step = True
                        item.yindex = 0
                elif node['type'] == 'Node':
                    col.operator_context = 'EXEC_DEFAULT'
                    op = col.operator(bl_plot_operators.PlotLineOperator.bl_idname, text=f'Plot 2d output',
                                      icon='ORIENTATION_VIEW')
                    op.probe = 'probeable.output'
                    op.xlabel = 'Step'
                    op.ylabel = 'Voltage'
                    op.xlocator = 'IntegerLocator'
                    op.xformat = '{:.0f}'
                    op.yformat = '{:.2f}'
                    op.title = f'{obj_name}: output'
                    item = op.indices.add()
                    item.x_is_step = True
                    item.yindex = 0
            if edge:
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
                source_node = share_data.model_graph.nodes[e_source]
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
                    op.probe = 'probeable.weights'
                    op.xlabel = 'Step'
                    op.ylabel = 'Neuron Weight'
                    op.xlocator = 'IntegerLocator'
                    op.xformat = '{:.0f}'
                    op.yformat = '{:.4f}'
                    op.title = f'{e_source} -> {e_target}: weights'
                    op.line_offset = -0.05
                    target_node = share_data.model_graph.nodes[e_target]
                    # dimension 1 weight [neuron1, neuron2, ...]
                    # dimension 2 weight [neuron1, neuron2, ...], ...
                    for d in range(target_node['size_in']):
                        for i in range(source_node['neurons']['size_out']):
                            item = op.indices.add()
                            item.x_is_step = True
                            item.yindex_multi_dim = f'[{d}, {i}]'  # same as numpy array slice. Must return single value
                            item.label = f'Neuron {item.yindex_multi_dim}'
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
            layout.label(text=f'Edge: {obj.name}, {e_source} -> {e_target}')
            col = layout.box().column(align=True)
            self._draw_expand(col, edge)
        else:
            layout.label(text=f'Not a network element')

    @staticmethod
    def draw_info_chart(ax: Axes, layout, obj: bpy.types.Object):
        row = layout.row()
        row.label(text=obj.name)
        row.label(text=ax.title_text)
        row = layout.row()
        row.label(text='Parameter')
        row.label(text=f'{ax.parameter}')
        row = layout.row(align=True)
        row.label(text='X range:')
        row.label(text='{:.2f}'.format(ax.xlim_min))
        row.label(text='{:.2f}'.format(ax.xlim_max))
        row = layout.row(align=True)
        row.label(text='Legend:')
        col = layout.box().column(align=True)
        for line in ax.plot_lines:
            row = col.row(align=True)
            row.separator(factor=1.4)
            row.label(text=line.label)
            row.prop(line._line.nengo_colors, 'color', text='')
            indices = share_data.plot_line_sources.get(line)
            if not indices: continue
            row.label(text=str(indices))

    def _draw_expand(self, col, items: dict, tab=0):
        edge = items
        for param, value in sorted(edge.items()):
            if param.startswith('_'):
                continue
            if value is None: continue
            row = col.row()
            row.separator(factor=tab)
            if isinstance(value, dict):
                row.label(text=param + ':')
                self._draw_expand(col.box().column(align=True), value, tab + 1.4)
            else:
                row.label(text=param)
                row.label(text=str(value))


def draw_enum(layout, nengo_3d):
    row = layout.row(align=True)
    row.prop(nengo_3d, 'node_initial_color')
    row.prop(nengo_3d, 'node_color_shift', text='')
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
    bl_category = 'Nengo Colors'

    def draw(self, context):
        layout = self.layout
        nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
        layout.active = bool(share_data.model_graph)


class NengoNodeColorsPanel(bpy.types.Panel):
    bl_label = 'Node'
    bl_idname = 'NENGO_PT_node_colors'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo Colors'
    bl_parent_id = NengoColorsPanel.bl_idname

    def draw(self, context):
        layout = self.layout
        nengo_3d: Nengo3dProperties = context.window_manager.nengo_3d
        layout.active = bool(share_data.model_graph)
        layout.prop(nengo_3d, 'node_color_source', expand=True)
        layout.operator(bl_operators.NengoColorNodesOperator.bl_idname)

        if nengo_3d.node_color_source == 'SINGLE':
            nengo_3d.node_color_map = 'ENUM'
            layout.prop(nengo_3d, 'node_color_single', text='')
        elif nengo_3d.node_color_source == 'GRAPH':
            pass
        elif nengo_3d.node_color_source == 'MODEL':
            self.draw_model(layout, nengo_3d)
        elif nengo_3d.node_color_source == 'MODEL_DYNAMIC':
            pass
        else:
            assert False, nengo_3d.node_color_source

    @staticmethod
    def draw_model(layout, nengo_3d):
        layout.prop(nengo_3d, 'node_attribute', text='')
        if nengo_3d.node_attribute == ':':
            return
        elif nengo_3d.node_attribute.endswith(':str'):
            nengo_3d.node_color_map = 'ENUM'
            draw_enum(layout, nengo_3d)
        elif nengo_3d.node_attribute.endswith(':int'):
            layout.prop(nengo_3d, 'node_color_map', expand=True)
            if nengo_3d.node_color_map == 'GRADIENT':
                draw_gradient(layout, nengo_3d)
            elif nengo_3d.node_color_map == 'ENUM':
                draw_enum(layout, nengo_3d)
            else:
                logging.error(f'Unknown value: {nengo_3d.node_color_map}')
        elif nengo_3d.node_attribute.endswith(':float'):
            nengo_3d.node_color_map = 'GRADIENT'
            draw_gradient(layout, nengo_3d)
        elif nengo_3d.node_attribute.endswith(':bool'):
            draw_enum(layout, nengo_3d)
        else:
            logging.error(f'Unknown type: "{nengo_3d.node_attribute}"')


classes = (
    NengoSettingsPanel,
    NengoContextPanel,
    NengoInfoPanel,
    NengoAlgorithmPanel,
    NengoColorsPanel,
    NengoNodeColorsPanel,
)

register, unregister = bpy.utils.register_classes_factory(classes)
