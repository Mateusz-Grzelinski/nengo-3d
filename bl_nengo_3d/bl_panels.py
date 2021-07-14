# GPLv3 License
#
# Copyright (C) 2020 Ubisoft
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
This module define Blender Panels and UI types for the addon.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

import bpy

import os

import logging
from bl_nengo_3d import bl_operators
from bl_nengo_3d.share_data import share_data

logger = logging.getLogger(__name__)

user_modes = {
    'EDIT_MESH': ('Edit', 'EDITMODE_HLT'),
    'EDIT_CURVE': ('Curve', 'EDITMODE_HLT'),
    'EDIT_SURFACE': ('Surface', 'EDITMODE_HLT'),
    'EDIT_TEXT': ('Text', 'EDITMODE_HLT'),
    'EDIT_ARMATURE': ('Armature', 'EDITMODE_HLT'),
    'EDIT_METABALL': ('Metaball', 'EDITMODE_HLT'),
    'EDIT_LATTICE': ('Lattice', 'EDITMODE_HLT'),
    'POSE': ('Pose', 'POSE_HLT'),
    'SCULPT': ('Sculpt', 'SCULPTMODE_HLT'),
    'PAINT_WEIGHT': ('Weight', 'WPAINT_HLT'),
    'PAINT_VERTEX': ('Vertex', 'VPAINT_HLT'),
    'PAINT_TEXTURE': ('Texture', 'TPAINT_HLT'),
    'PARTICLE': ('Particle', 'PARTICLEMODE'),
    'OBJECT': ('Object', 'OBJECT_DATAMODE'),
    'PAINT_GPENCIL': ('GP Paint', 'GREASEPENCIL'),
    'EDIT_GPENCIL': ('GP Edit', 'EDITMODE_HLT'),
    'SCULPT_GPENCIL': ('GP Sculpt', 'SCULPTMODE_HLT'),
    'WEIGHT_GPENCIL': ('GP Weight', 'WPAINT_HLT'),
    'VERTEX_GPENCIL': ('GP Vertex', 'VPAINT_HLT'),
}


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

        if not self.connected():
            layout.separator(factor=0.2)
            split = layout.split(factor=0.258, align=False)
            split.label(text='Host:')
            # split.prop(mixer_prefs, 'host', text="")

            layout.separator(factor=0.5)
            row = layout.row()
            row.scale_y = 1.5
            row.operator(bl_operators.ConnectOperator.bl_idname, text='Connect')
            layout.separator(factor=1.0)
        else:
            layout.separator(factor=0.5)
            # layout.label(text=f'Connected to  {mixer_prefs.host}:{mixer_prefs.port}')

            row = layout.row()
            row.scale_y = 1.5
            row.operator(bl_operators.DisconnectOperator.bl_idname, text='Disconnect', depress=True)
            layout.separator(factor=2.0)

            layout.separator(factor=1.5)


classes = (NengoSettingsPanel,)
register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()


def unregister():
    unregister_factory()
