#include "Python.h"

#if PY_MAJOR_VERSION >= 3
  #define MOD_ERROR_VAL NULL
  #define MOD_SUCCESS_VAL(val) val
  #define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
  #define MOD_DEF(ob, name, doc, methods) \
          static struct PyModuleDef moduledef = { \
            PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
          ob = PyModule_Create(&moduledef);
#else
  #define MOD_ERROR_VAL
  #define MOD_SUCCESS_VAL(val)
  #define MOD_INIT(name) void init##name(void)
  #define MOD_DEF(ob, name, doc, methods) \
          ob = Py_InitModule3(name, methods, doc);
#endif


static PyObject *fn_1(PyObject *self, PyObject *args) {
  return Py_BuildValue("s", "fn_1");
}

static PyObject *fn_2(PyObject *self, PyObject *args) {
  return Py_BuildValue("s", "fn_2");
}

static PyMethodDef module_functions[] = {
  { "fn_1", fn_1, METH_VARARGS, "fn_1" },
  { "fn_2", fn_2, METH_VARARGS, "fn_2" },
  { NULL, },
};


MOD_INIT(ext) {
  PyObject *m;
  MOD_DEF(m, "ext", "Extension", module_functions)

  if (m == NULL)
      return MOD_ERROR_VAL;

  return MOD_SUCCESS_VAL(m);
}
