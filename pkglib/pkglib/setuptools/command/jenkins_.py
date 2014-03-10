import cgi
import getpass
import sys

from distutils import log
from string import Template

from setuptools import Command

from pkglib import CONFIG, util

import base

# Below, XML templates are loaded which are used to build and update Jenkins
# jobs. They have the following variables:
#
#  $description
#  $name
#  $repository
#  $email

# For matrix jobs:
#  $python_string_xml



class jenkins(Command, base.CommandMixin):
    """ Create or update Jenkins build job """
    description = "Create or update the Hudson build job"

    user_options = [
        ('server=', 's', 'Jenkins server (defaults to %s)' % CONFIG.jenkins_url),
        ('username=', 'u', 'Windows username (defaults to your current user)'),
        ('password=', 'p', 'Windows password (will prompt if omitted)'),
        ('keytab=', 'k', 'Kerberos keytab (will prompt if omitted)'),
        ('vcs-url=', 'V', 'Override VCS Url (only really for testing)'),
        ('no-prompt', 'P', 'Disable prompts'),
        ('matrix', 'm', 'Create a matrix build'),
    ]
    boolean_options = [
        'no-prompt',
    ]

    def initialize_options(self):
        self.username = getpass.getuser()
        self.password = None
        self.keytab = None
        self.server = None
        self.no_prompt = False
        self.vcs_url = None
        self.matrix = False

    def finalize_options(self):
        if self.vcs_url:
            self.distribution.metadata.url = self.vcs_url

    def _get_active_python_versions(self):
        if CONFIG.jenkins_matrix_job_pyversions:
            return CONFIG.jenkins_matrix_job_pyversions
        return (util.short_version(sys.version_info, max_parts=3, separator='.'),)

    def _construct_string_values(self, values):
        return "\n".join("<string>%s</string>" % s for s in values)

    def run(self):
        # Run the egg_info step to find our VCS url.
        self.run_command('egg_info')
        if not self.distribution.metadata.url:
            log.warn("This package does not appear to be in any repository, "
                     "aborting.")
            sys.exit(1)

        # Pull down Jenkins package
        base.fetch_build_eggs(['jenkins'], dist=self.distribution)
        from jenkins import Jenkins
        server = CONFIG.jenkins_url
        log.info("Connecting to Jenkins at %s" % server)

        jenkins = Jenkins(server, self.username, self.password)
        name = self.distribution.metadata.name

        if (self.matrix):
            log.info("Matrix job")
            if CONFIG.jenkins_matrix_job_xml:
                path, fname = CONFIG.jenkins_matrix_job.split(':')
            else:
                path, fname = None, 'jenkins_job_matrix.xml'
        else:
            log.info("Non-matrix job - use \'--matrix\' option for matrix builds")
            if CONFIG.jenkins_job_xml:
                path, fname = CONFIG.jenkins_job.split(':')
            else:
                path, fname = None, 'jenkins_job.xml'

        with open(base.get_resource_file(fname, path)) as f:
            jenkins_config_xml = Template(f.read())

        cfg_xml = jenkins_config_xml.safe_substitute(
            name=cgi.escape(name),
            hyphen_escaped_name=cgi.escape(name).replace("-", "?").replace("_", "?"),
            description=cgi.escape(self.distribution.metadata.description),
            repository=self.distribution.metadata.url,
            email=self.distribution.metadata.author_email,
            python_string_xml=self._construct_string_values(self._get_active_python_versions()),
            virtualenv=CONFIG.virtualenv_executable,
            username=self.username
        )

        if jenkins.job_exists(name):
            log.error("Job found at %s/job/%s Please delete this before creating a new one." % (server, name))
        else:
            if (not self.dry_run):
                log.info("Creating job at %s/job/%s" % (server, name))
                jenkins.create_job(name, cfg_xml)
# TODO: look at str.format()
