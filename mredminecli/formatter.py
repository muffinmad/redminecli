import sys
import re
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
            self.orderby_field = None
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
            if param in ['INDENT', 'GROUP']:
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

    def _prepare_subvalues(self, obj, default='', print_missing=False):
        for sv in self._subvalues:
            subvals = sv.split('__')
            value = obj
            try:
                while subvals:
                    s = subvals.pop(0)
                    value = value[s]
                obj[sv] = value
            except (KeyError, TypeError):
                if print_missing:
                    print >> sys.stderr, '%s has no %s' % (value, s)
                obj[sv] = default

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
        if 'INDENT' not in params:
            il = params.get('INDENT_LEVEL', 0)
            iw = params.get('INDENT_WIDTH', 0)
            ic = params.get('INDENT_CHAR', ' ')
            params['INDENT'] = ic * iw * il
        result = fmt.format(**params).encode('utf-8')
        print result

    def _get_global_out_params(self):
        result = self._widths
        result.update({
            'INDENT_WIDTH': int(self._get_param('group_indent_width', self.config.get('_list_group_indent_width', 0))),
            'INDENT_CHAR': self._get_param('group_indent_str', self.config.get('_list_group_indent_str', ' '))
        })
        return result

    def _get_out(self, format_key):
        return partial(self._print, self.formats[format_key], **self._get_global_out_params())

    def _order_result(self, result):
        if self.orderby_field:
            return sorted(result, key=itemgetter(self.orderby_field), reverse=self.orderby_desc)
        return result


class ListFormatter(BaseFormatter):

    def _get_formats(self):
        result = {}
        result['list_format'] = unicode(self._get_param('format', '{id}'))
        self.groupby = filter(bool, map(lambda x: x.strip(), self._get_param('groupby', '').split(',')))
        if self.groupby:
            result['_groupby'] = unicode(''.join(map(lambda x: '{%s}' % x, self.groupby)))
            i = 0
            for grp in self.groupby:
                if i == 0:
                    result['group_format'] = unicode(self._get_param('group_format', self.config.get('_list_group_format')))
                    result['group_separator'] = unicode(self._get_param('group_separator', self.config.get('_list_group_separator', '')))
                else:
                    k = 'group_format_%d' % i
                    result[k] = unicode(self._get_param(k, result['group_format']))
                    k = 'group_separator_%d' % i
                    result[k] = unicode(self._get_param(k, result['group_separator']))
                i += 1
        return result

    def prepare_result(self, result):
        for item in result:
            self._prepare_subvalues(item)
            self._prepare_widths(item)

    def _order_result(self, result):
        def _sort(a, b):
            for grp in self.groupby:
                ag = itemgetter(grp)
                r = cmp(ag(a), ag(b))
                if r:
                    return r
            ag = itemgetter(self.orderby_field)
            r = cmp(ag(a), ag(b))
            return -r if self.orderby_desc else r
        return sorted(result, cmp=_sort)

    def print_result(self, result):
        out_list = self._get_out('list_format')
        groups = len(self.groupby)
        prev_item = None
        prev_item_groups = [None] * groups

        def _print_separator(idx, item_groups, print_empty=True):
            empty_printed = False
            for x in reversed(xrange(idx, groups)):
                k = 'group_separator' if x == 0 else 'group_separator_%d' % x
                fmt = self.formats[k]
                if fmt == 'EMPTY':
                    if not empty_printed:
                        if print_empty:
                            print
                        empty_printed = True
                elif fmt:
                    empty_printed = False
                    out_separator = self._get_out(k)
                    partial(out_separator, **prev_item)(GROUP=item_groups[x], INDENT_LEVEL=x)

        item = None
        for item in self._order_result(result):
            item_groups = [item[g] for g in self.groupby]
            if prev_item:
                i = groups
                if prev_item_groups != item_groups:
                    for x in xrange(len(item_groups)):
                        if item_groups[x] != prev_item_groups[x]:
                            i = x
                            break
                _print_separator(i, item_groups)
            else:
                i = 0
            for x in xrange(i, len(item_groups)):
                k = 'group_format' if x == 0 else 'group_format_%d' % x
                out_group = self._get_out(k)
                partial(out_group, **item)(GROUP=item_groups[x], INDENT_LEVEL=x)
            partial(out_list, **item)(INDENT_LEVEL=groups)
            prev_item = item
            prev_item_groups = item_groups
        if item:
            _print_separator(0, item_groups, False)


class ResourceFormatter(BaseFormatter):

    def _get_formats(self):
        result = {}
        result['issue_format'] = unicode(self._get_param('format', '{id}'))
        return result

    def print_result(self, result):
        result = dict(list(result))
        self._prepare_subvalues(result)
        out = self._get_out('issue_format')
        out(**result)
