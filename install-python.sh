#!/bin/bash

# Install common tools
apt-get update

# Install Python
apt-get install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y \
  python \
  python-dev \
  python-pip \

