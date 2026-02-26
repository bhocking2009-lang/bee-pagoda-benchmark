import os
import importlib.util

def load_plugins(category):
    plugins_dir = os.path.join("plugins", category)
    plugins = []
    if not os.path.isdir(plugins_dir):
        print(f"No plugins directory for category: {category}")
        return plugins
    for filename in os.listdir(plugins_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            file_path = os.path.join(plugins_dir, filename)
            module_name = filename[:-3]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugins.append(module)
    print(f"Loaded {len(plugins)} plugins for {category}")
    return plugins
