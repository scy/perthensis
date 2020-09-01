__all__ = []

# Try to import the important classes from our submodules.
for module, classes in [
            ('heartbeat', ['Heartbeat']),
            ('scheduler', ['Scheduler']),
        ]:
    try:
        imported = __import__('perthensis.{0}'.format(module),
                              globals(), locals(), classes)
        __all__.extend(classes)
        for cls in classes:
            globals()[cls] = getattr(imported, cls)
        del imported, cls
    except ImportError:
        # This error can also originate from _inside_ the module, but
        # in any case, it can't be used. Nevertheless, we _could_ try to
        # re-raise the error here...?
        pass

# Keep the namespace clear.
del module, classes
