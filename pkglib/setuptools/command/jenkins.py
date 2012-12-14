import sys
import getpass
from setuptools import Command
from string import Template

from pkglib import CONFIG
from base import CommandMixin

# This is the XML template that is used to build and update Jenkins jobs
# It has the following variables:
#  $virtualenv
#  $description
#  $name
#  $repository
#  $email


#TODO: look at str.format()
JENKINS_CFG_XML = Template("""<?xml version='1.0' encoding='UTF-8'?>
<project>
  <actions/>
  <description>$description</description>
  <logRotator>
    <daysToKeep>-1</daysToKeep>
    <numToKeep>10</numToKeep>
    <artifactDaysToKeep>-1</artifactDaysToKeep>
    <artifactNumToKeep>-1</artifactNumToKeep>
  </logRotator>
  <keepDependencies>false</keepDependencies>
  <properties>
    <de.pellepelster.jenkins.walldisplay.WallDisplayJobProperty/>
  </properties>
  <scm class="hudson.scm.SubversionSCM">
    <locations>
      <hudson.scm.SubversionSCM_-ModuleLocation>
        <remote>$repository/trunk</remote>
        <local>$name</local>
      </hudson.scm.SubversionSCM_-ModuleLocation>
    </locations>
    <excludedRegions></excludedRegions>
    <includedRegions></includedRegions>
    <excludedUsers></excludedUsers>
    <excludedRevprop></excludedRevprop>
    <excludedCommitMessages></excludedCommitMessages>
    <workspaceUpdater class="hudson.scm.subversion.CheckoutUpdater"/>
  </scm>
  <assignedNode>reggie</assignedNode>
  <canRoam>false</canRoam>
  <disabled>false</disabled>
  <blockBuildWhenDownstreamBuilding>false</blockBuildWhenDownstreamBuilding>
  <blockBuildWhenUpstreamBuilding>false</blockBuildWhenUpstreamBuilding>
  <jdk>(Default)</jdk>
  <triggers class="vector">
    <hudson.triggers.TimerTrigger>
      <spec>32 22 * * 1-5</spec>
    </hudson.triggers.TimerTrigger>
    <hudson.triggers.SCMTrigger>
      <spec># set by slow_svn_poll
1,11,21,31,41,51 * * * *
</spec>
    </hudson.triggers.SCMTrigger>
  </triggers>
  <concurrentBuild>false</concurrentBuild>
  <builders>
    <hudson.tasks.Shell>
      <command>rm -rf build tmp*
$virtualenv -v --distribute build
./build/bin/easy_install pkglib
</command>
    </hudson.tasks.Shell>
    <hudson.tasks.Shell>
      <command>. ./build/bin/activate
cd ${JOB_NAME}
python setup.py develop
python setup.py test

# Build the documentation
python setup.py build_sphinx

</command>
    </hudson.tasks.Shell>
    <hudson.tasks.Shell>
      <command># This step runs the build, checks the version of the package and if it&apos;s a dev version uploads it to pypi.
. ./build/bin/activate
cd ${JOB_NAME}
python setup.py build
[ ! -z &quot;`grep &apos;^Version:&apos; ${JOB_NAME}.egg-info/PKG-INFO  | cut -d&apos; &apos; -f2 | sed s/[\.0-9]//g`&quot; ] &amp;&amp; python setup.py bdist_egg register upload
python setup.py upload_docs
</command>
    </hudson.tasks.Shell>
  </builders>
  <publishers>
    <hudson.plugins.cobertura.CoberturaPublisher>
      <coberturaReportFile>**/coverage.xml</coberturaReportFile>
      <onlyStable>false</onlyStable>
      <healthyTarget>
        <targets class="enum-map" enum-type="hudson.plugins.cobertura.targets.CoverageMetric">
          <entry>
            <hudson.plugins.cobertura.targets.CoverageMetric>CONDITIONAL</hudson.plugins.cobertura.targets.CoverageMetric>
            <int>70</int>
          </entry>
          <entry>
            <hudson.plugins.cobertura.targets.CoverageMetric>LINE</hudson.plugins.cobertura.targets.CoverageMetric>
            <int>80</int>
          </entry>
          <entry>
            <hudson.plugins.cobertura.targets.CoverageMetric>METHOD</hudson.plugins.cobertura.targets.CoverageMetric>
            <int>80</int>
          </entry>
        </targets>
      </healthyTarget>
      <unhealthyTarget>
        <targets class="enum-map" enum-type="hudson.plugins.cobertura.targets.CoverageMetric">
          <entry>
            <hudson.plugins.cobertura.targets.CoverageMetric>CONDITIONAL</hudson.plugins.cobertura.targets.CoverageMetric>
            <int>0</int>
          </entry>
          <entry>
            <hudson.plugins.cobertura.targets.CoverageMetric>LINE</hudson.plugins.cobertura.targets.CoverageMetric>
            <int>0</int>
          </entry>
          <entry>
            <hudson.plugins.cobertura.targets.CoverageMetric>METHOD</hudson.plugins.cobertura.targets.CoverageMetric>
            <int>0</int>
          </entry>
        </targets>
      </unhealthyTarget>
      <failingTarget>
        <targets class="enum-map" enum-type="hudson.plugins.cobertura.targets.CoverageMetric">
          <entry>
            <hudson.plugins.cobertura.targets.CoverageMetric>CONDITIONAL</hudson.plugins.cobertura.targets.CoverageMetric>
            <int>0</int>
          </entry>
          <entry>
            <hudson.plugins.cobertura.targets.CoverageMetric>LINE</hudson.plugins.cobertura.targets.CoverageMetric>
            <int>0</int>
          </entry>
          <entry>
            <hudson.plugins.cobertura.targets.CoverageMetric>METHOD</hudson.plugins.cobertura.targets.CoverageMetric>
            <int>0</int>
          </entry>
        </targets>
      </failingTarget>
      <sourceEncoding>ASCII</sourceEncoding>
    </hudson.plugins.cobertura.CoberturaPublisher>
    <hudson.tasks.junit.JUnitResultArchiver>
      <testResults>**/junit.xml</testResults>
      <keepLongStdio>false</keepLongStdio>
      <testDataPublishers/>
    </hudson.tasks.junit.JUnitResultArchiver>
    <hudson.plugins.violations.ViolationsPublisher>
      <config>
        <suppressions class="tree-set">
          <no-comparator/>
        </suppressions>
        <typeConfigs>
          <no-comparator/>
          <entry>
            <string>checkstyle</string>
            <hudson.plugins.violations.TypeConfig>
              <type>checkstyle</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>codenarc</string>
            <hudson.plugins.violations.TypeConfig>
              <type>codenarc</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>cpd</string>
            <hudson.plugins.violations.TypeConfig>
              <type>cpd</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>cpplint</string>
            <hudson.plugins.violations.TypeConfig>
              <type>cpplint</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>csslint</string>
            <hudson.plugins.violations.TypeConfig>
              <type>csslint</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>findbugs</string>
            <hudson.plugins.violations.TypeConfig>
              <type>findbugs</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>fxcop</string>
            <hudson.plugins.violations.TypeConfig>
              <type>fxcop</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>gendarme</string>
            <hudson.plugins.violations.TypeConfig>
              <type>gendarme</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>jcreport</string>
            <hudson.plugins.violations.TypeConfig>
              <type>jcreport</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>jslint</string>
            <hudson.plugins.violations.TypeConfig>
              <type>jslint</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>pep8</string>
            <hudson.plugins.violations.TypeConfig>
              <type>pep8</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>pmd</string>
            <hudson.plugins.violations.TypeConfig>
              <type>pmd</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>pylint</string>
            <hudson.plugins.violations.TypeConfig>
              <type>pylint</type>
              <min>10</min>
              <max>200</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern>**/pylint.xml</pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>simian</string>
            <hudson.plugins.violations.TypeConfig>
              <type>simian</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
          <entry>
            <string>stylecop</string>
            <hudson.plugins.violations.TypeConfig>
              <type>stylecop</type>
              <min>10</min>
              <max>999</max>
              <unstable>999</unstable>
              <usePattern>false</usePattern>
              <pattern></pattern>
            </hudson.plugins.violations.TypeConfig>
          </entry>
        </typeConfigs>
        <limit>100</limit>
        <sourcePathPattern></sourcePathPattern>
        <fauxProjectPath></fauxProjectPath>
        <encoding>default</encoding>
      </config>
    </hudson.plugins.violations.ViolationsPublisher>
    <hudson.plugins.claim.ClaimPublisher/>
    <hudson.tasks.Mailer>
      <recipients>$email</recipients>
      <dontNotifyEveryUnstableBuild>false</dontNotifyEveryUnstableBuild>
      <sendToIndividuals>false</sendToIndividuals>
    </hudson.tasks.Mailer>
  </publishers>
  <buildWrappers>
    <EnvInjectBuildWrapper>
      <info>
        <scriptContent>MPLCONFIGDIR=$WORKSPACE</scriptContent>
        <loadFilesFromMaster>false</loadFilesFromMaster>
      </info>
    </EnvInjectBuildWrapper>
  </buildWrappers>
</project>

""")


