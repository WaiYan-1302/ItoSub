# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


mac_dir = Path(SPECPATH).resolve()
project_root = mac_dir.parent
target_arch = os.getenv("ITOSUB_TARGET_ARCH") or None
codesign_identity = os.getenv("ITOSUB_CODESIGN_IDENTITY") or None

datas = [(str(project_root / "assets"), "assets")]
binaries = []
hiddenimports = []

# These libraries load models, tokenizers, and native extensions dynamically.
# Collecting them explicitly makes the app independent from a Python install on
# the destination Mac.
for package_name in (
    "argostranslate",
    "ctranslate2",
    "faster_whisper",
    "huggingface_hub",
    "minisbd",
    "onnxruntime",
    "sentencepiece",
    "sounddevice",
    "spacy",
    "stanza",
    "tokenizers",
    "torch",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package_name)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

a = Analysis(
    [str(project_root / "itosub" / "app" / "main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ItoSub",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_arch,
    codesign_identity=codesign_identity,
    entitlements_file=str(mac_dir / "entitlements.plist"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ItoSub",
)
app = BUNDLE(
    coll,
    name="ItoSub.app",
    icon=str(mac_dir / "ItoSubIcon.icns"),
    bundle_identifier="com.itosub.app",
    version="0.0.1",
    info_plist={
        "CFBundleDisplayName": "ItoSub",
        "CFBundleName": "ItoSub",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription": (
            "ItoSub uses microphone audio to create live speech captions and translations."
        ),
        "NSPrincipalClass": "NSApplication",
    },
)
