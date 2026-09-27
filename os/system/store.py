import json
import os


def _path(name):
    return "/data/{}.json".format(name)


def load(name, default=None):
    try:
        with open(_path(name)) as f:
            return json.load(f)
    except OSError:
        return default
    except ValueError:
        print("store: {} is not valid JSON".format(_path(name)))
        return default


def save(name, value):
    temporary = _path(name) + ".tmp"
    with open(temporary, "w") as f:
        json.dump(value, f)
    try:
        os.rename(temporary, _path(name))
    except OSError:
        os.remove(_path(name))
        os.rename(temporary, _path(name))
