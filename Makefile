# Package list, in order of ancestry
# removed pytest-qt-app                  
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
UPLOAD_OPTS =

# Used for determining which packages get released
LAST_TAG := $(shell git tag -l v\* | sort -t. -k 1,1n -k 2,2n -k 3,3n -k 4,4n | tail -1)
CHANGED_PACKAGES := $(shell git diff --name-only $(LAST_TAG) | grep pytest- | cut -d'/' -f1 | sort | uniq)

# removed from PHONY:  circleci_sip circleci_pyqt
.PHONY: extras copyfiles wheels eggs sdists install develop test upload clean

extras:
	pip install $(EXTRA_DEPS)

copyfiles:
	./foreach.sh 'for file in $(COPY_FILES); do cp ../$$file .; done'

wheels: copyfiles
	pip install -U wheel
	./foreach.sh 'python setup.py bdist_wheel'

eggs: copyfiless
	./foreach.sh 'python setup.py bdist_egg'

sdists: copyfiles
	./foreach.sh 'python setup.py sdist'

install: wheels
	./foreach.sh 'pip install dist/*.whl'

develop: copyfiles extras
	./foreach.sh 'pip install -e.[tests]'

test:
	rm -f FAILED-*
	./foreach.sh 'DEBUG=1 python setup.py test || touch ../FAILED-$$PKG'
	compgen -G 'FAILED-*' && exit 1

upload: 
	pip install twine
	for package in $(CHANGED_PACKAGES); do                     \
	    cd $$package;                                  \
            if [ -f common_setup.py ]; then  \
                twine upload $(UPLOAD_OPTS) dist/*; \
            fi; \
	    cd ..;                                         \
    done

clean:
	./foreach.sh 'rm -rf build dist *.xml *.egg-info .eggs htmlcov .cache $(COPY_FILES)'
	rm -rf pytest-pyramid-server/vx pip-log.txt
	find . -name *.pyc -name .coverage -name .coverage.* -delete
	rm -f FAILED-*

all: extras develop test