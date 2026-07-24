# Releases / standalone builds

English. Русский: [../ru/RELEASES.md](../ru/RELEASES.md).

## What GitHub Releases contain

On each git tag `v*` (example: `v0.1.0`), [`.github/workflows/release.yml`](../../.github/workflows/release.yml) builds **PyInstaller** one-file binaries for:

| Artifact zip | Runner | Notes |
|--------------|--------|--------|
| `smart_convert_nvenc-windows-amd64.zip` | `windows-latest` | `.exe` for CLI + GUI |
| `smart_convert_nvenc-linux-amd64.zip` | `ubuntu-latest` | ELF binaries |
| `smart_convert_nvenc-macos-arm64.zip` | `macos-latest` | Apple Silicon (GitHub’s current macOS runners) |

Each zip includes:

- `smart-convert`
- `smart-convert-course`
- `smart-convert-gui`
- `README.md`, `LICENSE`, `README-RELEASE.txt`

## Important: FFmpeg is still required

These builds **do not** ship FFmpeg or NVIDIA drivers.

You still need on the machine:

1. FFmpeg with `hevc_nvenc` + `av1_nvenc` on `PATH`
2. An NVIDIA GPU + driver for actual NVENC encode

macOS/Linux packages exist so the app can run where Python packaging is awkward, but **NVENC encode is NVIDIA-centric**. On Mac without NVIDIA NVENC, CLI/GUI can start, but encoding will fail environment checks unless a suitable FFmpeg/GPU stack exists.

## How to cut a release

1. Update `__version__` in `src/smart_convert_nvenc/__init__.py` (single source of truth; hatch reads it).
2. Move items from **Unreleased** into a new section in [CHANGELOG.md](../../CHANGELOG.md) and [CHANGELOG.ru.md](../../CHANGELOG.ru.md).
3. Commit, then tag matching the version:

```powershell
git tag v0.1.2
git push origin v0.1.2
```

Or run the **Release** workflow manually (`workflow_dispatch`) from the Actions tab.

CLI/GUI expose the same version via `smart-convert --version` / window title.

## Local build (optional)

```powershell
uv sync --group release
uv run pyinstaller --onefile --name smart-convert scripts/pyi_smart_convert.py
uv run pyinstaller --onefile --name smart-convert-course scripts/pyi_smart_convert_course.py
uv run pyinstaller --onefile --windowed --collect-all customtkinter --name smart-convert-gui scripts/pyi_smart_convert_gui.py
```

Outputs land in `dist/`.
