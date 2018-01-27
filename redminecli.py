#!/usr/bin/python2
import sys
from mredminecli import RedmineCliException
from mredminecli.main import RedmineCli


def main():
    redminecli = RedmineCli()
    redminecli.run()


if __name__ == '__main__':
    try:
        main()
    except RedmineCliException, e:
        print >> sys.stdout, e
        sys.exit(1)
