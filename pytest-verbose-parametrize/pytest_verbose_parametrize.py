from collections.abc import Iterable


def _strize_arg(arg):
    try:
        s = arg.__name__
    except AttributeError:
        s = str(arg)
    if len(s) > 32:
        s = s[:29] + '...'
    return s


def pytest_generate_tests(metafunc):

    try:
        markers = metafunc.definition.get_closest_marker('parametrize')
        if not markers:
            return
    except AttributeError:
        # Deprecated in pytest >= 3.6
        # See https://docs.pytest.org/en/latest/mark.html#marker-revamp-and-iteration
        try:
            markers = metafunc.function.parametrize
        except AttributeError:
            return

    if 'ids' not in markers.kwargs:
        list_names = []
        for i, argvalue in enumerate(markers.args[1]):
            if (not isinstance(argvalue, Iterable)) or isinstance(argvalue, str):
                argvalue = (argvalue,)
            name = '-'.join(_strize_arg(arg) for arg in argvalue)
            if len(name) > 64:
                name = name[:61] + '...'
            while name in list_names:
                name = '%s#%d' % (name, i)
            list_names.append(name)
        markers.kwargs['ids'] = list_names
        # In pytest versions pre-3.1.0 MarkInfo copies the
        # kwargs into an internal variable as well :/
        if hasattr(markers, '_arglist'):
            markers._arglist[0][-1]['ids'] = list_names
