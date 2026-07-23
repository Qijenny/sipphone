[app]

# (str) Title of your application
title = 国贸游泳馆值班呼叫系统

# (str) Package name
package.name = sipphone

# (str) Package domain (needed for android/ios packaging)
package.domain = com.gyhd.tsg

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,tcl,txt,wav

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy=1.11.1,numpy
requirements = python3==3.9,kivy==2.2.0,pyjnius,android

# (str) Presplash of the application
# presplash.filename = %(source.dir)s/presplash.png

# (str) Icon of the application
# icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET,RECORD_AUDIO,MODIFY_AUDIO_SETTINGS,WAKE_LOCK,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

# (int) Android API to use
android.api = 31

# (int) Minimum API required (default 21)
# android.minapi = 21

# (int) Android SDK version to use
# android.sdk = 20

# (str) Android NDK version to use
# android.ndk = 23b

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
# android.ndk_path =

# (str) ANT home directory
# ant.dir =

# (bool) If True, then skip trying to update the Android SDK
# We can set this to True if you don't want to update the Android SDK (or if you have issues)
# android.skip_update = True

# (bool) If True, then automatically accept SDK license
# android.accept_sdk_license = True

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.renpy.android.PythonActivity

# (list) Pattern to whitelist for the whole project
#android.whitelist =

# (str) Path to a custom temp.txt file to override the default one
#android.temp.txt =

# (str) Path to a custom blacklist file to override the default one
# (list) List of Java .kt files to be included
#android.add_aars =

# (list) List of Java .aar files to be included
#android.add_jars =

# (str) python-for-android branch to use, defaults to master
#p4a.branch = master

# (str) OUYA Console category. Should be one of GAME or APP
# If you leave this empty, your application will be placed in the default (GAME) category
# ouya.category = GAME

# (str) Filename of the main .py file
# main.cx_freeze is the default
# main.filename = main.py

# (str) Name of the directory containing the main.py file
# main.cx_freeze_pyinstaller_dir =

# (bool) Indicate whether the app is a game (True) or not (False)
# Used by some Android emulators to improve rendering
# android.app_icon_game = False

# (str) Activity class name. This is the name of the main Activity class in your
# Android manifest. If you leave this empty, the default Activity class
# name (org.kivy.android.PythonActivity) will be used.
# android.activity_class_name =

# (str) Activity title. This is the title of the main Activity in your
# Android manifest. If you leave this empty, the default Activity title
# (Kivy) will be used.
# android.activity_title = Kivy

# (list) Python for Android whitelist
#android.p4a_whitelist =


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (default))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 0


# -----------------------------------------------------------------------------
# Options specific to android
# -----------------------------------------------------------------------------

# (str) Whether to use SDL2 or pygame as the main renderer
# p4a.renderer = sdl2

# (str) Whether to use SDL2 or pygame as the audio renderer
# p4a.audio = sdl2

# (int) SDL2 window mode (0 = windowed, 1 = fullscreen, 2 = borderless)
# p4a.window.mode = 0

# (str) Whether to use Android's native TextView or SDL2
# p4a.text = sdl2

# (int) Whether to enable SDL2's window resize
# p4a.window.resize = 0

# (str) Whether to use TextInput or Label widgets for input
# p4a.input = sdl2

# (int) Android logcat logging level
# android.logcat = info

# -----------------------------------------------------------------------------
# Options specific to iOS
# -----------------------------------------------------------------------------

# (str) Path to the directory where to put iOS files
# ios.force_fullscreen = 0

# (str) Path to a .plist file containing the application metadata
# ios.info =

# (str) Supported orientation (one of landscape, portrait, all)
# ios.orientation = landscape

# (bool) Indicate if the application should be fullscreen or not
# ios.fullscreen = 0

# (str) Bundle identifier
# ios.identifier =

# (str) Name of the application as displayed on the home screen
# ios.shortname =
