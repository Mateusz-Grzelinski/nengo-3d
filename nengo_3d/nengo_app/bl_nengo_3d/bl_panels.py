from __future__ import annotations
from typing import TYPE_CHECKING

import bpy

import os

import logging
from bl_nengo_3d import bl_operators, debug
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
        # return False
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
        # mixer_prefs = get_mixer_prefs()

        layout.label(text='localhost:6001')
        if not self.connected():
            row = layout.row()
            row.scale_y = 1.5
            row.operator(bl_operators.ConnectOperator.bl_idname, text='Connect')
        else:
            row = layout.row()
            row.scale_y = 1.5
            row.operator(bl_operators.DisconnectOperator.bl_idname, text='Disconnect')


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
        layout.use_property_split = False
        row = layout.row()
        row.prop(win_man.nengo_3d, 'algorithm_dim', expand=True)
        if win_man.nengo_3d.algorithm_dim == '2D':
            layout.prop(win_man.nengo_3d, 'layout_algorithm_2d')
        else:
            layout.prop(win_man.nengo_3d, 'layout_algorithm_3d')


class NengoDebugPanel(bpy.types.Panel):
    bl_label = 'Nengo 3d Debug'
    bl_idname = 'NENGO_PT_debug'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Nengo 3d'

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout.column()
        layout.operator(debug.ReloadAddonOperator.bl_idname)
        layout.operator(debug.DebugConnectionOperator.bl_idname)


classes = (
    NengoSettingsPanel,
    NengoAlgorithmPanel,
    NengoDebugPanel,
)
register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()


def unregister():
    unregister_factory()
