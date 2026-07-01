import os
import yaml

_ENV_OVERRIDES = {
    "server": {
        "host": "HOST",
        "port": "PORT",
    },
    "db": {
        "path": "DB_PATH",
    },
    "vector_store": {
        "path": "VECTOR_STORE_PATH",
    },
}


def _apply_env(cfg: dict) -> dict:
    """Override config values from environment variables where defined."""
    for section, keys in _ENV_OVERRIDES.items():
        for key, env in keys.items():
            val = os.environ.get(env)
            if val is not None:
                section_dict = cfg.setdefault(section, {})
                if key == "port":
                    section_dict[key] = int(val)
                else:
                    section_dict[key] = val
    return cfg


class Config:
    def __init__(self, path="config.yaml"):
        with open(path, encoding="utf-8") as f:
            self._cfg = _apply_env(yaml.safe_load(f))

    def __getattr__(self, name):
        if name.startswith("_"):
            return super().__getattribute__(name)
        return type("Obj", (object,), self._cfg.get(name, {}))()
