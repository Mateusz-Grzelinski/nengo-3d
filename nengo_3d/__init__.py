import os

from .gui import GUI

import subprocess
import sys

BLENDER_PIP_MODULES = ['marshmallow', 'graphviz', 'ogdf-python', 'networkx']

script_path = os.path.dirname(os.path.realpath(__file__))
BLENDER_PIP_MODULES_PATH = os.path.join(script_path, 'blender_pip_modules')

if not os.path.exists(BLENDER_PIP_MODULES_PATH):
    command = [sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--target', BLENDER_PIP_MODULES_PATH]
    command.extend(BLENDER_PIP_MODULES)
    subprocess.check_call(command)

if BLENDER_PIP_MODULES_PATH not in sys.path:
    sys.path.append(BLENDER_PIP_MODULES_PATH)
