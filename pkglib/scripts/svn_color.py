#!/usr/bin/env python
""" Colourized SVN filter
    ---------------------

    Also adds some custom commands:
    allst:  recursively find all svn checkouts under PROJECT_HOME and run 'svn st' on them.
"""

import sys
import re
import subprocess
import itertools
import os.path

tabsize = 4

colorizedSubcommands = (
    'status', 'st',
    'add',
    'copy', 'cp',
    'remove', 'rm', 'del', 'delete',
    'move', 'mv', 'rename', 'rn',
    'diff', 'di',
    'co', 'checkout',
    # custom
    'allst',
)

#TODO: convert to use termcolor
statusColors = {
    "\s*M\s*": "33", # red
    "\s*\?\s*": "37", # grey
    "\s*A\s*": "32", # green
    "\s*X\s*": "33", # yellow
    "\s*C\s*": "30;41", # black on red
    "\s*-\s*": "31", # red
    "\s*D\s*": "31;1", # bold red
    "\s*\+\s*": "32", # green
}


def colorize(stream):
    for line in stream:
        for color in statusColors.keys():
            if re.match(color, line):
                line = ''.join(("\033[", statusColors[color], "m", line, "\033[m"))
                break
        yield line


def filter_blacklist(stream, patterns):
    for line in stream:
        matched = False
        for p in patterns:
            if re.match(p, line):
                matched = True
                break
        if not matched:
            yield line


def expandtabs(stream):
    for line in stream:
        yield line.expandtabs(tabsize)


def escape(s):
    s = s.replace('$', r'\$')
    s = s.replace('"', r'\"')
    s = s.replace('`', r'\`')
    return s

passthru = lambda x: x
quoted = lambda x: '"%s"' % escape(x)


def traverse(dirname):
    """  Find svn head dirs
    """
    heads = []
    _, dirs, _ = os.walk(dirname).next()
    if '.svn' in dirs:
        heads.append(dirname)
    else:
        for d in dirs:
            heads += traverse(os.path.join(dirname, d))
    return heads


def main():
    if sys.argv[1] == '-':
        # Work from stdin stream
        output = expandtabs(sys.stdin)
        output = colorize(output)
    else:
        # Work from subprocess driven by cmdline

        # Process Custom commands
        if sys.argv[1] == 'allst':
            # Stat all working project dirs
            output = subprocess.Popen('svn st --ignore-externals %s' % ' '.join(
                traverse(os.environ['PROJECT_HOME'])), shell=True, stdout=subprocess.PIPE)
            # skip externals stat lines
            output = itertools.ifilterfalse(lambda line: re.match('^X', line), output.stdout)
            output = expandtabs(output)
            output = colorize(output)

        # Colourised svn arguments
        elif(sys.argv[1] in colorizedSubcommands):
            cmd = ' '.join(['svn'] + [(passthru, quoted)[' ' in arg](arg) for arg in sys.argv[1:]])
            output = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
            output = output.stdout
            output = expandtabs(output)
            output = colorize(output)

        # Straight passthrough
        else:
            cmd = ' '.join(['svn'] + sys.argv[1:])
            subprocess.Popen(cmd, shell=True).communicate()
            output = []
    map(sys.stdout.write, output)

if __name__ == '__main__':
    main()
