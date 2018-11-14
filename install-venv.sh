#!/bin/bash

# Init venv
pip install --upgrade virtualenv
virtualenv venv
. venv/bin/activate
pip install \
  pandoc \
  wheel \
  coverage \
  python-jenkins \
  redis \
  pymongo \
  psycopg2 \
  boto3 \
  rethinkdb


