# -*- mode: python ; coding: utf-8 -*-
import os

# Define exact paths to our files
base_dir = '/Users/slaterbohm/projects/nextDayAccess'
inventory_dir = os.path.join(base_dir, 'inventoryManager')
mainCron_path = os.path.join(inventory_dir, 'mainCron.py')
env_file_path = os.path.join(base_dir, '.env')
json_file_path = os.path.join(inventory_dir, 'nextdayaccess-452516-a51a5b7a02b8.json')

a = Analysis(
    [mainCron_path],
    pathex=[inventory_dir],
    binaries=[],
    datas=[
        # CSV file is no longer bundled - will be provided as a command-line argument
        (json_file_path, '.'),
        (env_file_path, '.')
    ],
    hiddenimports=[
        'getterFunctions',
        'queryCost',
        'config',
        'googleSheetsManager',
        'requests',
        'json',
        'pprint',
        'argparse',
        'csv',
        'os',
        'dotenv'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mainCron',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
