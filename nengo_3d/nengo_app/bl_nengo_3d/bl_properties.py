import functools
import logging
import math

import bpy

from bl_nengo_3d import bl_nengo_primitives, axes
from bl_nengo_3d.axes import locators
from bl_nengo_3d.utils import get_from_path, recurse_dict
from bl_nengo_3d.bl_utils import probeable_nodes_items, probeable, probeable_edges_items


class ColorGeneratorProperties(bpy.types.PropertyGroup):
    initial_color: bpy.props.FloatVectorProperty(name='Initial color', subtype='COLOR',
                                                 default=[0.100000, 1.000000, 0.217877]
                                                 # [0.021821, 1.000000, 0.149937]
                                                 )
    shift: bpy.props.EnumProperty(name='Shift type', items=[
        ('H', 'Shift hue', ''),
        ('S', 'Shift saturation', ''),
        ('V', 'Shift value', ''),
    ])
    max_colors: bpy.props.IntProperty(name='Max number of different colors', min=1, default=8)


def draw_color_generator_properties_template(layout: bpy.types.UILayout, color_gen: ColorGeneratorProperties):
    layout.prop(color_gen, 'initial_color')
    layout.prop(color_gen, 'shift', text='')
    layout.prop(color_gen, 'max_colors', text='')


# class NodeColorSourceProperties(bpy.types.PropertyGroup):
#     # source_obj: bpy.props.StringProperty()
#     access_path: bpy.props.EnumProperty(items=probeable)  # todo filter probeable by source_obj
#     get: bpy.props.StringProperty(default='data')
#
#
# def draw_color_source_properties_template(layout: bpy.types.UILayout, color_source: NodeColorSourceProperties):
#     row = layout.row(align=True)
#     # row.prop(color_source, 'source_obj')
#     row.prop(color_source, 'access_path', text='')
#     layout.label(text='data: np.array = data[step]')
#     layout.prop(color_source, 'get')


# step based
class LineSourceProperties(bpy.types.PropertyGroup):
    # .name is line object name
    source_obj: bpy.props.StringProperty(name='Source', description='Source element from model')  # make enum?
    access_path: bpy.props.EnumProperty(items=probeable)
    # introduce special variables for step, tstep (trange)?
    iterate_step: bpy.props.BoolProperty(name='Iterate last n steps')
    fixed_step: bpy.props.IntProperty()
    # todo validate and report errors:
    get_x: bpy.props.StringProperty(default='')
    get_y: bpy.props.StringProperty(default='')
    get_z: bpy.props.StringProperty(default='')


def draw_line_source_properties_template(layout: bpy.types.UILayout, line_source: LineSourceProperties):
    row = layout.row(align=True)
    row.prop(line_source, 'source_obj')
    row.prop(line_source, 'access_path', text='')
    row = layout.row(align=True)
    row.prop(line_source, 'iterate_step')
    if not line_source.iterate_step:
        row.prop(line_source, 'fixed_step')
    col = layout.column(align=True)
    if line_source.iterate_step:
        col.label(text='for step, row in zip(steps, data):')
        col.label(text='    step: int, row: np.array')
        col.prop(line_source, 'get_x', text='    Get X')
        col.prop(line_source, 'get_y', text='    Get Y')
        col.prop(line_source, 'get_z', text='    Get Z')
    else:
        col.label(text=f'data: np.array = data[{line_source.fixed_step}]')
        col.prop(line_source, 'get_x', text='Get X')
        col.prop(line_source, 'get_y', text='Get Y')
        col.prop(line_source, 'get_z', text='Get Z')


class LineProperties(bpy.types.PropertyGroup):
    # .name is object name
    axes_obj: bpy.props.StringProperty()
    update: bpy.props.BoolProperty(default=True)
    label: bpy.props.StringProperty()
    ui_show_source: bpy.props.BoolProperty()
    source: bpy.props.PointerProperty(type=LineSourceProperties)


def draw_line_properties_template(layout: bpy.types.UILayout, line: 'LineProperties'):
    obj = bpy.data.objects[line.name]
    row = layout.row(align=True)
    subrow = row.row(align=True)
    subrow.prop(line, 'ui_show_source', text='', icon='TRIA_DOWN' if line.ui_show_source else 'TRIA_RIGHT',
                emboss=False)
    subrow.prop(line, 'update', text='', icon='ORIENTATION_VIEW', icon_only=True)
    subrow = row.row(align=True)
    subrow.active = line.update
    subrow.prop(line, 'label', text='')
    subrow.prop(obj.nengo_attributes, 'color', text='')
    subrow = row.row(align=True)
    subrow.prop(obj, 'hide_viewport', text='', icon_only=True, emboss=False)
    subrow.prop(obj, 'hide_render', text='', icon_only=True, emboss=False)
    if line.ui_show_source:
        col = layout.column()
        col.active = line.update
        draw_line_source_properties_template(col, line.source)


def line_offset_update(self: 'AxesProperties', context):
    ax_obj = bpy.data.objects.get(self.object)
    if not ax_obj:
        return
    i = 0
    for line in ax_obj.nengo_axes.lines:
        line_obj = bpy.data.objects[line.name]
        line_obj.location.z = ax_obj.nengo_axes.line_offset * i
        i += 1
        line_obj.update_tag()
    draw_legend_enum_update(self, context)


