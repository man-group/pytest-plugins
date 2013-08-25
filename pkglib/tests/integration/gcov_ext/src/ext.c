#include "Python.h"

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

void initext(void) {
  Py_InitModule3("ext", module_functions, "Extension");
}
