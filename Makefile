# Package list, in order of ancestry
PACKAGES = pytest-fixture-config      \
           pytest-shutil                  \
           pytest-server-fixtures         \
           pytest-pyramid-server          \
           pytest-devpi-server            \
           pytest-listener                \
           pytest-qt-app                  \
           pytest-svn                     \
           pytest-git                     \
           pytest-virtualenv              \
           pytest-webdriver               \
           pytest-profiling               \
           pytest-verbose-parametrize

VIRTUALENV = virtualenv
VENV = $(shell dirname $(shell readlink -f setup.py))/venv
VENV_PYTHON = $(VENV)/bin/python
VENV_PYVERSION = $(shell $(VENV_PYTHON) -c "import sys; print(sys.version[:3])")
PYVERSION_PACKAGES = $(shell for pkg in $(PACKAGES); do grep -q $(VENV_PYVERSION) $$pkg/setup.py && echo $$pkg; done)

ifeq ($(CIRCLE_NODE_INDEX),0)
  CIRCLE_PYVERSION = 2.6
  CIRCLE_PYVERSION_FULL = 2.6.9
  VENV_PYTHON = $(VENV)/bin/python2.6
endif
ifeq ($(CIRCLE_NODE_INDEX),1)
  CIRCLE_PYVERSION = 2.7
  CIRCLE_PYVERSION_FULL = 2.7.9
  VENV_PYTHON = $(VENV)/bin/python2.7
endif
ifeq ($(CIRCLE_NODE_INDEX),2)
  CIRCLE_PYVERSION = 3.4
  CIRCLE_PYVERSION_FULL = 3.4.4
  VENV_PYTHON = $(VENV)/bin/python3.4
endif
ifeq ($(CIRCLE_NODE_INDEX),3)
  CIRCLE_PYVERSION = 3.5
  CIRCLE_PYVERSION_FULL = 3.5.1
  VENV_PYTHON = $(VENV)/bin/python3.5
endif

# Look up the last completed build's python tarball. We can't use the normal cache from circleci as it only caches
# dependencies set up in node 0 *headdesk*
CIRCLE_API_KEY = fbb7daf2022ce0d88327252bc0bb0628f19d0a45
CIRCLE_CACHED_PYTHON = $(shell /usr/bin/python circle_artifact.py $(CIRCLE_API_KEY) 'venv.tgz')
CIRCLE_PYTHON_ARCH = https://www.python.org/ftp/python/$(CIRCLE_PYVERSION_FULL)/Python-$(CIRCLE_PYVERSION_FULL).tgz

EXTRA_DEPS = pypandoc       \
             wheel          \
             coverage       \
             python-jenkins \
             redis          \
             pymongo        \
             rethinkdb

COPY_FILES = VERSION CHANGES.md common_setup.py MANIFEST.in
DIST_FORMATS = sdist bdist_wheel bdist_egg
UPLOAD_OPTS =

# Used for determining which packages get released
LAST_TAG := $(shell git tag -l v\* | tail -1)
CHANGED_PACKAGES := $(shell git diff --name-only $(LAST_TAG) | grep pytest- | cut -d'/' -f1 | sort | uniq)

.PHONY: venv copyfiles extras install test test_nocheck dist upload clean circleci_setup circleci_sip circleci_pyqt circleci_venv circleci_collect circleci

# CircleCI builds Python from source instead of using virtualenv. It's easier to do this as:
#   a) Not all the python versions are available from Ubuntu without custom repos
#   b) We need to build sip and PyQt which don't work with easy_install/pip, and aren't
#      available from Ubuntu packages servers at all our different Python versions

