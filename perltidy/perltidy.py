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
import pickle

def error_message(message):
    def msg_on_close_destroy(button,response_id,dialog):
        if response_id == gtk.RESPONSE_CLOSE: 
            dialog.destroy()

    msg_dialog = gtk.MessageDialog(flags = gtk.DIALOG_MODAL, buttons = gtk.BUTTONS_CLOSE, type = gtk.MESSAGE_ERROR, message_format = message)
    msg_dialog.connect('response', msg_on_close_destroy, msg_dialog)
    msg_dialog.run()

class WindowControl:
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

        if self._plugin.settings().get('apply_to_select') and len(doc.get_selection_bounds()): #do we want to apply to, and have, a selection?
            start_iter, end_iter = doc.get_selection_bounds()
        else:            
            start_iter, end_iter = doc.get_start_iter(), doc.get_end_iter()
        if start_iter.compare(end_iter) == 0 : return #position the same, nothing to operate on
        tidied_text = self.tidy_text( doc.get_text( start_iter, end_iter ) )
        
        doc.delete(start_iter, end_iter)
        doc.insert(start_iter,tidied_text)
        
    def tidy_text(self, doc_text):
        if doc_text == None or doc_text == '' : return

        finput  = tempfile.NamedTemporaryFile(delete = False)
        foutput = tempfile.NamedTemporaryFile(delete = False)
            
        foutput.close()

        finput.write(doc_text)
        finput.close()

        s = self._plugin.settings()

        shell_args = ['perltidy',finput.name,'-o',foutput.name]

        if s.get('use_cfg') and not s.get('use_cfg_file') == '':
            if not os.path.exists(s.get('use_cfg_file')):
                error_message(_("Configuration file " + s.get('use_cfg_file') + " does not exist"))
                return
            else:        
                shell_args.append( "-pro="+s.get('use_cfg_file') )
        
        subprocess.Popen(shell_args).wait()

        foutput = open(foutput.name,'r')
        tidied_text = foutput.read()        
        foutput.close()
    
        os.remove(finput.name)
        os.remove(foutput.name)
           
        return tidied_text

class PluginConfig:
    config_file = os.path.expanduser('~/.gnome2/gedit/plugins/perltidy.conf')
    _setting_data = None

    def __init__(self, plugin):
        self._plugin = plugin

    def _on_checkbox_toggle(self, widget, data):
        if data == 'use_cfg':
            self.widgets.get('use_cfg_file').set_sensitive( widget.get_active() and True or False )
    
    def dialog(self):
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,gtk.STOCK_OK, gtk.RESPONSE_ACCEPT)
        dialog  = gtk.Dialog("PerlTidy Plugin " + _("configuration"),buttons = buttons)

        def on_btn_click(dialog, response_id, data): 
            if response_id == gtk.RESPONSE_CLOSE: return # not triggered by msgbox close
            if response_id == gtk.RESPONSE_ACCEPT:
                data.get('parent')._save_settings()
            data.get('dialog').destroy()      
        
        self.settings()        

        self.widgets = self._create_widgets()
        self._apply_current_settings()

        for widget in self.widgets.itervalues():
            dialog.vbox.add(widget)

        dialog.connect('response', on_btn_click, {'dialog':dialog,'parent':self})
        dialog.show_all()
        dialog.set_resizable(False)
        
        return dialog

    def _create_widgets(self):        
        cfg_entry = gtk.Entry()
        widgets = {
            'apply_to_select' : gtk.CheckButton( _("Apply to _selection if available") ),
            'use_cfg'         : gtk.CheckButton( _("Use custom _configuration file (e.g. " + os.path.expanduser('~/.perltidyrc') + ")" ) ),
            'use_cfg_file'    : cfg_entry,
        }
        widgets.get('use_cfg').connect('toggled',self._on_checkbox_toggle, 'use_cfg')
        return widgets

    def _apply_current_settings(self):
        widgets  = self.widgets
        settings = self.settings()
    
        s = settings.get('use_cfg_file')

        if s:
            use_cfg_file = s.startswith('~') and os.path.expanduser(s) or s
        else:
            use_cfg_file = os.path.expanduser('~/.perltidyrc')

        widgets.get('use_cfg').set_active(settings.get('use_cfg') or False)
        widgets.get('apply_to_select').set_active(settings.get('apply_to_select') or False)
        widgets.get('use_cfg_file').set_text(use_cfg_file)
        widgets.get('use_cfg').toggled()
        
    def settings(self, conf = None):
        if self._setting_data == None: 
            self._setting_data = {}
            self._load_settings_from_file()
        if not conf: return self._setting_data
        self._setting_data.update(conf)
        return self._setting_data
        
    def _save_settings(self):          
        conf = {
            'use_cfg_file'   : self.widgets.get('use_cfg_file').get_text(),
            'use_cfg'        : self.widgets.get('use_cfg').get_active(),
            'apply_to_select': self.widgets.get('apply_to_select').get_active(),
        }
        if conf.get('use_cfg') and conf.get('use_cfg_file') == '':
            error_message(_("Please enter a configuration file to use."))
            return
        self.settings(conf)    
        self._commit_settings_to_file()
    
    def _load_settings_from_file(self):
        if not os.path.exists(self.config_file): return
        try:
            f = open(self.config_file,'r')
        except:
            error_message( _("Unable to create/open config file " + self.config_file + ", cannot store settings.") )
            return        
        settings = pickle.load(f)
        f.close()
        self.settings(settings)
        
    def _commit_settings_to_file(self):
        if not os.path.exists(self.config_file): 
            try:
                f = open(self.config_file,'w').close() #create if not exist
            except:
                error_message( _("Unable to create config file " + self.config_file + ", cannot store settings.") )
                return
        try:
            f = open(self.config_file,'w')
        except:
            error_message( _("Unable to open config file " + self.config_file + ", cannot store settings.") )
            return
        f.write(pickle.dumps(self.settings()))
        f.close()        

class PerlTidyPlugin(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        self._instances = {}

    def activate(self, window):
        self._instances[window] = WindowControl(self, window)

    def deactivate(self, window):
        self._instances[window].deactivate()
        del self._instances[window]

    def update_ui(self, window):
        self._instances[window].update_ui()

    def settings(self):
        return PluginConfig(self).settings()

    def is_configurable(self):
        return True

    def create_configure_dialog(self):
        return PluginConfig(self).dialog()       

