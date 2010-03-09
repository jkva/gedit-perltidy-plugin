# Copyright (C) 2010 Job van Achterberg <jkva@cpan.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, 
# Boston, MA 02111-1307, USA.


import gedit

import pygtk
pygtk.require('2.0')

import gtk

from gettext import gettext as _

import os
import tempfile
import time
import subprocess

from warnings import warn

class WindowHandler:
    def __init__(self, plugin, window):
        self._window = window
        self._plugin = plugin
        self._insert_menu()

    def deactivate(self):
        self._remove_menu()
        self._window = self._plugin = self._action_group = None

    def _insert_menu(self):
        manager = self._window.get_ui_manager()

        self._action_group = gtk.ActionGroup("PerltidyPluginActions")
        self._action_group.add_actions([("PerltidyPlugin", None, _("Run PerlTidy"),
                                         None, _("Run through PerlTidy"),
                                         self.tidy)])

        manager.insert_action_group(self._action_group, -1)

        ui_str = """<ui>
            <menubar name="MenuBar">
                <menu name="ToolsMenu" action="Tools">
                    <placeholder name="ToolsOps_2">
                        <menuitem name="PerltidyPlugin" action="PerltidyPlugin"/>
                    </placeholder>
                    </menu>
            </menubar>
        </ui>
        """

        self._ui_id = manager.add_ui_from_string(ui_str)

    def _remove_menu(self):
        manager = self._window.get_ui_manager()
        manager.remove_ui(self._ui_id)
        manager.remove_action_group(self._action_group)
        manager.ensure_update()

    def update_ui(self):
        self._action_group.set_sensitive(self._window.get_active_document() != None)

    def tidy(self, action):
        doc = self._window.get_active_document()
        if not doc : return

        start, end = doc.get_start_iter(), doc.get_end_iter()
        tidied_text = self.tidy_text( doc.get_text( start, end ) );
        doc.set_text( tidied_text )
        
    def tidy_text(self, doc_text):
        finput  = tempfile.NamedTemporaryFile(delete = False)
        foutput = tempfile.NamedTemporaryFile(delete = False)
            
        foutput.close()

        finput.write(doc_text)
        finput.close()

        shell_args = ['perltidy',finput.name,'-o',foutput.name]
        
        subproc = subprocess.Popen(shell_args)
        subproc.wait()        

        foutput = open(foutput.name,'r')
        tidied_text = foutput.read()        
        foutput.close()
    
        os.remove(finput.name)
        os.remove(foutput.name)
           
        return tidied_text
    
class PerlTidyPlugin(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self._instances = {}

    def activate(self, window):
        self._instances[window] = WindowHandler(self, window)

    def deactivate(self, window):
        self._instances[window].deactivate()
        del self._instances[window]

    def update_ui(self, window):
        self._instances[window].update_ui()

    def is_configurable(self):
        return True

    def create_configure_dialog(self):
        dialog = gtk.Dialog("PerlTidy Plugin" + _(" Configuration"))
        # needs gtk code
        return dialog
        
