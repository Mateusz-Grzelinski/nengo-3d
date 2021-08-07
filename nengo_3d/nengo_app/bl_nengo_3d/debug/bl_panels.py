import itertools

import bpy

from .addon_reload import ReloadAddonOperator
from .charts import DebugPlotLine, DebugUpdatePlotLineOperator, DebugRasterPlotOperator
from .connection import DebugConnectionOperator


def ranges(i):
    for a, b in itertools.groupby(enumerate(i), lambda pair: pair[1] - pair[0]):
        b = list(b)
        yield b[0][1], b[-1][1]


class NengoDebugPanel(bpy.types.Panel):
    bl_label = 'Nengo 3d Debug'
    bl_idname = 'NENGO_PT_debug'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    def draw(self, context):
        layout = self.layout.column()
        from bl_nengo_3d.share_data import share_data
        if share_data.simulation_cache:
            layout.label(text=f'Cached steps: {share_data.simulation_cache_steps()}')
        col = layout.column(align=True)
        col.operator(DebugPlotLine.bl_idname, text='Plot 2d').dim = 2
        col.operator(DebugPlotLine.bl_idname, text='Plot 3d').dim = 3
        col.operator(DebugUpdatePlotLineOperator.bl_idname)
        col = layout.column(align=True)
        col.operator(DebugRasterPlotOperator.bl_idname, text='Raster plot').dim = 2
        layout.operator(ReloadAddonOperator.bl_idname)
        layout.operator(DebugConnectionOperator.bl_idname)


class NengoSimulationCachePanel(bpy.types.Panel):
    bl_parent_id = 'NENGO_PT_debug'
    bl_label = 'Simulation Cache'
    bl_idname = 'NENGO_PT_debug_cache'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout.column()
        from bl_nengo_3d.share_data import share_data

        if share_data.simulation_cache:
            layout.label(text=f'Cached steps: {share_data.simulation_cache_steps()}')
        col = layout.box().column(align=True)
        items = share_data.simulation_cache

        row = col.row()
        row.label(text=f'Key')
        # row.label(text=f'Used indices')
        row.label(text=f'First value')
        for param, value in sorted(items.items()):
            row = col.row()
            row.label(text=f'{str(param)}, dim={len(value[0]) if value else "?"}, len={len(value)}')
            # row.label(text=str([share_data.plot_line_sources[ax] for ax in share_data.charts[param[0], param[2]]]))
            row.label(text=f'{value[0]}, ...' if value else "?")
