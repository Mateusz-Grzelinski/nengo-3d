import logging
import math
import typing

import bpy
from mathutils import Vector

from bl_nengo_3d.bl_properties import AxesProperties, draw_axes_properties_template, LineProperties, \
    LineSourceProperties
from bl_nengo_3d.axes import Axes
from bl_nengo_3d.share_data import share_data


class PlotLineOperator(bpy.types.Operator):
    bl_idname = 'nengo_3d.plot_line'
    bl_label = 'Plot'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    axes: bpy.props.PointerProperty(type=AxesProperties, options={'SKIP_SAVE'})

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=500)

    def draw(self, context):
        layout = self.layout
        draw_axes_properties_template(layout, self.axes)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if share_data.model_graph is not None and obj:
            if share_data.model_graph.nodes.get(obj.name):
                return True
            if share_data.model_graph.get_subnetwork(obj.name):
                return True
            _, _, edge = share_data.model_graph.get_edge_by_name(obj.name)
            if edge:
                return True
        return False

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
            share_data.resume_playback_on_steps = False
            share_data.step_when_ready = 0
        context.scene.nengo_3d.requires_reset = True

        if self.axes.line_offset == 0:
            self.axes.line_offset = -0.01
        elif abs(self.axes.line_offset) * len(self.axes.lines) > 1:
            sign = 1 if self.axes.line_offset > 0 else -1
            self.axes.line_offset = sign / len(self.axes.lines)

        node: bpy.types.Object = context.active_object  # or for all selected_objects
        if not self.axes.model_source:
            self.axes.model_source = node.name
        ax = Axes(context, self.axes)
        ax.root.parent = node
        ax.root.location = node.dimensions / 2 + Vector((0, 0.0, 0.3))
        ax.root.rotation_euler.x += math.pi / 2

        share_data.register_chart(ax=ax)
        ax.draw()
        return {'FINISHED'}


class RemoveAxOperator(bpy.types.Operator):
    bl_idname = 'nengo_3d.remove_ax'
    bl_label = 'Remove axes'

    axes_obj: bpy.props.StringProperty()

    def execute(self, context: 'Context') -> typing.Union[typing.Set[str], typing.Set[int]]:
        ax_obj = bpy.data.objects.get(self.axes_obj)
        if not ax_obj:
            return {'CANCELLED'}

        # todo getting chart by parent relationship is not reliable
        # todo remove by collection name?
        names = set()

        def get_child_names(obj):
            nonlocal names
            for child in obj.children:
                names.add(child.name)
                if child.children:
                    get_child_names(child)

        ax: AxesProperties = ax_obj.nengo_axes
        try:
            for source, axes in share_data.charts.items():
                to_remove = []
                for _ax in axes:
                    if ax.object == _ax.root.name:
                        to_remove.append(_ax)
                for r in to_remove:
                    axes.remove(r)
        except ReferenceError as e:
            logging.exception(f'Known error (fix _ax.root). Please save and restart: {str(e)}')
            return {'CANCELLED'}

        # axes: Axes = share_data.charts[ax]
        get_child_names(ax_obj)
        for child in names:
            obj = bpy.data.objects[child]
            bpy.data.objects.remove(obj, do_unlink=True)
        # todo remove subcollections?
        bpy.data.collections.remove(bpy.data.collections[ax_obj.nengo_axes.collection])
        bpy.data.objects.remove(ax_obj, do_unlink=True)
        # for line in ax_obj.nengo_axes.lines:
        #     line_obj = bpy.data.objects[line.name]
        #     bpy.data.objects.remove(line_obj, do_unlink=True)
        return {'FINISHED'}


class PlotByRowSimilarityOperator(PlotLineOperator):
    bl_idname = 'nengo_3d.plot_byrow_similarity'
    bl_label = 'Plot similarity'

    object: bpy.props.StringProperty(options={'SKIP_SAVE'})
    access_path: bpy.props.StringProperty(options={'SKIP_SAVE'})
    dimensions: bpy.props.IntProperty(options={'SKIP_SAVE'})

    def invoke(self, context, event):
        node = share_data.model_graph.get_node_data(self.object)
        self.axes.model_source = self.object  # workaround for screating plot from edge
        for i in range(self.dimensions):
            line: LineProperties = self.axes.lines.add()
            line.source: LineSourceProperties
            line.source.source_obj = self.object
            line.source.access_path = f'{self.access_path}'
            line.source.iterate_step = True
            line.source.get_x = 'step'
            line.source.get_y = f'row[{i}]'
            line.label = node['vocabulary'][i]
        return self.execute(context)


