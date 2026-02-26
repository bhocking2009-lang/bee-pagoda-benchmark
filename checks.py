import importlib.util
import sys
import platform

def verify_deps():
    deps = ['typer', 'pyyaml', 'pygame']  # Example deps including pygame
    missing = []
    for dep in deps:
        if importlib.util.find_spec(dep) is None:
            missing.append(dep)
    if missing:
        print("Missing dependencies: " + ", ".join(missing))
        if platform.system() == 'Linux':
            install_cmd = "sudo apt update && sudo apt install " + " ".join(["python3-" + d for d in missing if d != 'pygame']) + " python3-pygame"
            print("To install, run:")
            print(install_cmd)
            # Optionally, ask if to run it, but for now prompt
        return False
    print("All dependencies present.")
    return True
