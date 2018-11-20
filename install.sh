#!/bin/bash

# Suppress the "dpkg-preconfigure: unable to re-open stdin: No such file or directory" error
export DEBIAN_FRONTEND=noninteractive

function install_base_tools {
  apt-get update
  apt-get install -y \
    build-essential \
    default-jdk \
    curl \
    wget \
    git \
    unzip
}

function install_python_ppa {
  apt-get install -y software-properties-common
  add-apt-repository -y ppa:deadsnakes/ppa
  apt-get update
}

function install_python {
  local py=$1
  apt-get install -y $py $py-dev
  curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | $py
  $py -m pip install --upgrade pip
  $py -m pip install --upgrade virtualenv
}

function init_venv {
  local py=$1
  virtualenv venv/$py --python=$py
  . venv/bin/activate
  pip install \
    pypandoc \
    coverage
}

function update_apt_sources {
  wget -qO- https://download.rethinkdb.com/apt/pubkey.gpg | apt-key add - 
  . /etc/lsb-release && echo "deb http://download.rethinkdb.com/apt $DISTRIB_CODENAME main" | tee /etc/apt/sources.list.d/rethinkdb.list

  wget -q -O - https://pkg.jenkins.io/debian/jenkins-ci.org.key | apt-key add -
  sh -c 'echo deb http://pkg.jenkins.io/debian-stable binary/ > /etc/apt/sources.list.d/jenkins.list'

  apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6 
  echo "deb [ arch=amd64 ] http://repo.mongodb.org/apt/ubuntu trusty/mongodb-org/3.4 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-3.4.list 

  apt-get update
}

function install_system_deps {
  apt-get install -y \
    xvfb \
    x11-utils \
    subversion \
    graphviz \
    pandoc 
}

function install_postgresql {
  apt-get install -y postgresql postgresql-contrib libpq-dev
  service postgresql stop; update-rc.d postgresql disable;
}

function install_redis {
  apt-get install -y redis-server
}

function install_rethinkdb {
  apt-get install -y rethinkdb
  service rethinkdb stop; update-rc.d rethinkdb disable;
}

function install_jenkins {
  apt-get install -y jenkins
  service jenkins stop; update-rc.d jenkins disable;
}

function install_mongodb {
  apt-get install -y mongodb-org mongodb-org-server
}

function install_apache {
  apt-get install -y apache2
  service apache2 stop; update-rc.d apache2 disable;
}

function install_minio {
  wget -q https://dl.minio.io/server/minio/release/linux-amd64/minio -O /tmp/minio
  mv /tmp/minio /usr/local/bin/minio
  chmod a+x /usr/local/bin/minio 
}

function install_chrome_headless {
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/google-chrome-stable_current_amd64.deb
  dpkg -i --force-depends /tmp/google-chrome-stable_current_amd64.deb || apt-get install -f -y
  wget -q https://chromedriver.storage.googleapis.com/2.43/chromedriver_linux64.zip -O /tmp/chromedriver_linux64.zip
  unzip /tmp/chromedriver_linux64.zip
  mv chromedriver /usr/local/bin/
  chmod a+x /usr/local/bin/chromedriver
}

# Install all
function install_all {
  install_base_tools
  install_python_ppa

  install_python python2.7
  install_python python3.4
  install_python python3.5
  install_python python3.6

  update_apt_sources
  install_system_deps
  install_postgresql
  install_redis
  install_rethinkdb
  install_jenkins
  install_mongodb
  install_apache
  install_minio
  install_chrome_headless
}
