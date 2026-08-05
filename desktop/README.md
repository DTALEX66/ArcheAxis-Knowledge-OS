# Windows desktop

## Normal installation

The normal Windows installation keeps application data in the current user's local application-data directory. Uninstalling the application does not automatically mean that local data is deleted; remove it only after confirming that the data is no longer needed.

## Portable copy

A portable copy keeps runtime data beside the copied desktop executable. Copy the executable, its `runtime` directory, and the two files in `desktop/portable/` into one directory. Start `launch_portable.bat` or `launch_portable.ps1`; the launcher creates a `data` directory beside the executable and sets the explicit `COGNITIVE_PORTABLE_ROOT` boundary before starting the application.

The portable launcher is fail-closed when the executable is missing. The desktop runtime also rejects a relative portable root, and it does not fall back to the user's profile when `COGNITIVE_PORTABLE_ROOT` is present.

Portable data includes the local database, logs, backend runtime state, and the WebView profile. Keep the executable, `runtime`, launcher, and `data` directory together when moving the copy to another location. Close the application before copying or backing up the directory.

## Verification boundary

The portable mode is separate from a normal installation and from the repository's development runtime. CI and local checks must use an isolated project-owned runtime directory; portable data must not be written into the source checkout or the global Hermes runtime.

## Current limitations

This document describes the data-boundary and lifecycle contract. It does not claim that every Workspace navigation area is a complete user workflow, nor that a local build is a public release.
