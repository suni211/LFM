@echo off
cd /d "%~dp0"
if exist "dist\RiftManagerNative.exe" (
  start "" "%~dp0dist\RiftManagerNative.exe"
) else if exist "build\Release\RiftManagerNative.exe" (
  start "" "%~dp0build\Release\RiftManagerNative.exe"
) else (
  echo RiftManagerNative.exe 가 없습니다.
  pause
)
