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
        
        self.libaccom = dbusapi.Accomplishments()
        
        self.populate_settings()
        # Bind each preference widget to gsettings
        #settings = Gio.Settings("net.launchpad.accomplishments-viewer")
        #widget = self.builder.get_object('example_entry')
        #settings.bind("example", widget, "text", Gio.SettingsBindFlags.DEFAULT)

        # Code for other initialization actions should be added here.

    def populate_settings(self):
        if self.libaccom.get_config_value("config", "daemon_sessionstart") == "true":
            self.cb_daemonsessionstart.set_active(True)

        u1configdir = os.path.join(
        xdg.BaseDirectory.xdg_config_home, "ubuntuone")

        if not os.path.exists(u1configdir):
            os.makedirs(u1configdir)

        cfile = os.path.join(u1configdir, "syncdaemon.conf")

        config = ConfigParser.ConfigParser()
        config.read(cfile)

        if config.has_option('notifications', 'show_all_notifications'):
            if config.get('notifications', 'show_all_notifications') == "False":
                self.cb_hideu1bubbles.set_active(True)
            else:
                self.cb_hideu1bubbles.set_active(False)
        else:
            self.cb_hideu1bubbles.set_active(False)

    def cb_daemonsessionstart(self, widget):
        if widget.get_active() == True:
            self.libaccom.enable_daemon_session_start()
        else:
            self.libaccom.disable_daemon_session_start()

    def cb_hideu1bubbles_toggled(self, widget):
        if widget.get_active() == True:
            self.libaccom.enable_block_ubuntuone_notification_bubbles()
        else:
            self.libaccom.disable_block_ubuntuone_notification_bubbles()
