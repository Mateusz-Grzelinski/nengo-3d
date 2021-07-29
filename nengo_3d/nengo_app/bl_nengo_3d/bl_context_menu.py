import logging

import bpy

from bl_nengo_3d import schemas
from bl_nengo_3d.charts import Axes, IntegerLocator
from bl_nengo_3d.share_data import share_data


def probeable(self, context):
    item = None
    obj = context.active_object
    if share_data.model_graph and obj:
        if node := share_data.model_graph.nodes.get(obj.name):
            item = node
        _, _, edge = share_data.model_get_edge_by_name(obj.name)
        if edge:
            item = edge
    for param in item['probeable']:
        yield param, param, ''


class DrawVoltagesOperator(bpy.types.Operator):
    bl_idname = 'nengo_3d.draw_voltages'
    bl_label = 'Voltages'

    probe: bpy.props.EnumProperty(items=probeable, name='Parameter')
    dim: bpy.props.IntProperty(name='Dimentions', min=2, max=3)

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'probe')

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if share_data.model_graph and obj:
            if share_data.model_graph.nodes.get(obj.name):
                return True
            _, _, edge = share_data.model_get_edge_by_name(obj.name)
            if edge:
                return True
        return False

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
            share_data.resume_playback_on_steps = False
            share_data.step_when_ready = 0
        # register chart as input source: send info to probe model
        ax = Axes(context, parameter=self.probe)
        if self.dim == 2:
            if self.probe in {'decoded_output'}:
                ax.xlabel('X')
                ax.ylabel('Y')
                data_indices = 1, 2
            else:
                ax.xlabel('Step')
                ax.ylabel('Voltage')
                ax.xlocator = IntegerLocator(numticks=8)
                ax.xformat = '{:.0f}'
                data_indices = 0, 1
        else:
            ax.xlabel('X')
            ax.ylabel('Y')
            ax.zlabel('Step')
            ax.zlocator = IntegerLocator(numticks=8)
            ax.zformat = '{:.0f}'
            data_indices = 1, 2, 0
        node: bpy.types.Object = context.active_object  # or selected_objects
        ax.title(f'{node.name}:{self.probe}')
        ax.location = node.location + node.dimensions / 2

        share_data.register_chart(source=node, ax=ax, data_indices=data_indices)

        s = schemas.Message()
        data_scheme = schemas.Observe()
        data = data_scheme.dump(
            obj={'source': node.name, 'parameter': ax.parameter})  # todo what params are allowed?
        message = s.dumps({'schema': schemas.Observe.__name__, 'data': data})
        logging.debug(f'Sending: {message}')
        share_data.sendall(message.encode('utf-8'))
        ax.draw()
        return {'FINISHED'}


# class NENGO_MT_context_menu(bpy.types.Menu):
#     bl_label = "Node Context Menu"
#     bl_idname = 'NENGO_MT_context_menu'
#
#     def draw(self, context):
#         layout = self.layout
#         layout.active = context.active_object
#         layout.operator(DrawVoltagesOperator.bl_idname)


classes = (
    DrawVoltagesOperator,
    # NENGO_MT_context_menu,
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)

addon_keymaps = []


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
