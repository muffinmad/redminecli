#!/usr/bin/env python2
import io
import os
import re
import sys
import argparse
import ConfigParser
from operator import itemgetter
from functools import partial

try:
    from redmine import Redmine
except ImportError:
    print >> sys.stderr, 'You need to install python-redmine'
    sys.exit(1)


DEFAULT_CONFIG = """
[DEFAULT]
default=False
host=
user=
password=
key=
redmineversion=
limit=100
project_list_format={id:>{id_width}} {identifier:<{identifier_width}} {name}
issue_list_format={project__name:<{project__name_width}} {tracker__name:^{tracker__name_width}} {priority__name:^{priority__name_width}} {status__name:^{status__name_width}} #{id:>{id_width}} {subject}
"""


RE_WIDTHS = re.compile('(\w+)_width')
RE_SUBVALS = re.compile('(\w+(__\w+)+)')


class RedmineCli(object):

    def __init__(self, args):
        self.args = args
        self.config = ConfigParser.ConfigParser()
        self.config.readfp(io.BytesIO(DEFAULT_CONFIG))
        self.config.read([os.path.expanduser('~/.redminecli')])

    @property
    def fmt(self):
        return unicode(self.config.get(self.profile, self.fmt_name, raw=True))

    def out(self, fmt, **kwargs):
        print fmt.format(**kwargs).encode('utf-8')

    def get_out(self, objs):
        fmt = self.fmt
        subvals = map(lambda x: x[0], re.findall(RE_SUBVALS, fmt))
        widths = {k: 0 for k in re.findall(RE_WIDTHS, fmt)}
        width_name = map(lambda x: x + '_width', widths.iterkeys())
        if widths or subvals:
            for obj in objs:
                for subval in subvals:
                    if subval in width_name:
                        continue
                    s = subval.split('__')
                    value = obj[s.pop(0)]
                    while s:
                        value = value[s.pop(0)]
                    obj[subval] = value
                for k in widths.iterkeys():
                    l = len(unicode(obj[k]))
                    if l > widths[k]:
                        widths[k] = l
            wk = widths.keys()
            for k in wk:
                widths[k + '_width'] = widths.pop(k)
        return partial(self.out, fmt, **widths)

    def ordered(self, objs):
        if not self.args.order:
            return objs
        o = self.args.order.split(':')
        r = len(o) > 1 and o[1] == 'desc'
        return sorted(objs, key=itemgetter(o[0]), reverse=r)

    def list_params(self, with_order=False):
        limit = self.args.limit
        if limit is None:
            limit = self.config.getint(self.profile, 'limit')
        result = {}
        if limit:
            result['limit'] = limit
        if self.args.offset:
            result['offset'] = self.args.offset
        if with_order and self.args.order:
            result['sort'] = self.args.order
        return result

    def project_list(self):
        projects = list(self.redmine.project.all(**self.list_params()).values())
        projects = self.ordered(projects)
        out = self.get_out(projects)
        for project in projects:
            out(**project)

    def issue_list(self):
        params = self.list_params(with_order=True)

        def _add_param(args_key, query_key):
            a = getattr(self.args, args_key)
            if a:
                params[query_key] = a

        _add_param('project', 'project_id')
        _add_param('query', 'query_id')
        _add_param('status', 'status_id')
        _add_param('assigned', 'assigned_to_id')

        issues = list(self.redmine.issue.filter(**params).values())
        out = self.get_out(issues)
        for issue in issues:
            out(**issue)

    def run(self):
        self.profile = self.args.profile
        if not self.profile:
            p = None
            for section in self.config.sections():
                if p is None:
                    p = section
                    continue
                if self.config.getboolean(section, 'default'):
                    p = section
            self.profile = p
            if not self.profile:
                self.profile = 'DEFAULT'
        host = self.args.host or self.config.get(self.profile, 'host')
        if not host:
            raise Exception('No Redmine host provided')
        user = self.args.user or self.config.get(self.profile, 'user')
        password = self.args.password or self.config.get(self.profile, 'password')
        key = self.args.key or self.config.get(self.profile, 'key')
        version = self.args.redmineversion or self.config.get(self.profile, 'redmineversion')
        k = {}
        if key:
            k['key'] = key
        elif user and password:
            k['username'] = user
            k['password'] = password
        else:
            raise Exception('No authentication information provided')
        if version:
            k['version'] = version
        self.redmine = Redmine(host, **k)
        fname = '%s_%s' % (self.args.object, self.args.command)
        self.fmt_name = '%s_format' % fname
        f = getattr(self, fname, None)
        if not f or not callable(f):
            raise Exception('%s %s not implemented yet' % (self.args.object, self.args.command))
        f()


