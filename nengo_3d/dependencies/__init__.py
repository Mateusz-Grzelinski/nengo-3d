import filecmp
import logging
import os
import shutil
import subprocess
import sys


# todo verify modules and its installation path (if blender can actually use them)
def install(blender_exe: str = 'blender.exe'):
    BLENDER_EXE_PATH = blender_exe
    BLENDER_PIP_MODULES = ['marshmallow', 'graphviz', 'networkx', 'pydot', 'scipy']

    current_dir = os.path.dirname(os.path.realpath(__file__))
    command = [BLENDER_EXE_PATH, '--background', '--python-exit-code', '111',
               '--python', os.path.join(current_dir, 'blender_app_template_check.py'),
               ]
    logging.debug(f'Running blender check: {" ".join(command)}')
    result = subprocess.run(command)

    BLENDER_NENGO_TEMPLATE = os.path.join(current_dir, '..', 'nengo_app')

    # install nengo app template
    if result.returncode == 111:
        logging.info('Installing blender template')
        command = [BLENDER_EXE_PATH, '--background', '--python-exit-code', '111',
                   '--python', os.path.join(current_dir, 'blender_app_template_install.py'),
                   '--', '--path', BLENDER_NENGO_TEMPLATE, '--link-only', '--force'
                   ]
        logging.debug(f'Running blender install: {" ".join(command)}')
        subprocess.check_call(command)
        logging.info(f'Blender nengo template is installed"')

    BLENDER_PIP_MODULES_PATH = os.path.join(BLENDER_NENGO_TEMPLATE, 'blender_pip_modules')

    # check 3rd party modules
    if not os.path.exists(BLENDER_PIP_MODULES_PATH):
        command = [sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', '--target',
                   BLENDER_PIP_MODULES_PATH, *BLENDER_PIP_MODULES]
        logging.debug(f'Running pip check: {" ".join(command)}')
        subprocess.check_call(command)

    NENGO_3D_SCHEMAS = os.path.join(BLENDER_PIP_MODULES_PATH, 'nengo_3d_schemas.py')
    NENGO_3D_SCHEMAS_DST = os.path.join(current_dir, '..', 'nengo_3d_schemas.py')

    # check internal shared communication protocols
    # windows does not support (well) file symlinks
    if not os.path.exists(NENGO_3D_SCHEMAS):
        shutil.copy(NENGO_3D_SCHEMAS_DST, NENGO_3D_SCHEMAS)
    elif not filecmp.cmp(NENGO_3D_SCHEMAS, NENGO_3D_SCHEMAS_DST, shallow=True):
        os.remove(NENGO_3D_SCHEMAS)
        shutil.copy(NENGO_3D_SCHEMAS_DST, NENGO_3D_SCHEMAS)
