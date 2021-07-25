import collections
import logging
import math
import types
from collections import Sequence

import bmesh
import bpy.utils

# import matplotlib.pyplot as plt
# import matplotlib.animation

# matplotlib.animation.FuncAnimation
# ln, = plt.plot([], [], 'ro')
# ln:plt.Line2D

# matplotlib.get_backend()
# matplotlib.rcsetup
# plt.Axes.__init__
# plt.axis
# plt.hist
# plt.plot

logger = logging.getLogger(__name__)


def normalize_precalculated(x: list[float], min_x: float, max_x: float):
    for i, _x in enumerate(x):
        x[i] = (_x - min_x) / (max_x - min_x)
    return x


def normalize(x: list[float]):
    min_x = min(x)
    max_x = max(x)
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


class Axes:
    """Contains most of chart
    2 or 3 Axis
    title, x label, y label,
    range: x ticks, y ticks
    legend
    color, color bar
    """

    def __init__(self, context: bpy.types.Context, parameter: str = None):
        self.parameter = parameter
        self.xlabel_text = None
        self.ylabel_text = None
        # self.title_text = None
        self.context = context
        collection = bpy.data.collections.new('Chart')
        context.collection.children.link(collection)
        self.collection = collection
        self._location = context.active_object.location if context.active_object else (0, 0, 0)

        self._data = {}
        self.original_data_x = []
        self.original_data_y = []
        self.min_x = 0
        self.max_x = 1
        self.min_y = 0
        self.max_y = 1

        # blender objects that create this chart:
        self._chart = None
        self._line = None
        self._ticks_x = None
        self._tick_text_x = []
        self._tick_text_y = []
        self._ticks_y = None
        self._xlabel = None
        self._ylabel = None

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value: Sequence[float, float, float]):
        if self._chart:
            self._chart.location = value
        self._location = value

    def xlabel(self, text: str):
        self.xlabel_text = text

    def ylabel(self, text: str):
        self.ylabel_text = text

    # def title(self, text: str):
    #     self.title_text = text

    # def grid(self):
    #     pass

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

    # def set_data(self, X, Y):
    #     y, self.min_y, self.max_y = normalize(Y)
    #     x, self.min_x, self.max_x = normalize(X)
    #     self._draw_line(X=x, Y=y)
    #
    # def set_y_data(self, Y):
    #     XY = {i.co.x: i.co.y for i in self._line.data.vertices}
    #     y, self.min_y, self.max_y = normalize(Y)
    #     self._draw_line(X=list(XY.keys()), Y=y)
    #
    # def set_x_data(self, X):
    #     x, self.min_x, self.max_x = normalize(X)
    #     XY = {i.co.x: i.co.y for i in self._line.data.vertices}
    #     self._draw_line(mesh=self._line.data, X=x, Y=list(XY.values()))

    def append_data(self, X, Y, truncate: int = None, auto_range=False):
        # todo this is not auto range. assumed that max(X) < self.max_x
        self.original_data_x.extend(X)
        self.original_data_y.extend(Y)
        if truncate:
            self.original_data_x = self.original_data_x[-truncate:]
            self.original_data_y = self.original_data_y[-truncate:]
        # logger.debug(self.original_data_x)
        # logger.debug(self.original_data_y)
        if auto_range:
            x, self.min_x, self.max_x = normalize(self.original_data_x)
            y, self.min_y, self.max_y = normalize(self.original_data_y)
            self._draw_ticks_x(ticks=10, ticks_x_mesh=self._ticks_x.data)
            self._draw_line(mesh=self._line.data, X=x, Y=y)
        else:
            x = normalize_precalculated(self.original_data_x, self.min_x, self.max_x)
            y = normalize_precalculated(self.original_data_y, self.min_y, self.max_y)
            self._draw_line(mesh=self._line.data, X=x, Y=y)

    def _draw_line(self, mesh: bpy.types.Mesh, X: list, Y: list):
        line_mesh = mesh
        bm = bmesh.new()
        bm.from_mesh(line_mesh)
        bm.clear()
        co1 = (X[0], Y[0], 0)
        v1 = bm.verts.new(co1)
        edges = []
        for x, y in zip(X[1:], Y[1:]):
            v2 = bm.verts.new((x, y, 0))
            edges.append(bm.edges.new((v1, v2)))
            v1 = v2
        result = bmesh.ops.extrude_edge_only(bm, edges=edges)
        for v in result['geom']:
            if isinstance(v, bmesh.types.BMVert):
                v.co.z += 0.04
        bm.to_mesh(line_mesh)
        bm.free()

    def _create_text(self, name, solidify: float = None, parent: bpy.types.Object = None, selectable=False, ):
        obj = bpy.data.objects.get(name)
        mesh = bpy.data.curves.get(name)
        if not obj:
            if not mesh:
                mesh = bpy.data.curves.new(name, type='FONT')
            obj = bpy.data.objects.new(name=name, object_data=mesh)
            self.collection.objects.link(obj)
            if solidify:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_add(type='SOLIDIFY')
                obj.modifiers["Solidify"].thickness = solidify  # 0.04
        obj.hide_select = not selectable
        obj.parent = parent
        return mesh, obj

    def _create_object(self, name, solidify: float = None, parent: bpy.types.Object = None, selectable=False, ):
        obj = bpy.data.objects.get(name)
        mesh = bpy.data.meshes.get(name)
        if not obj:
            if not mesh:
                mesh = bpy.data.meshes.new(name)
            else:
                mesh.clear_geometry()
            obj = bpy.data.objects.new(name=name, object_data=mesh)
            self.collection.objects.link(obj)
            if solidify:
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_add(type='SOLIDIFY')
                obj.modifiers["Solidify"].thickness = solidify  # 0.04
        obj.hide_select = not selectable
        obj.parent = parent
        return mesh, obj

    def plot(self, *args):
        x = args[0]
        y = args[1]
        assert len(x) == len(y)
        self.original_data_x = x
        self.original_data_y = y
        x, self.min_x, self.max_x = normalize(self.original_data_x)
        y, self.min_y, self.max_y = normalize(self.original_data_y)
        self.draw()

        self._draw_line(mesh=self._line.data, X=x, Y=y)

    def draw(self):
        chart_mesh, self._chart = self._create_object('Chart', selectable=True)
        chart_mesh.clear_geometry()
        chart_mesh.from_pydata(vertices=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)], edges=[], faces=[(0, 1, 3, 2)])
        self._chart.location = self._location

        line_mesh, self._line = self._create_object('Line', solidify=0.04, parent=self._chart)

        ticks_x_mesh, self._ticks_x = self._create_object('Arrow X', solidify=0.02, parent=self._chart)
        ticks_x_mesh.clear_geometry()
        self._draw_ticks_x(ticks=10, ticks_x_mesh=ticks_x_mesh)

        if self.xlabel_text:
            xlabel, self._xlabel = self._create_text('xlabel', solidify=0.01, parent=self._chart)
            xlabel.body = self.xlabel_text
            xlabel.size = 0.15
            xlabel.align_x = 'CENTER'
            xlabel.align_y = 'TOP'
            self._xlabel.location = (0.5, -0.07, 0)

        if self.ylabel_text:
            ylabel, self._ylabel = self._create_text('ylabel', solidify=0.01, parent=self._chart)
            ylabel.body = self.ylabel_text
            ylabel.size = 0.15
            ylabel.align_x = 'CENTER'
            ylabel.align_y = 'TOP'
            self._ylabel.location = (-0.07, 0.5, 0)
            self._ylabel.rotation_euler = (0, 0, -math.pi / 2)

    def _draw_ticks_x(self, ticks, ticks_x_mesh):
        bm = bmesh.new()
        tick_width = 0.01
        tick_height = 0.04
        x_loc_diff = 1 / ticks
        x_range_diff = (self.max_x - self.min_x) / ticks
        for i in range(ticks):
            x_loc = x_loc_diff * i
            v1 = bm.verts.new((x_loc, 0, 0))
            v2 = bm.verts.new((x_loc + tick_width, 0, 0))
            v3 = bm.verts.new((x_loc, -tick_height, 0))
            v4 = bm.verts.new((x_loc + tick_width, -tick_height, 0))
            bm.faces.new((v1, v2, v4, v3))

            tick_text, tick_text_obj = self._create_text(f'Tick text {i}', solidify=0.01, parent=self._chart)
            tick_text.body = str(round(self.min_x + x_range_diff * i, 1))
            tick_text.size = 0.05
            tick_text.align_x = 'CENTER'
            tick_text.align_y = 'TOP'
            tick_text_obj.location = (x_loc + tick_width / 2, -tick_height, 0)
            self._tick_text_x.append(tick_text_obj)
        bm.to_mesh(ticks_x_mesh)
        bm.free()

# register, unregister = bpy.utils.register_classes_factory(classes)
