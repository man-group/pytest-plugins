# Package list, in order of ancestry
PACKAGES=pytest-fixture-config pytest-shutil pytest-server-fixtures pytest-listener pytest-pyramid-server pytest-qt-app pytest-svn pytest-virtualenv pytest-webdriver pytest-profiling pytest-verbose-parametrize
VENV_PYTHON=venv/bin/python

.PHONY: test clean


$(VENV_PYTHON):
	virtualenv venv


venv: $(VENV_PYTHON)

test: $(VENV_PYTHON)
	for package in $(PACKAGES); do                      \
	    (cd $$package;                                  \
	     ../$(VENV_PYTHON) setup.py develop || exit 1;  \
	     ../$(VENV_PYTHON) setup.py test || exit 1;     \
	    ) || break;                                     \
    done

 
clean:
	for package in $(PACKAGES); do                      \
        (cd $$package;                                  \
         rm -rf build dist *.xml .coverage              \
        );                                              \
	done;                                               \
	rm -rf venv
	

all: 
	test