def draw_legend_enum_update(self: 'AxesProperties', context):
    from bl_nengo_3d.share_data import share_data
    legend_collection = bpy.data.collections.get(self.legend_collection_name)
    if not legend_collection:
        return
    if self.draw_legend == 'NONE':
        legend_collection.hide_viewport = True
        legend_collection.hide_render = True
    elif self.draw_legend == 'CLASSIC':
        legend_collection.hide_render = False
        legend_collection.hide_viewport = False
        ax = share_data.get_registered_chart(self)
        plot_obj = bpy.data.objects[ax.plot_name]

        for i, line_prop in enumerate(self.lines):
            line_prop: LineProperties
            line_obj = bpy.data.objects[line_prop.name]
            legend_prop: LegendProperties = self.legend_collection.get(line_prop.name)
            if not legend_prop:
                legend_prop = self.legend_collection.add()
                legend_prop.name = line_prop.name

            legend_box = legend_collection.objects.get(legend_prop.box_object)
            if not legend_box:
                legend_box = bl_nengo_primitives.get_primitive('Legend box')
                legend_box.active_material = axes.get_primitive_material()
                # obj.nengo_attributes.color = next(self.color_gen)
                legend_box.parent = plot_obj
                legend_prop.box_object = legend_box.name
                legend_collection.objects.link(legend_box)
                legend_box.nengo_attributes.color = line_obj.nengo_attributes.color
                legend_box.location = (1.3, i * legend_box.dimensions.y + i * 0.03, 0)
            else:
                legend_box.hide_viewport = line_obj.hide_viewport
                legend_box.hide_render = line_obj.hide_render

            legend_text = legend_collection.objects.get(legend_prop.text_object)
            if not legend_text:
                legend_text = ax._create_text('Legend text', parent=plot_obj, collection=legend_collection,
                                              selectable=True)
                legend_prop.text_object = legend_text.name
                legend_text_data = legend_text.data
                legend_text_data.body = line_prop.label
                legend_text_data.size = 0.08
                legend_text_data.body = line_prop.label
            legend_text.location = (legend_box.location.x + legend_box.dimensions.x / 2 + 0.05,
                                    legend_box.location.y,
                                    0)
            legend_text.hide_viewport = line_obj.hide_viewport
            legend_text.hide_render = line_obj.hide_render
        return
    elif self.draw_legend == 'DYNAMIC':
        legend_collection.hide_render = False
        legend_collection.hide_viewport = False
        ax = share_data.get_registered_chart(self)
        plot_obj = bpy.data.objects[ax.plot_name]

        for line_prop in self.lines:
            line_prop: LineProperties
            line_obj = bpy.data.objects[line_prop.name]
            legend_prop: LegendProperties = self.legend_collection.get(line_prop.name)
            if not legend_prop:
                legend_prop = self.legend_collection.add()
                legend_prop.name = line_prop.name

            legend_text = legend_collection.objects.get(legend_prop.text_object)
            if not legend_text:
                legend_text = ax._create_text('Legend text', parent=plot_obj, collection=legend_collection,
                                              selectable=True)
                legend_text_data = legend_text.data
                legend_text_data.body = line_prop.label
                legend_text_data.size = 0.08
                legend_prop.text_object = legend_text.name
            legend_text.hide_viewport = line_obj.hide_viewport
            legend_text.hide_render = line_obj.hide_render

            legend_box = legend_collection.objects.get(legend_prop.box_object)
            if legend_box:
                legend_box.hide_viewport = line_obj.hide_viewport
                legend_box.hide_render = line_obj.hide_render

            if len(line_obj.data.vertices) != 0:
                vert_co = line_obj.data.vertices[-1].co
                legend_text.location = (vert_co.x + 0.1, vert_co.y, line_obj.location.z)
            else:
                legend_text.location = (1.1, 0, line_obj.location.z)
    else:
        assert False


class LegendProperties(bpy.types.PropertyGroup):
    text_object: bpy.props.StringProperty()
    box_object: bpy.props.StringProperty()


class AxesProperties(bpy.types.PropertyGroup):
    object: bpy.props.StringProperty()
    model_source: bpy.props.StringProperty()
    collection: bpy.props.StringProperty()
    treat_as_node: bpy.props.BoolProperty(description='Treat axes as part of graph')
    auto_range: bpy.props.BoolProperty(default=True)
    x_min: bpy.props.FloatProperty(default=0)
    x_max: bpy.props.FloatProperty(default=1)
    y_min: bpy.props.FloatProperty(default=0)
    y_max: bpy.props.FloatProperty(default=1)
    z_min: bpy.props.FloatProperty(default=0)
    z_max: bpy.props.FloatProperty(default=1)

    title_obj_name: bpy.props.StringProperty()
    title: bpy.props.StringProperty(name='Title', default='')  # update=

    xticks_obj_name: bpy.props.StringProperty()
    yticks_obj_name: bpy.props.StringProperty()
    zticks_obj_name: bpy.props.StringProperty()

    xticks_collection_name: bpy.props.StringProperty()
    yticks_collection_name: bpy.props.StringProperty()
    zticks_collection_name: bpy.props.StringProperty()

    xnumticks: bpy.props.IntProperty(name='X ticks', default=6)  # update=
    ynumticks: bpy.props.IntProperty(name='Y ticks', default=6)  # update=
    znumticks: bpy.props.IntProperty(name='Z ticks', default=6)  # update=

    xlabel_obj_name: bpy.props.StringProperty()
    ylabel_obj_name: bpy.props.StringProperty()
    zlabel_obj_name: bpy.props.StringProperty()

    xlabel: bpy.props.StringProperty(name='X label', default='X')  # update=
    ylabel: bpy.props.StringProperty(name='Y label', default='Y')  # update=
    zlabel: bpy.props.StringProperty(name='Z label', default='')  # update=

    xlocator: bpy.props.EnumProperty(items=locators)  # update=
    ylocator: bpy.props.EnumProperty(items=locators)  # update=
    zlocator: bpy.props.EnumProperty(items=locators)  # update=

    xformat: bpy.props.StringProperty(default='{:.2f}')  # update=
    yformat: bpy.props.StringProperty(default='{:.2f}')  # update=
    zformat: bpy.props.StringProperty(default='{:.2f}')  # update=

    color_gen: bpy.props.PointerProperty(type=ColorGeneratorProperties)

    ui_show_lines: bpy.props.BoolProperty(default=False)
    lines_collection_name: bpy.props.StringProperty()
    lines: bpy.props.CollectionProperty(type=LineProperties)
    line_offset: bpy.props.FloatProperty(name='Line offset', update=line_offset_update, step=1)

    legend_collection_name: bpy.props.StringProperty()
    legend_collection: bpy.props.CollectionProperty(type=LegendProperties)
    draw_legend: bpy.props.EnumProperty(name='Legend', items=[
        ('NONE', 'No legend', ''),
        ('CLASSIC', 'Colored box with text', ''),
        ('DYNAMIC', 'Text at the end of the line', '')],
                                        update=draw_legend_enum_update,
                                        )


