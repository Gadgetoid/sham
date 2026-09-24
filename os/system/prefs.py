from system import store

_values = None


def _load():
    global _values
    if _values is None:
        _values = store.load("prefs", {})
    return _values


def get(name, default=None):
    return _load().get(name, default)


def set(name, value):
    _load()[name] = value
    store.save("prefs", _values)
