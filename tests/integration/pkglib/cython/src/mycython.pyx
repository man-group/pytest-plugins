cimport cython

cdef extern from "myheader.h":
    int times_two(int i)

cpdef test_cython(list L):
    cdef:
        int i
        list result = [0] * len(L)
    for i from 0 <= i < len(L):
        result[i] = times_two(int(L[i]))
    return result

