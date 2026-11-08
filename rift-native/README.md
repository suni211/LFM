# R/M native migration

Native C++ UI and career storage using SDL3, RmlUi and FreeType.
Dependency revisions are recorded in vendor/versions.txt.

## Build

    cmake -S . -B build -G "Visual Studio 17 2022" -A x64
    cmake --build build --config Release --parallel 6

Run build/Release/RiftManagerNative.exe with its adjacent assets directory.

Implemented migration scope: Korean text input through the SDL IME backend,
R/M icon, F11, club creation or existing-club selection, career save/load,
72-week progression, and the sourced personnel directory with 150 rows per page.

Native saves use SDL_GetPrefPath("RiftManager", "Native").
The Python save format and match engine are not yet migrated.
No match starts from opening the UI or advancing a week in this migration build.
The scheduled match service, server authority, web build, and Android APK are pending.

SDL's renderer selects the available graphics driver. This application does
not implement a custom OpenGL renderer. Graphics drivers vary by platform.
Web and Android require their respective toolchains and platform checks.
