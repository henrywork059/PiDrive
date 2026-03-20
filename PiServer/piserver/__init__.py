from importlib import import_module


def create_app():
    module = import_module('piserver.app')
    factory = getattr(module, 'create_app', None)
    if not callable(factory):
        raise RuntimeError(
            'piserver.app loaded, but create_app() is missing. '
            'Re-copy PiServer/piserver/app.py from the PiServer_0_2_12 patch.'
        )
    return factory()


__all__ = ['create_app']
