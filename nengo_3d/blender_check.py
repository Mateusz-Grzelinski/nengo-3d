import os
import bpy

app_template_dir = os.path.join(
    bpy.utils.resource_path('USER'),
    r'scripts\startup\bl_app_templates_user')
# bl_app_templates_system for system app template

if 'nengo_app' not in os.listdir(app_template_dir):
    exit(111)
