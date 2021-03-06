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

from gi.repository import Gtk  # pylint: disable=E0611
from operator import itemgetter
from accomplishments_viewer_lib.helpers import get_builder

import gettext
import locale
from accomplishments.util.paths import locale_dir
locale.bindtextdomain('accomplishments-viewer', locale_dir)
gettext.bindtextdomain('accomplishments-viewer', locale_dir)
locale.textdomain('accomplishments-viewer')


class EditExtrainfoDialog(Gtk.Dialog):
    __gtype_name__ = "EditExtrainfoDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when
        constructing a new instance of this class.

        Returns a fully instantiated EditExtrainfoDialog object.
        """
        builder = get_builder('EditExtrainfoDialog')
        new_object = builder.get_object('edit_extrainfo_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a EditExtrainfoDialog object with it in order to
        finish initializing the start of the new EditExtrainfoDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)
        self.auth_box = builder.get_object('auth_box')
        self.btn_ok = builder.get_object('btn_ok')

    def prepare(self, libaccom):
        """Called before run()nig, setups the window"""
        # use self.parent.libaccom for calling
        # use self.parent.connected to check if connected to daemon
        self.libaccom = libaccom

        i = self.libaccom.get_all_extra_information()

        self.entries_map = {}

        #remove all widgets that are contained in the auth_box
        #they will be there since the previous prepare() call
        c = self.auth_box.get_child()
        if c is not None:
            self.auth_box.remove(c)

        if len(i) is not 0:
            #there what to ask for
            self.main_box = Gtk.VBox()
            self.auth_box.add(self.main_box)

            #essential. It ensures we'll append items to section_dict, in an unchanging order.
            infoneeded = sorted(i, key=itemgetter('collection'))

            section_dict = {}
            extrainfo_dict = {}
            #section dict looks like: { "launchpad-email" : ["ubuntu-community","ubuntu-community-italy"],
            #                           "magic-token"     : ["ubuntu-community","ubuntu-community-italy"],
            #                           "askubuntu-login" : ["askubuntu"],
            #                           "github-id"       : ["openshot", "otherapp"]                     }
            for i in infoneeded:
                if i["needs-information"] not in section_dict:
                    section_dict[i["needs-information"]] = list([i["collection"]])
                    extrainfo_dict[i["needs-information"]] = i
                else:
                    section_dict[i["needs-information"]].append(i["collection"])
                    extrainfo_dict[i["needs-information"]] = i
            for a in section_dict:
                section_dict[a] = tuple(section_dict[a])

            rev_section_dict = {}
            #the rev_section_dict shal be the grouped inverse of section_dict:
            #                         { ("ubuntu-community","ubuntu-community-italy",) : ["launchpad-email","magic-token"],
            #                           ("askubuntu",)                                 : ["askubuntu-login"],
            #                           ("openshot", "otherapp",)                      : ["github-id"]       }
            #

            for i in section_dict:
                d = section_dict[i]
                if d not in rev_section_dict:
                    rev_section_dict[d] = list([i])
                else:
                    rev_section_dict[d].append(i)

            #print rev_section_dict

            for i in sorted(rev_section_dict.keys(), reverse=True, key=len):
                #the gui code is here - done for every GROUP of entry fields
                d = rev_section_dict[i]

                g_box = Gtk.VBox()
                g_box.set_margin_bottom(20)
                g_box.set_margin_left(10)
                self.main_box.pack_start(g_box, True, False, 0)

                g_upbox = Gtk.HBox()
                g_box.pack_start(g_upbox, True, False, 0)

                g_upimage = Gtk.Image()
                g_upimage.set_margin_left(5)
                g_upimage.set_margin_top(5)
                g_upimage.set_margin_bottom(5)
                g_upimage.set_margin_right(5)
                g_upimage.set_from_stock(Gtk.STOCK_GO_FORWARD, Gtk.IconSize.LARGE_TOOLBAR)

                #temporarily we'll use an ugly name
                n = len(i)
                if n is 1:
                    name = self.libaccom.get_collection_name(i[0])
                elif n is 2:
                    name = self.libaccom.get_collection_name(i[0]) + " and " + self.libaccom.get_collection_name(i[1])
                else:
                    name = ""
                    for k in range(0, n):
                        if n - k > 2:
                            name = name + self.libaccom.get_collection_name(i[k]) + ", "
                        elif n - k is 2:
                            name = name + self.libaccom.get_collection_name(i[k]) + " and "
                        elif n - k is 1:
                            name = name + self.libaccom.get_collection_name(i[k])

                g_uplabel = Gtk.Label("<big><b>" + name + "</b></big>")
                g_uplabel.set_use_markup(True)
                g_uplabel.set_margin_left(10)
                #g_uplabel.set_halign(Gtk.Align.START)

                g_sep = Gtk.HSeparator()
                g_box.pack_start(g_sep, True, False, 0)

                for f in d:
                    #for each information field in the group...
                    extrainfo = extrainfo_dict[f]
                    label = extrainfo['label']
                    label = label.replace("&", "&amp;")  # pango would complain on that
                    description = extrainfo['description']
                    description = description.replace("&", "&amp;")  # pango would complain on that
                    value = extrainfo['value']
                    example = extrainfo.get('example')

                    g_entrybox = Gtk.HBox()
                    g_mainlabel = Gtk.Label(label)
                    g_mainlabel.set_justify(Gtk.Justification.RIGHT)
                    g_mainlabel.set_margin_right(8)
                    g_entry = Gtk.Entry()
                    g_entry.connect("activate", self.on_enter)
                    g_entry.set_width_chars(30)
                    g_entry.set_text(value)
                    g_desclabel = Gtk.Label("<small><small><b>" + description + "</b></small></small>")
                    g_desclabel.set_use_markup(True)
                    g_desclabel.set_alignment(1, 0)

                    if example:
                        g_example = Gtk.Label("<small><small><b>Example: " + example + "</b></small></small>")
                        g_example.set_use_markup(True)
                        g_example.set_alignment(1, 0)
                        g_example.set_margin_right(20)

                    g_entrybox.set_margin_right(20)
                    g_desclabel.set_margin_right(20)

                    g_box.pack_start(g_entrybox, True, False, 0)
                    g_box.pack_start(g_desclabel, True, False, 0)
                    if example:
                        g_box.pack_start(g_example, True, False, 0)
                    g_entrybox.pack_end(g_entry, False, False, 0)
                    g_entrybox.pack_end(g_mainlabel, False, False, 0)

                    self.entries_map[f] = [g_entry, value]

                g_upbox.pack_start(g_upimage, False, False, 0)
                g_upbox.pack_start(g_uplabel, False, True, 0)

            self.auth_box.show_all()

        else:
            #no point in asking at all
            label = Gtk.Label("<i>(no extra-information is required, most likely there is something wrong with your installtion)</i>")
            label.set_use_markup(True)
            self.auth_box.add(label)
            self.auth_box.show_all()
        return

    def on_enter(self, widget):
        """Proxy function that simply calls the OK button when the user
        has pressed Enter on a textbox."""
        self.btn_ok.clicked()

    def on_btn_ok_clicked(self, widget, data=None):
        """The user has elected to save the changes.
        Called before the dialog returns Gtk.ResponseType.OK from run().
        """

        #saving the data should happen here.
        anything_changed = False
        for f in self.entries_map:
            entry = self.entries_map[f][0]
            origvalue = self.entries_map[f][1]
            newvalue = entry.get_text()
            if newvalue == origvalue:
                pass
            else:
                #print "value " + f + " changed"
                anything_changed = True
                self.libaccom.write_extra_information_file(f, newvalue)

        if anything_changed:
            self.libaccom.run_scripts(True)

    def on_btn_cancel_clicked(self, widget, data=None):
        """The user has elected cancel changes.
        Called before the dialog returns Gtk.ResponseType.CANCEL for run()
        """
        #not much to do...
        pass

    def init(self,):
        return

if __name__ == "__main__":
    dialog = EditExtrainfoDialog()
    dialog.show()
    Gtk.main()
