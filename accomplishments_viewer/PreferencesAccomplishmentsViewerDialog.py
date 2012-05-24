# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

# This is your preferences dialog.
#
# Define your preferences in
# data/glib-2.0/schemas/net.launchpad.accomplishments-viewer.gschema.xml
# See http://developer.gnome.org/gio/stable/GSettings.html for more info.

from gi.repository import Gio # pylint: disable=E0611

import gettext, locale
from gettext import gettext as _
from accomplishments.util.paths import locale_dir
locale.bindtextdomain('accomplishments-viewer', locale_dir)
gettext.bindtextdomain('accomplishments-viewer',locale_dir)
gettext.textdomain('accomplishments-viewer')

from accomplishments.daemon import dbusapi
import os, xdg.BaseDirectory, ConfigParser

import logging
logger = logging.getLogger('accomplishments_viewer')

from accomplishments_viewer_lib.PreferencesDialog import PreferencesDialog

class PreferencesAccomplishmentsViewerDialog(PreferencesDialog):
    __gtype_name__ = "PreferencesAccomplishmentsViewerDialog"

    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the preferences dialog"""
        super(PreferencesAccomplishmentsViewerDialog, self).finish_initializing(builder)
        self.cb_daemonsessionstart = self.builder.get_object("cb_daemonsessionstart")
        self.cb_hideu1bubbles = self.builder.get_object("cb_hideu1bubbles")
        
        # Bind each preference widget to gsettings
        #settings = Gio.Settings("net.launchpad.accomplishments-viewer")
        #widget = self.builder.get_object('example_entry')
        #settings.bind("example", widget, "text", Gio.SettingsBindFlags.DEFAULT)

        # Code for other initialization actions should be added here.

    def prepare(self,daemon_handle):
        self.libaccom = daemon_handle
        self.populate_settings()

    def populate_settings(self):
        self.cb_daemonsessionstart.handler_block_by_func(self.cb_daemonsessionstart_toggled)
        self.cb_hideu1bubbles.handler_block_by_func(self.cb_hideu1bubbles_toggled)
        
        self.cb_daemonsessionstart.set_active(bool(self.libaccom.get_daemon_session_start()))
        print self.libaccom.get_daemon_session_start()
        print type(self.libaccom.get_daemon_session_start())
        self.cb_hideu1bubbles.set_active(self.libaccom.get_block_ubuntuone_notification_bubbles())

        self.cb_daemonsessionstart.handler_unblock_by_func(self.cb_daemonsessionstart_toggled)
        self.cb_hideu1bubbles.handler_unblock_by_func(self.cb_hideu1bubbles_toggled)
        
    def cb_daemonsessionstart_toggled(self, widget):
        print widget.get_active()
        self.libaccom.set_daemon_session_start( widget.get_active() )

    def cb_hideu1bubbles_toggled(self, widget):
        self.libaccom.set_block_ubuntuone_notification_bubbles( widget.get_active() )
