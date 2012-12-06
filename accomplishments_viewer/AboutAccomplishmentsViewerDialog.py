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

import gettext
import locale
from locale import gettext as _
from accomplishments.util.paths import locale_dir
locale.bindtextdomain('accomplishments-viewer', locale_dir)
gettext.bindtextdomain('accomplishments-viewer', locale_dir)
locale.textdomain('accomplishments-viewer')

from accomplishments.daemon import dbusapi

import logging
logger = logging.getLogger('accomplishments_viewer')

from accomplishments_viewer_lib.AboutDialog import AboutDialog


# See accomplishments_viewer_lib.AboutDialog.py for more details about how this class works.
class AboutAccomplishmentsViewerDialog(AboutDialog):
    __gtype_name__ = "AboutAccomplishmentsViewerDialog"

    def finish_initializing(self, builder):  # pylint: disable=E1002
        """Set up the about dialog"""
        super(AboutAccomplishmentsViewerDialog, self).finish_initializing(builder)

        # Code for other initialization actions should be added here.

        self.libaccom = dbusapi.Accomplishments()

        # add app authors
        authors = sorted(["Jono Bacon <jono@ubuntu.com>", "Rafal Cieślak <rafalcieslak256@gmail.com>", "Matt Fischer <matt@mattfischer.com>", "Stuart Langridge <sil@kryogenix.org>"])

        for col in self.libaccom.list_collections():
            authors.append(" ")
            authors.append("'" + self.libaccom.get_collection_name(col) + "' " + _("Collection Authors:").decode('utf-8'))
            authors.append(" ")

            tempauthors = []
            for a in self.libaccom.get_collection_authors(col):
                tempauthors.append(a)

            authors = authors + sorted(tempauthors)

        self.set_authors(authors)
