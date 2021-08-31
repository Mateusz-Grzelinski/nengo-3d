import logging
import typing

import bpy

from bl_nengo_3d.bl_properties import AxesProperties, draw_axes_properties_template
from bl_nengo_3d.axes import Axes
from bl_nengo_3d.share_data import share_data


class PlotLineOperator(bpy.types.Operator):
    bl_idname = 'nengo_3d.plot_line'
    bl_label = 'Plot'

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
        context.window_manager.nengo_3d.requires_reset = True

        ax = Axes(context, self.axes)

        node: bpy.types.Object = context.active_object  # or for all selected_objects
        ax.root.parent = node
        ax.location = node.dimensions / 2

        share_data.register_chart(source=node.name, ax=ax)
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
        names = set()

        def get_child_names(obj):
            nonlocal names
            for child in obj.children:
                names.add(child.name)
                if child.children:
                    get_child_names(child)

        ax: AxesProperties = ax_obj.nengo_axes
        for source, axes in share_data.charts.items():
            to_remove = []
            for _ax in axes:
                if ax.object == _ax.root.name:
                    to_remove.append(_ax)
            for r in to_remove:
                axes.remove(r)

        # axes: Axes = share_data.charts[ax]
        get_child_names(ax_obj)
        for child in names:
            obj = bpy.data.objects[child]
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.objects.remove(ax_obj, do_unlink=True)
        # for line in ax_obj.nengo_axes.lines:
        #     line_obj = bpy.data.objects[line.name]
        #     bpy.data.objects.remove(line_obj, do_unlink=True)
        return {'FINISHED'}


classes = (
    PlotLineOperator,
    RemoveAxOperator,
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
