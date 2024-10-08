import sys
import gi
import os

gi.require_version('Gio', '2.0')
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, Gdk, GLib

class TextyWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        __gtype_name__ = "TextyWindow"

        # Load the UI file
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(os.path.dirname(__file__), "data", "shortcuts.ui"))
        # builder.template(os.path.join(os.path.dirname(__file__), "data", "window.ui"))
        
        self.shortcuts_window = builder.get_object("shortcuts_window")
        self.set_help_overlay(self.shortcuts_window)

        # preferences
        self.settings = Gio.Settings.new("ca.footeware.py.texty")

        # set default window size
        width = self.settings.get_int("window-width")
        height = self.settings.get_int("window-height")
        self.set_default_size(width, height)

        # add path to icon to default icon theme
        icon_dir = os.path.join(os.path.dirname(__file__), 'data', 'icons', 'hicolor', 'scalable', 'apps')
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon_theme.add_search_path(icon_dir)

        # create the header bar
        header = Adw.HeaderBar()

        # Save button
        save_button = Adw.SplitButton(label="Save")
        save_action = Gio.SimpleAction.new("save", None)
        save_action.connect("activate", self.on_save_action_activated)
        self.add_action(save_action)
        save_button.set_action_name("win.save")

        menu_model = Gio.Menu.new()

        new_menu_item = Gio.MenuItem.new("New", "win.new")
        new_action = Gio.SimpleAction.new("new", None)
        new_action.connect("activate", self.on_new_action_activated)
        self.add_action(new_action)
        menu_model.append_item(new_menu_item)
        
        open_menu_item = Gio.MenuItem.new("Open", "win.open")
        open_action = Gio.SimpleAction.new("open", None)
        open_action.connect("activate", self.on_open_action_activated)
        self.add_action(open_action)
        menu_model.append_item(open_menu_item)

        save_as_menu_item = Gio.MenuItem.new("Save As", "win.save_as")
        save_as_action = Gio.SimpleAction.new("save_as", None)
        save_as_action.connect("activate", self.on_save_as_action_activated)
        self.add_action(save_as_action)
        menu_model.append_item(save_as_menu_item)

        section = Gio.Menu.new()
        new_window_menu_item = Gio.MenuItem.new("New Window", "win.new_window")
        new_window_action = Gio.SimpleAction.new("new_window", None)
        new_window_action.connect("activate", self.on_new_window_action_activated)
        self.add_action(new_window_action)
        section.append_item(new_window_menu_item)
        menu_model.append_section(None, section)
        
        save_button.set_menu_model(menu_model)
        header.pack_start(save_button)

        self.title = Adw.WindowTitle()
        self.title.set_title("texty")
        self.title.set_subtitle("a minimal text editor")
        header.set_title_widget(self.title)

        hamburger_menu = Gtk.MenuButton.new()
        hamburger_menu.set_icon_name("open-menu-symbolic")
        builder.add_from_file(os.path.join(os.path.dirname(__file__), "data", "menu.ui"))
        menu_model = builder.get_object("hamburger-menu")
        hamburger_menu.set_menu_model(menu_model)

        toggle_wrap_action = Gio.SimpleAction.new_stateful("toggle_wrap", 
                                                           None, 
                                                           GLib.Variant.new_boolean(True)) # look at MENU_XML win.toggle_wrap
        toggle_wrap_action.connect("activate", self.on_toggle_wrap_action_activated)
        toggle_wrap_action.set_state(GLib.Variant.new_boolean(self.settings.get_boolean("wrap-mode")))
        self.add_action(toggle_wrap_action) # (self window) == win in MENU_XML

        font_size = self.settings.get_int("font-size")
        self.set_font_size(font_size)
        font_size_action = Gio.SimpleAction.new_stateful(
            "font_size", GLib.VariantType.new("i"), GLib.Variant.new_int32(font_size)
        )
        font_size_action.connect("change-state", self.on_font_size_action_changed)
        font_size_action.set_state(GLib.Variant.new_int32(font_size))
        self.add_action(font_size_action)

        show_shortcuts_action = Gio.SimpleAction.new("show_shortcuts", None)
        show_shortcuts_action.connect("activate", self.on_show_shortcuts_action_activated)
        self.get_application().set_accels_for_action("win.show_shortcuts", ["<Ctrl>question"])
        self.add_action(show_shortcuts_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about_action_activated)
        self.add_action(about_action)

        header.pack_end(hamburger_menu)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.set_homogeneous(False)

        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)
        self.toast_overlay.set_child(self.box)

        self.box.append(header)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.text_view = Gtk.TextView.new()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_hexpand(True)
        self.text_view.set_vexpand(True)
        self.text_view.set_left_margin(10)
        self.text_view.set_right_margin(10)
        self.text_view.set_top_margin(10)
        self.text_view.set_bottom_margin(10)

        self.current_file = None  # Store the currently open file

        scrolled_window.set_child(self.text_view)
        self.box.append(scrolled_window)
        
        self.buffer = self.text_view.get_buffer()
        self.buffer.connect("changed", self.on_buffer_changed)
        self.buffer_modified = False # Flag to track buffer changes

        self.load_wrap_mode()
        self.connect("close-request", self.on_close_request)

        self.text_view.grab_focus()

    def on_show_shortcuts_action_activated(self, action, param=None):
        self.shortcuts_window.present()
    
    def on_close_request(self, window):
        width = self.get_width()
        height = self.get_height()
        self.settings.set_int("window-width", width)
        self.settings.set_int("window-height", height)
        return False  # Return False to allow the window to close
                    
    def load_wrap_mode(self):
        wrap_mode = self.settings.get_boolean("wrap-mode")
        if wrap_mode:
            self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        else:
            self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
    
    def on_font_size_action_changed(self, action, value):
        font_size = value.get_int32()
        action.set_state(value)
        self.set_font_size(font_size)
        # save to pref
        self.settings.set_int("font-size", font_size)
    
    def set_font_size(self, font_size):
        css = f"textview {{font-size: {font_size}px;}}"
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def on_toggle_wrap_action_activated(self, action, param=None):
        old_state = action.get_state()
        new_state = not old_state.get_boolean()
        action.set_state(GLib.Variant.new_boolean(new_state))

        if new_state:
            self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        else:
            self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)

        # Save the wrap mode to prefs
        self.settings.set_boolean("wrap-mode", new_state)
            
    def on_about_action_activated(self, action, param=None):
        about_dialog = Adw.AboutDialog.new()
        about_dialog.set_application_name("texty")
        about_dialog.set_developers(["Craig Foote <CraigFoote@gmail.com>"])
        about_dialog.set_developer_name("Another fine mess by Footeware.ca")
        about_dialog.set_copyright("©︎2024 Craig Foote")
        about_dialog.set_application_icon("texty")
        about_dialog.present()
    
    def on_buffer_changed(self, buffer):
        self.buffer_modified = True
        title_str = self.title.get_title()
        if not title_str.startswith("* "):
            self.title.set_title(f"* {title_str}")
    
    def show_toast(self, message):
        toast = Adw.Toast.new(message)
        self.toast_overlay.add_toast(toast)
    
    def save_to_file(self, file):
        buffer = self.text_view.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        try:
            with open(file.get_path(), 'w') as f:
                f.write(text)
            self.title.set_title(f"{file.get_basename()}")
            self.title.set_subtitle(file.get_path())
            self.buffer_modified = False
            self.text_view.get_buffer().set_modified(False)
            self.show_toast(f"File saved: {file.get_basename()}")
            return True
        except IOError as e:
            self.show_toast(f"Error saving file: {str(e)}")
            return False

    def save_as(self):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Save File")
        dialog.save(self, None, self.on_save_dialog_response)
    
    def on_save_action_activated(self, action, parameters=None):
        self.save_file()

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
    
    def on_new_action_activated(self, action, parameters=None):
        self.new_file()
    
    def new_file(self):
        if self.buffer_modified:
            self.prompt_save_changes("new")
        else:
            self.create_new_file()
    
    def create_new_file(self):
        self.text_view.get_buffer().set_text("")
        self.text_view.get_buffer().set_modified(False)
        self.current_file = None
        self.title.set_title("texty")
        self.title.set_subtitle("a minimal text editor")
        self.show_toast("New file created")
        self.buffer_modified = False
        self.text_view.get_buffer().set_modified(False)
    
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

    def on_save_changes_response(self, dialog, response, next_action):
        if response == "save":
            success = self.save_file()
            if success:
                self.execute_next_action(next_action)
        elif response == "discard":
            self.execute_next_action(next_action)
        # If "cancel" or dialog is closed, do nothing

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

    def save_file(self):
        if self.current_file:
            return self.save_to_file(self.current_file)
        else:
            return self.save_as()
        
    def on_open_action_activated(self, action, parameters=None):
        if self.buffer_modified:
            self.prompt_save_changes("new")
        else:
            dialog = Gtk.FileDialog.new()
            dialog.set_title("Open File")
            dialog.open(self, None, self.on_open_dialog_response)
    
    def on_open_dialog_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self.load_file(file)
                self.title.set_title(f"{file.get_basename()}")
                self.title.set_subtitle(file.get_path())
                self.buffer_modified = False
                self.buffer.set_modified(False)
            else:
                self.show_toast("Open operation cancelled")
        except GLib.Error as error:
            self.show_toast(f"Error opening file: {error.message}")
    
    def on_save_as_action_activated(self, action, parameters=None):
        self.save_as()

    def on_new_window_action_activated(self, action, parameters=None):
        new_window = TextyWindow(application=self.get_application())
        new_window.present()

class TextyApp(Adw.Application):
    def __init__(self, **kwargs):
        """
        Initialize the application.

        This method calls the superclass constructor and then
        connects the activate signal to the on_activate method.
        It also defines some accelerators for actions.
        """
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)
        # Define accelerators for actions
        self.set_accels_for_action("win.new", ["<Control>n"])
        self.set_accels_for_action("win.open", ["<Control>o"])
        self.set_accels_for_action("win.save", ["<Control>s"])
        self.set_accels_for_action("win.save_as", ["<Control><Shift>s"])
        self.set_accels_for_action("win.new_window", ["<Control><Shift>n"])
        self.set_accels_for_action("win.toggle_wrap", ["<Control>w"])

    def on_activate(self, app):
        """
        Handle the application's activate signal.

        This method creates a new TextyWindow and presents it.
        """
        self.win = TextyWindow(application=app)
        self.win.present()

app = TextyApp(application_id="ca.footeware.py.texty")
app.run(sys.argv)