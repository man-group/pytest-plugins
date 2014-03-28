import os
import socket
import string

from .server import HTTPTestServer


SERVER_CFG = string.Template("""
  LoadModule headers_module modules/mod_headers.so
  LoadModule proxy_module modules/mod_proxy.so
  LoadModule proxy_http_module modules/mod_proxy_http.so
  LoadModule proxy_connect_module modules/mod_proxy_connect.so
  LoadModule alias_module modules/mod_alias.so
  LoadModule dir_module modules/mod_dir.so
  LoadModule autoindex_module modules/mod_autoindex.so
  LoadModule log_config_module modules/mod_log_config.so
  LoadModule mime_module modules/mod_mime.so

  StartServers 1
  ServerLimit 8

  TypesConfig /etc/mime.types
  DefaultType text/plain


  ServerRoot $server_root
  Listen $listen_addr

  ErrorLog $server_root/logs/error.log
  LogFormat "%h %l %u %t \\"%r\\" %>s %b" common
  CustomLog logs/access_log common
  LogLevel info

  $proxy_rules

  Alias / $document_root

  <Directory $server_root>
      Options +Indexes
  </Directory>

  $extra_cfg
""")


class HTTPDProxyServer(HTTPTestServer):
    port_seed = 65531

    def __init__(self, proxy_rules=None, extra_cfg='', **kwargs):
        """ httpd Proxy Server

        Parameters
        ----------
        proxy_rules: `dict`
            { proxy_src: proxy_dest }. Eg   {'/downstream_url/' : server.uri}
        extra_cfg: `str`
            Any extra Apache config

        """
        self.proxy_rules = proxy_rules if proxy_rules is not None else {}
        self.extra_cfg = extra_cfg
        self.document_root = kwargs.get('document_root')

        # Always print debug output for this process
        os.environ['DEBUG'] = '1'

        # Discover externally accessable hostname so selenium can get to it
        kwargs['hostname'] = kwargs.get('hostname', socket.gethostbyname(os.uname()[1]))

        super(HTTPDProxyServer, self).__init__(**kwargs)

    def pre_setup(self):
        """ Write out the config file
        """
        self.config = self.workspace / 'httpd.conf'
        rules = []
        for source in self.proxy_rules:
            rules.append("ProxyPass {} {}".format(source, self.proxy_rules[source]))
            rules.append("ProxyPassReverse {} {} \n".format(source, self.proxy_rules[source]))
        cfg = SERVER_CFG.substitute(
            server_root=self.workspace,
            document_root=self.document_root if self.document_root else self.workspace,
            listen_addr="{host}:{port}".format(host=self.hostname, port=self.port),
            proxy_rules='\n'.join(rules),
            extra_cfg=self.extra_cfg
        )
        self.config.write_text(cfg)

        (self.workspace / 'run').mkdir()
        if not os.path.exists(self.workspace / 'logs'):
            (self.workspace / 'logs').mkdir()

    @property
    def run_cmd(self):
        return ['/usr/sbin/httpd', '-f', self.config]
