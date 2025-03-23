# -*- mode: python ; coding: utf-8 -*-
import os

# Get project directory (where the spec file is located)
project_dir = os.path.dirname(os.path.abspath(SPECPATH))
inventory_dir = os.path.join(project_dir, 'inventoryManager')

a = Analysis(
    [os.path.join(inventory_dir, 'mainCron.py')],
    pathex=[inventory_dir],
    binaries=[],
    datas=[
        # Include JSON credentials file
        (os.path.join(inventory_dir, 'nextdayaccess-452516-a51a5b7a02b8.json'), '.'),
        # Include the .env file
        (os.path.join(project_dir, '.env'), '.')
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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
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