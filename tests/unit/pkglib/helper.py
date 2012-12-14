import io

from mock import Mock


class Req(object):
    def __init__(self, project_name, specs):
        self.project_name = project_name
        self.specs = specs

class Pkg(object):
    def __init__(self, name, requires, src=False, location=None, version='1.0.0'):
        self.project_name = name
        self._requires = requires
        self.version = version
        if location is None:
            if src:
                self.location = "/path/to/somewhere"
            else:
                self.location = "/path/to/an.egg"
        else:
            self.location = location

    def __repr__(self):
        return "<%s>" % self.project_name

    def requires(self):
        return self._requires


clue_page = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd"> 
<html xmlns="http://www.w3.org/1999/xhtml"> 
  <head> 
    <link rel="stylesheet" type="text/css" charset="utf-8"
          media="all" href="http://acmepypi/static/cluerelmgr.css" />
 
    <title>ClueReleaseManager :: acme.foo</title>
  </head> 
  <body> 
    <div class="top"> 
      <div class="logo"><a href="http://acmepypi/">ClueReleaseManager</a></div>
      <ul class="top-actions"> 
        <li class="first"><a href="http://acmepypi/login">Login</a></li>
         
        <li><a href="http://acmepypi/simple/">Simple Index</a></li>
        <li>v0.3.3</li> 
      </ul> 
    </div> 
    
<div class="breadcrumbs"><a href="http://acmepypi/">Home</a> :: acme.foo</div>
 
<div class="distro-block distro-metadata"> 
  <h4>Metadata</h4> 
  <dl> 
    <dt>Distro Index Owner:</dt> 
    <dd>acmepypi</dd>
    <dt>Home Page:</dt> 
    <dd><a href="http://mysvn/acme.foo">http://mysvn/acme.foo</a></dd>
  </dl> 
</div> 
 
<h1>acme.foo</h1>
<div class="distro-block distro-files"> 
  <h4>Files</h4> 
  <ul class="file-listing"> 
    
    <li><a href="http://acmepypi/d/acme.foo/f/acme.foo-1.0.dev1.tar.gz">acme.foo-1.0.dev1.tar.gz</a></li>
     
    <li><a href="http://acmepypi/d/acme.foo/f/acme.foo-1.0.dev1-py2.6.egg">acme.foo-1.0.dev1-py2.6.egg</a></li>
     
  </ul> 
</div> 
 
<div class="distro-block distro-indexes"> 
  <h4>Indexes</h4> 
  <ul class="index-listing"> 
    
    <li class="empty">no indexes</li> 
    
  </ul> 
</div> 
 
<p class="distro-summary">Hello !</p> 
<p class="distro-description"><div class="rst"><div class="document"> 
<p>Hello !</p> 
</div> 
</div></p> 
 
  </body> 
</html>
"""

def mock_clue():
    return Mock(return_value=io.BytesIO(clue_page))
