import yaml

def load_config(file_path):
    with open(file_path, 'r') as f:
        config = yaml.safe_load(f)
    # Networking example
    if 'networking' in config:
        net = config['networking']
        print(f"Networking settings: host={net.get('host')}, port={net.get('port')}, api_key={net.get('api_key')}")
    return config
