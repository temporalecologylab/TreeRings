import json
import os

def load_config(path = "."):
    config_dir = os.path.join(path, "config.json")
    f = open(config_dir)
    config = json.load(f)
    f.close()

    return config["config"]