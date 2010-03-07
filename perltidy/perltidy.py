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

# Menu item example, insert a new item in the Tools menu
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

class WindowHandler:
    def __init__(self, plugin, window):
        self._window = window
        self._plugin = plugin

        # Insert menu items
        self._insert_menu()

    def deactivate(self):
        # Remove any installed menu items
        self._remove_menu()

        self._window = None
        self._plugin = None
        self._action_group = None

    def _insert_menu(self):
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()

        # Create a new action group
        self._action_group = gtk.ActionGroup("PerltidyPluginActions")
        self._action_group.add_actions([("PerltidyPlugin", None, _("Run PerlTidy"),
                                         None, _("Run through PerlTidy"),
                                         self.tidy)])

        # Insert the action group
        manager.insert_action_group(self._action_group, -1)

        # Merge the UI
        self._ui_id = manager.add_ui_from_string(ui_str)

    def _remove_menu(self):
        # Get the GtkUIManager
        manager = self._window.get_ui_manager()

        # Remove the ui
        manager.remove_ui(self._ui_id)

        # Remove the action group
        manager.remove_action_group(self._action_group)

        # Make sure the manager updates
        manager.ensure_update()

    def update_ui(self):
        self._action_group.set_sensitive(self._window.get_active_document() != None)

    def tidy(self, action):
        doc = self._window.get_active_document()
        if not doc : return
        tidied_text = self.tidy_text( doc.get_text( doc.get_start_iter(),doc.get_end_iter() ) );
        doc.set_text( tidied_text )
        
    def tidy_text(self, doc_text):
        finput  = tempfile.NamedTemporaryFile(delete = False)
        foutput_name = tempfile.NamedTemporaryFile(delete = False).name

        finput.write(doc_text)
        finput.close()

        shell_args = ['perltidy',finput.name,'-o',foutput_name]
        
        subprocess.Popen(shell_args)
        
        foutput = open(foutput_name,'r')
        tidied_text = foutput.read()
        foutput.close()
    
        os.remove(finput.name)
        os.remove(foutput_name)
           
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
        
