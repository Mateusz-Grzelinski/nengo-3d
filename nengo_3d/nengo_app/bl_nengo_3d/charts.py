import collections
import logging
import math
import types
from collections import Sequence

import bmesh
import bpy.utils

import bl_nengo_3d.colors as colors
import numpy as np

logger = logging.getLogger(__name__)


def get_primitive_material():
    mat_name = 'NengoChartMaterial'
    material = bpy.data.materials.get(mat_name)
    if not material:
        material = bpy.data.materials.new(mat_name)
        material.use_nodes = True
        material.node_tree.nodes.remove(material.node_tree.nodes['Principled BSDF'])
        material_output = material.node_tree.nodes.get('Material Output')
        material_output.location = (0, 0)
        diffuse = material.node_tree.nodes.new('ShaderNodeBsdfDiffuse')
        diffuse.location = (-100, 0)
        material.node_tree.links.new(material_output.inputs[0], diffuse.outputs[0])
        attribute = material.node_tree.nodes.new('ShaderNodeAttribute')
        attribute.location = (-200, 0)
        attribute.attribute_type = 'OBJECT'
        attribute.attribute_name = 'nengo_colors.color'
        material.node_tree.links.new(diffuse.inputs[0], attribute.outputs[0])
    return material


def normalize_precalculated(x: list[float], min_x: float, max_x: float):
    if min_x == max_x:
        min_x -= 1
        max_x += 1
    for i, _x in enumerate(x):
        x[i] = (_x - min_x) / (max_x - min_x)
    return x


def normalize(x: list[float]):
    min_x = min(x) if len(x) == 0 else 0
    max_x = max(x) if len(x) == 0 else 1
    if min_x == max_x:
        min_x = round(min_x - 1)
        max_x = round(max_x + 1)
    for i, _x in enumerate(x):
        x[i] = (_x - min_x) / (max_x - min_x)
    return x, min_x, max_x


def denormalize(x: list[float], min_x: float, max_x: float):
    for i, _x in enumerate(x):
        x[i] = (_x - min_x) / (max_x - min_x)
    return x


class LinearLocator:
    """
    Determine the tick locations

    The first time this function is called it will try to set the
    number of ticks to make a nice tick partitioning.  Thereafter the
    number of ticks will be fixed so that interactive navigation will
    be nice

    """

    def __init__(self, numticks=None):
        self.numticks = numticks

    def tick_values(self, vmin, vmax):
        if vmax < vmin:
            vmin, vmax = vmax, vmin

        if self.numticks == 0:
            return []
        ticklocs = np.linspace(vmin, vmax, self.numticks)
        return ticklocs


class IntegerLocator:
    def __init__(self, numticks=None):
        self.numticks = numticks

    def tick_values(self, vmin, vmax):
        if vmax < vmin:
            vmin, vmax = vmax, vmin

        if self.numticks == 0:
            return []
        ticklocs = np.arange(vmin, vmax + 1, step=int((vmax - vmin) / self.numticks) or 1)
        return list(set(ticklocs))