class PlotByRowOperator(PlotLineOperator):
    bl_idname = 'nengo_3d.plot_byrow'
    bl_label = 'Plot output'

    object: bpy.props.StringProperty(options={'SKIP_SAVE'})
    access_path: bpy.props.StringProperty(options={'SKIP_SAVE'})
    dimensions: bpy.props.IntProperty(options={'SKIP_SAVE'})

    def invoke(self, context, event):
        # node = share_data.model_graph.get_node_data(self.object)
        op: PlotLineOperator = self
        # op.axes: AxesProperties
        # op.axes.xlabel = 'Step'
        # op.axes.ylabel = 'Voltage'
        # op.axes.xlocator = 'IntegerLocator'
        # op.axes.xformat = '{:.0f}'
        # op.axes.yformat = '{:.2f}'
        # op.axes.title = f'{self.object}: {self.probeable}'
        for i in range(self.dimensions):
            line: LineProperties = op.axes.lines.add()
            line.source: LineSourceProperties
            line.source.source_obj = self.object
            line.source.access_path = f'{self.access_path}'
            line.source.iterate_step = True
            line.source.get_x = 'step'
            line.source.get_y = f'row[{i}]'
            line.label = f'Dimension {i}'
        return self.execute(context)


class PlotBy2dRowOperator(PlotLineOperator):
    bl_idname = 'nengo_3d.plot_by2drow'
    bl_label = 'Plot output'

    object: bpy.props.StringProperty(options={'SKIP_SAVE'})
    access_path: bpy.props.StringProperty(options={'SKIP_SAVE'})
    dimension1: bpy.props.IntProperty(options={'SKIP_SAVE'})
    dimension2: bpy.props.IntProperty(options={'SKIP_SAVE'})

    def invoke(self, context, event):
        for i in range(self.dimension1):  # same as target_node['size_in']
            for d in range(self.dimension2):
                line: LineProperties = self.axes.lines.add()
                line.label = f'Neuron {d} {i}'
                line.source: LineSourceProperties
                line.source.source_obj = self.object
                line.source.access_path = self.access_path
                line.source.iterate_step = True
                line.source.get_x = 'step'
                line.source.get_y = f'row[{d}, {i}]'
        return self.execute(context)


class PlotBy2dColumnOperator(PlotLineOperator):
    bl_idname = 'nengo_3d.plot_neurons'
    bl_label = 'Plot input'

    object: bpy.props.StringProperty(options={'SKIP_SAVE'})
    access_path: bpy.props.StringProperty(options={'SKIP_SAVE'})
    n_neurons: bpy.props.IntProperty(options={'SKIP_SAVE'})

    def invoke(self, context: 'Context', event: 'Event') -> typing.Union[typing.Set[str], typing.Set[int]]:
        # ensemble = share_data.model_graph.get_node_data(self.object)
        # neurons = ensemble['neurons']
        frame_current = context.scene.frame_current
        # self.axes: AxesProperties
        # self.axes.xlabel = 'Input signal'
        # self.axes.ylabel = 'Firing rate (Hz)'
        # self.axes.title = f'{obj_name}: Neuron response curves\n' \
        #                 f'(step {frame_current}, {ensemble["neuron_type"]["name"]})'
        self.axes.line_offset = -0.03
        for i in range(self.n_neurons):
            line: LineProperties = self.axes.lines.add()
            line.label = f'Neuron {i}'
            line.update = False
            line_source = line.source
            line_source: LineSourceProperties
            line_source.source_obj = self.object
            line_source.iterate_step = False
            line_source.fixed_step = frame_current  # todo do we need to calculate nengo.sample_step here?
            line_source.access_path = self.access_path  # 'neurons.response_curves'
            line_source.get_x = 'data[:, 0]'
            line_source.get_y = f'data[:, {i + 1}]'
        return self.execute(context)


classes = (
    PlotLineOperator,
    RemoveAxOperator,
    PlotByRowOperator,
    PlotByRowSimilarityOperator,
    PlotBy2dRowOperator,
    PlotBy2dColumnOperator,
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


# addon_keymaps = []


def register():
    register_factory()
    # wm = bpy.context.window_manager
    #
    # wm = bpy.context.window_manager
    # kc = wm.keyconfigs.addon
    # km = kc.keymaps.new(name="Nengo 3d", space_type='VIEW_3D', region_type='WINDOW')
    # kmi = km.keymap_items.new(NENGO_MT_context_menu.bl_idname, 'RIGHTMOUSE', 'PRESS')
    # km = wm.keyconfigs.active.keymaps['3D View']  # .new(name='3D View', space_type='VIEW_3D')
    # kmi = km.keymap_items.new(DrawVoltagesOperator.bl_idname, 'RIGHTMOUSE', 'PRESS')
    # addon_keymaps.append((km, kmi))


def unregister():
    unregister_factory()
    # wm = bpy.context.window_manager
    # for km, kmi in addon_keymaps:
    #     km.keymap_items.remove(kmi)
    # wm.keyconfigs.addon.keymaps.remove(km)
    # addon_keymaps.clear()