def draw_axes_properties_template(layout: bpy.types.UILayout, axes: 'AxesProperties'):
    col = layout.column()
    col.enabled = False  # not supported
    col.prop(axes, 'title')
    row = col.row(align=True)
    row.prop(axes, 'xlabel', text='X')
    row.prop(axes, 'xlocator', text='')
    row.prop(axes, 'xformat', text='')
    row.prop(axes, 'xnumticks')
    row = col.row(align=True)
    row.prop(axes, 'ylabel', text='Y')
    row.prop(axes, 'ylocator', text='')
    row.prop(axes, 'yformat', text='')
    row.prop(axes, 'ynumticks')
    row = col.row(align=True)
    row.prop(axes, 'zlabel', text='Z')
    row.prop(axes, 'zlocator', text='')
    row.prop(axes, 'zformat', text='')
    row.prop(axes, 'znumticks')

    layout.prop(axes, 'auto_range')
    col = layout.column(align=True)
    col.enabled = not axes.auto_range
    row = col.row(align=True)
    row.prop(axes, 'x_min', emboss=col.enabled)
    row.prop(axes, 'x_max', emboss=col.enabled)
    row = col.row(align=True)
    row.prop(axes, 'y_min', emboss=col.enabled)
    row.prop(axes, 'y_max', emboss=col.enabled)
    row = col.row(align=True)
    row.prop(axes, 'z_min', emboss=col.enabled)
    row.prop(axes, 'z_max', emboss=col.enabled)

    from bl_nengo_3d.bl_operators import NengoColorLinesOperator, HideAllOperator
    from bl_nengo_3d.bl_plot_operators import EnableAllLinesOperator

    row = layout.row()
    row.prop(axes, 'draw_legend')
    legend_collection = bpy.data.collections.get(axes.legend_collection_name)
    row.prop(legend_collection, 'hide_select', icon_only=True, emboss=False)

    row = layout.row()
    row.prop(axes, 'ui_show_lines', text='', icon='TRIA_DOWN' if axes.ui_show_lines else 'TRIA_RIGHT',
             emboss=False)
    row.label(text=f'Lines ({len(axes.lines)}):')
    row.prop(axes, 'line_offset')
    lines_collection = bpy.data.collections.get(axes.lines_collection_name)
    row.prop(lines_collection, 'hide_select', icon_only=True, emboss=False)
    if axes.ui_show_lines:
        row = layout.row(align=True)
        op = row.operator(EnableAllLinesOperator.bl_idname, text='Enable update')
        op.root = axes.object
        op.enable = True
        op = row.operator(EnableAllLinesOperator.bl_idname, text='Disable update')
        op.root = axes.object
        op.enable = False
        row = layout.row(align=True)
        op = row.operator(HideAllOperator.bl_idname, text='Show all')
        op.collection = axes.lines_collection_name
        op.hide = False
        op = row.operator(HideAllOperator.bl_idname, text='Hide all')
        op.collection = axes.lines_collection_name
        op.hide = True
        row = layout.row(align=True)
        draw_color_generator_properties_template(row, axes.color_gen)
        op = row.operator(NengoColorLinesOperator.bl_idname, icon='FILE_REFRESH', text='')
        op.axes_obj = axes.object
        box = layout.box()
        for line in axes.lines:
            line: LineProperties
            draw_line_properties_template(box, line)


def node_color_update(self: 'NodeMappedColor', context):
    from bl_nengo_3d.share_data import share_data
    nengo_3d: Nengo3dProperties = context.scene.nengo_3d
    if nengo_3d.node_color == 'MODEL':
        access_path, attr_type = nengo_3d.node_attribute_with_type.split(':')
        access_path = access_path.split('.')
        for node, node_data in share_data.model_graph_view.nodes(data=True):
            node_data = share_data.model_graph.get_node_or_subnet_data(node)
            value = get_from_path(node_data, access_path)
            mapped_color = nengo_3d.node_mapped_colors.get(str(value))
            if not mapped_color:
                continue  # update only selected nodes
            obj = bpy.data.objects[node_data['_blender_object_name']]
            assert mapped_color, (node, str(value), list(nengo_3d.node_mapped_colors.keys()))
            obj.nengo_attributes.color = mapped_color.color
            obj.update_tag()
    elif nengo_3d.node_color == 'MODEL_DYNAMIC':
        # it is done in frame change to avoid infinite recursion
        from bl_nengo_3d.frame_change_handler import recolor_dynamic_node_attributes
        # todo not supported for now
        # recursive call!!!!
        # recolor_dynamic_node_attributes(nengo_3d, int(context.scene.frame_current / nengo_3d.sample_every))
        # access_path = nengo_3d.node_dynamic_access_path
        # for node, node_data in share_data.model_graph_view.nodes(data=True):
        #     node_data = share_data.model_graph.get_node_or_subnet_data(node)
        #     data = share_data.simulation_cache.get((node, access_path))
        #     if not data:
        #         continue
        #     obj = bpy.data.objects[node_data['_blender_object_name']]
        #     value = data[int(context.scene.frame_current / nengo_3d.sample_every)]
        #     mapped_color = nengo_3d.node_mapped_colors.get(str(value))
    else:
        assert False


