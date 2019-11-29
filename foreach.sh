#!/bin/bash
# Run a command for each of our packages
set -ef

if [ "$1" = '--changed' ]; then
    shift
    # Package list, filtered to ones changed since last tag
    LAST_TAG=$(git tag -l v\* | sort -t. -k 1,1n -k 2,2n -k 3,3n -k 4,4n | tail -1)
    PACKAGES=$(git diff --name-only ${LAST_TAG} | grep pytest- | cut -d'/' -f1 | sort | uniq)
else
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
fi

for pkg in $PACKAGES; do
   export PKG=$pkg
   (cd $pkg
    echo "-------------------------------------------------------------------------------------------------------------------------- "
    echo "                                                        $pkg"
    echo "-------------------------------------------------------------------------------------------------------------------------- "
    echo
    bash -x -c "$*"
    echo
   )
done
