# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# 获取Python路径
python_path = os.path.dirname(sys.executable)

# 收集所有依赖项
datas = []
binaries = []

# 添加所有必要的运行时DLL
runtime_dlls = [
    'vcruntime140.dll',
    'vcruntime140_1.dll',
    'msvcp140.dll',
    'python3*.dll',  # 将匹配所有Python 3.x的DLL
]

# 添加Python DLL
for file in os.listdir(python_path):
    if any(file.lower().startswith(dll.lower().replace('*', '')) for dll in runtime_dlls):
        full_path = os.path.join(python_path, file)
        if os.path.isfile(full_path):
            binaries.append((full_path, '.'))

# 添加pylink-square完整依赖
pylink_datas = []
pylink_binaries = []
try:
    from pylink import __path__ as pylink_path
    pylink_dir = pylink_path[0]
    
    # 收集所有pylink子模块
    pylink_imports = collect_submodules('pylink')
    
    # 收集所有pylink相关文件
    for root, dirs, files in os.walk(pylink_dir):
        for file in files:
            # 包含所有文件类型，确保完整功能
            rel_dir = os.path.relpath(root, pylink_dir)
            if rel_dir == '.':
                rel_dir = 'pylink'
            else:
                rel_dir = os.path.join('pylink', rel_dir)
            
            full_path = os.path.join(root, file)
            if file.lower().endswith(('.dll', '.so', '.dylib')):
                pylink_binaries.append((full_path, rel_dir))
            else:
                pylink_datas.append((full_path, rel_dir))
except ImportError:
    pass

# 收集项目模块
project_modules = [
    'config',
    'device_selector',
    'forwarder',
    'gui_manager',
    'rtt_manager',
    'udp_manager'
]

# 收集所有项目模块的依赖
for module in project_modules:
    module_datas, module_binaries, module_hiddenimports = collect_all(module)
    datas.extend(module_datas)
    binaries.extend(module_binaries)

# 确保包含tkinter完整依赖
import tkinter
tcl_tk_dirs = []

# 在Python安装目录下查找tcl/tk
for root, dirs, files in os.walk(python_path):
    if 'tcl' in dirs:
        tcl_path = os.path.join(root, 'tcl')
        if os.path.isdir(tcl_path):
            tcl_tk_dirs.append((tcl_path, 'tcl'))
    if 'tk' in dirs:
        tk_path = os.path.join(root, 'tk')
        if os.path.isdir(tk_path):
            tcl_tk_dirs.append((tk_path, 'tk'))

# 在DLLs目录下查找tk/tcl DLL
dlls_path = os.path.join(python_path, 'DLLs')
if os.path.exists(dlls_path):
    for file in os.listdir(dlls_path):
        if file.lower().startswith(('tk', 'tcl')) and file.lower().endswith('.dll'):
            binaries.append((os.path.join(dlls_path, file), '.'))

# 添加找到的tcl/tk目录
datas.extend(tcl_tk_dirs)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries + pylink_binaries,
    datas=datas + pylink_datas,
    hiddenimports=[
        'tkinter', 
        'tkinter.ttk', 
        'tkinter.messagebox', 
        'tkinter.scrolledtext',
        'pylink',
        'pylink.jlink',
        'socket',
        'select',
        'json',
        're',
        'threading',
        'queue',
        'logging'
    ] + project_modules + pylink_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RTT2UDP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False以隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
