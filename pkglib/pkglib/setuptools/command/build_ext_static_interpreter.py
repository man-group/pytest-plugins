import os

from distutils import log

from .base import CommandMixin, fetch_build_eggs, get_resource_file
from .build_ext import build_ext


with open(get_resource_file('gcov_main_c_template.c')) as f:
    GCOV_MAIN_C_TEMPLATE = f.read()

with open(get_resource_file('gcov_alias_template.pyx')) as f:
    GCOV_ALIASES_TEMPLATE = f.read()

with open(get_resource_file('gcov_module_init.c')) as f:
    GCOV_MODULE_INIT = f.read()


class static_interpreter_override_mixin(CommandMixin):
    description = " as static builtins"
    user_options = [
        ('extra-compile-args=', 'x',
         "extra arguments to pass to the compiler"),
        ('extra-link-args=', 'y',
         "extra arguments to pass to the linker"),
        ('interpreter-filename=', None,
         "relative filename of output interpreter "
         "(default {build_lib}/static_interpreter)"),
    ]

    def initialize_options(self):
        super(static_interpreter_override_mixin, self).initialize_options()
        self.extra_compile_args = ""
        self.extra_link_args = ""
        self.interpreter_filename = None

    def finalize_options(self):
        super(static_interpreter_override_mixin, self).finalize_options()
        self.extra_compile_args = self.extra_compile_args.split()
        self.extra_link_args = self.extra_link_args.split()
        self.interpreter_filename = (self.interpreter_filename or
                                     os.path.join(self.build_lib,
                                                  "static_interpreter"))

    # override, called from build_ext.run
    def build_extensions(self):
        # First, sanity-check the 'extensions' list
        self.check_extensions_list(self.extensions)

        built_objects = sum((self.build_extension_objects(ext)
                             for ext in self.extensions), [])
        self.build_static_interpreter(built_objects)

    # from distutils build_ext.py build_ext.build_extension
    def build_extension_objects(self, ext):
        log.info("building objects for {0}".format(ext.name))
        sources = self.swig_sources(list(ext.sources), ext)
        extra_args = ((ext.extra_compile_args or [])
                      + (self.extra_compile_args or []))
        macros = ext.define_macros[:] + [(u,) for u in ext.undef_macros]
        objects = self.compiler.compile(sources,
                                        output_dir=self.build_temp,
                                        macros=macros,
                                        include_dirs=ext.include_dirs,
                                        debug=self.debug,
                                        extra_postargs=extra_args,
                                        depends=ext.depends)
        return objects

    def build_static_interpreter(self, objects):
        main_c = os.path.join(self.build_temp, "static_interpreter_main.c")
        with open(main_c, 'w') as f:
            f.write(self.generate_main_c([e.name for e in self.extensions]))

        extra_postargs = self.extra_compile_args or []
        objects += self.compiler.compile([main_c],
                                         output_dir=self.build_temp,
                                         debug=self.debug,
                                         extra_postargs=extra_postargs)

        log.info("building {0}".format(self.interpreter_filename))
        extra_args = (sum((ext.extra_link_args or []
                           for ext in self.extensions), [])
                      + (self.extra_link_args or []))
        objects += sum((e.extra_objects or [] for e in self.extensions), [])
        libs = sum((self.get_libraries(e) or [] for e in self.extensions), [])
        lib_dirs = sum((e.library_dirs or [] for e in self.extensions), [])
        runtime_lib_dirs = sum((e.runtime_library_dirs or []
                                for e in self.extensions), [])
        target_lang = self.compiler.detect_language(sum((e.sources for e
                                                         in self.extensions),
                                                        []))

        self.compiler.link_executable(objects,
                                      self.interpreter_filename,
                                      libraries=libs,
                                      library_dirs=lib_dirs,
                                      runtime_library_dirs=runtime_lib_dirs,
                                      extra_postargs=extra_args,
                                      debug=self.debug,
                                      target_lang=target_lang)

    def generate_main_c(self, ext_names):
        basenames = dict((e, e.rsplit('.', 1)[-1]) for e in ext_names)
        declare = ';\n'.join('MOD_INIT({ext})'.format(ext=v)
                             for v in basenames.values())
        init = ""
        for fullname, ext in basenames.items():
            module_init = GCOV_MODULE_INIT.format(ext=ext, fullname=fullname)
            init += "\n    ".join(module_init.splitlines())

        ext_names = ', '.join('\'{ext}\''.format(ext=e) for e in ext_names)
        alias_code = GCOV_ALIASES_TEMPLATE.format(ext_names=ext_names)
        alias = '\n        '.join('"{line}\\n"'.format(line=line)
                                  for line in alias_code.split('\n'))
        s = GCOV_MAIN_C_TEMPLATE.format(file=os.path.abspath(__file__),
                                        declare=declare, init=init,
                                        alias=alias)
        return s


def _get_cython_build_ext_static_interpreter():
    from Cython.Distutils.__init__ import build_ext as cython_build_ext  # @UnresolvedImport

    class cython_static_interpreter(static_interpreter_override_mixin,
                                    cython_build_ext):
        description = (cython_build_ext.description
                       + static_interpreter_override_mixin.description)
        user_options = (cython_build_ext.user_options
                        + static_interpreter_override_mixin.user_options)

        def __init__(self, *args, **kwargs):
            cython_build_ext.__init__(self, *args, **kwargs)

        def build_extensions(self):
            for ext in self.extensions:
                ext.sources = self.cython_sources(ext.sources, ext)
            super(cython_static_interpreter, self).build_extensions()

    return cython_static_interpreter


class build_ext_static_interpreter(static_interpreter_override_mixin, build_ext):
    """
    Build a Python interpreter with all ext_modules linked in statically and
    imported.
    This is useful when working with analysis tools e.g. gcov that don't work
    with shared library modules.
    """
    description = (build_ext.description
                   + static_interpreter_override_mixin.description)
    user_options = (build_ext.user_options
                    + static_interpreter_override_mixin.user_options)

    def run(self):
        if self.uses_cython():
            # Cython source - use cython's build_ext
            log.info("This project uses Cython, fetching builder egg")
            fetch_build_eggs(['Cython'], dist=self.distribution)

            cmd_class = self.distribution.cmdclass
            cmd_obj = self.distribution.command_obj

            interpreter = _get_cython_build_ext_static_interpreter()
            cbe_class = cmd_class['cython_build_ext'] = interpreter
            cbe = cmd_obj['cython_build_ext'] = cbe_class(self.distribution)
            cbe.inplace = self.inplace
            cbe.extra_compile_args += ' '.join(self.extra_compile_args)
            cbe.extra_link_args += ' '.join(self.extra_link_args)
            cbe.interpreter_filename = self.interpreter_filename
            cbe.cython_line_directives = True  # HACK, ext_gcov_test needs this

            self.run_command('cython_build_ext')
        else:
            super(build_ext_static_interpreter, self).run()
