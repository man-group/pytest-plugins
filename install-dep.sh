#!/bin/bash

# Install System Deps
apt-get update
apt-get install -y \
  build-essential \
  default-jdk \
  curl \
  wget \
  git

# Update Apt-Sources
wget -qO- https://download.rethinkdb.com/apt/pubkey.gpg | apt-key add - 
. /etc/lsb-release && echo "deb http://download.rethinkdb.com/apt $DISTRIB_CODENAME main" | tee /etc/apt/sources.list.d/rethinkdb.list

wget -q -O - https://pkg.jenkins.io/debian/jenkins-ci.org.key | apt-key add -
sh -c 'echo deb http://pkg.jenkins.io/debian-stable binary/ > /etc/apt/sources.list.d/jenkins.list'

apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6 
echo "deb [ arch=amd64 ] http://repo.mongodb.org/apt/ubuntu trusty/mongodb-org/3.4 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-3.4.list 

apt-get update

# Install Fixtures
apt-get install -y \
  xvfb \
  x11-utils \
  subversion \
  graphviz \
  pandoc \
  postgresql \
  postgresql-contrib \
  libpq-dev \
  redis-server \
  rethinkdb \
  jenkins \
  mongodb-org \
  mongodb-org-server \
  apache2

wget -q https://dl.minio.io/server/minio/release/linux-amd64/minio -O /usr/local/bin/minio
chmod a+x /usr/local/bin/minio

curl -sL https://deb.nodesource.com/setup_6.x | bash -
apt-get install -y nodejs
$(which npm) install -g phantomjs
apt-get install -y libfontconfig
