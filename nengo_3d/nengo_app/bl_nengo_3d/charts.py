import collections
import logging
import math
import types
from collections import Sequence

import bmesh
import bpy.utils

# import matplotlib.pyplot as plt
# import matplotlib.ticker
#
# plt.xticks()
# matplotlib.ticker.MaxNLocator
import numpy as np

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
        return ticklocs


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
        self.parameter = parameter
        self.xlabel_text = None
        self.ylabel_text = None
        self.title_text = None
        # self.xticks = []
        self.xformat = '{:.2f}'
        self.xlocator = LinearLocator(numticks=8)
        # self.xticks_labels = []
        # self.yticks = []
        self.yformat = '{:.2f}'
        self.ylocator = LinearLocator(numticks=8)
        # self.yticks_labels = []
        self.context = context
        collection = bpy.data.collections.get('Charts')
        if not collection:
            collection = bpy.data.collections.new('Charts')
            context.collection.children.link(collection)
        self.collection = collection
        self._location = context.active_object.location if context.active_object else (0, 0, 0)

        self._data = {}
        self.original_data_x = []
        self.original_data_y = []
        self.xlim_min = 0
        self.xlim_max = 1
        self.ylim_min = 0
        self.ylim_max = 1

        # blender objects that create this chart:
        self._chart = None
        self._line = None
        self._ticks_x = None
        self._tick_text_x = []
        self._tick_text_y = []
        self._ticks_y = None
        self._xlabel = None
        self._ylabel = None
        self._title = None

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

    def title(self, text: str):
        self.title_text = text

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
    #     y, self.min_y, self.max_y = normalize(Y.copy())
    #     x, self.min_x, self.max_x = normalize(X.copy())
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
        self.original_data_x.extend(X)
        self.original_data_y.extend(Y)
        if truncate:
            self.original_data_x = self.original_data_x[-truncate:]
            self.original_data_y = self.original_data_y[-truncate:]
        if auto_range:
            x, self.xlim_min, self.xlim_max = normalize(self.original_data_x.copy())
            y, self.ylim_min, self.ylim_max = normalize(self.original_data_y.copy())
            self._draw_ticks_x(ticks=self.xlocator.tick_values(self.xlim_min, self.xlim_max),
                               ticks_x_mesh=self._ticks_x.data)
            self._draw_ticks_y(ticks=self.ylocator.tick_values(self.ylim_min, self.ylim_max),
                               ticks_y_mesh=self._ticks_y.data)
            self._draw_line(mesh=self._line.data, X=x, Y=y)
        else:
            x = normalize_precalculated(self.original_data_x.copy(), self.xlim_min, self.xlim_max)
            y = normalize_precalculated(self.original_data_y.copy(), self.ylim_min, self.ylim_max)
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
        # obj = bpy.data.objects.get(name)
        # mesh = bpy.data.curves.get(name)
        # if not obj:
        #     if not mesh:
        #     mesh = bpy.data.curves.new(name, type='FONT')
        mesh = bpy.data.curves.new(name, type='FONT')
        obj = bpy.data.objects.new(name=name, object_data=mesh)
        self.collection.objects.link(obj)
        if solidify:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_add(type='SOLIDIFY')
            obj.modifiers["Solidify"].thickness = solidify  # 0.04
        obj.hide_select = not selectable
        obj.parent = parent
        return obj

    def _create_object(self, name, solidify: float = None, parent: bpy.types.Object = None, selectable=False, ):
        # obj = bpy.data.objects.get(name)
        # mesh = bpy.data.meshes.get(name)
        # if not obj:
        #     if not mesh:
        #         mesh = bpy.data.meshes.new(name)
        #     else:
        #         mesh.clear_geometry()
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name=name, object_data=mesh)
        self.collection.objects.link(obj)
        if solidify:
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_add(type='SOLIDIFY')
            obj.modifiers["Solidify"].thickness = solidify  # 0.04
        obj.hide_select = not selectable
        obj.parent = parent
        return obj

    def plot(self, *args):
        x = args[0]
        y = args[1]
        assert len(x) == len(y)
        self.original_data_x = x
        self.original_data_y = y
        x, self.xlim_min, self.xlim_max = normalize(self.original_data_x.copy())
        y, self.ylim_min, self.ylim_max = normalize(self.original_data_y.copy())
        self.draw()

        self._draw_line(mesh=self._line.data, X=x, Y=y)

    def draw(self):
        if not self._chart:
            self._chart = self._create_object('Chart', selectable=True)
            chart_mesh = self._chart.data
            chart_mesh.from_pydata(vertices=[(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)], edges=[],
                                   faces=[(0, 1, 3, 2)])
            self._chart.location = self._location

        if not self._line:
            self._line = self._create_object('Line', solidify=0.04, parent=self._chart)

        if not self._ticks_x:
            self._ticks_x = self._create_object('Ticks X', solidify=0.02, parent=self._chart)
        self._draw_ticks_x(ticks=self.xlocator.tick_values(self.xlim_min, self.xlim_max),
                           ticks_x_mesh=self._ticks_x.data)

        if not self._ticks_y:
            self._ticks_y = self._create_object('Ticks Y', solidify=0.02, parent=self._chart)
        self._draw_ticks_y(ticks=self.ylocator.tick_values(self.ylim_min, self.ylim_max),
                           ticks_y_mesh=self._ticks_y.data)

        if self.xlabel_text:
            if not self._xlabel:
                self._xlabel = self._create_text('xlabel', solidify=0.01, parent=self._chart)
            xlabel = self._xlabel.data
            xlabel.body = self.xlabel_text
            xlabel.size = 0.1
            xlabel.align_x = 'CENTER'
            xlabel.align_y = 'TOP'
            marigin = self._tick_text_x[0].dimensions.y if self._tick_text_x else 0
            logger.debug(self._tick_text_x[0].dimensions.y)
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
