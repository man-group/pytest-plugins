$script = <<-SCRIPT
SVCS="postgresql jenkins rethinkdb apache2"
systemctl stop $SVCS
systemctl disable $SVCS
SCRIPT

############# Start vagrant config ###############
Vagrant.configure("2") do |config|
  # Specify your hostname if you like
  config.vm.provider "virtualbox" do |v|
    v.memory = 4096
    v.cpus = 4
  end

  if Vagrant.has_plugin?("vagrant-proxyconf")
    config.proxy.http = "#{ENV['http_proxy']}"
    config.proxy.https = "#{ENV['https_proxy']}"
  end

  config.vm.hostname = "pytest-plugins-dev"
  config.vm.box = "bento/ubuntu-16.04"
  config.vm.network "private_network", type: "dhcp"
  config.vm.provision "shell", path: "install-python.sh"
  config.vm.provision "shell", path: "install-dep.sh"
  config.vm.provision "shell", inline: $script
  config.vm.provision "shell", path: "install-venv.sh", privileged: false
end
