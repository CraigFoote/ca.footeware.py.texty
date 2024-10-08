import sys
import gi
import os

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the UI file
ui_file = os.path.join(current_dir, "data", "window.ui")

@Gtk.Template(filename=ui_file)
class TextyWindow(Adw.ApplicationWindow):
    __gtype_name__ = "TextyWindow"

    save_button = Gtk.Template.Child()
    text_view = Gtk.Template.Child()
    window_title = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.current_file = None
        self.buffer_modified = False
    
        # preferences
        self.settings = Gio.Settings.new("ca.footeware.py.texty")

        # set window size from prefs
        self.update_title()

        # set default window size
        width = self.settings.get_int("window-width")
        height = self.settings.get_int("window-height")
        self.set_default_size(width, height)

        # Connect to window size change signals
        self.connect("notify::default-width", self.on_window_size_change)
        self.connect("notify::default-height", self.on_window_size_change)

        # add path to icon to default icon theme
        icon_dir = os.path.join(os.path.dirname(__file__), 'data', 'icons', 'hicolor', 'scalable', 'apps')
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon_theme.add_search_path(icon_dir)

        self.buffer = self.text_view.get_buffer()
        self.buffer.connect("changed", self.on_buffer_changed)
        self.buffer_modified = False # Flag to track buffer changes

        # save clicked
        self.save_button.connect("clicked", self.on_save_clicked)

    def on_window_size_change(self, widget, param):
        self.save_window_size()
        
    def save_window_size(self):
        width = self.get_width() 
        height = self.get_height()
        self.settings.set_int("window-width", width)
        self.settings.set_int("window-height", height)
        self.settings.apply()

    def save_window_size(self):
        width = self.get_width()
        height = self.get_height()
        self.settings.set_int("window-width", width)
        self.settings.set_int("window-height", height)
        self.settings.apply()

    def get_text(self):
        buffer = self.text_view.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)

    def set_text(self, text):
        self.text_view.get_buffer().set_text(text)

    def on_save_clicked(self, button):
         self.save_file()

    def save_file(self):
        if self.current_file:
            return self.save_to_file(self.current_file)
        else:
            return self.save_as()
        
    def save_as(self):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Save File")
        dialog.save(self, None, self.on_save_dialog_response)

    def on_save_dialog_response(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                if self.save_to_file(file):
                    self.current_file = file
                    self.buffer_modified = False
                    self.text_view.get_buffer().set_modified(False)
            else:
                self.show_toast("Save operation cancelled")
        except GLib.Error as error:
            self.show_toast(f"Error saving file: {error.message}")

    def save_to_file(self, file):
        buffer = self.text_view.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        try:
            with open(file.get_path(), 'w') as f:
                f.write(text)
            self.window_title.set_title(f"{file.get_basename()}")
            self.window_title.set_subtitle(file.get_path())
            self.buffer_modified = False
            self.text_view.get_buffer().set_modified(False)
            self.show_toast(f"File saved: {file.get_basename()}")
            return True
        except IOError as e:
            self.show_toast(f"Error saving file: {str(e)}")
            return False
        
    def show_toast(self, message):
        toast = Adw.Toast.new(message)
        self.toast_overlay.add_toast(toast)

    def update_title(self):
        if self.current_file:
            self.window_title.set_title(os.path.basename(self.current_file))
            self.window_title.set_subtitle(os.path.dirname(self.current_file))
        else:
            self.window_title.set_title("texty")
            self.window_title.set_subtitle("a minimal text editor")

    def new_file(self):
        if self.buffer_modified:
            self.prompt_save_changes("new")
        else:
            self.create_new_file()

    def prompt_save_changes(self, next_action):
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading("Save changes?")
        dialog.set_body("There are unsaved changes. Do you want to save them?")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("discard", "Discard")
        dialog.add_response("save", "Save")
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")
        dialog.connect("response", self.on_save_changes_response, next_action)
        dialog.present()

    def create_new_file(self):
        self.text_view.get_buffer().set_text("")
        self.text_view.get_buffer().set_modified(False)
        self.current_file = None
        self.window_title.set_title("texty")
        self.window_title.set_subtitle("a minimal text editor")
        self.show_toast("New file created")
        self.buffer_modified = False
        self.text_view.get_buffer().set_modified(False)

    def on_buffer_changed(self, buffer):
        self.buffer_modified = True
        title_str = self.window_title.get_title()
        if not title_str.startswith("* "):
            self.window_title.set_title(f"* {title_str}")

    def on_save_changes_response(self, dialog, response, next_action):
        if response == "save":
            success = self.save_file()
            if success:
                self.execute_next_action(next_action)
        elif response == "discard":
            self.execute_next_action(next_action)
        # If "cancel" or dialog is closed, do nothing

    def on_open_dialog_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.load_file(file)
                self.window_title.set_title(f"{file.get_basename()}")
                self.window_title.set_subtitle(file.get_path())
                self.buffer_modified = False
                self.buffer.set_modified(False)
            else:
                self.show_toast("Open operation cancelled")
        except GLib.Error as error:
            self.show_toast(f"Error opening file: {error.message}")

    def execute_next_action(self, next_action):
        if next_action == "new":
            self.create_new_file()
            self.text_view.grab_focus()
        elif next_action == "open":
            self.open_file(self)

    def open_file(self):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Open File")
        dialog.open(self, None, self.on_open_dialog_response)

    def load_file(self, file):
        try:
            with open(file.get_path(), 'r') as f:
                text = f.read()
            buffer = self.text_view.get_buffer()
            buffer.set_text(text)
            self.current_file = file
            self.show_toast(f"File opened: {file.get_basename()}")
        except IOError as e:
            self.show_toast(f"Error opening file: {str(e)}")

    def save_as(self):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Save File")
        dialog.save(self, None, self.on_save_dialog_response)

    def toggle_wrap_text(self, state):
        if state:
            self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        else:
            self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)

class TextyApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="ca.footeware.py.texty",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.wrap_text_state = False  # Initialize the state

    def do_startup(self):
        Adw.Application.do_startup(self)

        save_action = Gio.SimpleAction.new("save", None)
        save_action.connect("activate", self.on_save_action)
        self.add_action(save_action)

        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self.on_new_action)
        self.add_action(new_action)

        open_action = Gio.SimpleAction.new("open", None)
        open_action.connect("activate", self.on_open_action)
        self.add_action(open_action)

        save_as_action = Gio.SimpleAction.new("save_as", None)
        save_as_action.connect("activate", self.on_save_as_action)
        self.add_action(save_as_action)

        new_window_action = Gio.SimpleAction.new("new_window", None)
        new_window_action.connect("activate", self.on_new_window_action)
        self.add_action(new_window_action)  

        toggle_wrap_action = Gio.SimpleAction.new_stateful("toggle_wrap", 
                                                       None, 
                                                       GLib.Variant.new_boolean(self.wrap_text_state))
        toggle_wrap_action.connect("change-state", self.on_toggle_wrap_text)
        toggle_wrap_action.set_enabled(True)
        self.add_action(toggle_wrap_action)

    def on_toggle_wrap_text(self, action, value):
        new_state = value.get_boolean()
        self.wrap_text_state = new_state
        action.set_state(value)
        win = self.get_active_window()
        if win:
            win.toggle_wrap_text(new_state)

    def do_activate(self):
        self.new_window()

    def new_window(self):
        win = TextyWindow(application=self)
        win.present()

    def on_save_action(self, action, parameter):
        win = self.get_active_window()
        win.save_file()

    def on_open_action(self, action, parameters=None):
        win = self.get_active_window()
        if win.buffer_modified:
            win.prompt_save_changes("new")
        else:
            dialog = Gtk.FileDialog.new()
            dialog.set_title("Open File")
            dialog.open(win, None, win.on_open_dialog_response)

    def on_new_action(self, action, parameter):
        win = self.get_active_window()
        win.new_file()

    def on_save_as_action(self, action, parameters=None):
        win = self.get_active_window()
        win.save_as()
    
    def on_new_window_action(self, action, parameter):
        self.new_window()

def main(version):

    app = TextyApplication()
    return app.run(sys.argv)

if __name__ == '__main__':
    main(sys.argv)