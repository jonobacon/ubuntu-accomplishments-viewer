# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import gettext
from gettext import gettext as _
gettext.textdomain('accomplishments-viewer')

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