class Line:
    def __init__(self, ax: 'Axes', name: str):
        self.ax = ax
        self.label = str(name)
        self.original_data_x = []
        self.original_data_y = []
        self.original_data_z = None

        self._line = ax._create_object('Line', solidify=None, parent=ax.root)
        if not self.label:
            self.label = self._line.name

    def set_label(self, text):
        self.label = text

    def make_line(self, X: list, Y: list, width: float = 0.01, depth: float = 0.04):
        vers_pos = []
        faces = []
        for i, (x, y) in enumerate(zip(X, Y)):
            vers_pos.append((x, y, 0.0))
            # rotate vector 90 degrees to make line uniformly thick
            # todo problems with edge cases
            tangent_x = -(y - Y[i - 1])
            tangent_y = x - X[i - 1]
            # logger.debug(f'{x}: {(y - Y[i - 1], x - X[i - 1])}, {(tangent_x, tangent_y)}')
            tangent_len = math.sqrt(tangent_x * tangent_x + tangent_y * tangent_y)
            vers_pos.append((x + (tangent_x / tangent_len) * width,
                             y + tangent_y / tangent_len * width,
                             0.0))
            if i >= 2:
                i = 2 * i
                faces.append((i - 4, i - 3, i - 1, i - 2))
                assert len(vers_pos) == i + 2, i
        faces.append((i - 2, i - 1, i - 1, i))  # last face
        return vers_pos, [(0, 1)], faces

    def set_data(self, X, Y, Z=None):
        self.original_data_x = list(X)
        self.original_data_y = list(Y)
        if Z is not None:
            assert len(X) == len(Z), (len(X), len(Z), X, Z)
            self.original_data_z = list(Z)
        assert len(self.original_data_x) == len(self.original_data_y), \
            (len(self.original_data_x), len(self.original_data_y), X, Y)

    # def set_y_data(self, Y):
    #     XY = {i.co.x: i.co.y for i in self._line.data.vertices}
    #     y, self.min_y, self.max_y = normalize(Y)
    #     self._draw_line(X=list(XY.keys()), Y=y)

    # def set_x_data(self, X):
    #     x, self.min_x, self.max_x = normalize(X)
    #     XY = {i.co.x: i.co.y for i in self._line.data.vertices}
    #     self._draw_line(mesh=self._line.data, X=x, Y=list(XY.values()))

    def append_data(self, X, Y, Z=None, truncate: int = None):
        self.original_data_x.extend(X)
        self.original_data_y.extend(Y)
        if Z:
            self.original_data_z.extend(Z)
        if truncate:
            self.original_data_x = self.original_data_x[-truncate:]
            self.original_data_y = self.original_data_y[-truncate:]
            if Z:
                self.original_data_z = self.original_data_z[-truncate:]
        self.set_data(self.original_data_x, self.original_data_y, Z=self.original_data_z)

    def draw_line(self):
        X = normalize_precalculated(self.original_data_x.copy(), self.ax.xlim_min, self.ax.xlim_max)
        Y = normalize_precalculated(self.original_data_y.copy(), self.ax.ylim_min, self.ax.ylim_max)
        if not self.original_data_z:
            Z = [0 for _i in X]
        else:
            Z = normalize_precalculated(self.original_data_z.copy(), self.ax.zlim_min, self.ax.zlim_max)

        line_mesh = self._line.data
        if not X:
            return
        bm = bmesh.new()
        bm.from_mesh(line_mesh)
        bm.clear()
        co1 = (X[0], Y[0], Z[0])
        v1 = bm.verts.new(co1)
        edges = []
        for x, y, z in zip(X[1:], Y[1:], Z[1:]):
            v2 = bm.verts.new((x, y, z))
            edges.append(bm.edges.new((v1, v2)))
            v1 = v2
        result = bmesh.ops.extrude_edge_only(bm, edges=edges)
        for v in result['geom']:
            if isinstance(v, bmesh.types.BMVert):
                v.co.z += 0.04
        bm.to_mesh(line_mesh)
        bm.free()

    @property
    def dim(self):
        return 3 if self.original_data_z else 2


