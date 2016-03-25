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
VENV_PYTHON = venv/bin/python
VENV_PYVERSION = $(shell $(VENV_PYTHON) -c "import sys; print(sys.version[:3])")

ifeq ($(CIRCLE_NODE_INDEX),0)
  CIRCLE_PYVERSION = 2.6
endif
ifeq ($(CIRCLE_NODE_INDEX),1)
  CIRCLE_PYVERSION = 2.7
endif
ifeq ($(CIRCLE_NODE_INDEX),2)
  CIRCLE_PYVERSION = 3.4
endif
ifeq ($(CIRCLE_NODE_INDEX),3)
  CIRCLE_PYVERSION = 3.5
endif

PYVERSION_PACKAGES = $(shell for pkg in $(PACKAGES); do grep -q $(VENV_PYVERSION) $$pkg/setup.py && echo $$pkg; done)

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

.PHONY: venv copyfiles install test dist upload clean circleci circleci_setup


$(VENV_PYTHON):
	$(VIRTUALENV) venv;                 \
	for package in $(EXTRA_DEPS); do    \
	   venv/bin/pip install $$package;  \
	done

venv: $(VENV_PYTHON)

copyfiles:
	for package in $(PACKAGES); do                      \
	    cd $$package;                                   \
	    for file in $(COPY_FILES); do                   \
	        cp ../$$file .;                             \
	    done;                                           \
	    cd ..;                                          \
    done

install: venv copyfiles
	for package in $(PYVERSION_PACKAGES); do            \
	    cd $$package;                                   \
	    ../$(VENV_PYTHON) setup.py bdist_egg || exit 1; \
	    ../venv/bin/easy_install dist/*.egg || exit 1;  \
	    cd ..;                                          \
    done


develop: venv copyfiles
	for package in $(PYVERSION_PACKAGES); do            \
	    cd $$package;                                   \
	    ../($VENV_PYTHON) setup.py develop || exit 1;   \
	    cd ..;                                          \
    done


local_develop: copyfiles
	for package in $(PYVERSION_PACKAGES); do            \
	    cd $$package;                                   \
	    python setup.py develop || exit 1;              \
	    cd ..;                                          \
    done

test: install
	for package in $(PYVERSION_PACKAGES); do            \
	    (cd $$package;                                  \
	     ../venv/bin/coverage run -p setup.py test -sv -ra || touch ../FAILED; \
	    )                                               \
    done;                                               \
    [ -f FAILED ] && exit 1  || true

dist: venv copyfiles
	for package in $(CHANGED_PACKAGES); do                     \
	    cd $$package;                                  \
            for format in $(DIST_FORMATS); do          \
                 ../$(VENV_PYTHON) setup.py $$format || exit 1;   \
            done;                                      \
	    cd ..;                                         \
    done

upload: dist
	for package in $(CHANGED_PACKAGES); do                     \
	    cd $$package;                                  \
            ../$(VENV_PYTHON) setup.py register $(UPLOAD_OPTS) || exit 1;   \
            for format in $(DIST_FORMATS); do          \
                 ../$(VENV_PYTHON) setup.py $$format upload $(UPLOAD_OPTS) || exit 1;   \
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
	rm -rf venv pytest-pyramid-server/vx pip-log.txt
	find . -name *.pyc -name .coverage -name .coverage.* -delete
	rm -f FAILED

circleci_setup:
	mkdir -p $CIRCLE_ARTIFACTS/htmlcov/$(CIRCLE_PYVERSION);  \
    mkdir -p $CIRCLE_TEST_REPORTS/junit; \
    (cd venv/lib/python$(CIRCLE_PYVERSION)/site-packages;  \
     ln -s $(python$(CIRCLE_PYVERSION) -c "import PyQt4; print PyQt4.__path__[0]"); \
     ln -s $(python$(CIRCLE_PYVERSION) -c "import sip; print sip.__file__");  \
     );

circleci: VIRTUALENV = virtualenv -p python$(CIRCLE_PYVERSION)
circleci: clean venv circleci_setup test dist
	cp pytest-*/junit.xml $CIRCLE_TEST_REPORTS/junit/$$package-py$(CIRCLE_PYVERSION).xml;
	venv/bin/coverage combine pytest-*/.coverage;  \
    venv/bin/coverage html -d $CIRCLE_ARTIFACTS/htmlcov/$(CIRCLE_PYVERSION);  \
    cp pytest-*/dist/* $CIRCLE_ARTIFACTS

all:
	test
