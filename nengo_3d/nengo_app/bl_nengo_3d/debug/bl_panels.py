import itertools
import sys

import bpy

import networkx as nx
from .addon_reload import ReloadAddonOperator
from .charts import DebugPlotLine, DebugUpdatePlotLineOperator, DebugRasterPlotOperator
from .connection import DebugConnectionOperator
from .. import connection_handler
from ..digraph_model import DiGraphModel


def ranges(i):
    for a, b in itertools.groupby(enumerate(i), lambda pair: pair[1] - pair[0]):
        b = list(b)
        yield b[0][1], b[-1][1]


class NengoDebugPanel(bpy.types.Panel):
    bl_label = 'Nengo 3d debug'
    bl_idname = 'NENGO_PT_debug'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout.column()
        from bl_nengo_3d.share_data import share_data
        layout.label(
            text=f'Processing messages (last {connection_handler.execution_times.max_items} avg): {connection_handler.execution_times.average():.2f}')
        if share_data.simulation_cache:
            layout.label(text=f'Cached steps: {share_data.simulation_cache_steps()}')
        col = layout.column(align=True)
        # col.operator(DebugPlotLine.bl_idname, text='Plot 2d').dim = 2
        # col.operator(DebugPlotLine.bl_idname, text='Plot 3d').dim = 3
        # col.operator(DebugUpdatePlotLineOperator.bl_idname)
        col = layout.column(align=True)
        # col.operator(DebugRasterPlotOperator.bl_idname, text='Raster plot').dim = 2
        # layout.operator(ReloadAddonOperator.bl_idname)
        layout.operator(DebugConnectionOperator.bl_idname)


def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size


class NengoSimulationCachePanel(bpy.types.Panel):
    bl_parent_id = 'NENGO_PT_debug'
    bl_label = 'Simulation Cache'
    bl_idname = 'NENGO_PT_debug_cache'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        from bl_nengo_3d.share_data import share_data
        layout = self.layout.column()

        if share_data.simulation_cache:
            layout.label(
                text=f'Cached steps: {share_data.simulation_cache_steps()} * {context.scene.nengo_3d.sample_every} (sample every)'
                # f', {get_size(share_data.simulation_cache) / 1024 / 1024:.2f}Mb'
            )
        col = layout.box().column(align=True)
        row = col.row()
        row.label(text=f'Key')
        row.label(text=f'First value')
        for param, value in sorted(share_data.simulation_cache.items()):
            row = col.row()
            value: list
            if len(value) > 0:
                dim = value[0].shape
            else:
                dim = len(value[0])
            row.label(text=f'{str(param)}, dim={dim if value else "?"}, len={len(value)}')
            row.label(text=f'{value[0]}, ...' if value else "?")


class NengoSimulationChartPanel(bpy.types.Panel):
    bl_parent_id = 'NENGO_PT_debug'
    bl_label = 'Registered Charts'
    bl_idname = 'NENGO_PT_debug_chart'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        from bl_nengo_3d.share_data import share_data
        layout = self.layout.column()

        col = layout.box().column(align=True)
        # row = col.row()
        # row.label(text=f'Key')
        # row.label(text=f'First value')
        for param, value in sorted(share_data.charts.items()):
            row = col.row()
            row.label(text=f'{str(param)}:{str(value)}')


class NengoSubnetsPanel(bpy.types.Panel):
    bl_parent_id = 'NENGO_PT_debug'
    bl_label = 'Subnets'
    bl_idname = 'NENGO_PT_debug_subnets'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        from bl_nengo_3d.share_data import share_data
        layout = self.layout.column()
        col = layout.box().column(align=True)
        if share_data.model_graph is None:
            return
        self.recurse_subnets(col, share_data.model_graph)

    def recurse_subnets(self, layout, g: DiGraphModel, separator: float = 0):
        row = layout.row()
        row.separator(factor=separator)
        row.label(text=f'name: {g.name}')
        row = layout.row()
        row.separator(factor=separator)
        row.label(text=f'number of nodes: {len(g.nodes)}')
        row = layout.row()
        row.separator(factor=separator)
        row.label(text=f'number of edges: {len(g.edges)}')
        for param, value in sorted(g.graph.items()):
            if param in {'_networks', 'name'}:
                continue
            row = layout.row()
            row.separator(factor=separator)
            row.label(text=f'{str(param)}: {str(value)}')

        subnets = g.networks or {}
        for g_name, g in sorted(subnets.items()):
            row = layout.row()
            row.separator(factor=separator)
            row.label(text='networks["' + g_name + '"]:')
            self.recurse_subnets(layout.box().column(align=True), g, separator + 1.4)


class NengoNodesPanel(bpy.types.Panel):
    bl_parent_id = 'NENGO_PT_debug'
    bl_label = 'Nodes'
    bl_idname = 'NENGO_PT_debug_nodes'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        from bl_nengo_3d.share_data import share_data
        layout = self.layout.column()
        if share_data.model_graph is None:
            return
        layout.label(text=str(share_data.model_graph))
        col = layout.box().column(align=True)
        for node, data in share_data.model_graph.nodes(data=True):
            col.label(text=str(node))
            col.label(text=str(data))
        for subnet in share_data.model_graph.list_subnetworks():
            layout.label(text=str(subnet))
            col = layout.box().column(align=True)
            for node, data in subnet.nodes(data=True):
                col.label(text=str(node))
                col.label(text=str(data))
