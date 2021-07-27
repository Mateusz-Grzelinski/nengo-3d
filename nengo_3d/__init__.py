import os

from .gui import GUI

import logging
import subprocess
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format=f'%(levelname)s:{__name__}:"%(pathname)s:%(lineno)d":%(message)s'
)

BLENDER_EXE_PATH = r'E:\PycharmProjects\nengo_3d_thesis\blender-2.93.1-windows-x64\blender.exe'
BLENDER_PIP_MODULES = ['marshmallow', 'graphviz', 'ogdf-python', 'networkx', 'pydot', 'scipy']

current_dir = os.path.dirname(os.path.realpath(__file__))
command = [BLENDER_EXE_PATH, '--background', '--python-exit-code', '111',
           '--python', os.path.join(current_dir, 'blender_check.py'),
           ]
logging.debug(f'Running blender check: {" ".join(command)}')
result = subprocess.run(command)

if result.returncode == 111:
    logging.info('Installing blender template')

    # first download 3rd party modules
    BLENDER_NENGO_TEMPLATE = os.path.join(current_dir, 'nengo_app')
    BLENDER_PIP_MODULES_PATH = os.path.join(BLENDER_NENGO_TEMPLATE, 'blender_pip_modules')

    if not os.path.exists(BLENDER_PIP_MODULES_PATH):
        command = [sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--target',
                   BLENDER_PIP_MODULES_PATH, *BLENDER_PIP_MODULES]
        logging.debug(f'Running pip check: {" ".join(command)}')
        subprocess.check_call(command)

    # second install app template
    # logging.info(
    #     f'Blender nengo template is ready at: "{BLENDER_NENGO_TEMPLATE}" ({os.stat(BLENDER_NENGO_TEMPLATE).st_size / 1000_000}Mb)')
    command = [BLENDER_EXE_PATH, '--background', '--python-exit-code', '111',
               '--python', os.path.join(current_dir, 'blender_install.py'),
               '--', '--path', BLENDER_NENGO_TEMPLATE, '--link-only', '--force'
               ]
    logging.debug(f'Running blender install: {" ".join(command)}')
    subprocess.check_call(command)
    logging.info(f'Blender nengo template is installed"')