$(VENV_PYTHON):
	if [ -z "$$CIRCLECI" ]; then \
       $(VIRTUALENV) $(VENV);  \
    else \
        if [ -z "$(CIRCLE_CACHED_PYTHON)" ]; then \
            curl -L "$(CIRCLE_PYTHON_ARCH)" | tar xzf -; \
            cd Python-*; \
            ./configure --prefix=$(VENV) && make -j4 && make install; \
            cd $(VENV)/bin; \
            [ ! -f python ] && ln -s python$(CIRCLE_PYVERSION) ./python; \
            wget https://bootstrap.pypa.io/ez_setup.py -O - | ./python; \
            ./easy_install pip; \
        else \
            wget $(CIRCLE_CACHED_PYTHON); \
            tar xzf venv.tgz; \
            mv venv.tgz $$CIRCLE_ARTIFACTS; \
        fi \
    fi

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
	     $(VENV)/bin/coverage run -p setup.py test -sv -ra || touch ../FAILED-$$package; \
	    )                                               \
    done;                                               \

test: test_nocheck
	[ -f FAILED-* ] && exit 1  || true

dist: venv copyfiles
	for package in $(CHANGED_PACKAGES); do                     \
	    cd $$package;                                  \
            for format in $(DIST_FORMATS); do          \
                 $(VENV_PYTHON) setup.py $$format || exit 1;   \
            done;                                      \
	    cd ..;                                         \
    done

upload: dist
	for package in $(CHANGED_PACKAGES); do                     \
	    cd $$package;                                  \
            $(VENV_PYTHON) setup.py register $(UPLOAD_OPTS) || exit 1;   \
            for format in $(DIST_FORMATS); do          \
                 $(VENV_PYTHON) setup.py $$format upload $(UPLOAD_OPTS) || exit 1;   \
            done;                                      \
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
	sudo /usr/bin/python -m pip install circleclient
	mkdir -p $$CIRCLE_ARTIFACTS/htmlcov/$(CIRCLE_PYVERSION);  \
	mkdir -p $$CIRCLE_ARTIFACTS/dist/$(CIRCLE_PYVERSION);  \
    mkdir -p $$CIRCLE_TEST_REPORTS/junit;  \

circleci_sip:
	if [ ! -f "$$CIRCLE_ARTIFACTS/venv.tgz" ]; then \
        curl -L "http://downloads.sourceforge.net/project/pyqt/sip/sip-4.17/sip-4.17.tar.gz?r=&ts=1458926351&use_mirror=heanet" | tar xzf -; \
        cd sip*; \
        $(VENV_PYTHON) configure.py; \
        make -j 4 && make install; \
    fi

circleci_pyqt:
	if [ ! -f "$$CIRCLE_ARTIFACTS/venv.tgz" ]; then \
        curl -L "http://downloads.sourceforge.net/project/pyqt/PyQt4/PyQt-4.11.4/PyQt-x11-gpl-4.11.4.tar.gz?r=&ts=1458926298&use_mirror=netix" | tar xzf -;  \
        cd PyQt*; \
        $(VENV_PYTHON) configure.py --confirm-license; \
        make -j 4 && make install; \
    fi

circleci_venv: venv circleci_sip circleci_pyqt
	if [ ! -f "$$CIRCLE_ARTIFACTS/venv.tgz" ]; then \
        tar czf $$CIRCLE_ARTIFACTS/venv.tgz venv; \
    fi

circleci_collect:
	for i in $(PYVERSION_PACKAGES); do \
        sed -i $$i/junit.xml 's/classname="tests/classname="tests$(CIRCLE_PYVERSION)'/; \
        sed -i $$i/junit.xml 's/classname="tests/classname="tests$(CIRCLE_PYVERSION)'/; \
        cp $$i/junit.xml $$CIRCLE_TEST_REPORTS/junit/$$i-py$(CIRCLE_PYVERSION).xml; \
    done; \
	$(VENV)/bin/coverage combine pytest-*/.coverage;  \
    $(VENV)/bin/coverage html -d $$CIRCLE_ARTIFACTS/htmlcov/$(CIRCLE_PYVERSION);  \
    cp pytest-*/dist/* $$CIRCLE_ARTIFACTS

circleci: clean circleci_setup circleci_venv test_nocheck dist circleci_collect
	[ -f FAILED-* ] && exit 1  || true

all:
	test
