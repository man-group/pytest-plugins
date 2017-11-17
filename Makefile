# Package list, in order of ancestry
# removed pytest-qt-app                  
PACKAGES = pytest-fixture-config      \
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
           pytest-verbose-parametrize

PYTHON = python
VIRTUALENV = virtualenv
VENV = $(shell dirname $(shell perl -e 'use Cwd "abs_path";print abs_path(shift)' VERSION))/venv
VENV_PYVERSION = $(shell $(VENV_PYTHON) -c "import sys; print(sys.version[:3])")
PYVERSION_PACKAGES = $(shell for pkg in $(PACKAGES); do grep -q $(VENV_PYVERSION) $$pkg/setup.py && echo $$pkg; done)
VENV_PYTHON = $(VENV)/bin/python


ifeq ($(CIRCLE_NODE_INDEX),0)
  CIRCLE_PYVERSION = 2.7
  CIRCLE_PYVERSION_FULL = 2.7.11
endif
ifeq ($(CIRCLE_NODE_INDEX),1)
  CIRCLE_PYVERSION = 3.4
  CIRCLE_PYVERSION_FULL = 3.4.4
endif
ifeq ($(CIRCLE_NODE_INDEX),2)
  CIRCLE_PYVERSION = 3.5
  CIRCLE_PYVERSION_FULL = 3.5.2
endif

ifeq ($(CIRCLECI),true)
    PYTHON = python$(CIRCLE_PYVERSION)
    VENV_PYTHON = $(VENV)/bin/python$(CIRCLE_PYVERSION)
    VIRTUALENV = $(PYTHON) -m virtualenv
endif

EXTRA_DEPS = pypandoc       \
             wheel          \
             coverage       \
             python-jenkins \
             redis          \
             pymongo        \
             psycopg2       \
             boto3          \
             rethinkdb

COPY_FILES = VERSION CHANGES.md common_setup.py MANIFEST.in LICENSE
DIST_FORMATS = sdist bdist_wheel bdist_egg
UPLOAD_OPTS =

# Used for determining which packages get released
LAST_TAG := $(shell git tag -l v\* | sort -t. -k 1,1n -k 2,2n -k 3,3n -k 4,4n | tail -1)
CHANGED_PACKAGES := $(shell git diff --name-only $(LAST_TAG) | grep pytest- | cut -d'/' -f1 | sort | uniq)

# removed from PHONY:  circleci_sip circleci_pyqt
.PHONY: venv copyfiles extras install test test_nocheck dist upload clean circleci_setup circleci_collect circleci

$(VENV_PYTHON):
	if [ ! -z "$$CIRCLECI" ]; then \
	    sudo $(PYTHON) -m pip install virtualenv; \
	fi; \
    $(VIRTUALENV) $(VENV)

venv: $(VENV_PYTHON)

extras: venv
	for package in $(EXTRA_DEPS); do    \
           $(VENV)/bin/pip install $$package;  \
    done; \

copyfiles:
	for package in $(PACKAGES); do                      \
	    cd $$package;                                   \
	    for file in $(COPY_FILES); do                   \
	        cp ../$$file .;                             \
	    done;                                           \
	    cd ..;                                          \
    done

install: venv extras copyfiles
	for package in $(PYVERSION_PACKAGES); do            \
	    cd $$package;                                   \
	    $(VENV_PYTHON) setup.py bdist_egg || exit 1; \
	    $(VENV)/bin/easy_install dist/*.egg || exit 1;  \
	    cd ..;                                          \
    done

develop: venv copyfiles
	for package in $(PYVERSION_PACKAGES); do            \
	    cd $$package;                                   \
	    $(VENV_PYTHON) setup.py develop || exit 1;   \
	    cd ..;                                          \
    done

local_develop: copyfiles
	for package in $(PYVERSION_PACKAGES); do            \
	    cd $$package;                                   \
	    python setup.py develop || exit 1;              \
	    cd ..;                                          \
    done

test_nocheck: install
	for package in $(PYVERSION_PACKAGES); do            \
	    (cd $$package;                                  \
	     export DEBUG=1; 				    \
	     echo $$package | sed s/-/_/g | xargs -Ipysrc $(VENV)/bin/coverage run -p --source=pysrc setup.py test -sv -ra || touch ../FAILED-$$package; \
	    )                                               \
    done;                                               \

test: test_nocheck
	compgen -G 'FAILED-*' && exit 1

dist: venv copyfiles
	for package in $(CHANGED_PACKAGES); do                     \
	    cd $$package;                                  \
            if [ -f common_setup.py ]; then  \
                for format in $(DIST_FORMATS); do          \
                     $(VENV_PYTHON) setup.py $$format || exit 1;   \
                done;                                      \
            fi; \
	    cd ..;                                         \
    done

upload: dist
	for package in $(CHANGED_PACKAGES); do                     \
	    cd $$package;                                  \
            if [ -f common_setup.py ]; then  \
                $(VENV_PYTHON) setup.py register $(UPLOAD_OPTS) || exit 1;   \
                for format in $(DIST_FORMATS); do          \
                     $(VENV_PYTHON) setup.py $$format upload $(UPLOAD_OPTS) || exit 1;   \
                done;                                      \
            fi; \
	    cd ..;                                         \
    done

clean:
	for package in $(PACKAGES); do                            \
        (cd $$package;                                        \
         rm -rf build dist *.xml *.egg-info .eggs htmlcov .cache  \
         rm $(COPY_FILES);                                   \
        );                                                    \
	done;                                                     \
	rm -rf $(VENV) pytest-pyramid-server/vx pip-log.txt
	find . -name *.pyc -name .coverage -name .coverage.* -delete
	rm -f FAILED-*

circleci_setup:
	mkdir -p $$CIRCLE_ARTIFACTS/htmlcov/$(CIRCLE_PYVERSION);  \
	mkdir -p $$CIRCLE_ARTIFACTS/dist/$(CIRCLE_PYVERSION);  \
    mkdir -p $$CIRCLE_TEST_REPORTS/junit;  \

#circleci_sip:
#	curl -L "http://downloads.sourceforge.net/project/pyqt/sip/sip-4.17/sip-4.17.tar.gz?r=&ts=1458926351&use_mirror=heanet" | tar xzf -; \
#    cd sip*; \
#    $(VENV_PYTHON) configure.py; \
#    make -j 4 && make install

#circleci_pyqt:
#	curl -L "http://downloads.sourceforge.net/project/pyqt/PyQt4/PyQt-4.11.4/PyQt-x11-gpl-4.11.4.tar.gz?r=&ts=1458926298&use_mirror=netix" | tar xzf -;  \
#    cd PyQt*; \
#    $(VENV_PYTHON) configure.py --confirm-license; \
#    make -j 4 && make install

circleci_collect:
	for i in $(PYVERSION_PACKAGES); do \
        sed 's/classname="tests/classname="tests$(CIRCLE_PYVERSION)/g' $$i/junit.xml > $$CIRCLE_TEST_REPORTS/junit/$$i-py$(CIRCLE_PYVERSION).xml; \
    done; \
	$(VENV)/bin/coverage combine pytest-*/.coverage*; \
	$(VENV)/bin/coverage report; \
    $(VENV)/bin/pip install python-coveralls; \
    $(VENV)/bin/coveralls --ignore-errors

#removed: circleci_sip circleci_pyqt
circleci: clean circleci_setup venv  test_nocheck dist circleci_collect
	compgen -G 'FAILED-*' && exit 1


all: test
