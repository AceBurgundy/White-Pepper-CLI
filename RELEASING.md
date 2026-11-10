# Release Guide — White Pepper CLI Engine

This document outlines the build and release workflow for packaging the standalone White Pepper CLI Engine.

---

## 1. Automated GitHub Actions Release Workflow

The repository includes a GitHub Actions workflow at [`.github/workflows/release-cli.yml`](./.github/workflows/release-cli.yml) that triggers automatically when a version tag is pushed:

```bash
git tag -a v1.3.0 -m "Release v1.3.0 milestone"
git push origin v1.3.0
```

GitHub Actions will automatically:
1. Check out the repository.
2. Build standard Python distribution wheels (`.whl`) and source archives (`.tar.gz`) via `python -m build`.
3. Run Inno Setup Compiler (`ISCC.exe`) to generate `WhitePepper-CLI-Setup-v1.3.0.exe`.
4. Compress a portable ZIP archive `WhitePepper-CLI-Portable.zip`.
5. Publish all artifacts directly to the GitHub Release.

---

## 2. Local Installer Compilation (PowerShell)

To build the CLI installer locally:

```powershell
powershell -ExecutionPolicy Bypass -File installer\build_cli_installer.ps1
```

The resulting installer is saved in:
```text
installer\output\WhitePepper-CLI-Setup-v1.3.0.exe
```
