

cdef extern from "cppheader.hpp" namespace "test":
    double halve(int)

cpdef test_cpp_cython(list L):
    cdef:
        int i
        list out = []
    for i from 0 <= i < len(L):
        out.append(halve(L[i]))
    return out
        
