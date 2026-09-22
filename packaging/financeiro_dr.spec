from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).resolve().parent.parent
src = root / "src"
migrations = src / "financeiro_dr" / "database" / "migrations"

hiddenimports = collect_submodules("argon2")

a = Analysis(
    [str(src / "financeiro_dr" / "main.py")],
    pathex=[str(src)],
    binaries=[],
    datas=[(str(migrations), "financeiro_dr/database/migrations")],
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="FinanceiroPessoalDr",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FinanceiroPessoalDr",
)
