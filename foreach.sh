#!/bin/bash
# Run a command for each of our packages

# Package list, in order of ancestry
# removed pytest-qt-app                  
PACKAGES="pytest-fixture-config      \
         pytest-shutil                  \
         pytest-server-fixtures         \
         pytest-pyramid-server          \
         pytest-devpi-server            \
         pytest-listener                \
         pytest-svn                     \
         pytest-git                     \
         pytest-virtualenv              \
         pytest-webdriver               \
         pytest-profiling               \
         pytest-verbose-parametrize"

for pkg in $PACKAGES; do
   export PKG=$pkg
   (cd $pkg
    bash -c "$*"
   )
done