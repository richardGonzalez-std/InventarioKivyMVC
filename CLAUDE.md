# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a KivyMD-based inventory management application following the MVC pattern. It runs on both Android (mobile) and desktop platforms with platform-specific UIs.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

On desktop, the app opens a 1360x768 window with the AdminScreen. On Android, it loads a mobile UI with bottom navigation.

## Architecture

### MVC Structure

```
controlador/       # Controller layer
  app_controller.py   # Main app (InventoryApp), navigation, permissions
modelo/            # Model layer
  database_abstract.py # DatabaseInterface ABC - contract for DB implementations
  database_dummy.py    # In-memory mock database for development
  inventory_model.py   # Business logic (validates entries/exits, quantity checks)
vista/             # View layer
  screens/            # Python screen classes
    camera_screen.py     # Barcode scanning with pyzbar/OpenCV
    inventory_screen.py  # Generic inventory list screen
    admin_screen.py      # Desktop admin panel
  mobile.kv           # Android UI with bottom MDNavigationBar
  pc.kv               # Desktop UI with sidebar layout
```

### Key Patterns

- **Database abstraction**: `DatabaseInterface` ABC allows swapping implementations (currently only `DummyDatabase`)
- **Platform detection**: `kivy.utils.platform` determines Android vs desktop behavior
- **KivyMD Material Design 3**: Using MD3 widgets with CORPOELEC corporate colors (blue #001A70, red #E31C23)

### Screen Navigation (Mobile)

The mobile app uses `MDScreenManager` with screens named: `camera`, `consumos`, `mantenimiento`, `oficina`. Navigation is handled in `app_controller.py:on_switch_tabs()`.

### Camera/Barcode Scanning

`CameraScreen` handles:
- Android camera permissions via `android.permissions`
- Barcode scanning via `pyzbar` (optional dependency)
- Frame capture using OpenCV

## Dependencies

Key packages:
- `kivy==2.3.1` - UI framework
- `kivymd` - Material Design components (installed from git)
- `pyzbar` + `opencv-python` - Barcode scanning (optional)
- Windows-specific deps are auto-filtered via platform markers
