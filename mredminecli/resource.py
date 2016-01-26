from collections import OrderedDict
from command import ProjectListCommand, IssueListCommand, IssueShowCommand, IssueUpdateCommand,\
    IssueCreateCommand, UserListCommand, VersionListCommand, IssueStatusList


class BaseResource(object):

    commands = {}

    def __init__(self, redminecli):
        self.redminecli = redminecli
        self._command = None

    @property
    def command(self):
        if not self._command:
            self._command = self.commands[self.redminecli.config.command](self)
        return self._command


class ProjectResource(BaseResource):
    name = 'project'

    commands = OrderedDict({c.name: c for c in [
        ProjectListCommand
    ]})


class IssueResource(BaseResource):
    name = 'issue'

    commands = OrderedDict({c.name: c for c in [
        IssueListCommand, IssueShowCommand, IssueUpdateCommand, IssueCreateCommand
    ]})


class UserResource(BaseResource):
    name = 'user'

    commands = OrderedDict({c.name: c for c in [
        UserListCommand
    ]})


class VersionResource(BaseResource):
    name = 'version'

    commands = OrderedDict({c.name: c for c in [
        VersionListCommand
    ]})


class IssueStatusResource(BaseResource):
    name = 'issuestatus'
    redmine_name = 'issue_status'

    commands = OrderedDict({c.name: c for c in [
        IssueStatusList
    ]})
