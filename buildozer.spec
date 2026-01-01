[app]

# Nombre de la aplicación
title = SIAM

# Nombre del paquete
package.name = siam

# Dominio del paquete (usado para el identificador completo)
package.domain = com.richard

# Código fuente principal
source.dir = .

# Extensiones a incluir
source.include_exts = py,png,jpg,kv,atlas,json,ttf,otf

# Patrones a incluir
source.include_patterns = assets/*,images/*,vista/*,controlador/*,modelo/*

# Patrones a excluir
source.exclude_patterns = license,images/*/.git,hoja de ruta/*,tools/*,*.md,tests/*

# Versión de la aplicación
version = 0.1.0

# Requisitos de la aplicación
requirements = python3,kivy==2.3.1,kivymd==2.0.1.dev0,pillow,pyzbar,opencv,android,plyer

# Permisos de Android
android.permissions = CAMERA,INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Características de Android
android.features = android.hardware.camera,android.hardware.camera.autofocus

# Orientación de pantalla
orientation = portrait

# Pantalla completa
fullscreen = 0

# Ícono de la aplicación (crear assets/icon.png de 512x512)
#icon.filename = assets/icon.png

# Presplash/splash screen
#presplash.filename = assets/presplash.png

# API de Android (target)
android.api = 33

# API mínima de Android
android.minapi = 21

# NDK API
android.ndk_api = 21

# SDK y NDK (Buildozer los descarga automáticamente)
#android.sdk_path =
#android.ndk_path =

# Arquitecturas a compilar
android.archs = arm64-v8a,armeabi-v7a

# Aceptar licencias automáticamente
android.accept_sdk_license = True

# Gradle dependencies para cámara
android.gradle_dependencies = androidx.camera:camera-camera2:1.1.0

# Activar AndroidX
android.enable_androidx = True

# Archivo de entrada
#android.entrypoint = org.kivy.android.PythonActivity

# Whitelist de permisos
android.whitelist = lib-dynload/_csv.so

# Modo de compilación
#android.release_artifact = apk
#android.debug_artifact = apk

# Logcat filters
android.logcat_filters = *:S python:D

# Copiar bibliotecas
#android.copy_libs = 1

# Metadatos adicionales
#android.meta_data =

# Características de la pantalla
android.screen = normal,large,xlarge

[buildozer]

# Nivel de log (0 = error, 1 = info, 2 = debug)
log_level = 2

# Mostrar advertencias
warn_on_root = 1

# Directorio de build
build_dir = ./.buildozer

# Directorio de salida del APK
bin_dir = ./bin
