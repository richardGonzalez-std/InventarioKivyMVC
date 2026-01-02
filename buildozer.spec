[app]

# (str) Title of your application
title = SIAM

# (str) Package name
package.name = siam

# (str) Package domain (needed for android/ios packaging)
package.domain = com.richard

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,db,json

# (list) List of directories to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, venv, .venv, .buildozer, __pycache__, hoja de ruta, tools

# (str) Application versioning
version = 0.1

# (list) Application requirements
requirements = python3,kivy,pillow,pyjnius,https://github.com/kivymd/KivyMD/archive/master.zip,materialyoucolor,materialshapes,asyncgui,asynckivy

# (list) Supported orientations
orientation = portrait

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET, CAMERA, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (list) The Android archs to build for
android.archs = armeabi-v7a, arm64-v8a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

#
# Python for android (p4a) specific
#

# (str) python-for-android branch to use
#p4a.branch = master

#
# iOS specific
#

ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master

ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0

ios.codesign.allowed = false

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
