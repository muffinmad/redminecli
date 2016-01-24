import io
import os
import ConfigParser
from . import RedmineCliException


DEFAULT_CONFIG = """
[DEFAULT]
default=False
host=
user=
password=
key=
redmineversion=
fg0=\033[0;30m
fg1=\033[0;31m
fg2=\033[0;32m
fg3=\033[0;33m
fg4=\033[0;34m
fg5=\033[0;35m
fg6=\033[0;36m
fg7=\033[0;37m
bld=\033[1m
clr=\033[0m
_list_group_format=%(bld)s{GROUP}%(clr)s
_list_group_indent_width=2
project_list_format=%(fg5)s{id:>{id_WIDTH}}%(clr)s %(fg6)s{identifier:<{identifier_WIDTH}}%(clr)s {name}
issue_list_format={INDENT}%(fg5)s{tracker__name:^{tracker__name_WIDTH}}%(clr)s %(fg2)s{priority__name:^{priority__name_WIDTH}}%(clr)s %(fg6)s{status__name:^{status__name_WIDTH}}%(clr)s #{id:>{id_WIDTH}} {subject}
issue_list_groupby=project__name
user_list_format=%(fg5)s{id:>{id_WIDTH}}%(clr)s %(fg6)s{mail:<{mail_WIDTH}}%(clr)s {firstname} {lastname}
"""


class Config(object):

    def __init__(self, args):
        self.args = args
        self.config = ConfigParser.ConfigParser()
        self.config.readfp(io.BytesIO(DEFAULT_CONFIG))
        self.config.read([os.path.expanduser('~/.redminecli')])
        self.profile = self._get_profile()
        self.host = self.args.host or self.get('host')
        if not self.host:
            raise RedmineCliException('No Redmine host provided')
        self.auth_info = self._get_auth_info()
        if not self.auth_info:
            raise RedmineCliException('No authentication information provided')
        version = self.args.redmineversion or self.get('redmineversion')
        if version:
            self.auth_info['version'] = version
        self.resource = self.get_arg('resource')
        self.command = self.get_arg('command')

    def get(self, option, default=None):
        try:
            return self.config.get(self.profile, option)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default

    def get_arg(self, option, default=None):
        return getattr(self.args, option, default)

    def _get_auth_info(self):
        key = self.args.key or self.get('key')
        if key:
            return {'key': key}
        user = self.args.user or self.get('user')
        password = self.args.password or self.get('password')
        if user and password:
            return {
                'username': user,
                'password': password
            }
        return {}

    def _get_profile(self):
        result = self.args.profile or None
        if result:
            return result
        for section in self.config.sections():
            if result is None:
                result = section
                continue
            if self.config.getboolean(section, 'default'):
                result = section
        return result if result else 'DEFAULT'
