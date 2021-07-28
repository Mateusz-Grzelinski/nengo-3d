from __future__ import annotations

import logging

import bpy

from bl_nengo_3d import bl_operators, bl_context_menu
from bl_nengo_3d.share_data import share_data

logger = logging.getLogger(__name__)


def connected():
    return share_data.client is not None  # and share_data.client.is_connected()


class NengoSettingsPanel(bpy.types.Panel):
    bl_label = 'Nengo 3d'
    bl_idname = 'NENGO_PT_settings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw_header_preset(self, context):
        layout = self.layout
        layout.emboss = 'NONE'
        if share_data.simulation_cache:
            any_object = next(iter(share_data.simulation_cache.values()))
            if any_object:
                any_param = next(iter(any_object.values()))
                cached_frames = len(any_param)
                layout.label(text=f'Cached: {cached_frames}')

    def draw(self, context):
        layout = self.layout.column()

        layout.label(text='localhost:6001')
        if not connected():
            row = layout.row()
            row.scale_y = 1.5
            row.operator(bl_operators.ConnectOperator.bl_idname, text='Connect')
        else:
            row = layout.row()
            row.scale_y = 1.5
            row.operator(bl_operators.DisconnectOperator.bl_idname, text='Disconnect')

        win_man = context.window_manager

        nengo_3d = win_man.nengo_3d
        row = layout.row()
        row.active = not connected()
        row.prop(nengo_3d, 'use_collection')
        screen = context.screen
        col = layout.column(align=True)
        col.active = connected()
        col.prop(nengo_3d, 'is_realtime', text='Live update')
        col.prop(context.scene.render, 'fps')
        col.prop(context.scene, 'frame_end')
        # if screen.is_animation_playing:
        #     col.operator('screen.animation_play', text='Stop', icon='PAUSE')
        # else:
        #     col.operator('screen.animation_play', text='Simulate', icon='PLAY')
        col.operator(bl_operators.NengoSimulateOperator.bl_idname, text='Step', icon='FRAME_NEXT').action = 'step'
        col.operator(bl_operators.NengoSimulateOperator.bl_idname, text='Step x10',
                     icon='FRAME_NEXT').action = 'stepx10'


class NengoAlgorithmPanel(bpy.types.Panel):
    bl_label = 'Nengo Algorithms'
    bl_idname = 'NENGO_PT_algorithms'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout.column()
        win_man = context.window_manager
        layout.operator(bl_operators.NengoCalculateOperator.bl_idname)

        nengo_3d = win_man.nengo_3d
        layout.prop(nengo_3d, 'spacing')
        layout.use_property_split = False
        row = layout.row()
        row.prop(nengo_3d, 'algorithm_dim', expand=True)
        if nengo_3d.algorithm_dim == '2D':
            layout.prop(nengo_3d, 'layout_algorithm_2d')
        else:
            layout.prop(nengo_3d, 'layout_algorithm_3d')


class NengoContextPanel(bpy.types.Panel):
    bl_label = 'Context Actions'
    bl_idname = 'NENGO_PT_context'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout.column()
        layout.operator(bl_context_menu.DrawVoltagesOperator.bl_idname, text='Plot voltage',
                        icon='OUTLINER_DATA_EMPTY')


class NengoInfoPanel(bpy.types.Panel):
    bl_label = 'Info'
    bl_idname = 'NENGO_PT_info'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw_header_preset(self, context):
        layout = self.layout
        layout.emboss = 'NONE'
        row = layout.row(align=True)
        obj: bpy.types.Object = context.active_object
        if not obj:
            return
        if share_data.model_graph:
            node = share_data.model_graph.nodes.get(obj.name)
            if node:
                layout.label(text=f'Node: {obj.name}')
        else:
            for source, charts in share_data.charts.items():
                for chart in charts.values():
                    if chart._chart == obj:
                        layout.label(text=f'Chart {obj.name}')

    def draw(self, context):
        layout = self.layout.column()
        obj: bpy.types.Object = context.active_object
        if not obj:
            layout.label(text='No active object')
            return

        if share_data.model_graph:
            node = share_data.model_graph.nodes.get(obj.name)
        else:
            layout.label(text='No active model')
            return

        for source, charts in share_data.charts.items():
            for chart in charts.values():
                if chart._chart == obj:
                    layout.label(text=f'{obj.name}:  {chart.title_text}')
                    col = layout.box().column(align=True)
                    row = col.row()
                    row.label(text='Parameter:')
                    row.label(text=f'{chart.parameter}')
                    row = col.row()
                    row.label(text='Source:')
                    row.label(text=f'{source}')
                    return

        if node:
            layout.label(text=f'Node: {obj.name}')
            col = layout.box().column(align=True)
            for param, value in node.items():
                row = col.row()
                row.label(text=param)
                row.label(text=str(value))
        else:
            layout.label(text=f'Not a network element')


classes = (
    NengoSettingsPanel,
    NengoContextPanel,
    NengoInfoPanel,
    NengoAlgorithmPanel,
)
register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()


def unregister():
    unregister_factory()
