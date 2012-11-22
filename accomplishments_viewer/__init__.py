# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2012 Jono Bacon <jono@ubuntu.com>
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import optparse

import gettext, locale
from locale import gettext as _
from accomplishments.util.paths import locale_dir
locale.bindtextdomain('accomplishments-viewer', locale_dir)
gettext.bindtextdomain('accomplishments-viewer',locale_dir)
locale.textdomain('accomplishments-viewer')

from gi.repository import Gtk, GObject # pylint: disable=E0611

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
        help=_("Display information about the provided accomplishment ID (e.g. 'ubuntu-community/registered-on-launchpad')").decode('utf-8'))
    (options, args) = parser.parse_args()
    
    set_up_logging(options)
    return options

def main():
    'constructor for your class instances'
    GObject.threads_init()
    options = parse_options()

    # Run the application.    
    window = AccomplishmentsViewerWindow.AccomplishmentsViewerWindow()
    
    if options.id:
        window.optparse_accomplishment(options.id)
    
    window.show()
    Gtk.main()
