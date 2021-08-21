import logging
from typing import Optional, Literal

import bmesh
import bpy

logger = logging.getLogger(__file__)

_PRIMITIVES = {}


def get_primitive_material(mat_name: str) -> bpy.types.Material:
    material = bpy.data.materials.get(mat_name)
    if not material:
        material = bpy.data.materials.new(mat_name)
        material.use_nodes = True
        material.node_tree.nodes.remove(material.node_tree.nodes['Principled BSDF'])
        material_output = material.node_tree.nodes.get('Material Output')
        material_output.location = (0, 0)
        diffuse = material.node_tree.nodes.new('ShaderNodeBsdfDiffuse')
        diffuse.location = (-100 * 2, 0)
        material.node_tree.links.new(material_output.inputs[0], diffuse.outputs[0])

        attribute = material.node_tree.nodes.new('ShaderNodeAttribute')
        attribute.location = (-400 * 2, 100 * 2)
        attribute.attribute_type = 'OBJECT'
        attribute.attribute_name = 'nengo_colors.weight'

        color_ramp = material.node_tree.nodes.new('ShaderNodeValToRGB')
        color_ramp.location = (-300 * 2, 0)
        material.node_tree.links.new(color_ramp.inputs[0], attribute.outputs[0])

        attribute = material.node_tree.nodes.new('ShaderNodeAttribute')
        attribute.location = (-400 * 2, 0)
        attribute.attribute_type = 'OBJECT'
        attribute.attribute_name = 'nengo_colors.color'

        mix_rgb = material.node_tree.nodes.new('ShaderNodeMixRGB')
        mix_rgb.location = (-200 * 2, 0)
        mix_rgb.inputs[0].default_value = 1  # ???
        material.node_tree.links.new(mix_rgb.inputs[2], attribute.outputs[0])
        material.node_tree.links.new(mix_rgb.inputs[1], color_ramp.outputs[0])
        material.node_tree.links.new(diffuse.inputs[0], mix_rgb.outputs[0])

    return material


def get_primitive(type_name: Literal['Node', 'Ensemble', 'Network']) -> Optional[bpy.types.Object]:
    global _PRIMITIVES

    if not _PRIMITIVES:
        collection_name = 'Nengo primitives'
        collection = bpy.data.collections.get(collection_name)

        if not collection:
            collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(collection)
            collection.hide_viewport = True
            collection.hide_render = True

        name = 'Node primitive'
        if not _PRIMITIVES.get(name):
            obj = bpy.data.objects.get(name)
            if not obj:
                primitive_mesh = bpy.data.meshes.get(name)
                if not primitive_mesh:
                    primitive_mesh = bpy.data.meshes.new(name)
                    bm = bmesh.new()
                    bmesh.ops.create_cube(bm, size=0.4)
                    bm.to_mesh(primitive_mesh)
                    bm.free()
                obj = bpy.data.objects.new(name=name, object_data=primitive_mesh)
            _PRIMITIVES[name] = obj
            collection.objects.link(obj)

        name = 'Ensemble primitive'
        if not _PRIMITIVES.get(name):
            obj = bpy.data.objects.get(name)
            if not obj:
                primitive_mesh = bpy.data.meshes.get(name)
                if not primitive_mesh:
                    primitive_mesh = bpy.data.meshes.new(name)
                    bm = bmesh.new()
                    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=16, diameter=0.5)
                    for f in bm.faces:
                        f.smooth = True
                    bm.to_mesh(primitive_mesh)
                    bm.free()
                obj = bpy.data.objects.new(name=name, object_data=primitive_mesh)
            _PRIMITIVES[name] = obj
            collection.objects.link(obj)

        name = 'Network primitive'
        if not _PRIMITIVES.get(name):
            obj = bpy.data.objects.get(name)
            if not obj:
                primitive_mesh = bpy.data.meshes.get(name)
                if not primitive_mesh:
                    primitive_mesh = bpy.data.meshes.new(name)
                    bm = bmesh.new()
                    geom = bmesh.ops.create_cube(bm, size=0.7, calc_uvs=False)
                    bmesh.ops.bevel(bm, geom=geom['verts'], offset=0.2, segments=1, affect='VERTICES')
                    bm.to_mesh(primitive_mesh)
                    bm.free()
                obj = bpy.data.objects.new(name=name, object_data=primitive_mesh)
            _PRIMITIVES[name] = obj
            collection.objects.link(obj)

    if obj := _PRIMITIVES.get(f'{type_name} primitive'):
        return obj.copy()
    else:
        logger.error(f'Unknown type: {type_name}')
        return None
