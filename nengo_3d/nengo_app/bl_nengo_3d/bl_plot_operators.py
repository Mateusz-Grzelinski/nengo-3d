import logging

import bpy

from bl_nengo_3d import schemas, charts
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


def neurons_probeable(self, context):
    item = None
    obj = context.active_object
    if share_data.model_graph and obj:
        if node := share_data.model_graph.nodes.get(obj.name):
            item = node['neuron_type']
    for param in item['probeable']:
        yield param, param, ''


class Sources(bpy.types.PropertyGroup):
    xindex: bpy.props.IntProperty(name='Source of x', min=0, max=2, default=0)
    yindex: bpy.props.IntProperty(name='Source of y', min=0, max=2, default=1)
    use_z: bpy.props.BoolProperty(default=False)
    zindex: bpy.props.IntProperty(name='Source of z', min=0, max=2, default=2)


locators = [
    (charts.LinearLocator.__name__, charts.LinearLocator.__name__, ''),
    (charts.IntegerLocator.__name__, charts.IntegerLocator.__name__, ''),
]


class PlotLineOperator(bpy.types.Operator):
    bl_idname = 'nengo_3d.plot_line'
    bl_label = 'Voltages'

    probe: bpy.props.EnumProperty(items=probeable, name='Probeable')
    probe_neurons: bpy.props.EnumProperty(items=neurons_probeable, name='Probeable neurons')
    neurons: bpy.props.BoolProperty(name='Is neuron', default=False)
    indices: bpy.props.CollectionProperty(type=Sources)
    xlabel: bpy.props.StringProperty(name='X label', default='X')
    ylabel: bpy.props.StringProperty(name='Y label', default='Y')
    zlabel: bpy.props.StringProperty(name='Z label', default='')
    title: bpy.props.StringProperty(name='Title', default='')
    xlocator: bpy.props.EnumProperty(items=locators)
    ylocator: bpy.props.EnumProperty(items=locators)
    zlocator: bpy.props.EnumProperty(items=locators)
    numticks: bpy.props.IntProperty(default=8)
    xformat: bpy.props.StringProperty(default='{:.2f}')
    yformat: bpy.props.StringProperty(default='{:.2f}')
    zformat: bpy.props.StringProperty(default='{:.2f}')

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

    def get_locator(self, name: str):
        if name == charts.LinearLocator.__name__:
            return charts.LinearLocator(numticks=self.numticks)
        if name == charts.IntegerLocator.__name__:
            return charts.IntegerLocator(numticks=self.numticks)
        return None

    def execute(self, context):
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
            share_data.resume_playback_on_steps = False
            share_data.step_when_ready = 0
        # register chart as input source: send info to probe model
        ax = Axes(context, parameter=self.probe_neurons if self.neurons else self.probe)
        ax.xlabel(self.xlabel)
        ax.ylabel(self.ylabel)
        ax.zlabel(self.zlabel)
        ax.xlocator = self.get_locator(self.xlocator)
        ax.ylocator = self.get_locator(self.ylocator)
        ax.zlocator = self.get_locator(self.zlocator)
        ax.xformat = self.xformat
        ax.yformat = self.yformat
        ax.zformat = self.zformat

        node: bpy.types.Object = context.active_object  # or for all selected_objects
        if self.title:
            ax.title(self.title)
        ax.location = node.location + node.dimensions / 2

        for sources in self.indices:
            line = ax.plot([0], [0])
            if sources.use_z:
                share_data.register_plot_line_source(line=line,
                                                     data_indices=(sources.xindex, sources.yindex, sources.zindex))
            else:
                share_data.register_plot_line_source(line=line, data_indices=(sources.xindex, sources.yindex))

        share_data.register_chart(source=node.name, is_neurons=self.neurons, ax=ax)

        s = schemas.Message()
        data_scheme = schemas.Observe()
        data = data_scheme.dump(
            obj={'source': node.name, 'parameter': ax.parameter,
                 'neurons': self.neurons})
        message = s.dumps({'schema': schemas.Observe.__name__, 'data': data})
        logging.debug(f'Sending: {message}')
        share_data.sendall(message.encode('utf-8'))
        ax.draw()
        # todo reset connection?
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
    Sources,
    PlotLineOperator,
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
