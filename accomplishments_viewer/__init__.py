# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import optparse

import gettext, locale
from gettext import gettext as _
from accomplishments.util.paths import locale_dir
locale.bindtextdomain('accomplishments-viewer', locale_dir)
gettext.bindtextdomain('accomplishments-viewer',locale_dir)
gettext.textdomain('accomplishments-viewer')

from gi.repository import Gtk # pylint: disable=E0611

from accomplishments_viewer import AccomplishmentsViewerWindow

from accomplishments_viewer_lib import set_up_logging, get_version

def parse_options():
    """Support for command line options"""
    parser = optparse.OptionParser(version="%%prog %s" % get_version())
    parser.add_option(
        "-v", "--verbose", action="count", dest="verbose",
        help=_("Show debug messages (-vv debugs accomplishments_viewer_lib also)").decode('utf-8'))
    parser.add_option(
        "-a", "--accomplishment", action="store", dest="id",
        help=_("Display information about the provided accomplishment ID (e.g. 'ubuntu-community/registered-on-launchpad'").decode('utf-8'))
    (options, args) = parser.parse_args()
    
    set_up_logging(options)
    return options

def main():
    'constructor for your class instances'
    options = parse_options()

    # Run the application.    
    window = AccomplishmentsViewerWindow.AccomplishmentsViewerWindow()
    
    window.optparse_accomplishment(options.id)
    
    window.show()
    Gtk.main()
