def alias_ext_imports(ext_names):
    class ImportAlias:
        def find_module(self, fullname, path=None):
            return self if fullname in ext_names else None
        def load_module(self, fullname):
            m = __import__(fullname.rsplit('.', 1)[-1])
            sys.modules[fullname] = m
            return m

    import sys
    sys.meta_path.append(ImportAlias())

alias_ext_imports([{ext_names}])
del alias_ext_imports
