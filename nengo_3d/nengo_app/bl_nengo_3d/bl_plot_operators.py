import logging

import bpy

from bl_nengo_3d import schemas, charts
from bl_nengo_3d.bl_properties import AxesProperties, draw_axes_properties_template, LineProperties, \
    LineSourceProperties
from bl_nengo_3d.bl_utils import probeable
from bl_nengo_3d.charts import Axes, locators
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

        ax = Axes(context, self.axes)

        node: bpy.types.Object = context.active_object  # or for all selected_objects
        ax.location = node.location + node.dimensions / 2

        share_data.register_chart(source=node.name, ax=ax)
        # observe = set()
        # plot = set()
        # for line in self.axes.lines:
        #     line: LineProperties
        #     line_source: LineSourceProperties = line.source
        #     mess_schema = schemas.Message()
        #     if line_source.iterate_step:
        #         observe.add((line_source.source_obj, line_source.access_path))
        #     else:
        #         plot.add((line_source.source_obj, line_source.access_path, line_source.fixed_step))
        # for i in observe:
        #     data_scheme = schemas.Observe()
        #     data = {'source': i[0],
        #             'access_path': i[1],
        #             'sample_every': context.window_manager.nengo_3d.sample_every,
        #             'dt': context.window_manager.nengo_3d.dt}
        #     message = mess_schema.dumps({'schema': schemas.Observe.__name__, 'data': data_scheme.dump(obj=data)})
        #     logging.debug(f'Sending: {message}')
        #     share_data.sendall(message.encode('utf-8'))
        # for i in plot:
        #     data_scheme = schemas.PlotLines(context={
        #         'source_obj_name': i[0],
        #         'access_path': i[1],
        #         'step': i[2],
        #     })
        #     data = data_scheme.dump(obj=ax)
        #     message = mess_schema.dumps({'schema': schemas.PlotLines.__name__, 'data': data})
        #     logging.debug(f'Sending: {message}')
        #     share_data.sendall(message.encode('utf-8'))
        ax.draw()
        return {'FINISHED'}


classes = (
    PlotLineOperator,
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
