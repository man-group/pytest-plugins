/* Import of: {fullname} (short name: {ext}) */
res = PyImport_AppendInittab("{ext}", MOD_INIT_FUNC({ext}));
if (res != 0) {{
    fprintf(stderr, "Error initialising module: {ext} (fullname: {fullname})\n");
    return 1;
}}