class NodeMappedColor(bpy.types.PropertyGroup):
    color: bpy.props.FloatVectorProperty(subtype='COLOR', default=[1.0, 1.0, 1.0], update=node_color_update)


class Nengo3dShowNetwork(bpy.types.PropertyGroup):
    network: bpy.props.StringProperty(name='Network')
    expand: bpy.props.BoolProperty(default=False)
    # draw_bounded: bpy.props.BoolProperty(default=True)


def select_edges_update(self: 'Nengo3dProperties', context):
    col = bpy.data.collections['Edges']
    col.hide_select = not self.select_edges
    # from bl_nengo_3d.share_data import share_data
    # if share_data.model_graph is None:
    #     return
    # for e_s, e_dst, e_data in share_data.model_graph_view.edges(data=True):
    #     obj = bpy.data.objects[e_data.get('_blender_object_name')]
    #     if not obj:
    #         continue
    #     obj.hide_select = not self.select_edges
    # for e_s, e_dst, e_data in share_data.model_graph.edges(data=True):
    #     obj = bpy.data.objects[e_data.get('_blender_object_name')]
    #     if not obj:
    #         continue
    #     obj.hide_select = not self.select_edges


def recalculate_edges(self: 'Nengo3dProperties', context):
    from bl_nengo_3d.share_data import share_data
    if share_data.model_graph_view is None:
        return
    from bl_nengo_3d.connection_handler import regenerate_edges

    pos = {}
    for node in share_data.model_graph_view:
        data = share_data.model_graph.get_node_or_subnet_data(node)
        pos[node] = bpy.data.objects[data['_blender_object_name']].location

    regenerate_edges(
        g=share_data.model_graph,
        g_view=share_data.model_graph_view,
        nengo_3d=context.scene.nengo_3d,
        pos=pos)
    return


def regenerate_network(context: bpy.types.Context, nengo_3d: 'Nengo3dProperties', recalculate_locations: bool = False):
    from bl_nengo_3d.share_data import share_data
    from bl_nengo_3d.connection_handler import handle_network_model
    from bl_nengo_3d.bl_operators import NengoColorNodesOperator, NengoColorEdgesOperator
    for node in share_data.model_graph_view.nodes:
        node_data = share_data.model_graph.get_node_or_subnet_data(node)
        obj = bpy.data.objects[node_data['_blender_object_name']]
        obj.hide_viewport = True
        obj.hide_render = True
    for e_s, e_v, key, e_data in share_data.model_graph_view.edges(data=True, keys=True):
        e_data = share_data.model_graph.edges[e_data['pre'], e_data['post'], key]
        obj = bpy.data.objects[e_data['_blender_object_name']]
        obj.hide_viewport = True
        obj.hide_render = True
    share_data.model_graph_view = share_data.model_graph.get_graph_view(nengo_3d)
    # logging.debug(share_data.model_graph_view.nodes(data=False))
    # logging.debug(share_data.model_graph_view.nodes['model.cortical'])
    handle_network_model(g=share_data.model_graph, g_view=share_data.model_graph_view,
                         nengo_3d=nengo_3d, select=True,
                         force_refresh_node_placement=recalculate_locations)
    NengoColorNodesOperator.recolor(nengo_3d, context.scene.frame_current)
    NengoColorEdgesOperator.recolor(nengo_3d, context.scene.frame_current)


def force_one_connection_per_edge_update(self: 'Nengo3dProperties', context: bpy.types.Context):
    regenerate_network(context=context, nengo_3d=self, recalculate_locations=False)


def draw_labels_update(self: 'Nengo3dProperties', context):
    from bl_nengo_3d.share_data import share_data
    if share_data.model_graph_view is None:
        return
    from bl_nengo_3d.connection_handler import regenerate_labels

    regenerate_labels(
        g=share_data.model_graph,
        g_view=share_data.model_graph_view,
        nengo_3d=context.scene.nengo_3d
    )
    return


def sample_every_update(self: 'Nengo3dProperties', context):
    from bl_nengo_3d.share_data import share_data
    if share_data.model_graph is not None:
        self.requires_reset = True


def requires_reset_update(self: 'Nengo3dProperties', context):
    if self.requires_reset is True:
        context.scene.is_simulation_playing = False


#### start nodes functions ####

_node_anti_crash = None
_node_attribute_with_types_cache = None


def node_attribute_with_types_items(self, context):
    from bl_nengo_3d.share_data import share_data
    global _node_anti_crash, _node_attribute_with_types_cache
    g = share_data.model_graph_view
    if not g:
        return [(':', '--no data--', '')]
    if _node_attribute_with_types_cache == g and _node_anti_crash:
        return _node_anti_crash
    else:
        _node_attribute_with_types_cache = g
    used = {}
    for node, data in g.nodes(data=True):
        data = share_data.model_graph.get_node_or_subnet_data(node)
        for k, v in data.items():
            if k.startswith('_'):
                continue
            if used.get(k):
                if used[k] is None:
                    used[k] = v
                continue
            elif isinstance(v, list):
                continue
            elif isinstance(v, tuple):
                continue
            elif isinstance(v, dict):
                for i, _v in recurse_dict(prefix=k, value=v):
                    if used.get(i):
                        if used[i] is None:
                            used[i] = _v
                        continue
                    used[i] = _v
            elif v is None:
                continue
            else:
                used[k] = v
    _node_anti_crash = [(':', '--Choose an attribute--', '')]
    for k, v in sorted(used.items()):
        _node_anti_crash.append((f'{k}:{type(v).__name__}', f'{k}: {type(v).__name__}', f''))
    return _node_anti_crash


