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

import urllib2
import gettext, locale, datetime
from locale import gettext as _
from accomplishments.util.paths import locale_dir
locale.bindtextdomain('accomplishments-viewer', locale_dir)
gettext.bindtextdomain('accomplishments-viewer',locale_dir)
locale.textdomain('accomplishments-viewer')

import traceback
import os
import sys
import webbrowser
import xdg.BaseDirectory

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop

from gi.repository import Gtk, GObject, GdkPixbuf, WebKit # pylint: disable=E0611
from gi.repository import Unity

import logging
logger = logging.getLogger('accomplishments_viewer')

from accomplishments_viewer_lib import Window
from accomplishments_viewer.AboutAccomplishmentsViewerDialog import AboutAccomplishmentsViewerDialog
from accomplishments_viewer.EditExtrainfoDialog import EditExtrainfoDialog
from accomplishments_viewer.PreferencesAccomplishmentsViewerDialog import PreferencesAccomplishmentsViewerDialog

from accomplishments.daemon import dbusapi
from accomplishments.util.paths import daemon_exec_dir
from accomplishments_viewer_lib.helpers import get_media_file
from accomplishments_viewer_lib.accomplishments_viewerconfig import get_data_path

try:
    from gi.repository import GwibberGtk
    GWIBBER_OK = True
except ImportError, ie:
    # could not import GwibberGtk, bug #1026406
    # start but disable any social media stuff
    GWIBBER_OK = False

locale.textdomain('accomplishments-viewer')
DBusGMainLoop(set_as_default=True)
logger = logging.getLogger('accomplishments-viewer')

COL_TITLE = 0
COL_PIXBUF = 1
COL_ACCOMPLISHED = 2
COL_LOCKED = 3
COL_COLLECTION = 4
COL_ID = 5

MYTROPHIES_FILTER_UNSPECIFIED = 0
MYTROPHIES_FILTER_ALL = 1
MYTROPHIES_FILTER_LATEST = 2

DISPLAY_MODE_UNSPECIFIED = 0
DISPLAY_MODE_DETAILS = 1
DISPLAY_MODE_TROPHIES = 2
DISPLAY_MODE_OPPORTUNITIES = 3

DISPLAY_FILTER_LOCKED_UNSPECIFIED = 0
DISPLAY_FILTER_LOCKED_SHOW = 1
DISPLAY_FILTER_LOCKED_HIDE = 2

DISPLAY_FILTER_COLLECTION_UNSPECIFIED = 0
DISPLAY_FILTER_CATEGORY_UNSPECIFIED = 0
DISPLAY_FILTER_SUBCAT_UNSPECIFIED = 0
DISPLAY_FILTER_SEARCH_UNSPECIFIED = 0

TROPHY_GALLERY_URL = 'http://213.138.100.229:8000'