def int_or_string(s):
    return int(s) if s.isdigit() else s


def status_type(s):
    if s.isdigit():
        return int(s)
    if s in ['open', 'closed', '*']:
        return s
    raise argparse.ArgumentTypeError('%s is not valid value for status' % s)


def assigned_type(s):
    if s.isdigit():
        return int(s)
    if s == 'me':
        return s
    raise argparse.ArgumentTypeError('%s is not valid value for assigned' % s)


def main():
    parser = argparse.ArgumentParser(description='Redmine command line interface')

    parser.add_argument('-p', '--profile', type=str, help='Profile from config file')
    parser.add_argument('-H', '--host', type=str, help='Redmine URL')
    parser.add_argument('-u', '--user', type=str, help='Redmine login')
    parser.add_argument('-P', '--password', type=str, help='Redmine password')
    parser.add_argument('-k', '--key', type=str, help='Redmine API key')
    parser.add_argument('-V', '--redmineversion', type=str, help='Redmine version')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.1')

    subparsers = parser.add_subparsers(title='Objects', dest='object')

    project = subparsers.add_parser('project', help='Projects commands')
    project_sub = project.add_subparsers(title='Project commands', dest='command')
    project_list = project_sub.add_parser('list', help='List projects')
    project_list.add_argument('--limit', type=int, help='Limit', default=100)
    project_list.add_argument('--offset', type=int, help='Offset')
    project_list.add_argument('--order', type=str, help='Order field. field or field:desc', default='id')
    project_show = project_sub.add_parser('show', help='Show project info')
    project_show.add_argument('project', type=int_or_string, help='Project id or project identifier')

    issue = subparsers.add_parser('issue', help='Issues commands')
    issue_sub = issue.add_subparsers(title='Issue commands', dest='command')
    issue_list = issue_sub.add_parser('list', help='List issues')
    issue_list.add_argument('--project', type=int_or_string, help='Project id or project identifier')
    issue_list.add_argument('--query', type=int, help='Query id')
    issue_list.add_argument('--status', type=status_type, help='Status: open, closed, * or status id')
    issue_list.add_argument('--assigned', type=assigned_type, help='Assigned to: me or user id')
    issue_list.add_argument('--limit', type=int, help='Limit', default=100)
    issue_list.add_argument('--offset', type=int, help='Offset')
    issue_list.add_argument('--order', type=str, help='Order field. field or field:desc', default='id')
    issue_show = issue_sub.add_parser('show', help='Show issue')
    issue_show.add_argument('issue', type=int, help='Issue id')
    issue_update = issue_sub.add_parser('update', help='Update issue')
    issue_update.add_argument('issue', type=int, help='Issue id')
    issue_update.add_argument('--status', type=int, help='Status')
    issue_update.add_argument('--done_ratio', type=int, help='Done ratio')
    issue_update.add_argument('--note', type=str, help='Journal note')

    issuestatus = subparsers.add_parser('issuestatus', help='Issue statuses commands')
    issuestatus_sub = issuestatus.add_subparsers(title='Issue Status commands', dest='command')
    issuestatus_sub.add_parser('list', help='List issue statuses')

    query = subparsers.add_parser('query', help='Queries commands')
    query_sub = query.add_subparsers(title='Query commands', dest='command')
    query_sub.add_parser('list', help='List queries')

    user = subparsers.add_parser('user', help='Users commands')
    user_sub = user.add_subparsers(title='User commands', dest='command')
    user_list = user_sub.add_parser('list', help='List users')
    user_list.add_argument('--name', help='Filter users by name')
    user_show = user_sub.add_parser('show', help='Show user info')
    user_show.add_argument('user', type=int, help='User id')

    args = parser.parse_args()
    RedmineCli(args).run()

if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print >> sys.stdout, e
