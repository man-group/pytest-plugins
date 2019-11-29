#!/bin/bash
# Run a command for each of our packages
set -ef

QUIET=0
if [ "$1" = '--quiet' ]; then
  QUIET=1
  shift
fi

if [ "$1" = '--changed' ]; then
    shift
    # Package list, filtered to ones changed since last tag
    LAST_TAG=$(git tag -l v\* | sort -t. -k 1,1n -k 2,2n -k 3,3n -k 4,4n | tail -1)
    PACKAGES=$(git diff --name-only ${LAST_TAG} | grep pytest- | cut -d'/' -f1 | sort | uniq)
else
    # Package list, in order of ancestry
    # removed pytest-qt-app
    DEFAULT_PACKAGES="pytest-fixture-config     \
             pytest-shutil                      \
             pytest-server-fixtures             \
             pytest-pyramid-server              \
             pytest-devpi-server                \
             pytest-listener                    \
             pytest-svn                         \
             pytest-git                         \
             pytest-virtualenv                  \
             pytest-webdriver                   \
             pytest-profiling                   \
             pytest-verbose-parametrize"
    PACKAGES="${PACKAGES:-$DEFAULT_PACKAGES}"
fi

for pkg in $PACKAGES; do
   export PKG=$pkg
   (cd $pkg
    if [ $QUIET -eq 1 ]; then
        bash -c "$*"
    else
        echo "-----------------------------------------------------"
        echo "                   $pkg"
        echo "-----------------------------------------------------"
        echo
        bash -x -c "$*"
        echo
    fi
   )
done
