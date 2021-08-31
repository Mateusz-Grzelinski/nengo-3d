import logging
import math
from collections import Sequence
from typing import Mapping, Union

import bmesh
import bpy.utils

import bl_nengo_3d.colors as colors
import numpy as np
from bl_nengo_3d.utils import normalize_precalculated, normalize

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


class Locator:
    def __init__(self, numticks: int = None):
        self.numticks = numticks

    def tick_values(self, vmin, vmax):
        raise NotImplemented


class LinearLocator(Locator):
    """
    Determine the tick locations

    The first time this function is called it will try to set the
    number of ticks to make a nice tick partitioning.  Thereafter the
    number of ticks will be fixed so that interactive navigation will
    be nice

    """

    def tick_values(self, vmin, vmax):
        if vmax < vmin:
            vmin, vmax = vmax, vmin

        if self.numticks == 0:
            return []
        ticklocs = np.linspace(vmin, vmax, self.numticks)
        return ticklocs


class IntegerLocator(Locator):
    def tick_values(self, vmin, vmax):
        if vmax < vmin:
            vmin, vmax = vmax, vmin

        if self.numticks == 0:
            return []
        ticklocs = np.arange(vmin, vmax + 1, step=int((vmax - vmin) / self.numticks) or 1)
        return list(set(ticklocs))


_locators = {
    LinearLocator.__name__: LinearLocator,
    IntegerLocator.__name__: IntegerLocator,
}

locators = [(loc, loc, '') for loc in _locators.keys()]


class Line:
    def __init__(self, ax: 'Axes', line: 'LineProperties'):
        self.ax = ax
        self.original_data_x = []
        self.original_data_y = []
        self.original_data_z = None

        self._line = ax._create_object('Line', solidify=None, parent=ax.root)
        line.name = self._line.name

    # def set_label(self, text):
    #     self.label = text

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
        X = normalize_precalculated(self.original_data_x.copy(), self.ax.x_min, self.ax.x_max)
        Y = normalize_precalculated(self.original_data_y.copy(), self.ax.y_min, self.ax.y_max)
        if not self.original_data_z:
            Z = [0 for _i in X]
        else:
            Z = normalize_precalculated(self.original_data_z.copy(), self.ax.z_min, self.ax.z_max)

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


class AxesAccessors:
    def __init__(self, nengo_axes: 'AxesProperties') -> None:
        from bl_nengo_3d.bl_properties import AxesProperties
        self._nengo_axes: AxesProperties = nengo_axes
        self._xlocator = None
        self._ylocator = None
        self._zlocator = None

    @property
    def auto_range(self) -> float:
        return self._nengo_axes.auto_range

    @property
    def x_min(self) -> float:
        return self._nengo_axes.x_min

    @x_min.setter
    def x_min(self, value):
        self._nengo_axes.x_min = value

    @property
    def x_max(self) -> float:
        return self._nengo_axes.x_max

    @x_max.setter
    def x_max(self, value):
        self._nengo_axes.x_max = value

    @property
    def y_min(self) -> float:
        return self._nengo_axes.y_min

    @y_min.setter
    def y_min(self, value):
        self._nengo_axes.y_min = value

    @property
    def y_max(self) -> float:
        return self._nengo_axes.y_max

    @y_max.setter
    def y_max(self, value):
        self._nengo_axes.y_max = value

    @property
    def z_min(self) -> float:
        return self._nengo_axes.z_min

    @z_min.setter
    def z_min(self, value):
        self._nengo_axes.z_min = value

    @property
    def z_max(self) -> float:
        return self._nengo_axes.z_max

    @z_max.setter
    def z_max(self, value: float):
        self._nengo_axes.z_max = value

    @property
    def xlabel(self) -> str:
        return self._nengo_axes.xlabel

    @xlabel.setter
    def xlabel(self, value: str):
        self._nengo_axes.xlabel = value

    @property
    def ylabel(self) -> str:
        return self._nengo_axes.ylabel

    @ylabel.setter
    def ylabel(self, value: str):
        self._nengo_axes.ylabel = value

    @property
    def zlabel(self) -> str:
        return self._nengo_axes.zlabel

    @zlabel.setter
    def zlabel(self, value: str):
        self._nengo_axes.zlabel = value

    @property
    def title(self) -> str:
        return self._nengo_axes.title

    @title.setter
    def title(self, value: str):
        self._nengo_axes.title = value

    @staticmethod
    def _create_locator(locator: str, numticks: int) -> Locator:
        cls = _locators.get(locator)
        return cls(numticks=numticks)

    @property
    def xlocator(self) -> Locator:
        if not self._xlocator or self._xlocator.numticks != self._nengo_axes.xnumticks:
            self._xlocator = self._create_locator(locator=self._nengo_axes.xlocator,
                                                  numticks=self._nengo_axes.xnumticks)
        return self._xlocator

    @property
    def ylocator(self) -> Locator:
        if not self._ylocator or self._ylocator.numticks != self._nengo_axes.ynumticks:
            self._ylocator = self._create_locator(locator=self._nengo_axes.ylocator,
                                                  numticks=self._nengo_axes.ynumticks)
        return self._ylocator

    @property
    def zlocator(self) -> Locator:
        if not self._zlocator or self._zlocator.numticks != self._nengo_axes.znumticks:
            self._zlocator = self._create_locator(locator=self._nengo_axes.zlocator,
                                                  numticks=self._nengo_axes.znumticks)
        return self._zlocator

    @property
    def xformat(self) -> str:
        return self._nengo_axes.xformat

    @property
    def yformat(self) -> str:
        return self._nengo_axes.yformat

    @property
    def zformat(self) -> str:
        return self._nengo_axes.zformat

    @property
    def line_initial_color(self) -> tuple:
        return self._nengo_axes.line_initial_color

    @property
    def line_max_colors(self) -> int:
        return self._nengo_axes.line_max_colors

    @property
    def lines(self) -> Mapping[Union[str, int], 'LineProperties']:
        return self._nengo_axes.lines