class Axes:
    # todo handle graph removal
    """Contains most of chart
    2 or 3 Axis
    title, x label, y label,
    range: x ticks, y ticks
    legend
    color, color bar
    """

    def __init__(self, context: bpy.types.Context, parameter: str = None):
        self.text_color = [0.019607, 0.019607, 0.019607]  # [1.000000, 0.982973, 0.926544]
        self.parameter = parameter
        self.color_gen = colors.cycle_color(initial_rgb=(0.080099, 0.226146, 1.000000))

        self.xlabel_text = None
        self.ylabel_text = None
        self.zlabel_text = None
        self.title_text = None
        # self.xticks = []
        self.xformat = '{:.2f}'
        self.xlocator = LinearLocator(numticks=8)
        # self.xticks_labels = []
        # self.yticks = []
        self.yformat = '{:.2f}'
        self.ylocator = LinearLocator(numticks=8)
        # self.yticks_labels = []
        self.zformat = '{:.2f}'
        self.zlocator = LinearLocator(numticks=8)
        self.context = context
        collection = bpy.data.collections.get('Charts')
        if not collection:
            collection = bpy.data.collections.new('Charts')
            context.collection.children.link(collection)
        self.collection = collection
        self._location = context.active_object.location if context.active_object else (0, 0, 0)
        self._line_z_offset = 0
        """Offset multiple lines in z direction. Only for 2 dim lines"""

        self.plot_lines: list[Line] = []

        self.xlim_min = 0
        self.xlim_max = 1
        self.ylim_min = 0
        self.ylim_max = 1
        self.zlim_min = 0
        self.zlim_max = 1

        # blender objects that create this chart:
        self.root = bpy.data.objects.new('Plot', None)
        self.collection.objects.link(self.root)
        self.root.empty_display_size = 1.1
        self.root.empty_display_type = 'ARROWS'  # 'PLAIN_AXES'

        self._chart = None
        self._ticks_x = None
        self._ticks_y = None
        self._ticks_z = None
        self._tick_text_x = []
        self._tick_text_y = []
        self._tick_text_z = []
        self._xlabel = None
        self._ylabel = None
        self._zlabel = None
        self._title = None

    @property
    def line_offset(self):
        return self._line_z_offset

    @line_offset.setter
    def line_offset(self, value: float):
        for i, line in enumerate(self.plot_lines):
            line._line.location.z = value * i
        self._line_z_offset = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value: Sequence[float, float, float]):
        if self.root:
            self.root.location = value
        self._location = value

    def xlabel(self, text: str):
        self.xlabel_text = text

    def ylabel(self, text: str):
        self.ylabel_text = text

    def zlabel(self, text: str):
        self.zlabel_text = text

    def title(self, text: str):
        self.title_text = text

    def relim(self):
        if not self.plot_lines:
            return
        xlim_max = -math.inf
        xlim_min = math.inf
        ylim_max = -math.inf
        ylim_min = math.inf
        zlim_max = -math.inf
        zlim_min = math.inf
        for line in self.plot_lines:
            if not line.original_data_x:
                continue
            if not line.original_data_y:
                continue
            xlim_max = max(xlim_max, max(line.original_data_x))
            xlim_min = min(xlim_min, min(line.original_data_x))
            ylim_max = max(ylim_max, max(line.original_data_y))
            ylim_min = min(ylim_min, min(line.original_data_y))
            if line.original_data_z:
                zlim_max = max(zlim_max, max(line.original_data_z))
                zlim_min = min(zlim_min, min(line.original_data_z))
        self.xlim_max = 1 if xlim_max == -math.inf else xlim_max
        self.xlim_min = 0 if xlim_min == math.inf else xlim_min
        self.ylim_max = 1 if ylim_max == -math.inf else ylim_max
        self.ylim_min = 0 if ylim_min == math.inf else ylim_min
        assert self.xlim_min not in {math.inf, -math.inf}, (self.xlim_min, line.original_data_x)
        assert self.xlim_max not in {math.inf, -math.inf}
        assert self.ylim_min not in {math.inf, -math.inf}
        assert self.ylim_max not in {math.inf, -math.inf}
        if any(line.original_data_z for line in self.plot_lines):
            self.zlim_max = 1 if zlim_max == -math.inf else zlim_max
            self.zlim_min = 0 if zlim_min == math.inf else zlim_min
            assert self.zlim_min not in {math.inf, -math.inf}
            assert self.zlim_max not in {math.inf, -math.inf}

    def _create_text(self, name, solidify: float = None, parent: bpy.types.Object = None, selectable=False, ):
        mesh = bpy.data.curves.new(name, type='FONT')
        obj = bpy.data.objects.new(name=name, object_data=mesh)
        self.collection.objects.link(obj)
        if solidify:
            bpy.ops.object.modifier_add({'object': obj}, type='SOLIDIFY')
            obj.modifiers["Solidify"].thickness = solidify  # 0.04
        obj.hide_select = not selectable
        obj.active_material = get_primitive_material()
        obj.nengo_colors.color = self.text_color
        obj.parent = parent
        return obj

    def _create_object(self, name, solidify: float = None, parent: bpy.types.Object = None, selectable=False, ):
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name=name, object_data=mesh)
        self.collection.objects.link(obj)
        if solidify:
            bpy.ops.object.modifier_add({'object': obj}, type='SOLIDIFY')
            obj.modifiers["Solidify"].thickness = solidify  # 0.04
        obj.hide_select = not selectable
        obj.active_material = get_primitive_material()
        obj.nengo_colors.color = next(self.color_gen)
        obj.parent = parent
        return obj

    def plot(self, *args, label: str):
        x = args[0]
        y = args[1]
        try:
            z = list(args[2])
            assert len(x) == len(y) == len(z)
        except IndexError:
            z = None
            assert len(x) == len(y)

        _x, xlim_min, xlim_max = normalize(x.copy())
        self.xlim_max = max(xlim_max, self.xlim_max)
        self.xlim_min = min(xlim_min, self.xlim_min)
        _y, ylim_min, ylim_max = normalize(y.copy())
        self.ylim_max = max(ylim_max, self.ylim_max)
        self.ylim_min = min(ylim_min, self.ylim_min)
        if z:
            _z, zlim_min, zlim_max = normalize(z.copy())
            self.zlim_max = max(zlim_max, self.zlim_max)
            self.zlim_min = min(zlim_min, self.zlim_min)
        line = Line(self, name=label)
        line._line.location.z = len(self.plot_lines) * self._line_z_offset
        line.set_data(x, y, z)
        self.plot_lines.append(line)
        # line.draw_line()
        # self.draw()  # todo should we draw here?
        return line

    def draw(self):
        if not self._chart:
            self.root.location = self._location
            self._chart = self._create_object('Chart', selectable=True, parent=self.root)

        if not self._ticks_x:
            self._ticks_x = self._create_object('Ticks X', solidify=0.02, parent=self._chart)
            self._ticks_x.nengo_colors.color = self.text_color
        self._draw_ticks_x(ticks=self.xlocator.tick_values(self.xlim_min, self.xlim_max),
                           ticks_x_mesh=self._ticks_x.data)

        if not self._ticks_y:
            self._ticks_y = self._create_object('Ticks Y', solidify=0.02, parent=self._chart)
            self._ticks_y.nengo_colors.color = self.text_color
        self._draw_ticks_y(ticks=self.ylocator.tick_values(self.ylim_min, self.ylim_max),
                           ticks_y_mesh=self._ticks_y.data)

        if any(line.original_data_z for line in self.plot_lines):
            if not self._ticks_z:
                self._ticks_z = self._create_object('Ticks Z', solidify=0.02, parent=self._chart)
                self._ticks_z.nengo_colors.color = self.text_color
            self._draw_ticks_z(ticks=self.zlocator.tick_values(self.zlim_min, self.zlim_max),
                               ticks_z_mesh=self._ticks_z.data)

            if self.zlabel_text:
                if not self._zlabel:
                    self._zlabel = self._create_text('zlabel', solidify=0.01, parent=self._chart)
                zlabel = self._zlabel.data
                zlabel.body = self.zlabel_text
                zlabel.size = 0.1
                zlabel.align_x = 'CENTER'
                zlabel.align_y = 'TOP'
                marigin = self._tick_text_z[0].dimensions.x if self._tick_text_z else 0
                self._zlabel.location = (-marigin - 0.07, 0, 0.5)
                self._zlabel.rotation_euler = (math.pi / 2, math.pi / 2, 0)
        else:
            if self._ticks_z:
                bpy.ops.object.delete({'selected_objects': [self._ticks_z]})
                self._ticks_z = None
                while self._tick_text_z:
                    obj = self._tick_text_z.pop()
                    bpy.ops.object.delete({'selected_objects': [obj]})
            if not self._zlabel:
                bpy.ops.object.delete({'selected_objects': [self._zlabel]})

        if self.xlabel_text:
            if not self._xlabel:
                self._xlabel = self._create_text('xlabel', solidify=0.01, parent=self._chart)
            xlabel = self._xlabel.data
            xlabel.body = self.xlabel_text
            xlabel.size = 0.1
            xlabel.align_x = 'CENTER'
            xlabel.align_y = 'TOP'
            marigin = self._tick_text_x[0].dimensions.y if self._tick_text_x else 0
            self._xlabel.location = (0.5, -0.10 - marigin, 0)

        if self.ylabel_text:
            if not self._ylabel:
                self._ylabel = self._create_text('ylabel', solidify=0.01, parent=self._chart)
            ylabel = self._ylabel.data
            ylabel.body = self.ylabel_text
            ylabel.size = 0.1
            ylabel.align_x = 'CENTER'
            ylabel.align_y = 'TOP'
            marigin = self._tick_text_y[0].dimensions.x if self._tick_text_y else 0
            self._ylabel.location = (-0.07 - marigin, 0.5, 0)
            self._ylabel.rotation_euler = (0, 0, -math.pi / 2)

        if self.title_text:
            if not self._title:
                self._title = self._create_text('Title', solidify=0.01, parent=self._chart)
            title = self._title.data
            title.body = self.title_text
            title.size = 0.15
            title.align_x = 'CENTER'
            title.align_y = 'BOTTOM'
            self._title.location = (0.5, 1.1, 0)
            # self._title.rotation_euler = (0, 0, -math.pi / 2)

        for line in self.plot_lines:
            line.draw_line()

    def _draw_ticks_x(self, ticks: list, ticks_x_mesh):
        bm = bmesh.new()
        ticks = [i for i in ticks if self.xlim_max >= i >= self.xlim_min]
        tick_width = 0.01
        tick_height = 0.04
        ticks_loc = normalize_precalculated(ticks.copy(), self.xlim_min, self.xlim_max)
        for t in ticks_loc:
            x_loc = t
            v1 = bm.verts.new((x_loc, 0, 0))
            v2 = bm.verts.new((x_loc + tick_width, 0, 0))
            v3 = bm.verts.new((x_loc, -tick_height, 0))
            v4 = bm.verts.new((x_loc + tick_width, -tick_height, 0))
            bm.faces.new((v1, v2, v4, v3))
        bm.to_mesh(ticks_x_mesh)
        bm.free()

        while len(self._tick_text_x) < len(ticks):
            self._tick_text_x.append(self._create_text(f'Tick x {len(self._tick_text_x)}',
                                                       solidify=0.01, parent=self._chart))
        while len(self._tick_text_x) > len(ticks):
            obj = self._tick_text_x.pop()
            bpy.ops.object.delete({'selected_objects': [obj]})

        for i, (t, t_loc) in enumerate(zip(ticks, ticks_loc)):
            tick_text_obj = self._tick_text_x[i]
            tick_text = tick_text_obj.data
            tick_text.body = self.xformat.format(t)
            tick_text.size = 0.05
            tick_text.align_x = 'CENTER'
            tick_text.align_y = 'TOP'
            tick_text_obj.location = (t_loc + tick_width / 2, -tick_height, 0)

    def _draw_ticks_y(self, ticks: list, ticks_y_mesh):
        bm = bmesh.new()
        ticks = [i for i in ticks if self.ylim_max >= i >= self.ylim_min]
        tick_width = 0.01
        tick_height = 0.04
        ticks_loc = normalize_precalculated(ticks.copy(), self.ylim_min, self.ylim_max)
        for t in ticks_loc:
            y_loc = t
            v1 = bm.verts.new((0, y_loc, 0))
            v2 = bm.verts.new((0, y_loc + tick_width, 0))
            v3 = bm.verts.new((-tick_height, y_loc, 0))
            v4 = bm.verts.new((-tick_height, y_loc + tick_width, 0))
            bm.faces.new((v1, v2, v4, v3))
        bm.to_mesh(ticks_y_mesh)
        bm.free()

        while len(self._tick_text_y) < len(ticks):
            self._tick_text_y.append(self._create_text(f'Tick y {len(self._tick_text_y)}',
                                                       solidify=0.01, parent=self._chart))
        while len(self._tick_text_y) > len(ticks):
            obj = self._tick_text_y.pop()
            bpy.ops.object.delete({'selected_objects': [obj]})

        for i, (t, t_loc) in enumerate(zip(ticks, ticks_loc)):
            tick_text_obj = self._tick_text_y[i]
            tick_text = tick_text_obj.data
            tick_text.body = self.yformat.format(t)
            tick_text.size = 0.05
            tick_text.align_x = 'RIGHT'
            tick_text.align_y = 'CENTER'
            tick_text_obj.location = (-tick_height, t_loc + tick_width / 2, 0)

    def _draw_ticks_z(self, ticks: list, ticks_z_mesh):
        bm = bmesh.new()
        ticks = [i for i in ticks if self.zlim_max >= i >= self.zlim_min]
        tick_width = 0.01
        tick_height = 0.04
        ticks_loc = normalize_precalculated(ticks.copy(), self.zlim_min, self.zlim_max)
        for t in ticks_loc:
            z_loc = t
            v1 = bm.verts.new((0, 0, z_loc,))
            v2 = bm.verts.new((0, 0, z_loc + tick_width))
            v3 = bm.verts.new((0, -tick_height, z_loc))
            v4 = bm.verts.new((0, -tick_height, z_loc + tick_width))
            bm.faces.new((v1, v2, v4, v3))
        bm.to_mesh(ticks_z_mesh)
        bm.free()

        while len(self._tick_text_z) < len(ticks):
            self._tick_text_z.append(self._create_text(f'Tick z {len(self._tick_text_z)}',
                                                       solidify=0.01, parent=self._chart))
        while len(self._tick_text_z) > len(ticks):
            obj = self._tick_text_z.pop()
            bpy.ops.object.delete({'selected_objects': [obj]})

        for i, (t, t_loc) in enumerate(zip(ticks, ticks_loc)):
            tick_text_obj = self._tick_text_z[i]
            tick_text = tick_text_obj.data
            tick_text.body = self.zformat.format(t)
            tick_text.size = 0.05
            tick_text.align_x = 'RIGHT'
            tick_text.align_y = 'TOP'
            tick_text_obj.location = (-tick_height, 0, t_loc + tick_width / 2)


locators = [
    (LinearLocator.__name__, LinearLocator.__name__, ''),
    (IntegerLocator.__name__, IntegerLocator.__name__, ''),
]