def node_attribute_with_types_update(self: 'Nengo3dProperties', context):
    from bl_nengo_3d.share_data import share_data
    from bl_nengo_3d import colors
    nengo_3d: Nengo3dProperties = self
    if nengo_3d.node_attribute_with_type == ':' or not nengo_3d.node_attribute_with_type:
        return
    access_path, attr_type = nengo_3d.node_attribute_with_type.split(':')
    nengo_3d.node_mapped_colors.clear()
    access_path = access_path.split('.')
    color_gen = colors.cycle_color(nengo_3d.node_color_gen.initial_color,
                                   shift_type=nengo_3d.node_color_gen.shift,
                                   max_colors=nengo_3d.node_color_gen.max_colors)
    is_numerical = attr_type.strip().lower() in {'int', 'float'}
    minimum, maximum = math.inf, -math.inf
    for node, data in share_data.model_graph_view.nodes(data=True):
        data = share_data.model_graph.get_node_or_subnet_data(node)
        value = get_from_path(data, access_path)
        mapped_color = nengo_3d.node_mapped_colors.get(str(value))
        if not mapped_color:
            mapped_color: NodeMappedColor = nengo_3d.node_mapped_colors.add()
            mapped_color.name = str(value)
            mapped_color.color = next(color_gen)
        if is_numerical and value is not None:
            if minimum > value:
                minimum = value
            if maximum < value:
                maximum = value

    if is_numerical:
        if minimum == maximum:
            minimum -= 1
            maximum += 1
        if minimum == math.inf:
            minimum = 0
        if maximum == -math.inf:
            maximum = 1
        assert minimum not in {math.inf, -math.inf}
        assert maximum not in {math.inf, -math.inf}
        if nengo_3d.node_attr_auto_range:
            nengo_3d.node_attr_min = minimum
            nengo_3d.node_attr_max = maximum

        for node, data in share_data.model_graph_view.nodes(data=True):
            data = share_data.model_graph.get_node_or_subnet_data(node)
            value = get_from_path(data, access_path)
            obj = bpy.data.objects[data['_blender_object_name']]
            if value is None:
                obj.nengo_attributes.weight = 0
            else:
                # must be normalized for color ramp to work
                obj.nengo_attributes.weight = (float(value) - nengo_3d.node_attr_min) / (
                        nengo_3d.node_attr_max - nengo_3d.node_attr_min)
                # logging.debug((node, value, obj.nengo_attributes.weight))
                if obj.nengo_attributes.weight > 1:
                    obj.nengo_attributes.weight = 1
                elif obj.nengo_attributes.weight < 0:
                    obj.nengo_attributes.weight = 0
                assert 1 >= obj.nengo_attributes.weight >= 0, (
                    node, obj.nengo_attributes.weight, minimum, maximum, value)

    if nengo_3d.node_color_gen.max_colors != len(nengo_3d.node_mapped_colors) + 1:
        nengo_3d.node_color_gen.max_colors = len(nengo_3d.node_mapped_colors) + 1
        color_gen = colors.cycle_color(nengo_3d.node_color_gen.initial_color,
                                       shift_type=nengo_3d.node_color_gen.shift,
                                       max_colors=nengo_3d.node_color_gen.max_colors)

        if is_numerical:
            key = lambda mapped_color: float(
                mapped_color.name) if mapped_color.name is not None and mapped_color.name not in {'None', ''} else 0
        else:
            key = lambda mapped_color: mapped_color.name
        for mapped_color in sorted(nengo_3d.node_mapped_colors, key=key):
            mapped_color: NodeMappedColor
            mapped_color.color = next(color_gen)

    # force particular representation where it does not make sense to have different
    if nengo_3d.node_attribute_with_type.endswith(':str'):
        nengo_3d.node_color_map = 'ENUM'
    elif nengo_3d.node_attribute_with_type.endswith(':float'):
        nengo_3d.node_color_map = 'GRADIENT'


def color_map_node_update(self: 'Nengo3dProperties', context):
    material = bpy.data.materials.get('NengoNodeMaterial')
    if not material:
        return
    mix = material.node_tree.nodes['Mix']
    if self.node_color_map == 'ENUM':
        mix.inputs[0].default_value = 1.0
    elif self.node_color_map == 'GRADIENT':
        mix.inputs[0].default_value = 0.0
    else:
        logging.error(f'Unknown value: {self.node_color_map}')


def node_color_single_update(self: 'Nengo3dProperties', context):
    from bl_nengo_3d.share_data import share_data
    for node in share_data.model_graph_view.nodes:
        data = share_data.model_graph.get_node_or_subnet_data(node)
        obj = bpy.data.objects[data['_blender_object_name']]
        obj.nengo_attributes.color = self.node_color_single
        obj.update_tag()


_last_node_dynamic_access_path = None


def node_dynamic_access_path_update(self: 'Nengo3dProperties', context):
    global _last_node_dynamic_access_path
    if _last_node_dynamic_access_path != self.node_dynamic_access_path:
        self.requires_reset = True
    _last_node_dynamic_access_path = self.node_dynamic_access_path


def node_enum_color_update(self: 'Nengo3dProperties', context):
    if self.node_color == 'SINGLE':
        self.node_color_map = 'ENUM'
        node_color_single_update(self, context)


#### end nodes functions ####

#### start edges functions ####

_last_edge_dynamic_access_path = None


