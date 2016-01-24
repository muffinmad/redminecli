import sys
import re
from itertools import groupby
from operator import itemgetter
from functools import partial
from collections import defaultdict


RE_PARAMS = re.compile('(?:[^{]|^)\{(\w+)')


class BaseFormatter(object):

    def __init__(self, command, base_key=None, orderby=None):
        self.command = command
        self.base_key = self._get_base_key() if base_key is None else base_key
        self.config = command.resource.redminecli.config
        orderby = orderby or self._get_param('orderby')
        if orderby:
            o = orderby.split(':')
            self.orderby_field = o[0]
            self.orderby_desc = len(o) > 1 and o[1] == 'desc'
        else:
            self.orderby = orderby
        self._values = set()
        self._subvalues = set()
        self._width_for = set()
        self._widths = defaultdict(int)
        self.formats = self._get_formats()
        self._parse_formats()

    def _get_base_key(self):
        return '%s_%s' % (self.command.resource.name, self.command.name)

    def _get_key(self, key):
        return '%s_%s' % (self.base_key, key)

    def _get_param(self, key, default=''):
        return self.config.get(self._get_key(key), default)

    def _get_formats(self):
        return {}

    def _parse_formats(self):
        params = re.findall(RE_PARAMS, ' '.join(self.formats.values()))
        if self.orderby_field:
            params.append(self.orderby_field)
        for param in params:
            if param == 'GROUP':
                continue
            width_for = param.endswith('_WIDTH')
            param = param.replace('_WIDTH', '')
            if width_for:
                self._width_for.add(param)
            parts = param.split('__')
            if len(parts) > 1:
                self._subvalues.add(param)
            self._values.add(parts[0])

    @property
    def values(self):
        return self._values

    def _prepare_subvalues(self, obj):
        for sv in self._subvalues:
            subvals = sv.split('__')
            value = obj
            try:
                while subvals:
                    s = subvals.pop(0)
                    value = value[s]
                obj[sv] = value
            except (KeyError, TypeError):
                print >> sys.stderr, '%s has no %s' % (value, s)

    def _prepare_widths(self, obj):
        for w in self._width_for:
            key = w + '_WIDTH'
            l = 0
            try:
                l = len(unicode(obj[w]))
            except (KeyError, TypeError):
                print >> sys.stderr, '%s has no %s' % (obj, w)
            else:
                self._widths[key] = max(self._widths[key], l)

    def prepare_result(self, result):
        pass

    def print_result(self, result):
        print result

    def _print(self, fmt, **params):
        print fmt.format(**params).encode('utf-8')

    def _get_out(self, format_key):
        return partial(self._print, self.formats[format_key], **self._widths)

    def _order_result(self, result):
        if self.orderby_field:
            return sorted(result, key=itemgetter(self.orderby_field), reverse=self.orderby_desc)
        return result


class ListFormatter(BaseFormatter):

    def _get_formats(self):
        result = {}
        result['list_format'] = unicode(self._get_param('format', '{id}'))
        self.groupby = self._get_param('groupby')
        if self.groupby:
            result['_groupby'] = unicode('{%s}' % self.groupby)
        result['group_format'] = unicode(self._get_param('group_format', self.config.get('_list_group_format')))
        result['group_separator'] = unicode(self._get_param('group_separator', self.config.get('_list_group_separator', '')))
        return result

    def prepare_result(self, result):
        for item in result:
            self._prepare_subvalues(item)
            self._prepare_widths(item)

    def print_result(self, result):
        out_group = self._get_out('group_format')
        out_list = self._get_out('list_format')
        out_separator = self._get_out('group_separator')
        if self.groupby:
            a = itemgetter(self.groupby)
            first = True
            item = None
            last_group = None
            for group, items in groupby(sorted(result, key=a), key=a):
                if first:
                    first = False
                else:
                    partial(out_separator, **item)(GROUP=last_group)
                new_group = True
                for item in self._order_result(list(items)):
                    if new_group:
                        partial(out_group, **item)(GROUP=group)
                        new_group = False
                    out_list(**item)
                last_group = group
            if item and self.formats['group_separator']:
                partial(out_separator, **item)(GROUP=group)
        else:
            for item in self._order_result(result):
                out_list(**item)
