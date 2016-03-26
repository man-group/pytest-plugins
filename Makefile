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

CIRCLE_SYSTEM_PYTHON = python$(CIRCLE_PYVERSION)
CIRCLE_API_KEY = fbb7daf2022ce0d88327252bc0bb0628f19d0a45

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
	     ../venv/bin/coverage run -p setup.py test -sv -ra || touch ../FAILED-$$package; \
	    )                                               \
    done;                                               \
    [ -f FAILED-* ] && exit 1  || true

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

circleci_python:
	case $(CIRCLE_PYVERSION) in  \
        2.6|3.5 ) sudo add-apt-repository -y ppa:fkrull/deadsnakes && sudo apt-get update; \
    esac; \
	case $(CIRCLE_PYVERSION) in  \
        2.6) sudo apt-get install -y python2.6 python2.6-dev ;;  \
        3.4) sudo apt-get install -y python3.4-dev ;; \
        3.5) sudo apt-get install -y python3.5 python3.5-dev ;;  \
    esac; \


circleci_sip:
	previous_build=`venv/bin/python ./circle_artifact.py $(CIRCLE_API_KEY) 'sip*.tgz'` \
	mkdir sip; \
    (cd sip; \
     if [ -z "$$previous_build" ]; then \
         curl -L "http://downloads.sourceforge.net/project/pyqt/sip/sip-4.17/sip-4.17.tar.gz?r=&ts=1458926351&use_mirror=heanet" | tar xzf -; \
         cd sip-4.17; \
         $(CIRCLE_SYSTEM_PYTHON) configure.py; \
         make -j 4;  \
         cd ..; tar czf sip-py$(CIRCLE_PYVERSION).tgz sip-4.17; \
     else \
         wget "$$previous_build"; \
         tar xzf sip-*.tgz; \
     fi;  \
     mv sip*.tgz $(CIRCLE_ARTIFACTS); \
     cd sip-4.17; \
     sudo make install; \
    ); \
    (cd venv/lib/python$(CIRCLE_PYVERSION)/site-packages; \
     ln -s `$(CIRCLE_SYSTEM_PYTHON) -c "import sip; print(sip.__file__)"`; \
    )
    
circleci_pyqt:
	previous_build=`venv/bin/python ./circle_artifact.py 'PyQt*.tgz'` \
	mkdir pyqt; \
    (cd pyqt; \
     if [ -z "$$previous_build" ]; then \
         curl -L "http://downloads.sourceforge.net/project/pyqt/PyQt4/PyQt-4.11.4/PyQt-x11-gpl-4.11.4.tar.gz?r=&ts=1458926298&use_mirror=netix" | tar xzf -;  \
         cd PyQt-4.11.4; \
         $(CIRCLE_SYSTEM_PYTHON) configure.py --confirm-license; \
         make -j 4; \
         cd ..; tar czf PyQt-py$(CIRCLE_PYVERSION).tgz PtQt*; \
     else \
         wget "$$previous_build"; \
         tar xzf PyQt*.tgz; \
     fi; \
     mv PyQt*.tgz $(CIRCLE_ARTIFACTS); \
     cd PyQt-4.11.4; \
     sudo make install;  \
    ); \
    (cd venv/lib/python$(CIRCLE_PYVERSION)/site-packages;  \
     ln -s `$(CIRCLE_SYSTEM_PYTHON) -c "import PyQt4; print(PyQt4.__file__)"`; \
    )
    
circleci_setup:
	mkdir -p $$CIRCLE_ARTIFACTS/htmlcov/$(CIRCLE_PYVERSION);  \
	mkdir -p $$CIRCLE_ARTIFACTS/dist/$(CIRCLE_PYVERSION);  \
    mkdir -p $$CIRCLE_TEST_REPORTS/junit;  \
    venv/bin/pip install circleclient

circleci: VIRTUALENV = virtualenv -p $(CIRCLE_SYSTEM_PYTHON)
circleci: clean circleci_python venv circleci_setup circleci_sip circleci_pyqt test dist
	for i in $(PYVERSION_PACKAGES); do \
        cp $$i/junit.xml $$CIRCLE_TEST_REPORTS/junit/$$i-py$(CIRCLE_PYVERSION).xml; \
    done; \
	venv/bin/coverage combine pytest-*/.coverage;  \
    venv/bin/coverage html -d $$CIRCLE_ARTIFACTS/htmlcov/$(CIRCLE_PYVERSION);  \
    cp pytest-*/dist/* $$CIRCLE_ARTIFACTS

all:
	test
