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

gettext.textdomain('accomplishments-viewer')
DBusGMainLoop(set_as_default=True)
logger = logging.getLogger('accomplishments-viewer')

COL_TITLE = 0
COL_PIXBUF = 1
COL_ACCOMPLISHED = 2
COL_LOCKED = 3
COL_COLLECTION = 4
COL_ID = 5

# See accomplishments_viewer_lib.Window.py for more details about how this class works
class AccomplishmentsViewerWindow(Window):
    __gtype_name__ = "AccomplishmentsViewerWindow"
    
    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window."""
        
        super(AccomplishmentsViewerWindow, self).finish_initializing(builder)

        self.AboutDialog = AboutAccomplishmentsViewerDialog
        self.PreferencesDialog = PreferencesAccomplishmentsViewerDialog
        self.EditExtraDialog = EditExtrainfoDialog()
        self.EditExtraDialog.parent = self
        self.curr_height = 0
        self.curr_width = 0
        self.do_not_react_on_cat_changes = False
        # Code for other initialization actions should be added here.

        # self.accomdb provides a collection of all accomplishments
        # that we query throughout the application
        self.accomdb = []

        # create a connection to the daemon
        self.connected = False
        self.connect_to_daemon()

        # reference to the Unity Launchcher
        self.launcher = Unity.LauncherEntry.get_for_desktop_id("accomplishments-viewer.desktop")
        self.newtrophies = 0
        
        # set up all of the different UI references
        self.tb_mytrophies = self.builder.get_object("tb_mytrophies")
        self.tb_opportunities = self.builder.get_object("tb_opportunities")
        self.trophy_icon = self.builder.get_object("trophy_icon")
        self.opp_combo_col = self.builder.get_object("opp_combo_app")
        self.opp_combo_cat = self.builder.get_object("opp_combo_cat")
        self.opp_icon = self.builder.get_object("opp_icon")
        self.notebook = self.builder.get_object("notebook")
        self.additional_info_req = self.builder.get_object("add_info_req")
        self.additional_ubuntu1 = self.builder.get_object("add_ubu1")
        self.additional_daemon = self.builder.get_object("add_daemon")
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

        # make the toolbar black in Ubuntu
        context = self.toolbar.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)

        # create the stores used by the IconViews
        self.trophystore = Gtk.ListStore(str, GdkPixbuf.Pixbuf, bool, bool, str, str) # title, icon accomplished, locked, col, accomplishment
        self.trophystore.set_sort_column_id(COL_TITLE, Gtk.SortType.ASCENDING)
        self.trophy_icon.set_model(self.trophystore)

        self.oppstore = Gtk.ListStore(str, GdkPixbuf.Pixbuf, bool, bool, str, str) # title, icon, accomplished, locked, col, accomplishment
        self.oppstore.set_sort_column_id(COL_TITLE, Gtk.SortType.ASCENDING)
        self.opp_icon.set_model(self.oppstore)

        self.trophy_icon.set_text_column(COL_TITLE)
        self.trophy_icon.set_pixbuf_column(COL_PIXBUF)

        self.opp_icon.set_text_column(COL_TITLE)
        self.opp_icon.set_pixbuf_column(COL_PIXBUF)

        # set up webkit

        self.webview = WebKit.WebView()
        self.scrolledwindow.add(self.webview)
        self.webview.props.settings.props.enable_default_context_menu = False
        self.webkitlink = self.webview.connect("navigation-policy-decision-requested",self.webkit_link_clicked)

        self.webview.show()

        self.opp_col_store = Gtk.ListStore(str, str)
        self.col_combo_renderer_text = Gtk.CellRendererText()
        self.opp_combo_col.pack_start(self.col_combo_renderer_text, True)
        self.opp_combo_col.add_attribute(self.col_combo_renderer_text, "text", 1)

        self.opp_cat_store = Gtk.ListStore(str, str)
        self.cat_combo_renderer_text = Gtk.CellRendererText()
        self.opp_combo_cat.pack_start(self.cat_combo_renderer_text, True)
        self.opp_combo_cat.add_attribute(self.cat_combo_renderer_text, "text", 1)

        if self.connected is True:
            self.populate_opp_combos()

        self.u1_button = Gtk.Button()
        self.u1_button_sig = None
        self.verif_box.pack_start(self.u1_button, False, False, 0)

        # set up logging
        self.dir_cache = os.path.join(
            xdg.BaseDirectory.xdg_cache_home, "accomplishments")

        if not os.path.exists(self.dir_cache):
            os.makedirs(self.dir_cache)

        if not os.path.exists(os.path.join(self.dir_cache, "logs")):
            os.makedirs(os.path.join(self.dir_cache, "logs"))

        if self.connected is True:
            self.check_and_ask_for_info()

        if self.connected is False:
            self.run_daemon()

        self.datapath = get_data_path()
        #self.datapath = "/home/jono/source/accomplishments-viewer/data/"

        self.update_widgets_sensitivity()

        #self._load_accomplishments()
        #self.update_views(None)
        self.notebook.set_current_page(2)
        self.tb_opportunities.set_active(True)

    def trophy_received(self, message):
        """Called when a new trophy is detected on the system."""
        
        self.newtrophies = self.newtrophies + 1
        
        # run this to refresh our accomplishments list
        self._load_accomplishments()
        self.update_views(None)
        
        # set the Launcher icon to be urgent and show new trophy count
        self.launcher.set_property("urgent", True)
        self.launcher.set_property("count", self.newtrophies)
        
        if self.newtrophies > 0:
            self.launcher.set_property("count_visible", True)
        else:
            self.launcher.set_property("count_visible", False)
        
        self.on_tb_mytrophies_clicked(None)

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
            object.connect_to_signal("scriptrunner_start",
                self.scriptrunner_start,
                dbus_interface="org.ubuntu.accomplishments")
            object.connect_to_signal("scriptrunner_finish",
                self.scriptrunner_finish,
                dbus_interface="org.ubuntu.accomplishments")
        except dbus.DBusException:
            traceback.print_exc()
            print usage
            return False

        bus.add_signal_receiver(self.trophy_received,
            dbus_interface = "org.ubuntu.accomplishments",
            signal_name = "trophy_received")
        bus.add_signal_receiver(self.scriptrunner_start,
            dbus_interface = "org.ubuntu.accomplishments",
            signal_name = "scriptrunner_start")
        bus.add_signal_receiver(self.scriptrunner_finish,
            dbus_interface = "org.ubuntu.accomplishments",
            signal_name = "scriptrunner_finish")
        
        self.connected = True
        return True
        
    def run_daemon(self):
        """Starts the daemon process"""                

        command = "twistd -noy " + daemon_exec_dir + "/accomplishments-daemon --logfile=" + os.path.join(self.dir_cache, "logs", "daemon.log") + " &"
        print ("Starting the daemon using command `%s`" % command)
        os.system(command)
        #apparently as that process daemonizes it will not get killed when one closes the client
        
        self.statusbar.set_text("Starting the daemon...")
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
            self.populate_opp_combos()
            self.check_and_ask_for_info()
            self.notebook.set_current_page(2)
            self.tb_opportunities.set_active(1)
            
        self.update_widgets_sensitivity()
        
        #returning false removes the timeout
        return False    

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
        self.EditExtraDialog.prepare(self.libaccom)
        result = self.EditExtraDialog.run() #the dialog's response handlers will take care about storing the result
        self.EditExtraDialog.hide()
        
        # re-load accoms and show the opps view, which will update both views
        # XXX we should probably do this inside EditExtraInfoDialog.py
        self._load_accomplishments()
        # self.on_tb_opportunities_clicked(None)
        return

    def webkit_link_clicked(self, view, frame, net_req, nav_act, pol_dec):
        """Load a link from the webkit view in an external system browser."""
        
        uri=net_req.get_uri()
        if uri.startswith('about:'):
            return False

        if uri.startswith('file:'):
            return False            
            
        if uri.startswith('http'):
            webbrowser.open_new_tab(uri)
            return True

        if uri.startswith('accomplishment:'):
            id = uri[17:]
            self.accomplishment_info(id)
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
        self.u1_button.set_label("Register with Ubuntu One")
        self.u1_button_sig = self.u1_button.connect("clicked", self.register_with_u1)
        self.verif_box.show_all()
        self.additional_ubuntu1.set_visible(True)

    def register_with_u1(self, widget):
        webbrowser.open("http://one.ubuntu.com")
        self.verify_u1_account()

    def verify_u1_account(self):
        ver = self.libaccom.verify_ubuntu_one_account()

        if bool(ver) == True:
            self.u1_button.disconnect(self.u1_button_sig)
            self.u1_button.set_label("Click here to confirm your Ubuntu One account")
            self.u1_button_sig = self.u1_button.connect("clicked", self.register_with_verif)
            self.has_u1 = True
            self.libaccom.write_config_file_item("config", "has_u1", True)

        else:
            print ""

    def cancel_register_with_u1(self, widget):
        self.additional_ubuntu1.set_visible(False)

    def create_trophy_share(self, widget):
        trophydir = self.libaccom.get_config_value("config", "trophypath")

        self.has_verif = True
        self.libaccom.write_config_file_item("config", "has_verif", True)

        res = self.libaccom.register_trophy_dir(trophydir)

        if res == 1:
            self.u1_button.set_label("Successfully shared. Click here to continue...")
            self.u1_button.disconnect(self.u1_button_sig)
            self.u1_button_sig = self.u1_button.connect("clicked", self.complete_share_process)

    def complete_share_process(self, widget):
        self.additional_ubuntu1.set_visible(False)
        self.check_for_extra_info_required()

    def register_with_verif(self, widget):
        self.u1_button.set_label("Approve verified trophies")

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
            self.update_views(widget)

    def update_views(self, widget):
        """Update all of the views to reflect the current state of Trophies and Opportunities."""
        status_trophies = 0
        status_opps = 0

        show_locked = True

        if self.opp_showlocked.get_active():
            show_locked = True
        else:
            show_locked = False

        trophymodel = self.trophy_icon.get_model()
        oppmodel = self.opp_icon.get_model()

        trophymodel.clear()
        oppmodel.clear()

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

        # update opportunities
        for acc in self.accomdb:
            icon = None
            icon = GdkPixbuf.Pixbuf.new_from_file_at_size(str(acc["iconpath"]), 90, 90)

            if str(acc["accomplished"]) == '1':
                trophymodel.append([acc["title"], icon, bool(acc["accomplished"]), acc["locked"], acc["collection"], acc["id"]])
                status_trophies = status_trophies + 1
            else:
                status_opps = status_opps + 1
                if acc["collection"] == col and acc["category"] == cat:
                    if not acc["locked"] or show_locked:
                        oppmodel.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                if col == "" and cat == "":
                    if not acc["locked"] or show_locked:
                        oppmodel.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])
                if acc["collection"] == col and cat == "":
                    if not acc["locked"] or show_locked:
                        oppmodel.append([acc["title"], icon, bool(acc["accomplished"]), bool(acc["locked"]), acc["collection"], acc["id"]])

    def populate_opp_combos(self):

        # grab data
        self._load_accomplishments()

        temp = []

        for i in self.accomdb:
            temp.append({i["collection"] : i["collection-human"] })

        # uniqify the values
        result = [dict(tupleized) for tupleized in set(tuple(item.items()) for item in temp)]

        # set up app
        self.opp_col_store.append(["", "All"])

        for i in result:
            self.opp_col_store.append([i.keys()[0], i.values()[0]])

        self.opp_combo_col.set_model(self.opp_col_store)

        self.opp_combo_col.set_active(0)
        self.opp_combo_col.show()

        # set up cat

        self.opp_combo_cat.set_model(self.opp_cat_store)
        
        self.opp_combo_cat.show()
      

    def opp_app_updated(self, widget):
        self.do_not_react_on_cat_changes = True
        catlist = set()
        tree_iter = widget.get_active_iter()
        model = widget.get_model()
        col, name = model[tree_iter][:2]

        for i in self.accomdb:
            if i["collection"] == col:
                if i["category"] != "":
                    catlist.add(i["category"])

        self.opp_cat_store.clear()

        self.opp_cat_store.append(["", "everything"])

        for i in catlist:
            self.opp_cat_store.append([i, i])

        self.do_not_react_on_cat_changes = False
        self.opp_combo_cat.set_active(0)
        
        # Following does not have to be done, because using
        # opp_combo_cat.set_active will cause opp_cat_updated
        # to run update_views
        #self.update_views(None)

    def check_accomplishments(self, widget):
        """Called when Check Accomplishments is selected in the interface."""
        
        self.libaccom.run_scripts(True)
        self.notebook.set_current_page(2)

    def opp_cat_updated(self, widget):
        if self.do_not_react_on_cat_changes:
            return
        self.update_views(None)

    def on_tb_mytrophies_clicked(self, widget):
        """Called when the My Trophies button is clicked."""
        
        mytrophies_toggled = self.tb_mytrophies.get_active()
        opportunities_toggled = self.tb_opportunities.get_active()
        
        if mytrophies_toggled == True:
            self.tb_opportunities.handler_block_by_func(self.on_tb_opportunities_clicked)
            self.tb_opportunities.set_active(False) 
            self.tb_opportunities.handler_unblock_by_func(self.on_tb_opportunities_clicked)
            self.notebook.set_current_page(1)
        else:
            self.tb_mytrophies.set_active(True)

    def on_tb_opportunities_clicked(self, widget):
        """Called when the Opportunities button is clicked."""
        
        self.launcher.set_property("urgent", False)
        self.newtrophies = 0
        self.launcher.set_property("count_visible", False)
        
        mytrophies_toggled = self.tb_mytrophies.get_active()
        opportunities_toggled = self.tb_opportunities.get_active()
        
        if opportunities_toggled == True:
            self.tb_mytrophies.handler_block_by_func(self.on_tb_mytrophies_clicked)       
            self.tb_mytrophies.set_active(False) 
            self.tb_mytrophies.handler_unblock_by_func(self.on_tb_mytrophies_clicked)
            self.notebook.set_current_page(2)
        else:
            self.tb_opportunities.set_active(True)

    def get_icon(self, name):
        theme = Gtk.IconTheme.get_default()
        return theme.load_icon(name, 48, 0)

    def check_for_extra_info_required(self):
        """Check if the installed accomplishments require additional information to be gathered from the user."""
        
        infoneeded = self.libaccom.get_all_extra_information_required()

        if len(infoneeded) is not 0:
            # kick of the process of gathering the information needed
            self.additional_info_req.set_visible(True)

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
        self.accomplishment_info(accomID)

    def mytrophy_clicked(self, widget):
        selection = widget.get_selected_items()
        if len(selection) is 0:
            return
        item = selection[0]
        widget.unselect_path(item)
        model = widget.get_model()
        accomID = model[item][COL_ID]
        self.accomplishment_info(accomID)

    def optparse_accomplishment(self, accom_id):
        """Process the -a command line option"""
        if not self.libaccom.get_acc_exists(accom_id):
            # this accomplishment does not exist! aborting...
            print "There is no accomplishment with this ID."
            return
                
        self.accomplishment_info(accom_id)
        print self.accomdb

    def accomplishment_info(self, accomID):
        """Display information about the selected accomplishment."""
        data = []
        
        # determine dependencies
        
        deps = []
        depstatus = []
        
        deps = self.libaccom.get_acc_depends(accomID)
        
        for acc in self.accomdb:
            for d in deps:
                if acc["id"] == d:
                    depstatus.append({ "id" : acc["id"], "accomplished" : acc["accomplished"], "collection-human" : acc["collection-human"], "title" : acc["title"] })
        
        
        achieved = self.libaccom.get_acc_is_completed(accomID)
        data = self.libaccom.get_acc_data(accomID)
        if achieved:
            trophydata = self.libaccom.get_trophy_data(accomID)
        

        html = None

        iconpath = self.libaccom.get_acc_icon_path(accomID)

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
        <div id='accomplishment-badge' class='grid_8 clearfix'> \
            <img class='icon' src='" + str(iconpath) + "'> \
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
                    html = html + "<li>" + l + "</li>"
            else:
                html = html + "<li>" + _("No help available.").decode('utf-8') + "</li>"
            
            html = html + "</ul></div>"


        html = html + "</div>"

        html = html + "<div id='accomplishment-conditions' class='grid_8'> \
            <ul class='none'>"
            
        if "depends" in data:
            # check if it is locked
            if not self.libaccom.get_acc_is_unlocked(accomID):
                if len(depstatus) > 0:
                    if len(depstatus) == 1:
                        print depstatus[0]["title"]
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
                    e = self.libaccom.get_extra_information(data["application"],i)
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
            html = html + """<script language="JavaScript">function ShwHid(divId){if(document.getElementById(divId).style.display == 'none'){document.getElementById(divId).style.display='block';}else{document.getElementById(divId).style.display='none';}}</script>"""
            html = html + """<a onclick="javascript:ShwHid('acc_body')" href="javascript:;" class='grid_3' style='outline: none'>"""
            html = html + _("Accomplishment Details") + "</a>"
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
        haspitfalls = False
        
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
        self.notebook.set_current_page(0)
        self.webview.show()

