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
    config.proxy.no_proxy = "localhost,127.0.0.0/8,10.0.0.0/8,172.0.0.0/8"
  end

  config.vm.hostname = "pytest-plugins-dev"
  config.vm.box = "bento/ubuntu-16.04"
  config.vm.network "private_network", type: "dhcp"
  config.vm.provision "docker"
  config.vm.provision "file", source: "install.sh", destination: "/tmp/install.sh"
  config.vm.provision "shell", inline: ". /tmp/install.sh && install_all"
  config.vm.provision "shell", inline: ". /tmp/install.sh && init_venv python3.7", privileged: false
end
