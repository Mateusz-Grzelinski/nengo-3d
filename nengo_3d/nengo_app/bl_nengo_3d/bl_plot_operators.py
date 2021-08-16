import logging

import bpy

from bl_nengo_3d import schemas, charts
from bl_nengo_3d.charts import Axes, locators
from bl_nengo_3d.share_data import share_data


def probeable_recurse_dict(prefix: str, value: dict):
    probeable = value.get('probeable') or []
    for param in probeable:
        yield prefix + '.probeable.' + param if prefix else 'probeable.' + param

    for k, v in value.items():
        if k.startswith('_'):
            continue
        elif isinstance(v, list):
            continue
        elif isinstance(v, tuple):
            continue
        elif isinstance(v, dict):
            yield from probeable_recurse_dict(prefix=prefix + '.' + k if prefix else k, value=v)
        yield prefix + '.' + k if prefix else k


def probeable(self, context):
    yield ':', '--Choose--', ''
    item = None
    obj = context.active_object
    if share_data.model_graph and obj:
        if node := share_data.model_graph.nodes.get(obj.name):
            item = node
        _, _, edge = share_data.model_get_edge_by_name(obj.name)
        if edge:
            item = edge
    else:
        return

    if item:
        for param in probeable_recurse_dict(None, item):
            yield param, param, ''

        if item.get('type') == 'Ensemble':
            yield 'neurons.response_curves', 'Response Curves', ''
            yield 'neurons.tuning_curves', 'Tuning Curves', ''


class Sources(bpy.types.PropertyGroup):
    xindex: bpy.props.IntProperty(name='Source of x', min=0, default=0)
    x_is_step: bpy.props.BoolProperty(default=False,
                                      description='Ignore value of xindex, instead use x as step indicator')
    yindex: bpy.props.IntProperty(name='Source of y', min=0, default=1)
    yindex_multi_dim: bpy.props.StringProperty()
    use_z: bpy.props.BoolProperty(default=False)
    zindex: bpy.props.IntProperty(name='Source of z', min=0, default=2)
    z_is_step: bpy.props.BoolProperty(default=False,
                                      description='Ignore value of zindex, instead use z as step indicator')
    label: bpy.props.StringProperty()


class PlotLineOperator(bpy.types.Operator):
    bl_idname = 'nengo_3d.plot_line'
    bl_label = 'Plot'

    probe: bpy.props.EnumProperty(items=probeable, name='Inspect value connected to node')
    probe_now: bpy.props.EnumProperty(items=[
        (':', '--Choose--', ''),
        ('neurons.response_curves', 'Response curves', ''),
        ('neurons.tuning_curves', 'Tuning curves', ''),
    ])

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
    line_offset: bpy.props.FloatProperty(default=0)

    def invoke(self, context, event):
        wm = context.window_manager
        self.probe = ':'
        self.probe_now = ':'
        self.indices.clear()
        self.indices.add()  # todo make this list dynamic
        # https://sinestesia.co/blog/tutorials/using-uilists-in-blender/
        return wm.invoke_props_dialog(self, width=500)

    def draw(self, context):
        properties = self
        layout = self.layout
        col = layout.column()
        col.prop(properties, 'probe', text='Observe')
        col.active = (properties.probe_now == ':')
        col = layout.column()
        col.prop(properties, 'probe_now', text='Draw now')
        col.active = (properties.probe == ':')
        col = layout.column()
        col.prop(properties, 'title')
        row = layout.row(align=True)
        row.prop(properties, 'xlabel', text='X')
        row.prop(properties, 'xlocator', text='')
        row.prop(properties, 'xformat', text='')
        row = layout.row(align=True)
        row.prop(properties, 'ylabel', text='Y')
        row.prop(properties, 'ylocator', text='')
        row.prop(properties, 'yformat', text='')
        row = layout.row(align=True)
        row.prop(properties, 'zlabel', text='Z')
        row.prop(properties, 'zlocator', text='')
        row.prop(properties, 'zformat', text='')
        # layout.prop(properties, 'line_offset')
        box = layout.box()
        # todo make this list dynamic
        for line in properties.indices:
            col = box.column()
            col.prop(line, 'label')
            line: Sources
            col.prop(line, 'xindex')
            col.prop(line, 'yindex')
            row = col.row()
            row.prop(line, 'use_z', text='')
            col = row.column(align=True)
            col.active = line.use_z
            col.prop(line, 'zindex')

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
        if self.probe_now == ':' and self.probe == ':':
            return {'CANCELLED'}
        if context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
            share_data.resume_playback_on_steps = False
            share_data.step_when_ready = 0

        if self.probe_now != ':':
            parameter = self.probe_now
        else:
            parameter = self.probe
        ax = Axes(context, parameter=parameter)
        ax.xlabel(self.xlabel)
        ax.ylabel(self.ylabel)
        ax.zlabel(self.zlabel)
        ax.xlocator = self.get_locator(self.xlocator)
        ax.ylocator = self.get_locator(self.ylocator)
        ax.zlocator = self.get_locator(self.zlocator)
        ax.xformat = self.xformat
        ax.yformat = self.yformat
        ax.zformat = self.zformat
        ax.line_offset = self.line_offset

        node: bpy.types.Object = context.active_object  # or for all selected_objects
        if self.title:
            ax.title(self.title)
        ax.location = node.location + node.dimensions / 2

        if self.probe_now != ':':
            share_data.register_chart(source=node.name, access_path=parameter, ax=ax)
            s = schemas.Message()
            data_scheme = schemas.PlotLines(context={'node': node, 'access_path': ax.parameter})
            data = data_scheme.dump(obj=ax)

            message = s.dumps({'schema': schemas.PlotLines.__name__, 'data': data})
            logging.debug(f'Sending: {message}')
            share_data.sendall(message.encode('utf-8'))
            return {'FINISHED'}

        for sources in self.indices:
            line = ax.plot([0], [0], label=sources.label)
            share_data.register_plot_line_source(
                line=line, xindex=sources.xindex, yindex=sources.yindex,
                zindex=sources.zindex if sources.use_z else None,
                yindex_multi_dim=sources.yindex_multi_dim,
                x_is_step=sources.x_is_step,
                z_is_step=sources.z_is_step if sources.use_z else False)

        share_data.register_chart(source=node.name, access_path=parameter, ax=ax)

        s = schemas.Message()
        data_scheme = schemas.Observe()
        data = data_scheme.dump(
            obj={'source': node.name, 'access_path': self.probe,
                 'sample_every': context.window_manager.nengo_3d.sample_every,
                 'dt': context.window_manager.nengo_3d.dt}
        )
        message = s.dumps({'schema': schemas.Observe.__name__, 'data': data})
        logging.debug(f'Sending: {message}')
        share_data.sendall(message.encode('utf-8'))
        ax.draw()
        return {'FINISHED'}


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
