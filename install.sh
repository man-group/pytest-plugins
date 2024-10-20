#!/bin/bash
set -eo pipefail
# Debug for now
set -x


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
    git-lfs \
    unzip
}

function install_python_ppa {
  apt-get install -y software-properties-common
  add-apt-repository -y ppa:deadsnakes/ppa
  apt-get update
}

function install_python_packaging {
  local py=$1
  $py -m pip install --upgrade pip
  $py -m pip install --upgrade setuptools
  $py -m pip install --upgrade virtualenv
}


function install_python {
  local py=$1
  sudo apt-get install -y $py $py-dev
  local version=$(echo $py | grep -oP '(?<=python)\d+\.\d+')

  if [ "$version" = "3.6" ] || [ "$version" = "3.7" ]; then
    sudo apt-get install ${py}-distutils || {
    curl --silent --show-error --retry 5 https://bootstrap.pypa.io/pip/$version/get-pip.py | sudo $py
    sudo $py -m pip install setuptools
    }
  elif [ "$version" = "3.10" ] || [ "$version" = "3.11" ] || [ "$version" = "3.12" ]; then
    sudo apt-get install ${py}-distutils
    curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo $py
  else
    sudo apt-get install ${py}
    curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo $py
  fi
  install_python_packaging $py
}

function choco_install {
  local args=$*
  for i in {1..5}; do
      choco install $args && return 0
      echo 'choco install failed, log tail follows:'
      tail -500 C:/ProgramData/chocolatey/logs/chocolatey.log
      echo 'sleeping for a bit and retrying'.
      sleep 5
  done
  return 1
}


function install_windows_make {
  choco_install make --params "/InstallDir:C:\\tools\\make"
}

function install_windows_python() {
    if [ -z "$1" ]; then
        echo "Please provide a Python version argument, e.g., 'python3.11'"
        return 1
    fi
    python_arg="$1"
    python_version="${python_arg#python}"
    major_version="${python_version%%.*}"
    minor_version="${python_version#*.}"
    choco_package="python${major_version}${minor_version}"
    install_dir="/c/Python${major_version}${minor_version}"
    choco_install "$choco_package" --params "/InstallDir:C:\\Python" -y
    if [ $? -ne 0 ]; then
        echo "Failed to install Python $python_version"
        return 1
    fi
    export PATH="$install_dir:$install_dir/Scripts:$PATH"
    install_python_packaging python
}

function init_venv {
  local py=$1
  virtualenv venv --python=$py
  if [ -f venv/Scripts/activate ]; then
      . venv/Scripts/activate
  else
      . venv/bin/activate
  fi
}


function update_apt_sources {
  # Add Jenkins GPG key and repository
  curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key | gpg --dearmor -o /usr/share/keyrings/jenkins-archive-keyring.gpg
  echo "deb [signed-by=/usr/share/keyrings/jenkins-archive-keyring.gpg] https://pkg.jenkins.io/debian-stable binary/" | tee /etc/apt/sources.list.d/jenkins.list > /dev/null

  # Add MongoDB GPG key and repository
  curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
     sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg \
     --dearmor
  echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

  apt install ca-certificates
  apt-get update
}

function install_system_deps {
  apt-get install -y \
    xvfb \
    x11-utils \
    subversion \
    graphviz \
    pandoc \
    net-tools
}

function install_postgresql {
  apt-get install -y postgresql postgresql-contrib libpq-dev
  service postgresql stop; update-rc.d postgresql disable;
}

function install_redis {
  apt-get install -y redis-server
}

function install_graphviz {
  apt-get install -y graphviz
}

function install_jenkins {
  apt-get install -y jenkins
  service jenkins stop; update-rc.d jenkins disable;
}

function install_mongodb {
  apt-get install -y mongodb mongodb-server
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
  json=$(curl -s https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json)
  version=$(echo "$json" | jq -r '.channels.Stable.version')
  url="https://storage.googleapis.com/chrome-for-testing-public/$version/linux64/chromedriver-linux64.zip"
  wget -q "$url" -O /tmp/chromedriver_linux64.zip
  unzip /tmp/chromedriver_linux64.zip
  mv chromedriver-linux64/chromedriver /usr/local/bin/
  chmod a+x /usr/local/bin/chromedriver
}

function install_kubernetes {
  apt-get update && apt-get install -y apt-transport-https curl

  curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
cat <<EOF >/etc/apt/sources.list.d/kubernetes.list
deb https://apt.kubernetes.io/ kubernetes-xenial main
EOF

  apt-get update
  apt-get install -y kubelet kubeadm kubectl
  apt-mark hold kubelet kubeadm kubectl

  systemctl daemon-reload
  systemctl stop kubelet
  swapoff -a
  kubeadm init --ignore-preflight-errors=SystemVerification --pod-network-cidr=192.168.0.0/16
  export KUBECONFIG=/etc/kubernetes/admin.conf

  # install cni (calico)
  kubectl apply -f https://docs.projectcalico.org/v3.3/getting-started/kubernetes/installation/hosted/rbac-kdd.yaml
  kubectl apply -f https://docs.projectcalico.org/v3.3/getting-started/kubernetes/installation/hosted/kubernetes-datastore/calico-networking/1.7/calico.yaml
  kubectl get node

  # allow master node to run pods since we are creating a single-node cluster
  kubectl taint node $(hostname -s) node-role.kubernetes.io/master-

  # copy kubeconfig
  cp -f /etc/kubernetes/admin.conf /home/vagrant/.kube/config
  chown -R vagrant: /home/vagrant/.kube
}

function install_black {
  python3.6 -mpip install black
}

# Install all
function install_all {
  install_base_tools
  install_python_ppa

  install_python python2.7
  install_python python3.5
  install_python python3.6
  install_python python3.7

  install_black

  update_apt_sources
  install_system_deps
  install_postgresql
  install_redis
  install_jenkins
  install_mongodb
  install_apache
  install_minio
  install_chrome_headless
}

