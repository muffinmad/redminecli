import argparse


class Arguments(object):

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class ArgumentsParser(object):

    def __init__(self, redminecli):
        self.redminecli = redminecli

    def add_arguments(self, parser, obj):
        for arg in getattr(obj, 'arguments', []):
            parser.add_argument(*arg.args, **arg.kwargs)

    def parse_args(self):
        parser = argparse.ArgumentParser(description=self.redminecli.description)
        self.add_arguments(parser, self.redminecli)

        resources = parser.add_subparsers(title='Resources', dest='resource')
        for resource in self.redminecli.resources.itervalues():
            resource_description = getattr(resource, 'description', '%s commands' % resource.name.capitalize())
            resource_parser = resources.add_parser(resource.name, help=resource_description)
            resource_commands = resource_parser.add_subparsers(title=resource_description, dest='command')
            for command in getattr(resource, 'commands', {}).itervalues():
                commands_parser = resource_commands.add_parser(command.name, help=command.description)
                self.add_arguments(commands_parser, command)

        return parser.parse_args()
