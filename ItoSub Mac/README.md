# ItoSub for macOS

This folder builds a native `ItoSub.app`, ZIP archive, and DMG. People using the
finished app do **not** need Python or a virtual environment.

The build must run on macOS. PyInstaller cannot create a macOS application from
Windows.

## Supported build machines

- Apple Silicon (`arm64`): M1 or newer, recommended.
- Intel Mac (`x86_64`): supported as a separate build.
- macOS 12 or newer.
- Python 3.11, 3.12, or 3.13 for the build only.

The resulting package matches the architecture of the Mac that builds it. Build
on Apple Silicon for Apple Silicon Macs and on Intel for Intel Macs.

## Recommended: build with GitHub Actions

The repository includes `.github/workflows/build-macos.yml`. This route does not
require Python on your Windows machine or destination Mac.

1. Push this repository to GitHub.
2. Open the repository's **Actions** tab.
3. Select **Build ItoSub for macOS**.
4. Choose **Run workflow**.
5. When it finishes, download the `ItoSub-macOS-arm64` artifact.
6. Extract it to get the ZIP and DMG packages.

The workflow builds for Apple Silicon (M1 or newer). Use the local build method
below when an Intel Mac package is required.

## Build on a Mac

Open Terminal in the repository root and run:

```bash
chmod +x "ItoSub Mac/build_macos.sh"
"ItoSub Mac/build_macos.sh"
```

If Python is missing, install Python 3.12 once on the build Mac:

```bash
brew install python@3.12
PYTHON_BIN="$(brew --prefix python@3.12)/bin/python3.12" \
  "ItoSub Mac/build_macos.sh"
```

Build outputs are written to:

```text
ItoSub Mac/dist/ItoSub.app
ItoSub Mac/dist/ItoSub-macOS-arm64.zip
ItoSub Mac/dist/ItoSub-macOS-arm64.dmg
```

On an Intel build Mac, the filenames use `x86_64` instead of `arm64`.

## Run on the destination Mac

1. Open the DMG.
2. Copy `ItoSub.app` into `/Applications`.
3. Control-click ItoSub and choose **Open** for the first unsigned test build.
4. Allow microphone access when macOS asks.
5. Select the microphone and caption language, then press **Start**.

The destination Mac does not need Python. The first use needs internet because
Whisper and Argos download their selected speech/translation models into the
user's cache. Rehearse once before the presentation so these models are already
installed and warmed up.

## Signing for distribution

Unsigned builds are suitable for testing on Macs you control. Public
distribution should use an Apple Developer ID certificate and notarization.

To make PyInstaller sign with an available Developer ID certificate:

```bash
export ITOSUB_CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)"
"ItoSub Mac/build_macos.sh"
```

Notarization is a separate release step performed after the DMG is created.

## Important presentation notes

- Build and test on the same Mac architecture used at the presentation.
- Launch each caption direction once while online so its Argos model is present.
- Test the real microphone or venue mixer feed before the event.
- Keep the Mac connected to power and disable automatic sleep.