# See accomplishments_viewer_lib.Window.py for more details about how this class works
class AccomplishmentsViewerWindow(Window):
    __gtype_name__ = "AccomplishmentsViewerWindow"
    
    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window."""
        
        super(AccomplishmentsViewerWindow, self).finish_initializing(builder)

        self.AboutDialog = AboutAccomplishmentsViewerDialog
        self.PreferencesDialog = PreferencesAccomplishmentsViewerDialog #class
        self.preferences_dialog = None #instance
        self.EditExtraDialog = EditExtrainfoDialog()
        self.EditExtraDialog.parent = self
        self.curr_height = 0
        self.curr_width = 0
        self.do_not_react_on_cat_changes = False
        
        self.display_mytrophies_filtermode = MYTROPHIES_FILTER_ALL
        self.display_mode = DISPLAY_MODE_OPPORTUNITIES
        self.display_filter_locked = DISPLAY_FILTER_LOCKED_SHOW
        self.display_filter_collection = ""
        self.display_filter_category = ""
        self.display_filter_subcat = ""
        self.display_filter_search = ""
        
        self.mytrophies_store_all = []
        # Code for other initialization actions should be added here.

        
        # set up autostart dir
        self.autostartdir = None

        self.autostartdir = os.path.join(
            xdg.BaseDirectory.xdg_config_home, "autostart")

        if not os.path.exists(self.autostartdir):
            os.makedirs(self.autostartdir)

        # self.accomdb provides a collection of all accomplishments
        # that we query throughout the application
        self.accomdb = []

        # reference to the Unity Launchcher
        self.launcher = Unity.LauncherEntry.get_for_desktop_id("accomplishments-viewer.desktop")
        self.newtrophies = 0
        
        # set up all of the different UI references
        self.tb_mytrophies = self.builder.get_object("tb_mytrophies")
        self.tb_opportunities = self.builder.get_object("tb_opportunities")
        self.opp_combo_col = self.builder.get_object("opp_combo_app")
        self.opp_combo_cat = self.builder.get_object("opp_combo_cat")
        self.opp_icon = self.builder.get_object("opp_icon")
        self.notebook = self.builder.get_object("notebook")
        self.additional_info_req = self.builder.get_object("add_info_req")
        self.additional_ubuntu1 = self.builder.get_object("add_ubu1")
        self.additional_daemon = self.builder.get_object("add_daemon")
        self.additional_daemon_session = self.builder.get_object("add_daemon_session")
        self.additional_no_collections = self.builder.get_object("add_no_collections")
        self.auth_scrolled = self.builder.get_object("auth_scrolled")
        self.auth_viewport = self.builder.get_object("auth_viewport")
        self.verif_box = self.builder.get_object("verif_box")
        self.opp_showlocked = self.builder.get_object("opp_showlocked")
        self.toolbar = self.builder.get_object("toolbar")
        self.statusbar = self.builder.get_object("statusbar")
        self.statusbox = self.builder.get_object("statusbox")
        self.spinner = self.builder.get_object("spinner")
        self.scrolledwindow = self.builder.get_object("scrolledwindow")
        self.webkitview = self.builder.get_object("webkitview")
        self.webkitbox = self.builder.get_object("webkitbox")
        self.mnu_check_acc = self.builder.get_object("mnu_check_acc")
        self.opp_tb = self.builder.get_object("opp_tb")
        self.mnu_edit_ident = self.builder.get_object("mnu_edit_ident")
        self.subcats_scroll = self.builder.get_object("subcats_scroll")
        self.subcats_back = self.builder.get_object("subcats_back")
        self.subcats_forward = self.builder.get_object("subcats_forward")
        self.subcats_buttonbox = self.builder.get_object("subcats_buttonbox")
        self.subcats_container = self.builder.get_object("subcats_container")
        self.mytrophies_mainbox = self.builder.get_object("mytrophies_mainbox")
        self.mytrophies_filter_latest = self.builder.get_object("mytrophies_filter_latest")
        self.mytrophies_filter_all = self.builder.get_object("mytrophies_filter_all")
        self.opp_frame = self.builder.get_object("opp_frame")

        # don't display the sub-cats scrollbars
        sb_h = self.subcats_scroll.get_hscrollbar()
        sb_v = self.subcats_scroll.get_vscrollbar()
        sb_h.set_child_visible(False)
        sb_v.set_child_visible(False)
                
        #h = self.subcats_scroll.get_hadjustment()
        self.subcat = None
        self.subcats_container.hide()
        
        # make the toolbar black in Ubuntu
        context = self.toolbar.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        # create the stores used by the IconViews in the Latest View

        self.mytrophies_filter_today = Gtk.ListStore(str, GdkPixbuf.Pixbuf, bool, bool, str, str) # title, icon accomplished, locked, col, accomplishment
        self.mytrophies_filter_today.set_sort_column_id(COL_TITLE, Gtk.SortType.ASCENDING)

        self.mytrophies_filter_week = Gtk.ListStore(str, GdkPixbuf.Pixbuf, bool, bool, str, str) # title, icon accomplished, locked, col, accomplishment
        self.mytrophies_filter_week.set_sort_column_id(COL_TITLE, Gtk.SortType.ASCENDING)

        self.mytrophies_filter_month = Gtk.ListStore(str, GdkPixbuf.Pixbuf, bool, bool, str, str) # title, icon accomplished, locked, col, accomplishment
        self.mytrophies_filter_month.set_sort_column_id(COL_TITLE, Gtk.SortType.ASCENDING)

        self.mytrophies_filter_sixmonths = Gtk.ListStore(str, GdkPixbuf.Pixbuf, bool, bool, str, str) # title, icon accomplished, locked, col, accomplishment
        self.mytrophies_filter_sixmonths.set_sort_column_id(COL_TITLE, Gtk.SortType.ASCENDING)

        self.mytrophies_filter_earlier = Gtk.ListStore(str, GdkPixbuf.Pixbuf, bool, bool, str, str) # title, icon accomplished, locked, col, accomplishment
        self.mytrophies_filter_earlier.set_sort_column_id(COL_TITLE, Gtk.SortType.ASCENDING)


        self.oppstore = Gtk.ListStore(str, GdkPixbuf.Pixbuf, bool, bool, str, str) # title, icon, accomplished, locked, col, accomplishment
        self.oppstore.set_sort_column_id(COL_TITLE, Gtk.SortType.ASCENDING)
        self.oppstore_filter = self.oppstore.filter_new()
        # The following sets the function for tree model filter. That function has
        # to return true if a given row has to be visible. This way we can control
        # which opportunities are displayed, and which are not.
        self.oppstore_filter.set_visible_func(self.opp_visible_func)
        self.opp_icon.set_model(self.oppstore_filter)

        #self.trophy_icon.set_text_column(COL_TITLE)
        #self.trophy_icon.set_pixbuf_column(COL_PIXBUF)

        self.opp_icon.set_text_column(COL_TITLE)
        self.opp_icon.set_pixbuf_column(COL_PIXBUF)

        #self.opp_icon.show()
        
        # set up webkit

        self.webview = WebKit.WebView()
        self.scrolledwindow.add(self.webview)
        self.webview.props.settings.props.enable_default_context_menu = False
        self.webkitlink = self.webview.connect("navigation-policy-decision-requested",self.webkit_link_clicked)

        self.webview.show()
        
        if GWIBBER_OK:
            self.messageentry = GwibberGtk.Entry()        
            self.messageentry.text_view.connect("submit",self.close_gwibber_window)
            self.messagewindow = Gtk.Window()
            self.messagewindow.set_transient_for(self)
            self.messagevbox = Gtk.VBox()
            self.messagewindow.set_title(_("Share Trophy"))
            self.messagewindow.set_icon_name("gwibber")
            self.messagewindow.resize(400, 150)
            self.messagewindow.set_resizable(False)
            self.messagevbox.pack_start(self.messageentry,True,True,0)
            self.messagelabel = Gtk.Label()
            self.messagelabel.set_markup(_("<b>Always add the link to your trophy on the web when sharing a trophy.</b>\nThis link works as a <b>proof</b> that you have really accomplished this trophy."))
            self.messagevbox.pack_start(self.messagelabel,False,False,0)
            self.messagewindow.add(self.messagevbox)
            self.messagevbox.show_all()   
            self.messagewindow.hide()
            self.messagewindow.connect("delete-event",self.close_gwibber_window)
            
        self.opp_col_store = Gtk.ListStore(str, str)
        self.col_combo_renderer_text = Gtk.CellRendererText()
        self.opp_combo_col.pack_start(self.col_combo_renderer_text, True)
        self.opp_combo_col.add_attribute(self.col_combo_renderer_text, "text", 1)

        self.opp_cat_store = Gtk.ListStore(str, str)
        self.cat_combo_renderer_text = Gtk.CellRendererText()
        self.opp_combo_cat.pack_start(self.cat_combo_renderer_text, True)
        self.opp_combo_cat.add_attribute(self.cat_combo_renderer_text, "text", 1)

        # LP: 1049300 - make sure we create the u1_button before calling
        # finalise_daemon_connection()
        self.u1_button = Gtk.Button()
        self.u1_button_sig = None
        self.verif_box.pack_start(self.u1_button, False, False, 0)

        # create a connection to the daemon
        self.connected = False
        self.connect_to_daemon()

        if self.connected is True:
            self.finalise_daemon_connection()
        else:
            self.run_daemon()

        # set up logging
        self.dir_cache = os.path.join(
            xdg.BaseDirectory.xdg_cache_home, "accomplishments")

        if not os.path.exists(self.dir_cache):
            os.makedirs(self.dir_cache)

        if not os.path.exists(os.path.join(self.dir_cache, "logs")):
            os.makedirs(os.path.join(self.dir_cache, "logs"))

        # IMPORTANT: This function should do no initialisations that depend
        # on having the daemon running. This is because if the daemon is not 
        # yet started it will take some time to connect to it. Such 
        # initialistions should land in appropriate place in run_daemon_timeout(...).

        self.datapath = get_data_path()

        self.update_widgets_sensitivity()

        

    def add_no_collections_installed(self):
        """Display the message that no collections are installed."""
        
        ### Commented out the following as it is confusing, and opens a lot of
        ### possible scenarios where these buttons are left insensitive.
        ## set bits of the user interface to be insensitive
        # self.tb_mytrophies.set_sensitive(False)
        # self.opp_frame.set_visible(False)
        
        
        # show the message
        self.additional_no_collections.set_visible(True)

    def on_add_no_collections_quit_clicked(self, widget):
        """Quit the app."""
        sys.exit(0)

    def on_reload_accomplishments_clicked(self, widget):
        self.additional_no_collections.set_visible(False)
        self.reload_accomplishments()
        
    def reload_accomplishments(self):
        if not self.connected:
            return
            
        self.statusbar_reload_msg_start()
        Gtk.main_iteration_do(False) # Force UI refresh
        self.libaccom.reload_accom_database()
        self.statusbar_reload_msg_stop()
        
        self.populate_opp_combos()
        if len(self.accomdb) == 0:
            self.add_no_collections_installed()
        self.set_display(DISPLAY_MODE_OPPORTUNITIES)
            
    def statusbar_reload_msg_start(self):
        self.statusbar.set_text(_("Reloading accomplishments collections..."))
        self.spinner.start()
        self.spinner.show()
        self.statusbox.show()
        self.statusbar_reload_msg = 0
        GObject.timeout_add(1000,self.statusbar_reload_msg_stop)
    
    def statusbar_reload_msg_stop(self):
        if self.statusbar_reload_msg is 0:
            # That would be too quick and the user wouldn't even notice the message
            self.statusbar_reload_msg = 1
        elif self.statusbar_reload_msg is 1:
            self.spinner.hide()
            self.statusbox.hide()
            
    
    def trophy_received(self, message):
        """Called when a new trophy is detected on the system."""
        
        self.newtrophies = self.newtrophies + 1
        
        # run this to refresh our accomplishments list
        self._load_accomplishments()
        
        # set the Launcher icon to be urgent and show new trophy count
        self.launcher.set_property("urgent", True)
        self.launcher.set_property("count", self.newtrophies)
        
        if self.newtrophies > 0:
            self.launcher.set_property("count_visible", True)
        else:
            self.launcher.set_property("count_visible", False)
        
        if not self.notebook.get_current_page() == 0:
            self.on_tb_mytrophies_clicked(None)

    def on_help_askubuntu_activate(self, widget):
        webbrowser.open("http://askubuntu.com/questions/ask?tags=accomplishments", True)

    def check_and_ask_for_info(self):
        """Asks the daemon for additional info needed, and asks
           the user for it, in case it has not been yet given"""
        
        if self.connected is False:
            return
    
        self.has_u1 = self.libaccom.get_config_value("config", "has_u1")
        self.has_verif = self.libaccom.get_config_value("config", "has_verif")

        if bool(self.has_u1) is False:
            self.approve_u1_trophies()

        if bool(self.has_u1) is True and bool(self.has_verif) is False:
            self.register_with_verif(None)

        if bool(self.has_u1) is True and bool(self.has_verif) is True:
            self.check_for_extra_info_required()

    def add_mytrophies_view(self, section, liststore):
        outerbox = Gtk.VBox()
        header = Gtk.Label("<span font_family='Ubuntu' size='18000' weight='light'>" + section + "</span>")
        header.set_use_markup(True)
        header.set_property("xalign", 0)
        header.set_property("margin_left", 10)
        header.set_property("margin_top", 5)
        header.set_property("margin_bottom", 2)
        separator = Gtk.Separator()
        separator.set_property("margin_left", 10)
        separator.set_property("margin_right", 10)
        
        iconview = Gtk.IconView()
        iconview.set_model(liststore)
        iconview.set_text_column(COL_TITLE)
        iconview.set_pixbuf_column(COL_PIXBUF)
        iconview.set_item_width(120)
        iconview.set_columns(-1)
        iconview.connect("selection-changed",self.mytrophy_clicked)

        outerbox.pack_start(header, False, False, 0)
        outerbox.pack_start(separator, False, False, 0)
        outerbox.pack_start(iconview, False, False, 0)
        outerbox.show_all()
        
        self.mytrophies_mainbox.add(outerbox)
            
    def connect_to_daemon(self):
        """Tries to connect to the daemon"""
        
        self.connected = False
        
        if dbusapi.daemon_is_registered():
            self.libaccom = dbusapi.Accomplishments()
        else:
            return False
                
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        bus = dbus.SessionBus()
        
        try:
            object  = bus.get_object("org.ubuntu.accomplishments",
                "/org/ubuntu/accomplishments")
            object.connect_to_signal("trophy_recieved",
                self.trophy_received,
                dbus_interface="org.ubuntu.accomplishments", arg0="Hello")
            object.connect_to_signal("publish_trophies_online_completed",
                self.publish_trophies_online_completed,
                dbus_interface="org.ubuntu.accomplishments", arg0="Hello")                
            object.connect_to_signal("scriptrunner_start",
                self.scriptrunner_start,
                dbus_interface="org.ubuntu.accomplishments")
            object.connect_to_signal("scriptrunner_finish",
                self.scriptrunner_finish,
                dbus_interface="org.ubuntu.accomplishments")
            object.connect_to_signal("ubuntu_one_account_ready",
                self.ubuntu_one_account_ready,
                dbus_interface="org.ubuntu.accomplishments", arg0="Hello")
        
        except dbus.DBusException:
            traceback.print_exc()
            print usage
            return False

        bus.add_signal_receiver(self.trophy_received,
            dbus_interface = "org.ubuntu.accomplishments",
            signal_name = "trophy_received")
        bus.add_signal_receiver(self.publish_trophies_online_completed,
            dbus_interface = "org.ubuntu.accomplishments",
            signal_name = "publish_trophies_online_completed")
        bus.add_signal_receiver(self.scriptrunner_start,
            dbus_interface = "org.ubuntu.accomplishments",
            signal_name = "scriptrunner_start")
        bus.add_signal_receiver(self.scriptrunner_finish,
            dbus_interface = "org.ubuntu.accomplishments",
            signal_name = "scriptrunner_finish")
        bus.add_signal_receiver(self.ubuntu_one_account_ready,
            dbus_interface = "org.ubuntu.accomplishments",
            signal_name = "ubuntu_one_account_ready")
        
        self.connected = True
        
        self.check_daemon_session()
        
        return True

    def publish_trophies_online_completed(self, url):
        webbrowser.open(url)

    def ubuntu_one_account_ready(self):        
        if not self.has_u1 == 1:
            self.register_with_verif(None)
        
    def run_daemon(self):
        """Starts the daemon process"""                

        command = os.path.join(daemon_exec_dir, "accomplishments-daemon") + " --start &"
        print ("Starting the daemon using command `%s`" % command)
        os.system(command)
        #apparently as that process daemonizes it will not get killed when one closes the client
        
        self.statusbar.set_text(_("Starting the daemon..."))
        self.spinner.start()
        self.spinner.show()
        self.statusbox.show()
        
        #try connecting to the daemon after having waited 1,5 sec
        GObject.timeout_add(1000,self.run_daemon_timeout)

    def run_daemon_timeout(self):
        """Called from run_daemon on timeout.
           Finishes what run_daemon would do"""
    
        self.connect_to_daemon()
        
        self.statusbox.hide()
        
        if self.connected is False:
            #Either failed to start the daemon, or failed to connect to
            #It may either be not installed, or may have crashed on startup
            self.statusbar.set_text("Failed to connect to the daemon.")
            self.spinner.hide()
            self.statusbox.show()
            GObject.timeout_add(10000,self.run_daemon)
        else:
            #successfully started and connected
            self.finalise_daemon_connection()
            
        self.update_widgets_sensitivity()
        
        #returning false removes the timeout
        return False    

    def finalise_daemon_connection(self):
        self.libaccom.create_all_trophy_icons()
        self._load_accomplishments()
        self.fill_in_tree_models()
        self.populate_opp_combos()
        if len(self.accomdb) == 0:
            self.add_no_collections_installed()
        self.set_display(DISPLAY_MODE_OPPORTUNITIES)
        

    def update_widgets_sensitivity(self):
        """Disables/enables some GUI elemets, according to whether the client is connected to the daemon or nor"""
        if self.connected is True:
            self.mnu_check_acc.set_sensitive(True)
            self.opp_tb.set_sensitive(True)
            self.mnu_edit_ident.set_sensitive(True)
        else:
            self.mnu_check_acc.set_sensitive(False)
            self.opp_tb.set_sensitive(False)
            self.mnu_edit_ident.set_sensitive(False)
        return

    def edit_identification_clicked(self,w):
        """Called when user clicks Edit->Identification..."""
        if self.connected is False:
            return

        # ACCOMPLISHMENT: Editing Credentials
        try:
            self.libaccom.accomplish("ubuntu-desktop/accomplishments-edit-credentials")
        except:
            pass

        self.EditExtraDialog.prepare(self.libaccom)
        result = self.EditExtraDialog.run() #the dialog's response handlers will take care about storing the result
        self.EditExtraDialog.hide()
        
        # re-load accoms and show the opps view, which will update both views
        # XXX we should probably do this inside EditExtraInfoDialog.py
        self._load_accomplishments()
        # self.on_tb_opportunities_clicked(None)
        return

    def enable_subcats_buttons(self):
        self.subcats_back.set_sensitive(True)
        self.subcats_forward.set_sensitive(True)

    def subcats_show(self, col, cat):                    
        tempcats = []
        if cat == "everything":
            self.subcats_container.hide()
        else:
            # set up the subcats
            cats = self.libaccom.get_collection_categories(col)
            for c in cats:
                if c == cat:
                    tempcats = cats[c]

            finalcats = []
            
            for s in tempcats:
                for i in self.accomdb:
                    if i["collection"] == col and i["categories"][0] == cat + ":" + s and i["accomplished"] == False:
                        finalcats.append(s)

            # convert to a set to remove dupes
            finalcats = set(finalcats)            
            
            # remove previous buttons from the button box
            for b in self.subcats_buttonbox.get_children():
                self.subcats_buttonbox.remove(b)

            # Add 'All' button
            button = Gtk.Button(_("All"))
            button.props.relief = Gtk.ReliefStyle.NONE
            button.connect("clicked", self.subcat_clicked, cat)
            self.subcats_buttonbox.add(button)
            button.show()
            
            # fill the button box with the sub categories
            for s in finalcats:
                button = Gtk.Button(s)
                button.props.relief = Gtk.ReliefStyle.NONE
                button.connect("clicked", self.subcat_clicked, cat)
                self.subcats_buttonbox.add(button)
                button.show()
            
            if len(finalcats) > 0:
                self.subcats_buttonbox.show_all()
                self.subcats_container.show()
            else:
                self.subcats_container.hide()
                

    def _subcat_clicked(self, button, data):
        self.subcat = button.get_label()
        self.update_views(None)

    def subcats_back_button(self, widget):
        h = self.subcats_scroll.get_hadjustment()
        new = h.get_value() - h.get_step_increment()
        h.set_value(new)
        self.subcats_scroll.set_hadjustment(h)

    def subcats_forward_button(self, widget):
        h = self.subcats_scroll.get_hadjustment()
        new = h.get_value() + h.get_step_increment()
        h.set_value(new)
        self.subcats_scroll.set_hadjustment(h)

    def show_gwibber_widget(self,accomID,name):
        if GWIBBER_OK:
            # Temporarily using trophies.ubuntu.com
            #trophyURL = TROPHY_GALLERY_URL+'/gallery/trophies/'+name+'/'+accomID
            trophyURL = 'http://trophies.ubuntu.com/gallery/trophies/'+name+'/'+accomID
            trophy_name = self.libaccom.get_accom_title(accomID);
            self.messageentry.text_view.get_buffer().set_text(_("I've just got the trophy '%s' in #ubuntu accomplishments!") % (trophy_name))
            self.messagewindow.show()
            self.messagewindow.present()

    def close_gwibber_window(self,widget=None,event=None):
        self.messagewindow.hide()
        return True
    
    def webkit_link_clicked(self, view, frame, net_req, nav_act, pol_dec):
        """Load a link from the webkit view in an external system browser."""

        uri=net_req.get_uri()
        if uri.startswith ('file:///gwibber-share'):
            if GWIBBER_OK:
                share_name = self.libaccom.get_share_name()
                share_name = urllib2.quote(share_name.encode('utf8'))
                share_ID = self.libaccom.get_share_id()
                nameURL = TROPHY_GALLERY_URL+"/user/getusername?share_name="+share_name+"&share_id="+share_ID

                publish_status = self.libaccom.get_published_status()
                if publish_status==0:
                    dialog = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, _("Your trophies are not yet published"))
                    dialog.format_secondary_text(_("You can do it from Edit->Preferences menu."))
                    dialog.run()
                    dialog.hide()
                else:
                    try:
                        response = urllib2.urlopen(nameURL)
                        for line in response:
                            name = line.rstrip()
                            break          
                        uri = uri.replace("file:///gwibber-share?accomID=", '');
                        gwibberPopup = self.show_gwibber_widget(uri,name)
                    except urllib2.HTTPError:
                        print 'HTTPError while getting username.'
                return True
            else:
                return False

        if uri.startswith('about:'):
            return False

        if uri.startswith('file:'):
            return False            
            
        if uri.startswith('http'):
            webbrowser.open_new_tab(uri)
            return True

        if uri.startswith('accomplishment:'):
            id = uri[17:]
            self.set_display(DISPLAY_MODE_DETAILS,accomID=id)
            return True

        pol_dec.ignore()
        return True        

    def scriptrunner_start(self):
        """Indicate that the script runner is starting."""
        
        self.statusbar.set_text("Checking for new accomplishments...")
        self.spinner.start()
        self.spinner.show()
        self.statusbox.show()

    def scriptrunner_finish(self):
        """Indicate that the script runner has stopped."""
        
        self.statusbar.set_text("")
        self.spinner.stop()
        self.spinner.hide()
        self.statusbox.hide()

    def approve_u1_trophies(self):
        self.u1_button.set_label("Check for Ubuntu One account")
        self.u1_button_sig = self.u1_button.connect("clicked", self.register_with_u1)
        self.verif_box.show_all()
        self.additional_ubuntu1.set_visible(True)

    def register_with_u1(self, widget):
        ver = self.libaccom.verify_ubuntu_one_account()

    def verify_u1_account(self):
        ver = self.libaccom.verify_ubuntu_one_account()

        if bool(ver) == True:
            self.u1_button.disconnect(self.u1_button_sig)
            self.u1_button.set_label("Click here to confirm your Ubuntu One account")
            self.u1_button_sig = self.u1_button.connect("clicked", self.register_with_verif)
            self.has_u1 = True
            self.libaccom.write_config_file_item("config", "has_u1", True)
        else:
            pass

    def cancel_register_with_u1(self, widget):
        self.additional_ubuntu1.set_visible(False)

    def create_trophy_share(self, widget):
        trophydir = self.libaccom.get_config_value("config", "trophypath")

        self.has_verif = True
        self.libaccom.write_config_file_item("config", "has_verif", True)

        res = self.libaccom.register_trophy_dir(trophydir)

        #if res == 1:
        #    print "foo"
        #self.u1_button.set_label("Successfully shared. Click here to continue...")
        #self.u1_button.disconnect(self.u1_button_sig)
        #self.u1_button_sig = self.u1_button.connect("clicked", self.complete_share_process)
        #self.u1_button.show()
        self.complete_share_process()

    def complete_share_process(self):
        self.has_u1 = True
        self.libaccom.write_config_file_item("config", "has_u1", True)
        
        self.additional_ubuntu1.set_visible(False)

        # ACCOMPLISHMENT: Editing Credentials
        try:
            self.libaccom.accomplish("ubuntu-desktop/accomplishments-shared-with-validation-server")
        except:
            pass
        
        self.check_for_extra_info_required()

    def register_with_verif(self, widget):
        self.u1_button.set_label("Account found, Approve verified trophies")

        if widget is not None:
            self.u1_button.disconnect(self.u1_button_sig)

        self.u1_button_sig = self.u1_button.connect("clicked", self.create_trophy_share)

        self.u1_button.show()
        self.additional_ubuntu1.set_visible(True)

    def on_window_resized(self,widget):
        # get the new size
        new_width = widget.get_size()[0]
        new_height = widget.get_size()[1]
        # if the size has changed...
        if(new_width != self.curr_width or new_height != self.curr_height):
            # remember new size
            self.curr_width = new_width
            self.curr_height = new_height
            # and refill iconviews with icons to adjust columns number
            if self.connected:
				if self.display_mode is DISPLAY_MODE_OPPORTUNITIES:
					self._update_views(None)
				if self.display_mode is DISPLAY_MODE_TROPHIES:
					self._update_mytrophy_filter()
            else:
                # Control flow may reach here if the daemon is not yet running 
                # and therefore connection is yet to be made. Passing here will
                # avoid errors about not-existing libaccom.
                pass
                      
    def populate_opp_combos(self):
        temp = []

        for i in self.accomdb:
            temp.append({i["collection"] : i["collection-human"] })

        # uniqify the values
        result = [dict(tupleized) for tupleized in set(tuple(item.items()) for item in temp)]

        # set up app
        self.opp_col_store.append(["", "All"])

        for i in sorted(result):
            self.opp_col_store.append([i.keys()[0], i.values()[0]])

        self.opp_combo_col.set_model(self.opp_col_store)

        self.opp_combo_col.set_active(0)
        self.opp_combo_col.show()

        # set up cat

        self.opp_combo_cat.set_model(self.opp_cat_store)
        
        self.opp_combo_cat.show()
      
    def on_filter_collection_changed(self,widget):
        tree_iter = widget.get_active_iter()
        model = widget.get_model()
        collection, name = model[tree_iter][:2]
        self.set_display(filter_collection = collection)

    def on_filter_category_changed(self, widget):
        tree_iter = widget.get_active_iter()
        if tree_iter == None: # Special case if the categories combo is not sensitive
            return
        model = widget.get_model()
        category, name = model[tree_iter][:2]
        self.set_display(filter_category = category)
    
    def on_filter_show_locked_clicked(self, widget):
		if widget.get_active():
			self.set_display(filter_locked=DISPLAY_FILTER_LOCKED_SHOW)
		else:
			self.set_display(filter_locked=DISPLAY_FILTER_LOCKED_HIDE)
    
    def on_search_changed(self,widget):
		value = widget.get_text()
		self.set_display(search_query=value)
    
    def check_accomplishments(self, widget):
        """Called when Check Accomplishments is selected in the interface."""
        self.libaccom.run_scripts(True)
        
    def on_mytrophies_filter_latest_toggled(self, widget):
		self.set_display(trophies_mode=MYTROPHIES_FILTER_LATEST)

    def on_mytrophies_filter_all_toggled(self, widget):   
		self.set_display(trophies_mode=MYTROPHIES_FILTER_ALL)

    def on_tb_mytrophies_clicked(self, widget):
        """Called when the My Trophies button is clicked."""
        
        mytrophies_toggled = self.tb_mytrophies.get_active()
        opportunities_toggled = self.tb_opportunities.get_active()
        
        if mytrophies_toggled == True:
            self.set_display(DISPLAY_MODE_TROPHIES)
        else:
            self.tb_mytrophies.set_active(True) # This also fires the signal handler

    def on_tb_opportunities_clicked(self, widget):
        """Called when the Opportunities button is clicked."""
        
        self.launcher.set_property("urgent", False)
        self.newtrophies = 0
        self.launcher.set_property("count_visible", False)
        
        mytrophies_toggled = self.tb_mytrophies.get_active()
        opportunities_toggled = self.tb_opportunities.get_active()
        
        if opportunities_toggled == True:
            self.set_display(DISPLAY_MODE_OPPORTUNITIES)
        else:
            self.tb_opportunities.set_active(True) # This also fires the signal handler

    def menu_prefs_clicked(self,widget):
        """Display the preferences window."""
        
        # If the window already is in use, when user clicks the menu
        # item, present() is used instead, to bring the window to front
        # etc.
        if self.preferences_dialog is not None:
            self.preferences_dialog.present()
        else:
            #create new instance
            self.preferences_dialog = self.PreferencesDialog()
            self.preferences_dialog.prepare(self.libaccom)
            self.preferences_dialog.connect('destroy', self.on_preferences_dialog_destroyed)
            self.preferences_dialog.show()
    
    def on_preferences_dialog_destroyed(self,widget):
        self.preferences_dialog = None
    
    def get_icon(self, name):
        theme = Gtk.IconTheme.get_default()
        return theme.load_icon(name, 48, 0)

    def check_for_extra_info_required(self):
        """Check if the installed accomplishments require additional information to be gathered from the user."""
        
        infoneeded = self.libaccom.get_all_extra_information_required()

        if len(infoneeded) is not 0:
            # kick of the process of gathering the information needed
            try:
                seen = self.libaccom.get_config_value("config", "extrainfo_seen")
                
                if seen == "NoOption" or seen == 0:
                    self.additional_info_req.set_visible(True)
                    self.libaccom.write_config_file_item("config", "extrainfo_seen", 1)
                else:
                    return
            except:
                self.additional_info_req.set_visible(True)
                self.libaccom.write_config_file_item("config", "extrainfo_seen", 1)

    def check_daemon_session(self):
        configvalue = self.libaccom.get_config_value("config", "daemon_sessionstart")
        if configvalue == "NoOption":
            self.additional_daemon_session.set_visible(True)
        elif configvalue == "false":
            pass

    def daemon_session_ok(self, widget):
        self.libaccom.set_daemon_session_start(True)
        self.additional_daemon_session.set_visible(False)

    def edit_auth_info(self,widget):
        """Called when user clicks "Edit credentials" from notification"""
        self.additional_info_req.set_visible(False)
        self.edit_identification_clicked(widget) #that's maily the same thing
        return

    def edit_auth_info_cancel(self,widget):
        """Called when user clicks "Later" from extrainfo-needed notification"""
        self.additional_info_req.set_visible(False)
        return
    
    def _load_accomplishments(self):
        # clear the local cache of accomplishments
        self.accomdb = []
        self.accomdb = self.libaccom.build_viewer_database()
        
    def opp_clicked(self, widget):
        selection = widget.get_selected_items()
        if len(selection) is 0:
            return
        item = selection[0]
        widget.unselect_path(item)
        model = widget.get_model()
        accomID = model[item][COL_ID]
        self.set_display(DISPLAY_MODE_DETAILS,accomID=accomID)

    def mytrophy_clicked(self, widget):
        selection = widget.get_selected_items()
        if len(selection) is 0:
            return
        item = selection[0]
        widget.unselect_path(item)
        model = widget.get_model()
        accomID = model[item][COL_ID]
        self.set_display(DISPLAY_MODE_DETAILS,accomID=accomID)

    def optparse_accomplishment(self, accom_id):
        """Process the -a command line option"""
        if not self.libaccom.get_accom_exists(accom_id):
            # this accomplishment does not exist! aborting...
            print "There is no accomplishment with this ID."
            return
                
        self.set_display(DISPLAY_MODE_DETAILS,accomID=accom_id)

    def fill_in_tree_models(self):
        # Fill in the opportunities tree
        for acc in self.accomdb:
            if str(acc["accomplished"]) != '1':
                icon = GdkPixbuf.Pixbuf.new_from_file_at_size(str(acc["iconpath"]), 90, 90)
                self.oppstore.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])

	def set_display(self, 
                    mode              = DISPLAY_MODE_UNSPECIFIED,
                    accomID           = "",
                    trophies_mode     = MYTROPHIES_FILTER_UNSPECIFIED,
                    filter_locked     = DISPLAY_FILTER_LOCKED_UNSPECIFIED,
                    filter_collection = DISPLAY_FILTER_COLLECTION_UNSPECIFIED,
                    filter_category   = DISPLAY_FILTER_CATEGORY_UNSPECIFIED,
                    filter_subcat     = DISPLAY_FILTER_SUBCAT_UNSPECIFIED,
                    search_query      = DISPLAY_FILTER_SEARCH_UNSPECIFIED):
		"""
		Switches display mode as specified in arguments. It takes care about flipping notebook pages, hiding unnecessary UI pieces etc.
		"""
		if mode is not DISPLAY_MODE_UNSPECIFIED:
			self.display_mode = mode
        if filter_locked is not DISPLAY_FILTER_LOCKED_UNSPECIFIED:
            self.display_filter_locked = filter_locked
        if filter_collection is not DISPLAY_FILTER_COLLECTION_UNSPECIFIED:
            self.display_filter_collection = filter_collection
            
            # As the requested collection changed, we need to update the categories combo.
            if filter_collection == "":
                self.opp_cat_store.clear()
                self.opp_cat_store.append(["", _("everything")])
                self.opp_combo_cat.set_sensitive(False)
            else:
                cats = self.libaccom.get_collection_categories(filter_collection)
                #for i in cats:
                #    catlist.add(i)
                self.opp_cat_store.clear()
                self.opp_cat_store.append(["", _("everything")])
                for i in sorted(cats):
                    self.opp_cat_store.append([i, i])
                self.opp_combo_cat.set_sensitive(True)
                    
            # Set the active item to "everything".
            self.display_filter_category = ""
            self.opp_combo_cat.handler_block_by_func(self.on_filter_category_changed)
            self.opp_combo_cat.set_active(0)
            self.opp_combo_cat.handler_unblock_by_func(self.on_filter_category_changed)
        
        if filter_category is not DISPLAY_FILTER_CATEGORY_UNSPECIFIED:
            self.display_filter_category = filter_category
        if filter_subcat is not DISPLAY_FILTER_SUBCAT_UNSPECIFIED:
			self.display_filter_subcat = filter_subcat
		
		if search_query is not DISPLAY_FILTER_SEARCH_UNSPECIFIED:
			self.display_filter_search = search_query
        
        
		if self.display_mode is DISPLAY_MODE_DETAILS:
			#Displaying details for an accomplishment
			
			if accomID == "":
				print "Unable to display details view, you probably forgot the accomID argument."
			else:
				self._accomplishment_info(accomID)
				self.notebook.set_current_page(0)
				
		elif self.display_mode is DISPLAY_MODE_TROPHIES:
			#Display the list of trophies
					
			if trophies_mode is not MYTROPHIES_FILTER_UNSPECIFIED:
				self.display_mytrophies_filtermode = trophies_mode
				
            # Set togglable buttons to reflect current state
            self.tb_mytrophies.handler_block_by_func(self.on_tb_mytrophies_clicked)      
            self.tb_opportunities.handler_block_by_func(self.on_tb_opportunities_clicked) 
            self.tb_mytrophies.set_active(True) 
            self.tb_opportunities.set_active(False)
            self.tb_mytrophies.handler_unblock_by_func(self.on_tb_mytrophies_clicked)
            self.tb_opportunities.handler_unblock_by_func(self.on_tb_opportunities_clicked)
            
			self._update_mytrophy_view()
			self.notebook.set_current_page(1)
		   
		elif self.display_mode is DISPLAY_MODE_OPPORTUNITIES:
            
            # Set togglable buttons to reflect current state
            self.tb_mytrophies.handler_block_by_func(self.on_tb_mytrophies_clicked)      
            self.tb_opportunities.handler_block_by_func(self.on_tb_opportunities_clicked) 
            self.tb_mytrophies.set_active(False) 
            self.tb_opportunities.set_active(True)
            self.tb_mytrophies.handler_unblock_by_func(self.on_tb_mytrophies_clicked)
            self.tb_opportunities.handler_unblock_by_func(self.on_tb_opportunities_clicked)
            
			self._update_opportunities_view()
			self.notebook.set_current_page(2)

    def _update_mytrophy_view(self):
        pass

    def _update_opportunities_view(self):
        # Causes the treemodel to call visible_func for all rows.
        self.oppstore_filter.refilter()
        
    def opp_visible_func(self, model, iterator, data):
        """
        This function is crucial for filtering opportunities. It is called
        by some internal GTK callbacks, whenever the treemodel changes.
        It has to return True/False, which states whether the given row
        should be displayed or not.
        """
        # If we are hiding locked accoms:
        if (self.display_filter_locked is DISPLAY_FILTER_LOCKED_HIDE) and model.get_value(iterator,COL_LOCKED):
            return False
        # If we ale looking for a certain collection:
        if (self.display_filter_collection != "") and (self.display_filter_collection != model.get_value(iterator,COL_COLLECTION)):
            return False
        if (self.display_filter_search != "") and  not (self.display_filter_search.lower() in model.get_value(iterator,COL_TITLE).lower()):
			return False
        return True

    def _____update_mytrophy_filter(self):
        
        kids = self.mytrophies_mainbox.get_children()
        
        if len(kids) > 0:
            for k in kids:
                self.mytrophies_mainbox.remove(k)
                
        if (self.display_mytrophies_filtermode == MYTROPHIES_FILTER_ALL):
            collections = self.libaccom.list_collections()
            
            for c in collections:
                ls = Gtk.ListStore(str, GdkPixbuf.Pixbuf, bool, bool, str, str) # title, icon accomplished, locked, col, accomplishment
                ls.set_sort_column_id(COL_TITLE, Gtk.SortType.ASCENDING)
                ls.clear()
                collectionhuman = ""
                for i in self.mytrophies_store_all:
                    if i[0]["collection"] == c:
                        collectionhuman = i[0]["collection-human"]
                        ls.append([i[0]["title"], i[0]["icon"], i[0]["accomplished"], i[0]["locked"], i[0]["collection"], i[0]["id"]])

                if len(ls) > 0:
                    self.add_mytrophies_view(collectionhuman, ls)
        elif (self.display_mytrophies_filtermode == MYTROPHIES_FILTER_LATEST):
            if len(self.mytrophies_filter_today) > 0:
                self.add_mytrophies_view(_("Today"), self.mytrophies_filter_today)
            
            if len(self.mytrophies_filter_week) > 0:
                self.add_mytrophies_view(_("This Week"), self.mytrophies_filter_week)
            
            if len(self.mytrophies_filter_month) > 0:
                self.add_mytrophies_view(_("This Month"), self.mytrophies_filter_month)
            
            if len(self.mytrophies_filter_sixmonths) > 0:
                self.add_mytrophies_view(_("Last Six Months"), self.mytrophies_filter_sixmonths)
            
            if len(self.mytrophies_filter_earlier) > 0:
                self.add_mytrophies_view(_("Earlier"), self.mytrophies_filter_earlier)
    

    def _____update_views(self, widget):
        """Update all of the views to reflect the current state of Trophies and Opportunities."""

        self.mytrophies_store_all = []
        
        #trophymodel = self.trophy_icon.get_model()
        oppmodel = self.opp_icon.get_model()

        # clear the models
        oppmodel.clear()
        self.mytrophies_filter_today.clear()
        self.mytrophies_filter_week.clear()
        self.mytrophies_filter_month.clear()
        self.mytrophies_filter_sixmonths.clear()
        self.mytrophies_filter_earlier.clear()
        """
        coltree_iter = self.opp_combo_col.get_active_iter()
        colmodel = self.opp_combo_col.get_model()

        if coltree_iter == None:
            col = ""
            colname = ""
        else:
            col, colname = colmodel[coltree_iter][:2]
        
        col_active_item = self.opp_combo_col.get_active()
        
        if col_active_item == 0:
            self.opp_combo_cat.set_sensitive(False)
        else:
            self.opp_combo_cat.set_sensitive(True)

        cattree_iter = self.opp_combo_cat.get_active_iter()
        catmodel = self.opp_combo_cat.get_model()

        if cattree_iter == None:
            cat = ""
            catname = ""
        else:
            cat, catname = catmodel[cattree_iter][:2]

        if cat == "":
            self.subcats_container.hide()
        else:
            self.subcats_show(col, cat)
        """
        
        # update opportunities
        for acc in self.accomdb:
            icon = GdkPixbuf.Pixbuf.new_from_file_at_size(str(acc["iconpath"]), 90, 90)

            if str(acc["accomplished"]) == '1':
                #self.mytrophies_filter_all = testlist.append( { acc["collection-human"] : [acc["title"], icon, bool(acc["accomplished"]), acc["locked"], acc["collection"], acc["id"]] } )
                self.mytrophies_store_all.append([{ "title" : acc["title"], "icon" : icon, "accomplished" : bool(acc["accomplished"]), "locked" : acc["locked"], "collection" : acc["collection"], "id" : acc["id"], "collection-human" : acc["collection-human"] }])

                today = datetime.date.today()
                margin_today = datetime.timedelta(days = 1)
                margin_week = datetime.timedelta(days = 7)
                margin_month = datetime.timedelta(days = 31)
                margin_sixmonths = datetime.timedelta(days = 180)

                match = False

                if str(acc["date-accomplished"]) == "None":
                    pass
                else:
                    year = int(acc["date-accomplished"].split("-")[0])
                    month = int(acc["date-accomplished"].split("-")[1])
                    day = int(acc["date-accomplished"].split("-")[2].split(" ")[0])

                    if (today - margin_today <= datetime.date(year, month, day) <= today + margin_today) == True:
                        self.mytrophies_filter_today.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                    elif (today - margin_week <= datetime.date(year, month, day) <= today + margin_week) == True:
                        self.mytrophies_filter_week.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                    elif (today - margin_month <= datetime.date(year, month, day) <= today + margin_month) == True:
                        self.mytrophies_filter_month.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                    elif (today - margin_sixmonths <= datetime.date(year, month, day) <= today + margin_sixmonths) == True:                        
                        self.mytrophies_filter_sixmonths.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                    #else:
                    #    self.mytrophies_filter_earlier.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                
            else:
                subcat = ""
                thiscat = ""

                c = [i for i in acc["categories"] if i == cat]
                if len(c) is not 0:
                    thiscat = c[0]
                else:
                    thiscat = ""                    
                

                if self.subcat is not None:
                    subcat = str(cat) + ":" + str(self.subcat)
                    if self.subcat == "All":
                        if acc["collection"] == col and cat in list(acc["categories"])[0]:
                            if not acc["locked"] or show_locked:
                                oppmodel.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                    else:
                        if acc["collection"] == col and list(acc["categories"])[0] == subcat:
                            if not acc["locked"] or show_locked:
                                oppmodel.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                else:
                    if acc["collection"] == col and cat in list(acc["categories"])[0]:
                        if not acc["locked"] or show_locked:
                            oppmodel.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                    elif col == "" and cat == "":
                        if not acc["locked"] or show_locked:
                            oppmodel.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                    elif acc["collection"] == col and cat == "":
                        if not acc["locked"] or show_locked:
                            oppmodel.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
  

    def _accomplishment_info(self, accomID):
        """Display information about the selected accomplishment."""
        data = []
        
        # determine dependencies
        
        deps = []
        depstatus = []
        
        deps = self.libaccom.get_accom_depends(accomID)
        
        for acc in self.accomdb:
            for d in deps:
                if acc["id"] == d:
                    depstatus.append({ "id" : acc["id"], "accomplished" : acc["accomplished"], "collection-human" : acc["collection-human"], "title" : acc["title"] })
        
        
        achieved = self.libaccom.get_accom_is_accomplished(accomID)
        data = self.libaccom.get_accom_data(accomID)
        if achieved:
            trophydata = self.libaccom.get_trophy_data(accomID)
        

        html = None

        iconpath = self.libaccom.get_accom_icon_path(accomID)

        html = "<!DOCTYPE html> \
        <html lang='en'> \
        <head> \
            <link href='file://" + os.path.join(self.datapath, "css", "information.txt") + "' rel='stylesheet' type='text/css'> \
            <link href='file://" + os.path.join(self.datapath, "css", "font.txt") + "' rel='stylesheet' type='text/css'> \
        </head> \
        <body class='container_8' background='" + get_media_file("home-bkg.gif") + "'>"

        if "title" in data:
            html = html + "<div id='header' class='grid_8'> \
                <h1>" + data['title'] + "</h1> \
                </div>"
                


        ## summary table
        html = html + "<div id='accomplishment' class='grid_8 clearfix'> \
        <div id='accomplishment-badge' class='grid_8 clearfix'>"

        if achieved and GWIBBER_OK:
            html = html + "<div id='social-share'><a href='gwibber-share?accomID="+accomID+"' id='gwibber-share'>+SHARE</a></div>"

        html = html +"<img class='icon' src='" + str(iconpath) + "'> \
            <div class='grid_3 block'> \
                <h4>" + _("Opportunity Information").decode('utf-8') + ":</h4> \
            <ul class='none'> \
                <li>"

        if "description" in data:
            description = data["description"]
            html = html + description
        else:
            html = html + _("No information available.").decode('utf-8')
                
                
        html = html + "</li> \
            </ul> \
            </div>"

        if not achieved:
        
            html = html + "<div class='grid_3 block'> \
            <h4>" + _("Getting Help").decode('utf-8') + ":</h4> \
            <ul class='none'>"
            
            if "help" in data:
                help = data["help"]

                for l in help.split('\n'):
                    channelName = l[l.find("#")+1:l.find(" ")]
                    if l.startswith( '#'+channelName ):
                        l = "<a style='color:#FFF' href='http://webchat.freenode.net/?channels="+channelName+"'>"+'#'+channelName+" on freenode</a>"                 
                        html = html + "<li>" + l + "</li>"
                    else:
                        html = html + "<li>" + l + "</li>"  
            else:
                html = html + "<li>" + _("No help available.").decode('utf-8') + "</li>"
            
            html = html + "</ul></div>"


        html = html + "</div>"

        html = html + "<div id='accomplishment-conditions' class='grid_8'> \
            <ul class='none'>"
            
        if "depends" in data:
            # check if it is locked
            if not self.libaccom.get_accom_is_unlocked(accomID):
                if len(depstatus) > 0:
                    if len(depstatus) == 1:
                        html = html + "<li><i class='icon-key icon-large'></i>" + _("This opportunity is locked. You need to complete").decode('utf-8') + " <a href='accomplishment://" + depstatus[0]["id"] + "'><strong>" + depstatus[0]["title"] + "</strong></a> " + _("from").decode('utf-8') +" <strong>" + depstatus[0]["collection-human"] + "</strong> " + _("first").decode('utf-8') + ".</li>"
                    else:
                        html = html + "<li><i class='icon-key icon-large'></i>" + _("This opportunity is locked. You need to complete the following opportunities first:").decode('utf-8') + "</li>"
                        for d in depstatus:
                            if d["accomplished"] == False:
                                html = html + "<li class='deps_child'><a href='accomplishment://" + d["id"] + "'><strong>" + d["title"] + "</strong></a> " + _("from").decode('utf-8') +" <strong>" + d["collection-human"] + "</strong></li>"
        if achieved:
            #achieved
            
            html = html + "<li><img src='" + str(get_media_file("verify-icon.png")) + "' height='20' />" + _("This trophy <strong>was awarded</strong>").decode('utf-8')

            if "date-accomplished" in trophydata:
                date = trophydata["date-accomplished"]
                html = html + " " + _("on") + " " + date

            if "needs-information" in trophydata:
                extrainfo = trophydata["needs-information"].split(" ")
                html = html + ", " + _("using the following credentials").decode('utf-8') + ":</li><li><ul class='big'>"
                for i in extrainfo:
                    e = self.libaccom.get_extra_information(accomID.split("/")[0],i)
                    html = html + "<li>" + e[0]["label"] + ": " + trophydata[i] + "</li>"
                html = html + "</ul></li>"
            else:       
                html = html + ".</li>"

            if "needs-signing" in data:
                if data["needs-signing"] == "true" or data["needs-signing"] == "True":
                    html = html + "<li><img src='" + str(get_media_file("verify-icon.png")) + "' height='20' />" + _("This trophy has been verified").decode('utf-8') + ".</li>"
            #end of "if achieved"

        else:
            #not achieved
            if "needs-signing" in data:
                if data["needs-signing"] == "true" or data["needs-signing"] == "True":
                    html = html + "<li><i class='icon-trophy icon-large'></i>" + _("This opportunity requires verification").decode('utf-8') + ".</li> \
                        </ul>"

        html = html + "</ul></div> \
            </div>"

        if achieved:
            #script for showing details...
            html = html + """<script language="JavaScript">function ShwHid(divId){
var el = document.getElementById('accomDetails');
    if(document.getElementById(divId).style.display == 'none'){
        document.getElementById(divId).style.display='block';
        el.innerHTML = '""" + _("Accomplishment Details [-]") + """';
    }else{
        document.getElementById(divId).style.display='none';
                el.innerHTML = '""" + _("Accomplishment Details [-]") + """';
    }
}
</script>"""
            html = html + """<a id="accomDetails" onclick="javascript:ShwHid('acc_body')" href="javascript:;" class='grid_3' style='outline: none'>"""
            html = html + _("Accomplishment Details [+]") + "</a>"
            #details hidden by default
            html = html + "<div id='acc_body' style='display: none'>"
        else:
            #details not hidden by default
            html = html + "<div>"
        
        
        if "summary" in data:
            html = html + "<div id='accompilshment-info' class='grid_8'>"
            summary = data["summary"]
            for l in summary.split('\n'):
                html = html  + "<p>" + l + "</p>"
            html = html + "</div>"


        html = html + "<div id='accomplishment-more'  class='grid_8'>"

        if "steps" in data:

            html = html + "<div id='howto' class='grid_8'> \
                <i class='icon-list'></i> \
                <h2>" + _("How to accomplish this opportunity").decode('utf-8') + "</h2> \
                <ol>"
            
            steps = data["steps"]
            for l in steps.split('\n'):
                html = html + "<li class='icon-pushpin'>" + l + "</li>"
            html = html + "</ol> \
                </div>"

        showtipspitfalls = False
        haspitfalls = False
        hastips = False
        
        if "tips" in data or "pitfalls" in data:
            try:
                if not data["tips"] == "None":
                    showtipspitfalls = True
                    hastips = True
            except:
                hastips = False
                
            try:
                if not data["pitfalls"] == "None":
                    showtipspitfalls = True                                       
                    haspitfalls = True
            except:
                haspitfalls = False
                
            if showtipspitfalls == True:
                html = html + "  <div id='tipspitfalls' class='grid_8 clearfix'>"
        else:
            showtipspitfalls == False
                
        if showtipspitfalls == True:
            html = html + "<div class='grid_4 block left' id='tips'>"
            html = html + "<h2>" + _("Tips and Tricks").decode('utf-8') + ":</h2>"
            
            if hastips == True:
                tips = data["tips"]
            else:
                tips = None
            
            html = html + "<ul>"

            if tips == None:
                html = html + "<li class='icon-ok'>" + _("None.").decode('utf-8') + "</li>"
            else:
                for t in tips.split('\n'):
                    html = html + "<li class='icon-ok'>" + t + "</li>"
            
            html = html + "</ul>"
            html = html + "</div>"

            html = html + "<div id='divider' class='left'>&nbsp;</div>"
            html = html + "<div class='grid_3 block left' id='pitfals'>"
            html = html + "<h2>" + _("Pitfalls To Avoid").decode('utf-8') + ":</h2>"
            
            if haspitfalls == True:
                pitfalls = data["pitfalls"]
            else:
                pitfalls = None
            
            html = html + "<ul>"

            if pitfalls == None:
                html = html + "<li class='icon-remove'>" + _("None.").decode('utf-8') + "</li>"
            else:
                for p in pitfalls.split('\n'):
                    html = html + "<li class='icon-remove'>" + p + "</li>"

            html = html + "</ul>"
            html = html + "</div>"

            html = html + "</div>"

        if "links" in data:
            links = data["links"]
            html = html + "<div id='furtherreading' class='grid_8'> \
                <h2>" + _("Further Reading").decode('utf-8') + "</h2>"
            html = html + "<ul>"
            for l in links.split('\n'):
                html = html + "<li><a href='" + l + "'><i class='icon-external-link icon-large'></i>" + l + "</a></li>"
            html = html + "</ul> \
                </div>"

        html = html + "</ul></div></div> \
            </body> \
            </html>"

        self.webview.load_html_string(html, "file:///")
        self.webview.show()

