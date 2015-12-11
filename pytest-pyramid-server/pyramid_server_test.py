#
# Entrance point for the integration tests
#
from pyramid.response import Response
from pyramid.config import Configurator


def main(global_config, **settings):
    config = Configurator(settings=settings,)
    config.add_route('home', 'test')
    config.add_view(lambda request: Response('OK'), route_name='home')
    return config.make_wsgi_app()
