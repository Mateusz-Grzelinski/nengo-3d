from __future__ import annotations

import logging

import bpy

from bl_nengo_3d import bl_operators, bl_context_menu
from bl_nengo_3d.share_data import share_data

logger = logging.getLogger(__name__)


class NengoSettingsPanel(bpy.types.Panel):
    bl_label = 'Nengo 3d'
    bl_idname = 'NENGO_PT_settings'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def connected(self):
        return share_data.client is not None  # and share_data.client.is_connected()

    # def draw_header(self, context):
    #     self.layout.emboss = 'NONE'
    #     # icon = icons.icons_col['Mixer_32']
    #     row = self.layout.row(align=True)
    #     # row.operator('mixer.about', text="")
    #
    # def draw_header_preset(self, context):
    #     self.layout.emboss = 'NONE'
    #     row = self.layout.row(align=True)
    #     # row.menu('MIXER_MT_prefs_main_menu', icon='PREFERENCES', text="")
    #     row.separator(factor=1.0)

    def draw(self, context):
        layout = self.layout.column()

        layout.label(text='localhost:6001')
        if not self.connected():
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
        row.active = not self.connected()
        row.prop(nengo_3d, 'use_collection')
        layout.operator(bl_operators.NengoSimulateOperator.bl_idname, text='Simulate Step')


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
        layout.operator(bl_context_menu.DrawVoltagesOperator.bl_idname)


classes = (
    NengoSettingsPanel,
    NengoContextPanel,
    NengoAlgorithmPanel,
)
register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()


def unregister():
    unregister_factory()