def edge_color_update(self: 'NodeMappedColor', context):
    from bl_nengo_3d.share_data import share_data
    nengo_3d: Nengo3dProperties = context.scene.nengo_3d
    if nengo_3d.edge_color == 'MODEL':
        access_path, attr_type = nengo_3d.edge_attribute_with_type.split(':')
        access_path = access_path.split('.')
        for e_source, e_target, key, e_data in share_data.model_graph_view.edges(data=True, keys=True):
            e_data = share_data.model_graph.edges[e_data['pre'], e_data['post'], key]
            obj = bpy.data.objects[e_data['_blender_object_name']]
            value = get_from_path(e_data, access_path)
            mapped_color = nengo_3d.edge_mapped_colors.get(str(value))
            if not mapped_color:
                continue  # update only selected nodes
            assert mapped_color, (e_data['name'], str(value), list(nengo_3d.edge_mapped_colors.keys()))
            obj.nengo_attributes.color = mapped_color.color
            obj.update_tag()
    elif nengo_3d.edge_color == 'MODEL_DYNAMIC':
        from bl_nengo_3d.frame_change_handler import recolor_dynamic_edge_attributes
        # todo not supported for now
        # recursive call!!!!
    else:
        assert False


class EdgeMappedColor(bpy.types.PropertyGroup):
    color: bpy.props.FloatVectorProperty(subtype='COLOR', default=[1.0, 1.0, 1.0], update=edge_color_update)


def edge_attribute_with_types_update(self: 'Nengo3dProperties', context):
    from bl_nengo_3d.share_data import share_data
    from bl_nengo_3d import colors
    nengo_3d: Nengo3dProperties = self
    if nengo_3d.edge_attribute_with_type == ':' or not nengo_3d.edge_attribute_with_type:
        return
    access_path, attr_type = nengo_3d.edge_attribute_with_type.split(':')
    nengo_3d.edge_mapped_colors.clear()
    access_path = access_path.split('.')
    color_gen = colors.cycle_color(nengo_3d.edge_color_gen.initial_color,
                                   shift_type=nengo_3d.edge_color_gen.shift,
                                   max_colors=nengo_3d.edge_color_gen.max_colors)
    is_numerical = attr_type.strip().lower() in {'int', 'float'}
    minimum, maximum = math.inf, -math.inf
    for e_source, e_target, key, e_data in share_data.model_graph_view.edges(data=True, keys=True):
        e_data = share_data.model_graph.edges[e_data['pre'], e_data['post'], key]
        value = get_from_path(e_data, access_path)
        mapped_color = nengo_3d.edge_mapped_colors.get(str(value))
        if not mapped_color:
            mapped_color: NodeMappedColor = nengo_3d.edge_mapped_colors.add()
            mapped_color.name = str(value)
            mapped_color.color = next(color_gen)
        if is_numerical and value is not None:
            if minimum > value:
                minimum = value
            if maximum < value:
                maximum = value

    if is_numerical:
        if minimum == maximum:
            minimum -= 1
            maximum += 1
        if minimum == math.inf:
            minimum = 0
        if maximum == -math.inf:
            maximum = 1
        assert minimum not in {math.inf, -math.inf}
        assert maximum not in {math.inf, -math.inf}
        if nengo_3d.edge_attr_auto_range:
            nengo_3d.edge_attr_min = minimum
            nengo_3d.edge_attr_max = maximum

        for e_source, e_target, key, e_data in share_data.model_graph_view.edges(data=True, keys=True):
            e_data = share_data.model_graph.edges[e_data['pre'], e_data['post'], key]
            obj = bpy.data.objects[e_data['_blender_object_name']]
            value = get_from_path(e_data, access_path)
            if value is None:
                obj.nengo_attributes.weight = 0
            else:
                # must be normalized for color ramp to work
                obj.nengo_attributes.weight = (float(value) - nengo_3d.edge_attr_min) / (
                        nengo_3d.edge_attr_max - nengo_3d.edge_attr_min)
                # logging.debug((e_source, e_target, value, obj.nengo_attributes.weight))
                if obj.nengo_attributes.weight > 1:
                    obj.nengo_attributes.weight = 1
                elif obj.nengo_attributes.weight < 0:
                    obj.nengo_attributes.weight = 0
                assert 1 >= obj.nengo_attributes.weight >= 0, (
                    e_source, e_target, obj.nengo_attributes.weight, minimum, maximum, value)

    if nengo_3d.edge_color_gen.max_colors != len(nengo_3d.edge_mapped_colors) + 1:
        nengo_3d.edge_color_gen.max_colors = len(nengo_3d.edge_mapped_colors) + 1
        color_gen = colors.cycle_color(nengo_3d.edge_color_gen.initial_color,
                                       shift_type=nengo_3d.edge_color_gen.shift,
                                       max_colors=nengo_3d.edge_color_gen.max_colors)

        if is_numerical:
            key = lambda mapped_color: float(
                mapped_color.name) if mapped_color.name is not None and mapped_color.name not in {'None', ''} else 0
        else:
            key = lambda mapped_color: mapped_color.name
        for mapped_color in sorted(nengo_3d.edge_mapped_colors, key=key):
            mapped_color: NodeMappedColor
            mapped_color.color = next(color_gen)

    # force particular representation where it does not make sense to have different
    if nengo_3d.edge_attribute_with_type.endswith(':str'):
        nengo_3d.edge_color_map = 'ENUM'
    elif nengo_3d.edge_attribute_with_type.endswith(':float'):
        nengo_3d.edge_color_map = 'GRADIENT'


