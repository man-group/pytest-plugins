# Package list, in order of ancestry
# removed pytest-qt-app
EXTRA_DEPS = setuptools-git \
             pytest-timeout \
             pypandoc       \
             wheel          \
             coverage       \
             python-jenkins \
             redis          \
             pymongo        \
             psycopg2-binary\
             boto3          \
             docker         \
             kubernetes


COPY_FILES = VERSION CHANGES.md common_setup.py MANIFEST.in LICENSE
UPLOAD_OPTS =
PYPI_INDEX =

PIP_INSTALL_ARGS := $(shell [ ! -z "${PYPI_INDEX}" ] && echo --index ${PYPI_INDEX} )

# removed from PHONY:  circleci_sip circleci_pyqt
.PHONY: extras copyfiles wheels eggs sdists install develop test upload clean

extras:
	pip install ${PIP_INSTALL_ARGS} ${EXTRA_DEPS}

copyfiles:
	./foreach.sh 'for file in ${COPY_FILES}; do cp ../$$file .; done'

wheels: copyfiles
	pip install ${PIP_INSTALL_ARGS} -U wheel
	./foreach.sh --changed 'python setup.py bdist_wheel'

eggs: copyfiles
	./foreach.sh --changed 'python setup.py bdist_egg'

sdists: copyfiles
	./foreach.sh --changed 'python setup.py sdist'

install: copyfiles
	pip install ${PIP_INSTALL_ARGS} -U wheel
	./foreach.sh 'python setup.py bdist_wheel'
	./foreach.sh 'pip install ${PIP_INSTALL_ARGS} dist/*.whl'

develop: copyfiles extras
	./foreach.sh 'pip install ${PIP_INSTALL_ARGS} -e.[tests]'

test:
	rm -f FAILED-*
	./foreach.sh 'DEBUG=1 python setup.py test -sv -ra || touch ../FAILED-$$PKG'
	bash -c "! compgen -G 'FAILED-*'"

test-ci:
	rm -f FAILED-*
	./foreach.sh 'cat *.egg-info/top_level.txt  | xargs -Ipysrc coverage run -p --source=pysrc -m pytest --junitxml junit.xml -svvvv -ra || touch ../FAILED-$$PKG'

upload:
	pip install twine
	./foreach.sh --changed '[ -f common_setup.py ] && twine upload $(UPLOAD_OPTS) dist/*'

clean:
	./foreach.sh 'rm -rf build dist *.xml *.egg-info .eggs htmlcov .cache $(COPY_FILES)'
	rm -rf pytest-pyramid-server/vx pip-log.txt
	find . -name *.pyc -delete
	find . -name .coverage -delete
	find . -name .coverage.* -delete
	rm -f FAILED-*

all: extras develop test
