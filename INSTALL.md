# Installing White Pepper CLI Engine

The **White Pepper CLI Engine** is the standalone command-line scanner and document processing suite. It can be installed as a Windows utility with PATH integration, as a Python package via pip/wheel, or used portably.

---

## 1. Windows Setup Installer (`WhitePepper-CLI-Setup-v1.3.0.exe`)

The Windows CLI setup wizard installs the CLI scripts and command launcher batch wrappers with optional automatic PATH registration.

### Step-by-Step Installation:
1. Download **`WhitePepper-CLI-Setup-v1.3.0.exe`** from the [GitHub Releases](https://github.com/AceBurgundy/white_pepper_scripts/releases) page.
2. Run the installer.
3. Select your desired destination folder (Default: `%LOCALAPPDATA%\Programs\White Pepper CLI` or `C:\Program Files\White Pepper CLI`).
4. **Environment Variables**:
   - Check **Add White Pepper CLI (bin/) to user PATH environment variable**.
   - This allows you to run `scan-cli`, `process-cli`, and `diagnostics-cli` directly from any Command Prompt or PowerShell window.
5. Click **Install**.
6. When finished, open a new terminal window and verify:
   ```cmd
   scan-cli --help
   process-cli --help
   diagnostics-cli --json
   ```

---

## 2. Python Package Installation (`pip`)

You can also install White Pepper CLI into any Python 3.10+ virtual environment:

### From PyPI / GitHub Wheel:
```bash
pip install white_pepper_scanner-1.3.0-py3-none-any.whl
```

### From Local Source Repository:
```bash
cd scripts
pip install -r requirements.txt
pip install -e .
```

---

## 3. Uninstalling White Pepper CLI

- **Windows Installer Version**:
  - Open **Windows Settings** → **Apps** → **Installed Apps** → search for **White Pepper CLI Engine** → click **Uninstall**.
  - Or run `unins000.exe` in the installation folder.
  - The uninstaller automatically removes the CLI directory, Start Menu shortcuts, and PATH environment variable entries cleanly.
- **Pip Version**:
  ```bash
  pip uninstall white-pepper-scanner
  ```
