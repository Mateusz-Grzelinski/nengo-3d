import logging

import bpy

from bl_nengo_3d import schemas
from bl_nengo_3d.charts import Axes, IntegerLocator
from bl_nengo_3d.share_data import share_data


def probeable(self, context):
    for param in share_data.model_graph.nodes[context.active_object.name]['probeable']:
        yield param, param, ''


class DrawVoltagesOperator(bpy.types.Operator):
    bl_idname = 'nengo_3d.draw_voltages'
    bl_label = 'Voltages'

    probe: bpy.props.EnumProperty(items=probeable, name='Parameter')

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'probe')

    @classmethod
    def poll(cls, context):
        return share_data.model_graph and context.active_object and share_data.model_graph.nodes.get(
            context.active_object.name)

    def execute(self, context):
        # register chart as input source: send info to probe model
        logging.debug(self.probe)
        ax = Axes(context, parameter=self.probe)
        ax.xlabel('Step')
        ax.ylabel('Voltage')
        node: bpy.types.Object = context.active_object  # or selected_objects
        ax.title(f'{node.name}:{self.probe}')
        ax.location = node.location + node.dimensions / 2
        ax.xlocator = IntegerLocator(numticks=8)
        ax.xformat = '{:.0f}'

        share_data.register_chart(obj=node, ax=ax)

        s = schemas.Message()
        data_scheme = schemas.Observe()
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
        layout.active = context.active_object
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