class jenkins(Command, CommandMixin):
    """ Create or update Jenkins build job """
    description = "Create or update the Hudson build job"

    user_options = [
        ('server=', 's', 'Jenkins server (defaults to %s' % CONFIG.jenkins_url),
        ('username=', 'u', 'Windows username (defaults to your current user)'),
        ('password=', 'p', 'Windows password (will prompt if omitted)'),
        ('vcs-url=', 'V', 'Override VCS Url (only really for testing)'),
        ('no-prompt', 'P', 'Disable prompts'),
    ]
    boolean_options = [
        'no-prompt',
    ]

    def initialize_options(self):
        self.username = getpass.getuser()
        self.password = None
        self.server = CONFIG.jenkins_url
        self.no_prompt = False
        self.vcs_url = None

    def finalize_options(self):
        if self.vcs_url:
            self.distribution.metadata.url = self.vcs_url

    def run(self):
        # Run the egg_info step to find our VCS url.
        self.run_command('egg_info')
        if not self.distribution.metadata.url:
            print "This package does not appear to be in any repository, aborting."
            sys.exit(1)

        # Pull down jenkins package
        self.fetch_build_eggs(['python_jenkins'])

        from jenkins import Jenkins

        print "Connecting to Jenkins at %s" % self.server

        # Prompt for password or use command-line
        if self.no_prompt:
            if self.password is None:
                print "Must specify password if no-prompt is set."
                sys.exit(1)
            password = self.password
        else:
            password = getpass.getpass("Please enter your Jenkins password: ")

        jenkins = Jenkins(self.server, self.username, password)
        name = self.distribution.metadata.name
        cfg_xml = JENKINS_CFG_XML.safe_substitute(
                name=name,
                description=self.distribution.metadata.description,
                repository=self.distribution.metadata.url,
                email=self.distribution.metadata.author_email,
                virtualenv=CONFIG.virtualenv_executable,
        )
        if jenkins.job_exists(name):
            if not self.no_prompt:
                while True:
                    user_input = raw_input("Job already exists, update configuration? [y/n]")
                    if not user_input in ('y', 'n'):
                        continue
                    break
                if user_input == 'n':
                    return

            print "Reconfiguring job at %s/job/%s" % (self.server, name)
            jenkins.reconfig_job(name, cfg_xml)
        else:
            print "Creating job at %s/job/%s" % (self.server, name)
            jenkins.create_job(name, cfg_xml)
