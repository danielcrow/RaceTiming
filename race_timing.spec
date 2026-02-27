# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Race Timing System desktop application.
Build with:  pyinstaller race_timing.spec
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821  (SPECPATH injected by PyInstaller)

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Flask templates and static assets
        ('templates',  'templates'),
        ('static',     'static'),
        # Workspace / example config shipped with the bundle
        ('.env.example', '.'),
        ('workspace_config.yaml', '.'),
        ('llrp_config.example.json', '.'),
    ],
    hiddenimports=[
        # SQLAlchemy dialects
        'sqlalchemy.dialects.sqlite',
        'sqlalchemy.dialects.postgresql',
        # Flask internals
        'flask',
        'flask_cors',
        'jinja2',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.debug',
        # Project modules (PyInstaller may miss dynamic imports)
        'web_app',
        'database',
        'models',
        'config_manager',
        'race_manager',
        'race_control',
        'race_templates',
        'results_publisher',
        'report_generator',
        'reader_service',
        'reader',
        'llrp_station_manager',
        'tag_detection',
        'import_utils',
        # Third-party
        'requests',
        'qrcode',
        'qrcode.image.pil',
        'PIL',
        'PIL.Image',
        'numpy',
        'click',
        'tabulate',
        'dateutil',
        'dotenv',
        'psycopg2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy packages not needed at runtime
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
        'notebook',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RaceTimingSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # keep console visible so log output is readable
    icon=None,      # replace with 'static/images/icon.ico' if available
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RaceTimingSystem',
)