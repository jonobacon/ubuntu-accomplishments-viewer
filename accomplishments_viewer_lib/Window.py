# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

from gi.repository import Gio, Gtk # pylint: disable=E0611
import logging
logger = logging.getLogger('accomplishments_viewer_lib')

from . helpers import get_builder, show_uri, get_help_uri

# This class is meant to be subclassed by AccomplishmentsViewerWindow.  It provides
# common functions and some boilerplate.
class Window(Gtk.Window):
    __gtype_name__ = "Window"

    # To construct a new instance of this method, the following notable 
    # methods are called in this order:
    # __new__(cls)
    # __init__(self)
    # finish_initializing(self, builder)
    # __init__(self)
    #
    # For this reason, it's recommended you leave __init__ empty and put
    # your initialization code in finish_initializing
    
    def __new__(cls):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated BaseAccomplishmentsViewerWindow object.
        """
        builder = get_builder('AccomplishmentsViewerWindow')
        new_object = builder.get_object("accomplishments_viewer_window")
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called while initializing this instance in __new__

        finish_initializing should be called after parsing the UI definition
        and creating a AccomplishmentsViewerWindow object with it in order to finish
        initializing the start of the new AccomplishmentsViewerWindow instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self, True)
        self.PreferencesDialog = None # class
        self.preferences_dialog = None # instance
        self.AboutDialog = None # class

        self.settings = Gio.Settings("net.launchpad.accomplishments-viewer")
        self.settings.connect('changed', self.on_preferences_changed)

        # Optional Launchpad integration
        # This shouldn't crash if not found as it is simply used for bug reporting.
        # See https://wiki.ubuntu.com/UbuntuDevelopment/Internationalisation/Coding
        # for more information about Launchpad integration.
        # XXX: This is temporarily disabled, as there is no such package
        # in ubuntu repositories. We may want to re-enable it one day.
        """
        try:
            from gi.repository import LaunchpadIntegration # pylint: disable=E0611
            LaunchpadIntegration.add_items(self.ui.helpMenu, 2, True, True)
            LaunchpadIntegration.set_sourcepackagename('accomplishments-viewer')
        except ImportError:
            pass
        """

        # Optional application indicator support
        # Run 'quickly add indicator' to get started.
        # More information:
        #  http://owaislone.org/quickly-add-indicator/
        #  https://wiki.ubuntu.com/DesktopExperienceTeam/ApplicationIndicators
        try:
            from accomplishments_viewer import indicator
            # self is passed so methods of this class can be called from indicator.py
            # Comment this next line out to disable appindicator
            self.indicator = indicator.new_application_indicator(self)
        except ImportError:
            pass

    def on_mnu_contents_activate(self, widget, data=None):
        show_uri(self, "ghelp:%s" % get_help_uri())

    def on_mnu_about_activate(self, widget, data=None):
        """Display the about box for accomplishments-viewer."""
        if self.AboutDialog is not None:
            about = self.AboutDialog() # pylint: disable=E1102
            response = about.run()
            about.destroy()

    def on_mnu_close_activate(self, widget, data=None):
        """Signal handler for closing the AccomplishmentsViewerWindow."""
        self.destroy()

    def on_destroy(self, widget, data=None):
        """Called when the AccomplishmentsViewerWindow is closed."""
        # Clean up code for saving application state should be added here.
        Gtk.main_quit()

    def on_preferences_changed(self, settings, key, data=None):
        logger.debug('preference changed: %s = %s' % (key, str(settings.get_value(key))))

