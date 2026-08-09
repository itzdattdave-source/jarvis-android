# JARVIS Android Build Project

This project is prepared for a free GitHub Actions + Buildozer Android build.

IMPORTANT:
- `JARVIS_V2_DESKTOP_SOURCE.py` is the original desktop JARVIS source.
- The current desktop source contains Windows-specific APIs/libraries and cannot be
  honestly claimed to be a working Android app without further porting.
- `main.py` is an Android-compatible Kivy scaffold so the cloud APK pipeline has
  a valid Android target.
- `buildozer.spec` and `.github/workflows/build-apk.yml` are ready for a GitHub
  Actions build.

Next:
1. Upload this whole project to a GitHub repository.
2. Open Actions -> Build JARVIS APK -> Run workflow.
3. Download the generated APK artifact.

No Google Play publishing is required for a debug APK.
