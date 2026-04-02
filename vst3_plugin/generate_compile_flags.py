#!/usr/bin/env python3
"""Generate compile_flags.txt and .clangd for the VST3 plugin based on current environment."""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent


def get_python_include():
    return subprocess.check_output(
        [sys.executable, "-c", "import sysconfig; print(sysconfig.get_path('include'))"],
        text=True,
    ).strip()


def get_pybind11_include():
    return subprocess.check_output(
        [sys.executable, "-c", "import pybind11; print(pybind11.get_include())"],
        text=True,
    ).strip()


def get_juce_include():
    juce_modules = SCRIPT_DIR / "JUCE" / "modules"
    if juce_modules.is_dir():
        return str(juce_modules)
    return ""


def main():
    python_inc = get_python_include()
    pybind11_inc = get_pybind11_include()
    juce_inc = get_juce_include()

    common_flags = [
        "-std=c++17",
        "-x",
        "c++",
        f"-I{SCRIPT_DIR}/Source",
        f"-I{SCRIPT_DIR}",
        f"-I{python_inc}",
        f"-I{pybind11_inc}",
        f"-I{pybind11_inc}/include",
        "-DJUCE_GLOBAL_MODULE_SETTINGS_INCLUDED=1",
        "-DJUCE_PLUGINHOST_VST3=1",
        "-DJUCE_WEB_BROWSER=0",
        "-DJUCE_USE_CURL=0",
        "-DJUCE_VST3_CAN_REPLACE_VST2=0",
    ]

    if juce_inc:
        common_flags.insert(2, f"-I{juce_inc}")

    # Write compile_flags.txt
    compile_flags = SCRIPT_DIR / "compile_flags.txt"
    compile_flags.write_text("\n".join(common_flags) + "\n")
    print(f"Generated {compile_flags}")

    # Write .clangd
    clangd_config = {
        "CompileFlags": {"Add": common_flags},
        "Diagnostics": {"UnusedIncludes": "Strict"},
        "InlayHints": {"Enabled": True},
    }
    clangd_file = SCRIPT_DIR / ".clangd"
    clangd_file.write_text(json.dumps(clangd_config, indent=2) + "\n")
    print(f"Generated {clangd_file}")

    # Write compile_commands.json for full IDE support
    compile_commands = [
        {
            "directory": str(SCRIPT_DIR),
            "command": f"c++ {' '.join(common_flags)} -c Source/PluginProcessor.cpp",
            "file": str(SCRIPT_DIR / "Source" / "PluginProcessor.cpp"),
        },
        {
            "directory": str(SCRIPT_DIR),
            "command": f"c++ {' '.join(common_flags)} -c Source/PluginEditor.cpp",
            "file": str(SCRIPT_DIR / "Source" / "PluginEditor.cpp"),
        },
        {
            "directory": str(SCRIPT_DIR),
            "command": f"c++ {' '.join(common_flags)} -c Source/PythonIntegration.cpp",
            "file": str(SCRIPT_DIR / "Source" / "PythonIntegration.cpp"),
        },
        {
            "directory": str(SCRIPT_DIR),
            "command": f"c++ {' '.join(common_flags)} -c Source/XGParameterManager.cpp",
            "file": str(SCRIPT_DIR / "Source" / "XGParameterManager.cpp"),
        },
    ]
    compile_commands_file = SCRIPT_DIR / "compile_commands.json"
    compile_commands_file.write_text(json.dumps(compile_commands, indent=2) + "\n")
    print(f"Generated {compile_commands_file}")


if __name__ == "__main__":
    main()