def edge_dynamic_access_path_update(self: 'Nengo3dProperties', context):
    global _last_edge_dynamic_access_path
    if _last_edge_dynamic_access_path != self.edge_dynamic_access_path:
        self.requires_reset = True
    _last_edge_dynamic_access_path = self.edge_dynamic_access_path


def edge_color_single_update(self: 'Nengo3dProperties', context):
    from bl_nengo_3d.share_data import share_data
    for e_source, e_target, key, e_data in share_data.model_graph_view.edges(data=True, keys=True):
        e_data = share_data.model_graph.edges[e_data['pre'], e_data['post'], key]
        obj = bpy.data.objects[e_data['_blender_object_name']]
        obj.nengo_attributes.color = self.edge_color_single
        obj.update_tag()


_edge_anti_crash = None
_edge_attribute_with_types_cache = None


def edge_attribute_with_types_items(self, context):
    from bl_nengo_3d.share_data import share_data
    global _edge_anti_crash, _edge_attribute_with_types_cache
    g = share_data.model_graph_view
    if not g:
        return [(':', '--no data--', '')]
    if _edge_attribute_with_types_cache == g and _edge_anti_crash:
        return _edge_anti_crash
    else:
        _edge_attribute_with_types_cache = g
    used = {}
    for e_source, e_target, key, e_data in g.edges(data=True, keys=True):
        e_data = share_data.model_graph.edges[e_data['pre'], e_data['post'], key]
        for k, v in e_data.items():
            if k.startswith('_'):
                continue
            if used.get(k):
                if used[k] is None:
                    used[k] = v
                continue
            elif isinstance(v, list):
                continue
            elif isinstance(v, tuple):
                continue
            elif isinstance(v, dict):
                for i, _v in recurse_dict(prefix=k, value=v):
                    if used.get(i):
                        if used[i] is None:
                            used[i] = _v
                        continue
                    used[i] = _v
            elif v is None:
                continue
            else:
                used[k] = v
    _edge_anti_crash = [(':', '--Choose an attribute--', '')]
    for k, v in sorted(used.items()):
        _edge_anti_crash.append((f'{k}:{type(v).__name__}', f'{k}: {type(v).__name__}', f''))
    return _edge_anti_crash


def color_map_edge_update(self: 'Nengo3dProperties', context):
    material = bpy.data.materials.get('NengoEdgeMaterial')
    if not material:
        return
    mix = material.node_tree.nodes['Mix']
    if self.edge_color_map == 'ENUM':
        mix.inputs[0].default_value = 1.0
    elif self.edge_color_map == 'GRADIENT':
        mix.inputs[0].default_value = 0.0
    else:
        logging.error(f'Unknown value: {self.edge_color_map}')


def edge_enum_color_update(self: 'Nengo3dProperties', context):
    if self.edge_color == 'SINGLE':
        self.edge_color_map = 'ENUM'
        edge_color_single_update(self, context)


#### end edges functions ####