class Axes(AxesAccessors):
    # todo handle graph removal
    """Contains most of chart
    2 or 3 Axis
    title, x label, y label,
    range: x ticks, y ticks
    legend
    color, color bar
    """

    def __init__(self, context: bpy.types.Context, nengo_axes: 'AxesProperties' = None):
        self.text_color = [0.019607, 0.019607, 0.019607]  # [1.000000, 0.982973, 0.926544]
        # self.parameter = parameter

        self.context = context
        collection = bpy.data.collections.get('Charts')
        if not collection:
            collection = bpy.data.collections.new('Charts')
            context.collection.children.link(collection)
        self.collection = collection
        self._location = context.active_object.location if context.active_object else (0, 0, 0)
        self._line_z_offset = 0
        """Offset multiple lines in z direction. Only for 2 dim lines"""

        self._lines: dict[Line] = {}

        # blender objects that create this chart:
        self.root = bpy.data.objects.new('Plot', None)
        self.collection.objects.link(self.root)
        if nengo_axes is not None:
            from bl_nengo_3d.bl_utils import copy_property_group
            copy_property_group(nengo_axes, self.root.nengo_axes)
        self.root.nengo_axes.object = self.root.name
        super().__init__(self.root.nengo_axes)

        color_gen_prop = self.root.nengo_axes.color_gen
        color_gen = colors.cycle_color(color_gen_prop.initial_color, color_gen_prop.shift, color_gen_prop.max_colors)

        offset = 0
        for line_prop in self.lines:
            line_prop: 'LineProperties'
            line = Line(self, line=line_prop)
            line._line.location.z = offset
            line._line.nengo_colors.color = next(color_gen)
            offset += self.line_offset
            self._lines[line_prop.name] = line

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
        return self._nengo_axes.line_offset

    @line_offset.setter
    def line_offset(self, value: float):
        for i, line in enumerate(self._lines.values()):
            line._line.location.z = value * i
        self._line_z_offset = value
        self._nengo_axes.line_offset = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value: Sequence[float, float, float]):
        if self.root:
            self.root.location = value
        self._location = value

    def get_line(self, line: 'LineProperties') -> Line:
        return self._lines[line.name]

    def relim(self):
        if not self._lines:
            return
        x_max = -math.inf
        x_min = math.inf
        y_max = -math.inf
        y_min = math.inf
        z_max = -math.inf
        z_min = math.inf
        for line in self._lines.values():
            if not line.original_data_x:
                continue
            if not line.original_data_y:
                continue
            x_max = max(x_max, max(line.original_data_x))
            x_min = min(x_min, min(line.original_data_x))
            y_max = max(y_max, max(line.original_data_y))
            y_min = min(y_min, min(line.original_data_y))
            if line.original_data_z:
                z_max = max(z_max, max(line.original_data_z))
                z_min = min(z_min, min(line.original_data_z))
        self.x_max = 1 if x_max == -math.inf else x_max
        self.x_min = 0 if x_min == math.inf else x_min
        self.y_max = 1 if y_max == -math.inf else y_max
        self.y_min = 0 if y_min == math.inf else y_min
        assert self.x_min not in {math.inf, -math.inf}, (self.x_min, line.original_data_x)
        assert self.x_max not in {math.inf, -math.inf}
        assert self.y_min not in {math.inf, -math.inf}
        assert self.y_max not in {math.inf, -math.inf}
        if any(line.original_data_z for line in self._lines.values()):
            self.z_max = 1 if z_max == -math.inf else z_max
            self.z_min = 0 if z_min == math.inf else z_min
            assert self.z_min not in {math.inf, -math.inf}
            assert self.z_max not in {math.inf, -math.inf}

    def _create_text(self, name, solidify: float = None, parent: bpy.types.Object = None, selectable=False, ):
        mesh = bpy.data.curves.new(name, type='FONT')
        obj = bpy.data.objects.new(name=name, object_data=mesh)
        self.collection.objects.link(obj)
        if solidify:
            mod = obj.modifiers.new('Solidify', 'SOLIDIFY')
            mod.thickness = solidify
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
        # obj.nengo_colors.color = next(self.color_gen)
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

        _x, x_min, x_max = normalize(x.copy())
        self.x_max = max(x_max, self.x_max)
        self.x_min = min(x_min, self.x_min)
        _y, y_min, y_max = normalize(y.copy())
        self.y_max = max(y_max, self.y_max)
        self.y_min = min(y_min, self.y_min)
        if z:
            _z, z_min, z_max = normalize(z.copy())
            self.z_max = max(z_max, self.z_max)
            self.z_min = min(z_min, self.z_min)

        line_prop: 'LineProperties' = self.lines.add()
        line = Line(self, line=line_prop)
        line._line.location.z = len(self._lines) * self.line_offset
        line.set_data(x, y, z)
        self._lines[line_prop.name] = line
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
        self._draw_ticks_x(ticks=self.xlocator.tick_values(self.x_min, self.x_max),
                           ticks_x_mesh=self._ticks_x.data)

        if not self._ticks_y:
            self._ticks_y = self._create_object('Ticks Y', solidify=0.02, parent=self._chart)
            self._ticks_y.nengo_colors.color = self.text_color
        self._draw_ticks_y(ticks=self.ylocator.tick_values(self.y_min, self.y_max),
                           ticks_y_mesh=self._ticks_y.data)

        if any(line.original_data_z for line in self._lines.values()):
            if not self._ticks_z:
                self._ticks_z = self._create_object('Ticks Z', solidify=0.02, parent=self._chart)
                self._ticks_z.nengo_colors.color = self.text_color
            self._draw_ticks_z(ticks=self.zlocator.tick_values(self.z_min, self.z_max),
                               ticks_z_mesh=self._ticks_z.data)

            if self.zlabel:
                if not self._zlabel:
                    self._zlabel = self._create_text('zlabel', parent=self._chart)
                zlabel = self._zlabel.data
                zlabel.body = self.zlabel_text
                zlabel.size = 0.1
                zlabel.align_x = 'CENTER'
                zlabel.align_y = 'TOP'
                self._zlabel.hide_render = False
                self._zlabel.hide_viewport = False
                marigin = self._tick_text_z[0].dimensions.x if self._tick_text_z else 0
                self._zlabel.location = (-marigin - 0.07, 0, 0.5)
                self._zlabel.rotation_euler = (math.pi / 2, math.pi / 2, 0)
        else:
            if self._ticks_z:
                bpy.data.objects.remove(self._ticks_z, do_unlink=True)
                # bpy.ops.object.delete({'selected_objects': [self._ticks_z]})
                self._ticks_z = None
                while self._tick_text_z:
                    obj = self._tick_text_z.pop()
                    bpy.data.objects.remove(obj, do_unlink=True)
                    # bpy.ops.object.delete({'selected_objects': [obj]})
            if not self.zlabel and self._zlabel:
                self._zlabel.hide_render = True
                self._zlabel.hide_viewport = True
                # bpy.data.objects.remove(self._zlabel, do_unlink=True)
                # bpy.ops.object.delete({'selected_objects': [self._zlabel]})

        if self.xlabel:
            if not self._xlabel:
                self._xlabel = self._create_text('xlabel', parent=self._chart)
            xlabel = self._xlabel.data
            xlabel.body = self.xlabel
            xlabel.size = 0.1
            xlabel.align_x = 'CENTER'
            xlabel.align_y = 'TOP'
            marigin = self._tick_text_x[0].dimensions.y if self._tick_text_x else 0
            self._xlabel.location = (0.5, -0.10 - marigin, 0)

        if self.ylabel:
            if not self._ylabel:
                self._ylabel = self._create_text('ylabel', parent=self._chart)
            ylabel = self._ylabel.data
            ylabel.body = self.ylabel
            ylabel.size = 0.1
            ylabel.align_x = 'CENTER'
            ylabel.align_y = 'TOP'
            marigin = self._tick_text_y[0].dimensions.x if self._tick_text_y else 0
            self._ylabel.location = (-0.07 - marigin, 0.5, 0)
            self._ylabel.rotation_euler = (0, 0, -math.pi / 2)

        if self.title:
            if not self._title:
                self._title = self._create_text('Title', parent=self._chart)
            title = self._title.data
            title.body = self.title
            title.size = 0.15
            title.align_x = 'CENTER'
            title.align_y = 'BOTTOM'
            self._title.location = (0.5, 1.1, 0)
            # self._title.rotation_euler = (0, 0, -math.pi / 2)

        for line in self._lines.values():
            line.draw_line()

    def _draw_ticks_x(self, ticks: list, ticks_x_mesh):
        bm = bmesh.new()
        ticks = [i for i in ticks if self.x_max >= i >= self.x_min]
        tick_width = 0.01
        tick_height = 0.04
        ticks_loc = normalize_precalculated(ticks.copy(), self.x_min, self.x_max)
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
            self._tick_text_x.append(self._create_text(f'Tick x {len(self._tick_text_x)}', parent=self._chart))
        while len(self._tick_text_x) > len(ticks):
            obj = self._tick_text_x.pop()
            bpy.data.objects.remove(obj, do_unlink=True)
            # bpy.ops.object.delete({'selected_objects': [obj]})

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
        ticks = [i for i in ticks if self.y_max >= i >= self.y_min]
        tick_width = 0.01
        tick_height = 0.04
        ticks_loc = normalize_precalculated(ticks.copy(), self.y_min, self.y_max)
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
            self._tick_text_y.append(self._create_text(f'Tick y {len(self._tick_text_y)}', parent=self._chart))
        while len(self._tick_text_y) > len(ticks):
            obj = self._tick_text_y.pop()
            bpy.data.objects.remove(obj, do_unlink=True)
            # bpy.ops.object.delete({'selected_objects': [obj]})

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
        ticks = [i for i in ticks if self.z_max >= i >= self.z_min]
        tick_width = 0.01
        tick_height = 0.04
        ticks_loc = normalize_precalculated(ticks.copy(), self.z_min, self.z_max)
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
                                                       parent=self._chart))
        while len(self._tick_text_z) > len(ticks):
            obj = self._tick_text_z.pop()
            bpy.data.objects.remove(obj, do_unlink=True)
            # bpy.ops.object.delete({'selected_objects': [obj]})

        for i, (t, t_loc) in enumerate(zip(ticks, ticks_loc)):
            tick_text_obj = self._tick_text_z[i]
            tick_text = tick_text_obj.data
            tick_text.body = self.zformat.format(t)
            tick_text.size = 0.05
            tick_text.align_x = 'RIGHT'
            tick_text.align_y = 'TOP'
            tick_text_obj.location = (-tick_height, 0, t_loc + tick_width / 2)
