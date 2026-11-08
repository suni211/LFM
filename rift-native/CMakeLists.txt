cmake_minimum_required(VERSION 3.21)
project(RiftManagerNative LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_DISABLE_PRECOMPILE_HEADERS ON)
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)
if(MSVC)
    add_compile_options(/utf-8)
endif()
set(BUILD_SHARED_LIBS OFF)

set(FT_DISABLE_ZLIB ON CACHE BOOL "" FORCE)
set(FT_DISABLE_BZIP2 ON CACHE BOOL "" FORCE)
set(FT_DISABLE_PNG ON CACHE BOOL "" FORCE)
set(FT_DISABLE_HARFBUZZ ON CACHE BOOL "" FORCE)
set(FT_DISABLE_BROTLI ON CACHE BOOL "" FORCE)
add_subdirectory(vendor/freetype)
if(NOT TARGET Freetype::Freetype)
    add_library(Freetype::Freetype ALIAS freetype)
endif()

set(SDL_SHARED OFF CACHE BOOL "" FORCE)
set(SDL_STATIC ON CACHE BOOL "" FORCE)
set(SDL_TEST OFF CACHE BOOL "" FORCE)
set(SDL_TESTS OFF CACHE BOOL "" FORCE)
set(SDL_EXAMPLES OFF CACHE BOOL "" FORCE)
add_subdirectory(vendor/SDL)

set(SDLIMAGE_SAMPLES OFF CACHE BOOL "" FORCE)
set(SDLIMAGE_TESTS OFF CACHE BOOL "" FORCE)
add_subdirectory(vendor/SDL_image)

set(RMLUI_SAMPLES OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
add_subdirectory(vendor/RmlUi)

set(APP_SOURCES
    src/main.cpp
    vendor/RmlUi/Backends/RmlUi_Backend_SDL_SDLrenderer.cpp
    vendor/RmlUi/Backends/RmlUi_Platform_SDL.cpp
    vendor/RmlUi/Backends/RmlUi_Renderer_SDL.cpp
)

function(rift_native_app name)
    add_executable(${name} ${APP_SOURCES})
    target_include_directories(${name} PRIVATE
        vendor
        vendor/RmlUi/Backends
        vendor/RmlUi/Include
        vendor/SDL/include
        vendor/SDL_image/include
    )
    target_compile_definitions(${name} PRIVATE RMLUI_SDL_VERSION_MAJOR=3 RMLUI_STATIC_LIB ${ARGN})
    target_compile_options(${name} PRIVATE $<$<CXX_COMPILER_ID:MSVC>:/utf-8>)
    target_link_libraries(${name} PRIVATE rmlui SDL3-static SDL3_image-static freetype winhttp bcrypt)
    add_custom_command(TARGET ${name} POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory "${CMAKE_SOURCE_DIR}/assets" "$<TARGET_FILE_DIR:${name}>/assets")
endfunction()

rift_native_app(RiftManagerNative)
