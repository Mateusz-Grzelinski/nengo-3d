import os
import sys

import bpy
import argparse

argv = sys.argv
if "--" not in argv:
    argv = []  # as if no args are passed
else:
    argv = argv[argv.index("--") + 1:]  # get all args after "--"

parser = argparse.ArgumentParser()
parser.add_argument('--path', required=True, help='path to blender template: nengo_app')
parser.add_argument('--link-only', help='for development', action='store_true')
parser.add_argument('--force', help='First, remove existing template', action='store_true')
args = parser.parse_args(args=argv)

nengo_app_possible_path = os.path.join(bpy.utils.resource_path('USER'),
                                       r'scripts\startup\bl_app_templates_user\nengo_app')

assert nengo_app_possible_path in bpy.utils.app_template_paths()

if args.force:
    import shutil

    if os.path.exists(nengo_app_possible_path):
        shutil.rmtree(nengo_app_possible_path)

if args.link_only:
    # better for development for live changes
    def create_link(directory: str, link_path: str) -> None:
        if os.path.exists(link_path):
            os.remove(link_path)

        if sys.platform == "win32":
            import _winapi
            _winapi.CreateJunction(str(directory), str(link_path))
        else:
            os.symlink(str(directory), str(link_path), target_is_directory=True)


    os.makedirs(os.path.dirname(nengo_app_possible_path), exist_ok=True)
    create_link(directory=args.path, link_path=nengo_app_possible_path)
else:
    # handled by blender, more reliable
    def make_zip(destination: str) -> str:
        import zipfile

        ziph = zipfile.ZipFile(f'{destination}.zip', 'w')
        for root, dirs, files in os.walk(destination):
            for file in files:
                ziph.write(os.path.join(root, file),
                           os.path.relpath(os.path.join(root, file),
                                           os.path.join(destination, '..')))
        return f'{destination}.zip'


    nengo_app_zip = make_zip(args.path)
    result = bpy.ops.preferences.app_template_install(overwrite=True, filepath=nengo_app_zip)

    if 'FINISHED' not in result:
        exit(111)
