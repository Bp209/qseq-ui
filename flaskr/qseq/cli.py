#!/usr/bin/env python3.11

import sys
import os.path
import logging
from optparse import OptionParser

from qseq import __version__
from qseq.sequencer import Sequencer


def main():
    # parse commandline options
    usage = "usage: %prog [options] sequencefile"

    parser = OptionParser(usage=usage)
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
                      help='be more verbose')
    parser.add_option('-V', '--version', action='store_true', dest='version',
                      help='show version')
    parser.add_option('--dry-run', action='store_true', dest='dry_run',
                      help="don't execute any methods")

    (options, args) = parser.parse_args()

    if options.version:
        print('%s v%s' % (os.path.basename(sys.argv[0]), __version__))
        sys.exit()

    if len(args) < 1:
        parser.print_help()
        sys.exit(1)

    logging.basicConfig()
    if options.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    s = Sequencer()
    s.load_sequence_file(args[0])
    if not options.dry_run:
        s.start()


if __name__ == '__main__':
    main()
