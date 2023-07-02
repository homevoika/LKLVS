from configparser import ConfigParser
from shutil import copy


def set_param(field: str, value: str) -> None:
    config = ConfigParser()
    config.read('settings')
    if not config.sections():
        copy("static/default", "settings")
        config.read('settings')
    config.set('SETTINGS', field, value)
    with open('settings', 'w') as file:
        config.write(file)


def get_param(field: str) -> str:
    config = ConfigParser()
    config.read('settings')
    try:
        value = config['SETTINGS'][field]
        return value
    except KeyError:
        copy("static/default", "settings")
        return get_param(field)
