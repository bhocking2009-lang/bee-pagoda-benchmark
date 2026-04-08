import importlib.util
import subprocess
import sys


# Python packages required by the Python CLI components.
_PYTHON_DEPS = {
    "typer": "typer",       # CLI framework
    "yaml": "pyyaml",       # profile loading (import name differs from package name)
}

# System tools expected for benchmark execution.  These are checked via PATH
# rather than Python imports.  All are optional: missing ones are reported but
# do not prevent the suite from running (individual benchmark scripts degrade
# gracefully when tools are absent).
_SYSTEM_TOOLS = [
    "sysbench",
    "fio",
    "ffmpeg",
    "7z",
    "openssl",
]


def verify_deps() -> bool:
    """Check Python package and system tool availability.

    Returns True when all *required* Python packages are present.
    System tools are reported informatively but never cause a False return.
    """
    missing_python = []
    for import_name, package_name in _PYTHON_DEPS.items():
        if importlib.util.find_spec(import_name) is None:
            missing_python.append(package_name)

    if missing_python:
        print("Missing Python dependencies: " + ", ".join(missing_python))
        print("Install with: pip install " + " ".join(missing_python))
        return False

    print("Python dependencies: OK")

    missing_tools = []
    for tool in _SYSTEM_TOOLS:
        try:
            result = subprocess.run(
                ["command", "-v", tool],
                shell=False,
                capture_output=True,
                executable="/bin/sh",
            )
            if result.returncode != 0:
                missing_tools.append(tool)
        except Exception:
            # Fallback: try with which
            try:
                subprocess.run(["which", tool], check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing_tools.append(tool)

    if missing_tools:
        print("Optional system tools not found (benchmarks will degrade gracefully): "
              + ", ".join(missing_tools))
    else:
        print("System tools: OK")

    return True

