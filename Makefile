# Package list, in order of ancestry
PACKAGES=pytest-fixture-config          \
         pytest-shutil                  \
         pytest-server-fixtures         \
         pytest-pyramid-server          \
         pytest-listener                \
         pytest-qt-app                  \
         pytest-svn                     \
         pytest-virtualenv              \
         pytest-webdriver               \
         pytest-profiling               
         
# TODO: fix this package for latest py.test        
#         pytest-verbose-parametrize

VIRTUALENV=virtualenv
VENV_PYTHON=venv/bin/python
EXTRA_DEPS=pypandoc       \
           coverage       \
           python-jenkins \
           redis          \
           pymongo        \
           rethinkdb
DIST_FORMATS=sdist bdist_wheel bdist_egg

.PHONY: venv setup test dist clean


$(VENV_PYTHON):
	$(VIRTUALENV) venv;                 \
	for package in $(EXTRA_DEPS); do    \
	   venv/bin/pip install $$package;  \
	done

venv: $(VENV_PYTHON)

develop: venv
	for package in $(PACKAGES); do                      \
	    cd $$package;                                   \
	    ../$(VENV_PYTHON) setup.py develop || exit 1;   \
	    cd ..;                                          \
    done

test: develop
	for package in $(PACKAGES); do                      \
	    (cd $$package;                                  \
	     ../$(VENV_PYTHON) setup.py test;               \
	    )                                               \
    done


dist: venv
	for package in $(PACKAGES); do                     \
	    cd $$package;                                  \
            for format in $(DIST_FORMATS); do          \
                 ../$(VENV_PYTHON) setup.py $$format || exit 1;   \
            done;                                      \
	    cd ..;                                         \
    done
 
 
clean:
	for package in $(PACKAGES); do                            \
        (cd $$package;                                        \
         rm -rf build dist *.xml .coverage *.egg-info .eggs htmlcov .cache  \
        );                                                    \
	done;                                                     \
	rm -rf venv pytest-pyramid-server/vx pip-log.txt
	find . -name *.pyc -delete

all: 
	test