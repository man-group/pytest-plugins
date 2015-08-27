from collections import Iterable
from six import string_types


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
        param = metafunc.function.parametrize
    except AttributeError:
        return
    for p in param:
        if 'ids' not in p.kwargs:
            list_names = []
            for i, argvalue in enumerate(p.args[1]):
                if (not isinstance(argvalue, Iterable)) or isinstance(argvalue, string_types):
                    argvalue = (argvalue,)
                name = '-'.join(_strize_arg(arg) for arg in argvalue)
                if len(name) > 64:
                    name = name[:61] + '...'
                while name in list_names:
                    name = '%s#%d' % (name, i)
                list_names.append(name)
            p.kwargs['ids'] = list_names
