# coding: utf-8
import sys
from collections import OrderedDict
from arguments import Arguments as A, ArgumentsParser
from config import Config
from resource import ProjectResource, IssueResource, UserResource, VersionResource, IssueStatusResource

try:
    from redminelib import Redmine
except ImportError:
    print >> sys.stderr, 'You need to install python-redmine'
    sys.exit(1)


class RedmineCli(object):

    description = 'Redmine command line interface'

    arguments = [
        A('-p', '--profile', type=str, help='Profile from config file'),
        A('-H', '--host', type=str, help='Redmine URL'),
        A('-u', '--user', type=str, help='Redmine login'),
        A('-P', '--password', type=str, help='Redmine password'),
        A('-k', '--key', type=str, help='Redmine API key'),
        A('-V', '--redmineversion', type=str, help='Redmine version'),
        A('-v', '--version', action='version', version='%(prog)s 0.1'),
    ]

    resources = OrderedDict({r.name: r for r in [
        ProjectResource, IssueResource, UserResource, VersionResource, IssueStatusResource
    ]})

    def __init__(self):
        self.args = ArgumentsParser(self).parse_args()
        self.config = Config(self.args)
        self.redmine = Redmine(self.config.host, **self.config.auth_info)
        self._resource = None

    @property
    def resource(self):
        if not self._resource:
            self._resource = self.resources[self.config.resource](self)
        return self._resource

    def run(self):
        self.resource.command.run()
