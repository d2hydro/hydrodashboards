from pathlib import Path

CONFIG_JSON = Path(__file__).parent.joinpath("config.json")


def set_config_json(config_json):
    global CONFIG_JSON

    CONFIG_JSON = Path(config_json).absolute().resolve()
