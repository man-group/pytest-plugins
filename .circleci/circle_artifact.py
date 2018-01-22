#!/usr/bin/env python
""" CircleCI artifact query tool
"""
import sys
import os
from circleclient.circleclient import CircleClient
import fnmatch


def main():
    token = sys.argv[1]
    search_pattern = sys.argv[2]
    user = os.environ['CIRCLE_PROJECT_USERNAME']
    repo = os.environ['CIRCLE_PROJECT_REPONAME']
    branch = os.environ['CIRCLE_BRANCH']
    node = os.environ['CIRCLE_NODE_INDEX']
    client = CircleClient(token)
    builds = client.build.recent(username=user, project=repo, branch=branch, status_filter='completed')
    if builds:
        artifacts = client.build.artifacts(username=user, project=repo, build_num=builds[0]['build_num'])
        artifacts = [i for i in artifacts
                     if i['node_index'] == int(node) and
                     fnmatch.fnmatch(i['path'].rsplit('/', 1)[-1], search_pattern)]
        for i in artifacts:
            print(i['url'])

if __name__ == '__main__' :
    main()