class Nengo3dProperties(bpy.types.PropertyGroup):
    code_file_path: bpy.props.StringProperty()
    show_whole_simulation: bpy.props.BoolProperty(name='Show all steps', default=False)
    draw_labels: bpy.props.BoolProperty(name='Draw labels', default=False, update=draw_labels_update)
    force_one_connection_per_edge: bpy.props.BoolProperty(
        name='Force 1 connection per edge', default=False,
        update=force_one_connection_per_edge_update)
    select_edges: bpy.props.BoolProperty(name='Selectable edges', default=False, update=select_edges_update)
    arrow_length: bpy.props.FloatProperty(name='Arrow length', default=0.5, min=0, max=1, precision=2, step=1,
                                          update=recalculate_edges)
    arrow_back_length: bpy.props.FloatProperty(name='Arrow back length', default=0, precision=2, step=1,
                                               update=recalculate_edges)
    arrow_width: bpy.props.FloatProperty(name='Arrow width', default=0.6, min=0.0, precision=2, step=1,
                                         update=recalculate_edges)
    edge_width: bpy.props.FloatProperty(name='Edge width', default=0.5, min=0.0, precision=2, step=1,
                                        update=recalculate_edges)
    expand_subnetworks: bpy.props.CollectionProperty(type=Nengo3dShowNetwork)
    show_n_last_steps: bpy.props.IntProperty(name='Show last n steps', default=500, min=0, soft_min=0)
    sample_every: bpy.props.IntProperty(name='Sample every', description='Collect data from every n-th step',
                                        default=1, min=1, update=sample_every_update)
    requires_reset: bpy.props.BoolProperty(update=requires_reset_update)
    dt: bpy.props.FloatProperty(default=0.001, min=0.0, precision=3, step=1, update=sample_every_update)
    step_n: bpy.props.IntProperty(name='Step N', default=100, min=1)
    speed: bpy.props.FloatProperty(default=1.0, min=0.01, description='Default simulation rate is 24 steps per second')
    allow_scrubbing: bpy.props.BoolProperty(name='Step by timeline scrubbing')
    collection: bpy.props.StringProperty(name='Collection', default='Nengo Model')
    algorithm_dim: bpy.props.EnumProperty(
        items=[
            ('2D', '2d', 'Use 2d graph drawing algorithm'),
            ('3D', '3d', 'Use 3d graph drawing algorithm'),
        ], name='Algorithm 2d/3d', description='')
    layout_algorithm_2d: bpy.props.EnumProperty(
        items=[
            ('HIERARCHICAL', 'Hierarchical', ''),
            ('BIPARTITE_LAYOUT', 'Bipartite', 'Position nodes in two straight lines'),
            ('MULTIPARTITE_LAYOUT', 'Multipartite', 'Position nodes in layers of straight lines'),
            ('CIRCULAR_LAYOUT', 'Circular', 'Position nodes on a circle'),
            ('KAMADA_KAWAI_LAYOUT', 'Kamada kawai', 'Position nodes using Kamada-Kawai path-length cost-function'),
            ('PLANAR_LAYOUT', 'Planar', 'Position nodes without edge intersections'),
            ('RANDOM_LAYOUT', 'Random', 'Position nodes uniformly at random in the unit square'),
            ('SHELL_LAYOUT', 'Shell', 'Position nodes in concentric circles'),
            ('SPRING_LAYOUT', 'Spring', 'Position nodes using Fruchterman-Reingold force-directed algorithm'),
            ('SPECTRAL_LAYOUT', 'Spectral', 'Position nodes using the eigenvectors of the graph Laplacian'),
            ('SPIRAL_LAYOUT', 'Spiral', 'Position nodes in a spiral layout'),
        ], name='Layout', description='', default='SPRING_LAYOUT')
    layout_algorithm_3d: bpy.props.EnumProperty(
        items=[
            ('CIRCULAR_LAYOUT', 'Circular', 'Position nodes on a circle'),
            ('KAMADA_KAWAI_LAYOUT', 'Kamada kawai', 'Position nodes using Kamada-Kawai path-length cost-function'),
            ('RANDOM_LAYOUT', 'Random', 'Position nodes uniformly at random in the unit square'),
            ('SPRING_LAYOUT', 'Spring', 'Position nodes using Fruchterman-Reingold force-directed algorithm'),
            ('SPECTRAL_LAYOUT', 'Spectral', 'Position nodes using the eigenvectors of the graph Laplacian'),
        ], name='Layout', description='', default='SPRING_LAYOUT')
    spacing: bpy.props.FloatProperty(name='Spacing', description='', default=10, min=0)

    node_color: bpy.props.EnumProperty(items=[
        ('SINGLE', 'Single color', ''),
        ('MODEL', 'Model properties', ''),
        ('MODEL_DYNAMIC', 'Model dynamic properties', '')],
        update=node_enum_color_update,
    )
    node_color_single: bpy.props.FloatVectorProperty(name='Color', subtype='COLOR', update=node_color_single_update,
                                                     default=[0.099202, 1.000000, 0.217183])
    node_attribute_with_type: bpy.props.EnumProperty(name='Attribute', items=node_attribute_with_types_items,
                                                     update=node_attribute_with_types_update)
    node_dynamic_access_path: bpy.props.EnumProperty(name='Dynamic attributes', items=probeable_nodes_items,
                                                     update=node_dynamic_access_path_update)
    node_dynamic_get: bpy.props.StringProperty(default='sum(data)')
    node_attr_auto_range: bpy.props.BoolProperty(name='Auto range', default=True)
    node_attr_min: bpy.props.FloatProperty(name='Min')
    node_attr_max: bpy.props.FloatProperty(name='Max', default=1)
    node_color_map: bpy.props.EnumProperty(items=[('ENUM', 'Enum', ''),
                                                  ('GRADIENT', 'Gradient', '')
                                                  ],
                                           update=color_map_node_update)
    node_mapped_colors: bpy.props.CollectionProperty(type=NodeMappedColor)
    node_color_gen: bpy.props.PointerProperty(type=ColorGeneratorProperties)

    edge_color: bpy.props.EnumProperty(items=[
        ('SINGLE', 'Single color', ''),
        ('MODEL', 'Model properties', ''),
        ('MODEL_DYNAMIC', 'Model dynamic properties', '')],
        update=edge_enum_color_update,
    )
    edge_color_single: bpy.props.FloatVectorProperty(name='Color', subtype='COLOR', update=edge_color_single_update,
                                                     default=[0.099202, 0.140791, 1.000000])
    edge_attribute_with_type: bpy.props.EnumProperty(name='Attribute', items=edge_attribute_with_types_items,
                                                     update=edge_attribute_with_types_update)
    edge_dynamic_access_path: bpy.props.EnumProperty(name='Dynamic attributes', items=probeable_edges_items,
                                                     update=edge_dynamic_access_path_update)
    edge_dynamic_get: bpy.props.StringProperty(default='sum(data)')
    edge_attr_auto_range: bpy.props.BoolProperty(name='Auto range', default=True)
    edge_attr_min: bpy.props.FloatProperty(name='Min')
    edge_attr_max: bpy.props.FloatProperty(name='Max', default=1)
    edge_color_map: bpy.props.EnumProperty(items=[('ENUM', 'Enum', ''),
                                                  ('GRADIENT', 'Gradient', '')
                                                  ],
                                           update=color_map_edge_update)
    edge_mapped_colors: bpy.props.CollectionProperty(type=EdgeMappedColor)
    edge_color_gen: bpy.props.PointerProperty(type=ColorGeneratorProperties)


class NengoAttributes(bpy.types.PropertyGroup):
    color: bpy.props.FloatVectorProperty(subtype='COLOR', default=[0.099202, 1.000000, 0.217183])
    weight: bpy.props.FloatProperty(default=1.0)


classes = (
    ColorGeneratorProperties,
    LineSourceProperties,
    LineProperties,
    LegendProperties,
    AxesProperties,
    NodeMappedColor,
    EdgeMappedColor,
    Nengo3dShowNetwork,
    Nengo3dProperties,
    NengoAttributes,
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()
    bpy.types.Scene.nengo_3d = bpy.props.PointerProperty(type=Nengo3dProperties)
    bpy.types.Object.nengo_axes = bpy.props.PointerProperty(type=AxesProperties)
    bpy.types.Object.nengo_attributes = bpy.props.PointerProperty(type=NengoAttributes)


def unregister():
    del bpy.types.Scene.nengo_3d
    del bpy.types.Object.nengo_axes
    del bpy.types.Object.nengo_attributes
    unregister_factory()
