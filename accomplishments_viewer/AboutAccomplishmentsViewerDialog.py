# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import gettext, locale
from gettext import gettext as _
from accomplishments.util.paths import locale_dir
locale.bindtextdomain('accomplishments-viewer', locale_dir)
gettext.bindtextdomain('accomplishments-viewer',locale_dir)
gettext.textdomain('accomplishments-viewer')

from accomplishments.daemon import dbusapi

import logging
logger = logging.getLogger('accomplishments_viewer')

from accomplishments_viewer_lib.AboutDialog import AboutDialog

# See accomplishments_viewer_lib.AboutDialog.py for more details about how this class works.
class AboutAccomplishmentsViewerDialog(AboutDialog):
    __gtype_name__ = "AboutAccomplishmentsViewerDialog"
    
    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the about dialog"""
        super(AboutAccomplishmentsViewerDialog, self).finish_initializing(builder)

        # Code for other initialization actions should be added here.

        self.libaccom = dbusapi.Accomplishments()

        # add app authors
        authors = sorted([ "Jono Bacon <jono@ubuntu.com>", "Rafal Cieślak <rafalcieslak256@gmail.com>", "Stuart Langridge <sil@kryogenix.org>"])
        
        for col in self.libaccom.list_collections():
            authors.append(" ")
            authors.append("'" + self.libaccom.get_collection_name(col) + "' " + _("Collection Authors:"))
            authors.append(" ")
            
            tempauthors = []
            for a in self.libaccom.get_collection_authors(col):
                tempauthors.append(a)

            authors = authors + sorted(tempauthors)
            
        self.set_authors(authors)
