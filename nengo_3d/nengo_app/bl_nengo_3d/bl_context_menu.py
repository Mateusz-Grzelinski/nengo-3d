import logging
import urllib.parse

import bpy

from bl_nengo_3d import schemas
from bl_nengo_3d.charts import Axes
from bl_nengo_3d.share_data import share_data


class DrawVoltagesOperator(bpy.types.Operator):
    bl_idname = 'nengo_3d.draw_voltages'
    bl_label = 'Voltages'

    # node: bpy.props.StringProperty(name='Node', description='Node to probe', default='')

    @classmethod
    def poll(cls, context):
        return True
        return share_data.model.get(context.active_object.name)  # is used in model

    def execute(self, context):
        # register chart as input source: send info to probe model
        ax = Axes(context, parameter='decoded_output')
        ax.xlabel('Step')
        ax.ylabel('Voltage')
        node: bpy.types.Object = context.active_object  # or selected_objects
        ax.location = node.location
        share_data.register_chart(obj=node, ax=ax)

        s = schemas.Message()
        data_scheme = schemas.Observe()
        # logging.debug(data_scheme.fields)
        # v = {'source': node.name, 'parameter': 'decoded_output'}
        # logging.debug(data_scheme.validate(v ))
        # logging.debug(v)
        data = data_scheme.dump(
            obj={'source': node.name, 'parameter': ax.parameter})  # todo what params are allowed?
        message = s.dumps({'schema': schemas.Observe.__name__, 'data': data})
        logging.debug(f'Sending: {message}')
        share_data.client.sendall(message.encode('utf-8'))
        ax.draw()
        return {'FINISHED'}


class NENGO_MT_context_menu(bpy.types.Menu):
    bl_label = "Node Context Menu"
    bl_idname = 'NENGO_MT_context_menu'

    def draw(self, context):
        layout = self.layout
        layout.operator(DrawVoltagesOperator.bl_idname)


classes = (
    DrawVoltagesOperator,
    NENGO_MT_context_menu,
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)

addon_keymaps = []


def register():
    register_factory()
    wm = bpy.context.window_manager

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    km = kc.keymaps.new(name="Nengo 3d", space_type='VIEW_3D', region_type='WINDOW')
    kmi = km.keymap_items.new(NENGO_MT_context_menu.bl_idname, 'RIGHTMOUSE', 'PRESS')
    # km = wm.keyconfigs.active.keymaps['3D View']  # .new(name='3D View', space_type='VIEW_3D')
    # kmi = km.keymap_items.new(DrawVoltagesOperator.bl_idname, 'RIGHTMOUSE', 'PRESS')
    addon_keymaps.append((km, kmi))


def unregister():
    unregister_factory()
    wm = bpy.context.window_manager
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()
