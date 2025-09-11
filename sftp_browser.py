import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import paramiko
import urllib.parse
import os
import sys
from tkinter import filedialog
import stat
import subprocess
import datetime

# Catppuccin Macchiato palette
CATPPUCCIN_PALETTE = {
    "rosewater": "#f4dbd6",
    "flamingo": "#f0c6c6",
    "pink": "#f5bde6",
    "mauve": "#c6a0f6",
    "red": "#ed8796",
    "maroon": "#ee99a0",
    "peach": "#f5a97f",
    "yellow": "#eed49f",
    "green": "#a6da95",
    "teal": "#8bd5ca",
    "sky": "#91d7e3",
    "sapphire": "#7dc4e4",
    "blue": "#8aadf4",
    "lavender": "#b7bdf8",
    "text": "#cad3f5",
    "subtext1": "#b8c0e0",
    "subtext0": "#a5adcb",
    "overlay2": "#939ab7",
    "overlay1": "#8087a2",
    "overlay0": "#6e738d",
    "surface2": "#5b6078",
    "surface1": "#494d64",
    "surface0": "#363a4f",
    "base": "#24273a",
    "mantle": "#1e2030",
    "crust": "#181926",
}


# Custom Toplevel class - simplified for better cross-platform compatibility
# True rounded corners for Toplevel windows are complex and OS-dependent.
# We'll achieve a "softer" look primarily through widget styling.
class ThemedToplevel(tk.Toplevel):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        # Attempt to set background and a slight alpha for the window itself
        self.configure(bg=CATPPUCCIN_PALETTE["crust"])
        try:
            # Alpha for the window (if supported, e.g., on Windows/macOS)
            self.attributes("-alpha", 0.98)
        except tk.TclError:
            pass  # Not supported on all systems/compositors


class LoginDialog(ThemedToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("SFTP Login")
        self.result = None

        # Apply theme colors
        style = ttk.Style(self)
        style.theme_use("alt")  # Using 'alt' for better control

        # Configure styles for dialog widgets
        style.configure(
            "Dialog.TLabel",
            background=CATPPUCCIN_PALETTE["crust"],
            foreground=CATPPUCCIN_PALETTE["text"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Dialog.TEntry",
            fieldbackground=CATPPUCCIN_PALETTE["surface0"],
            foreground=CATPPUCCIN_PALETTE["text"],
            insertcolor=CATPPUCCIN_PALETTE["blue"],
            bordercolor=CATPPUCCIN_PALETTE["surface2"],
            relief="flat",
            borderwidth=1,
            focusthickness=2,
            focuscolor=CATPPUCCIN_PALETTE["blue"],
            padding=(5, 5),
            font=("Segoe UI", 10),
        )
        style.map(
            "Dialog.TEntry",
            fieldbackground=[("focus", CATPPUCCIN_PALETTE["surface1"])],
            bordercolor=[("focus", CATPPUCCIN_PALETTE["blue"])],
        )
        style.configure(
            "Dialog.TButton",
            background=CATPPUCCIN_PALETTE["blue"],
            foreground=CATPPUCCIN_PALETTE["base"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(10, 5),
            bordercolor=CATPPUCCIN_PALETTE["blue"],
            focusthickness=0,
        )
        style.map(
            "Dialog.TButton",
            background=[("active", CATPPUCCIN_PALETTE["lavender"])],
            foreground=[("active", CATPPUCCIN_PALETTE["base"])],
            relief=[("pressed", "sunken"), ("!pressed", "flat")],
        )

        # Main content frame for the dialog
        # Apply padding and background to this frame to create a visual "rounded" inner look
        content_frame = ttk.Frame(self, style="Dialog.TFrame")
        content_frame.pack(padx=15, pady=15, fill=tk.BOTH, expand=True) # Padding within the toplevel window

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Create widgets inside content_frame
        ttk.Label(content_frame, text="Hostname:", style="Dialog.TLabel").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Label(content_frame, text="Port:", style="Dialog.TLabel").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Label(content_frame, text="Username:", style="Dialog.TLabel").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Label(content_frame, text="Password:", style="Dialog.TLabel").grid(
            row=3, column=0, padx=5, pady=5, sticky="w"
        )

        self.hostname = ttk.Entry(content_frame, width=30, style="Dialog.TEntry")
        self.port = ttk.Entry(content_frame, width=30, style="Dialog.TEntry")
        self.username = ttk.Entry(content_frame, width=30, style="Dialog.TEntry")
        self.password = ttk.Entry(content_frame, show="*", width=30, style="Dialog.TEntry")

        self.hostname.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.port.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.username.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.password.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        content_frame.grid_columnconfigure(1, weight=1)

        self.port.insert(0, "22")

        ttk.Button(content_frame, text="Connect", command=self.on_connect, style="Dialog.TButton").grid(
            row=4, column=0, columnspan=2, pady=10
        )

        # Add Quick Connect URL field
        ttk.Label(content_frame, text="Quick Connect URL:", style="Dialog.TLabel").grid(
            row=5, column=0, padx=5, pady=5, sticky="w"
        )
        self.quick_connect_url = ttk.Entry(content_frame, width=40, style="Dialog.TEntry")
        self.quick_connect_url.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(content_frame, text="Go", command=self.on_quick_connect, style="Dialog.TButton").grid(
            row=6, column=0, columnspan=2, pady=5
        )

        # Add Enter key bindings
        self.hostname.bind("<Return>", lambda e: self.port.focus())
        self.port.bind("<Return>", lambda e: self.username.focus())
        self.username.bind("<Return>", lambda e: self.password.focus())
        self.password.bind("<Return>", lambda e: self.on_connect())
        self.quick_connect_url.bind("<Return>", lambda e: self.on_quick_connect())

        # Center the dialog
        self.update_idletasks()  # Update geometry for winfo_width/height
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def on_connect(self):
        self.result = {
            "hostname": self.hostname.get(),
            "port": int(self.port.get()),
            "username": self.username.get(),
            "password": self.password.get(),
        }
        self.destroy()

    def on_quick_connect(self):
        url = self.quick_connect_url.get()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a Quick Connect URL.")
            return

        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme != "sftp":
                raise ValueError("Not an SFTP URL")

            username = urllib.parse.unquote(parsed.username or "")
            password = urllib.parse.unquote(parsed.password or "")
            hostname = parsed.hostname or ""
            port = parsed.port or 22
            path = parsed.path or "/"

            self.result = {
                "hostname": hostname,
                "port": port,
                "username": username,
                "password": password,
                "path": path,
            }
            self.destroy()

        except Exception as e:
            messagebox.showerror("URL Parsing Error", f"Invalid SFTP URL: {e}")
            self.result = None


class SFTPBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("A Very Simple SFTP Browser")
        self.root.geometry("1000x700")  # Increased size for better layout
        self.root.configure(bg=CATPPUCCIN_PALETTE["mantle"])

        self.apply_catppuccin_theme()

        # SFTP client
        self.sftp = None
        self.transport = None

        # Initialize downloads list (persistent across sessions)
        self.downloads = []

        # GUI elements
        self.setup_gui()

        # Register protocol handler
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Don't show login dialog immediately
        self.initial_connect()

    def apply_catppuccin_theme(self):
        style = ttk.Style(self.root)
        style.theme_use("alt")  # 'alt' theme is generally good for customization

        # General background and foreground for certain elements
        self.root.option_add("*TCombobox*Listbox.background", CATPPUCCIN_PALETTE["base"])
        self.root.option_add("*TCombobox*Listbox.foreground", CATPPUCCIN_PALETTE["text"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", CATPPUCCIN_PALETTE["blue"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", CATPPUCCIN_PALETTE["base"])

        # PanedWindow
        style.configure("TPanedwindow", background=CATPPUCCIN_PALETTE["crust"])
        style.map("TPanedwindow", background=[("active", CATPPUCCIN_PALETTE["crust"])])

        # Frames
        style.configure("TFrame", background=CATPPUCCIN_PALETTE["mantle"])
        style.configure("Dialog.TFrame", background=CATPPUCCIN_PALETTE["crust"]) # For LoginDialog content frame
        
        # Labels
        style.configure(
            "TLabel",
            background=CATPPUCCIN_PALETTE["mantle"],
            foreground=CATPPUCCIN_PALETTE["text"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Header.TLabel", # For "Downloaded Files" label
            background=CATPPUCCIN_PALETTE["mantle"],
            foreground=CATPPUCCIN_PALETTE["text"],
            font=("Segoe UI", 12, "bold"),
        )
        
        # Entries
        style.configure(
            "TEntry",
            fieldbackground=CATPPUCCIN_PALETTE["surface0"],
            foreground=CATPPUCCIN_PALETTE["text"],
            insertcolor=CATPPUCCIN_PALETTE["blue"],
            bordercolor=CATPPUCCIN_PALETTE["surface2"],
            relief="flat",
            borderwidth=1,
            focusthickness=2,
            focuscolor=CATPPUCCIN_PALETTE["blue"],
            padding=(5, 5),
            font=("Segoe UI", 10),
        )
        style.map(
            "TEntry",
            fieldbackground=[("focus", CATPPUCCIN_PALETTE["surface1"])],
            bordercolor=[("focus", CATPPUCCIN_PALETTE["blue"])],
        )

        # Buttons
        style.configure(
            "TButton",
            background=CATPPUCCIN_PALETTE["blue"],
            foreground=CATPPUCCIN_PALETTE["base"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(6, 4),
            bordercolor=CATPPUCCIN_PALETTE["blue"],
            focusthickness=0,
        )
        style.map(
            "TButton",
            background=[("active", CATPPUCCIN_PALETTE["lavender"])],
            foreground=[("active", CATPPUCCIN_PALETTE["base"])],
            relief=[("pressed", "sunken"), ("!pressed", "flat")],
        )

        # Treeview (main browser and downloads)
        style.configure(
            "Treeview",
            background=CATPPUCCIN_PALETTE["surface0"],
            foreground=CATPPUCCIN_PALETTE["text"],
            fieldbackground=CATPPUCCIN_PALETTE["surface0"],
            font=("Segoe UI", 10),
            rowheight=25,
            bordercolor=CATPPUCCIN_PALETTE["mantle"], # No visible border
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", CATPPUCCIN_PALETTE["blue"])],
            foreground=[("selected", CATPPUCCIN_PALETTE["base"])],
        )
        style.configure(
            "Treeview.Heading",
            background=CATPPUCCIN_PALETTE["surface1"],
            foreground=CATPPUCCIN_PALETTE["subtext1"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(5, 5),
            bordercolor=CATPPUCCIN_PALETTE["mantle"], # No visible border
        )
        style.map(
            "Treeview.Heading",
            background=[("active", CATPPUCCIN_PALETTE["surface2"])],
        )

        # Custom Scrollbars (No arrows, minimal look)
        # Re-layout the scrollbar to only include the trough and thumb
        style.layout("Vertical.TScrollbar", [
            ("Vertical.Scrollbar.trough", {
                "sticky": "ns",
                "children": [
                    ("Vertical.Scrollbar.thumb", {"expand": 1, "sticky": "nswe"})
                ]
            })
        ])
        style.layout("Horizontal.TScrollbar", [
            ("Horizontal.Scrollbar.trough", {
                "sticky": "ew",
                "children": [
                    ("Horizontal.Scrollbar.thumb", {"expand": 1, "sticky": "nswe"})
                ]
            })
        ])

        # Configure the scrollbar style
        style.configure(
            "TScrollbar",
            background=CATPPUCCIN_PALETTE["crust"], # Background of the scrollbar widget area
            troughcolor=CATPPUCCIN_PALETTE["surface0"], # The track itself
            bordercolor=CATPPUCCIN_PALETTE["crust"],
            relief="flat",
            borderwidth=0,
            arrowsize=0, # This hides default arrows if they were present in the layout
        )
        style.map(
            "TScrollbar",
            background=[("active", CATPPUCCIN_PALETTE["overlay1"])],
        )
        style.configure(
            "TScrollbar.thumb",
            background=CATPPUCCIN_PALETTE["surface2"],
            bordercolor=CATPPUCCIN_PALETTE["surface2"],
            relief="flat",
        )
        style.map(
            "TScrollbar.thumb",
            background=[("active", CATPPUCCIN_PALETTE["overlay2"])],
        )


    def _clear_browser_state(self):
        """Clears the browser's view, path history, and closes the SFTP connection."""
        if self.sftp:
            try:
                self.sftp.close()
            except Exception as e:
                print(f"Error closing SFTP client: {e}")
            self.sftp = None
        if self.transport:
            try:
                self.transport.close()
            except Exception as e:
                print(f"Error closing Paramiko transport: {e}")
            self.transport = None
        
        self.current_path = "/"
        self.path_history = []
        self.path_label.config(text=self.current_path)
        
        for item in self.tree.get_children():
            self.tree.delete(item)

    def initial_connect(self):
        # Check command line args first
        if len(sys.argv) > 1:
            self.connect_sftp(sys.argv[1])
        else:
            self.show_login_dialog()

    def connect_sftp(self, url, retry_count=0):
        # Clear previous session data *before* attempting a new connection
        self._clear_browser_state() 

        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme != "sftp":
                raise ValueError("Not an SFTP URL")

            # Parse credentials and host info
            username = urllib.parse.unquote(parsed.username or "")
            password = urllib.parse.unquote(parsed.password or "")
            hostname = parsed.hostname or ""
            port = parsed.port or 22
            path = parsed.path or "/"

            # If password or username is missing, show login dialog with prefilled fields
            # and the full URL for quick connect re-attempt.
            if not username or not password:
                self.show_login_dialog(
                    hostname=hostname, port=port, username=username, path=path, initial_url=url
                )
                return

            # Connect
            self.transport = paramiko.Transport((hostname, port))
            self.transport.connect(username=username, password=password)
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)

            # Load initial directory
            self.current_path = path
            self.load_directory()

        except paramiko.AuthenticationException:
            # Show login dialog with prefilled fields on auth failure
            if retry_count < 3:
                retry = messagebox.askretrycancel(
                    "Authentication Failed",
                    "Wrong password for provided URL. Would you like to try again?",
                )
                if retry:
                    self.show_login_dialog(
                        hostname=hostname,
                        port=port,
                        username=username,
                        path=path,
                        initial_url=url, # Pass the original URL for potential quick connect retry
                        retry_count=retry_count + 1,
                    )
                else: # If retry cancelled, go to generic login
                    self.show_login_dialog()
            else:
                messagebox.showerror(
                    "Error",
                    "Maximum password attempts exceeded. Please try again from the New Connection dialog.",
                )
                self.show_login_dialog()  # Fall back to generic login
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.show_login_dialog()  # Fall back to generic login

    def show_login_dialog(self, hostname="", port=22, username="", path="/", initial_url="", retry_count=0):
        dialog = LoginDialog(self.root)
        if hostname:
            dialog.hostname.insert(0, hostname)
        if port:
            dialog.port.delete(0, tk.END)
            dialog.port.insert(0, str(port))
        if username:
            dialog.username.insert(0, username)
        if initial_url:  # Pre-fill quick connect URL if we are retrying
            dialog.quick_connect_url.insert(0, initial_url)

        self.root.wait_window(dialog)

        if dialog.result:
            # Clear previous session state *before* attempting new connection
            self._clear_browser_state()

            if "path" in dialog.result:  # Result from quick connect URL
                # Reconstruct URL to include password if provided
                url_to_connect = (
                    f"sftp://{dialog.result['username']}"
                    f"{':' + dialog.result['password'] if dialog.result['password'] else ''}"
                    f"@{dialog.result['hostname']}:{dialog.result['port']}"
                    f"{dialog.result['path']}"
                )
                self.connect_sftp(url_to_connect, retry_count=retry_count)
            else:  # Result from manual entry
                self.connect_manual(
                    dialog.result["hostname"],
                    dialog.result["port"],
                    dialog.result["username"],
                    dialog.result["password"],
                    retry_count=retry_count,
                )
        elif retry_count > 0:  # If we cancelled a retry, ensure connection is cleared
            self._clear_browser_state()

    def setup_gui(self):
        # Main container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL, style="TPanedwindow")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10) # Increased padding

        # Left side (main browser)
        left_frame = ttk.Frame(main_container, style="TFrame")
        main_container.add(left_frame, weight=3)

        # Navigation frame
        nav_frame = ttk.Frame(left_frame, style="TFrame")
        nav_frame.pack(fill=tk.X, padx=10, pady=5) # Increased padding

        self.back_btn = ttk.Button(nav_frame, text="← Back", command=self.go_back)
        self.back_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.path_label = ttk.Label(nav_frame, text="/", anchor="w")
        self.path_label.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        ttk.Button(
            nav_frame, text="New Connection", command=self.show_login_dialog
        ).pack(side=tk.RIGHT, padx=(5, 0))

        self.download_dir_btn = ttk.Button(
            nav_frame, text="Download Directory", command=self.download_current_directory
        )
        self.download_dir_btn.pack(side=tk.RIGHT, padx=5)

        # Main treeview
        self.tree = ttk.Treeview(left_frame, columns=("size", "date"), style="Treeview")
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("size", text="Size", anchor="w")
        self.tree.heading("date", text="Date Modified", anchor="w")

        # Set column widths (adjust as needed)
        self.tree.column("#0", width=300, minwidth=150, stretch=tk.YES)
        self.tree.column("size", width=120, minwidth=80, stretch=tk.NO)
        self.tree.column("date", width=180, minwidth=100, stretch=tk.NO)
        
        # Add scrollbars for the main tree
        tree_scroll_y = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview, style="TScrollbar")
        tree_scroll_x = ttk.Scrollbar(left_frame, orient=tk.HORIZONTAL, command=self.tree.xview, style="TScrollbar")
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        # Scrollbars will only appear when necessary due to Treeview's internal logic
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=(0, 10))
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X, padx=(10, 0), pady=(0, 10))
        self.tree.pack(fill=tk.BOTH, expand=True, padx=(10, 0), pady=(0, 0)) # Place tree after scrollbars for correct layout

        # Right side (downloads sidebar)
        right_frame = ttk.Frame(main_container, style="TFrame")
        main_container.add(right_frame, weight=1)

        # Downloads label
        ttk.Label(right_frame, text="Downloaded Files", style="Header.TLabel").pack(
            pady=10
        )

        # Downloads treeview
        self.downloads_tree = ttk.Treeview(right_frame, columns=("local_path", "time"), style="Treeview")
        self.downloads_tree.heading("#0", text="Remote Path", anchor="w")
        self.downloads_tree.heading("local_path", text="Local Path", anchor="w")
        self.downloads_tree.heading("time", text="Time", anchor="w")

        # Set column widths for downloads tree
        self.downloads_tree.column("#0", width=150, minwidth=100, stretch=tk.YES)
        self.downloads_tree.column("local_path", width=150, minwidth=100, stretch=tk.YES)
        self.downloads_tree.column("time", width=80, minwidth=60, stretch=tk.NO)
        
        # Add scrollbars for downloads tree
        downloads_tree_scroll_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.downloads_tree.yview, style="TScrollbar")
        downloads_tree_scroll_x = ttk.Scrollbar(right_frame, orient=tk.HORIZONTAL, command=self.downloads_tree.xview, style="TScrollbar")
        self.downloads_tree.configure(yscrollcommand=downloads_tree_scroll_y.set, xscrollcommand=downloads_tree_scroll_x.set)
        
        # Scrollbars will only appear when necessary
        downloads_tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=(0, 10))
        downloads_tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X, padx=(10, 0), pady=(0, 10))
        self.downloads_tree.pack(fill=tk.BOTH, expand=True, padx=(10, 0), pady=(0, 0)) # Place tree after scrollbars

        # Buttons for downloaded files
        btn_frame = ttk.Frame(right_frame, style="TFrame")
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="Open File", command=self.open_selected_file).pack(
            side=tk.LEFT, padx=(0, 2), expand=True, fill=tk.X
        )
        ttk.Button(
            btn_frame, text="Open Folder", command=self.open_containing_folder
        ).pack(side=tk.LEFT, padx=(2, 0), expand=True, fill=tk.X)

        self.current_path = "/"
        self.path_history = []

    def connect_manual(self, hostname, port, username, password, retry_count=0):
        # Clear previous session data *before* attempting a new connection
        self._clear_browser_state()

        try:
            self.transport = paramiko.Transport((hostname, port))
            self.transport.connect(username=username, password=password)
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)
            self.current_path = "/"
            self.path_history = []
            self.load_directory()
        except paramiko.AuthenticationException:
            if retry_count < 3:  # Allow 3 password attempts
                retry = messagebox.askretrycancel(
                    "Authentication Failed",
                    "Wrong password. Would you like to try again?",
                )
                if retry:
                    dialog = LoginDialog(self.root)
                    dialog.hostname.insert(0, hostname)
                    dialog.port.delete(0, tk.END)
                    dialog.port.insert(0, str(port))
                    dialog.username.insert(0, username)
                    self.root.wait_window(dialog)
                    if dialog.result:
                        # Ensure to clear previous session state before new connection attempt
                        self._clear_browser_state()
                        if "path" in dialog.result:  # If they tried quick connect during retry
                            self.connect_sftp(
                                f"sftp://{dialog.result['username']}:{dialog.result['password']}@"
                                f"{dialog.result['hostname']}:{dialog.result['port']}{dialog.result['path']}",
                                retry_count=retry_count + 1,
                            )
                        else:  # Regular manual retry
                            self.connect_manual(
                                dialog.result["hostname"],
                                dialog.result["port"],
                                dialog.result["username"],
                                dialog.result["password"],
                                retry_count=retry_count + 1,
                            )
                else: # If retry cancelled, clear state and return
                    self._clear_browser_state()
            else:
                messagebox.showerror(
                    "Error",
                    "Maximum password attempts exceeded. Please try again from the New Connection dialog.",
                )
                self._clear_browser_state() # Clear connection state

        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self._clear_browser_state() # Clear connection state

    def load_directory(self):
        if not self.sftp:
            # Only show error if it's not during an intentional clear_browser_state (i.e., current_path is not '/')
            if self.current_path != "/":
                messagebox.showerror("Error", "Not connected to SFTP server or connection lost.")
            self._clear_browser_state() # Ensure consistent state
            return

        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Update path label
        self.path_label.config(text=self.current_path)

        # List directory contents
        try:
            for entry in self.sftp.listdir_attr(self.current_path):
                name = entry.filename
                # Skip '.' and '..' for cleaner display, relying on back button for navigation
                if name in (".", ".."):
                    continue

                size = "Directory" if stat.S_ISDIR(entry.st_mode) else f"{entry.st_size:,} bytes"

                # Format date
                date_obj = datetime.datetime.fromtimestamp(entry.st_mtime)
                date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")

                self.tree.insert("", "end", text=name, values=(size, date_str))
        except IOError as e:
            messagebox.showerror(
                "SFTP Error", f"Cannot access directory {self.current_path}: {e}"
            )
            # Try to go back if current_path is invalid
            self.go_back()
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            self.go_back()

    def go_back(self):
        if self.path_history:
            self.current_path = self.path_history.pop()
            self.load_directory()
            self.path_label.config(text=self.current_path)
        elif self.current_path != "/":  # If at root and no history, try to go up
            parent_path = os.path.dirname(self.current_path)
            if parent_path == "":  # Handle cases like /folder -> /
                parent_path = "/"
            if parent_path != self.current_path:  # Prevent infinite loop if already at actual root
                self.current_path = parent_path
                self.load_directory()
                self.path_label.config(text=self.current_path)

    def on_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return

        item = item[0]
        filename = self.tree.item(item, "text")

        # Construct the new path, ensuring it's always an absolute path
        if self.current_path == "/":
            filepath = "/" + filename
        else:
            filepath = os.path.join(self.current_path, filename).replace("\\", "/")

        try:
            sftp_stat = self.sftp.stat(filepath)
            # Check if it's a directory
            if stat.S_ISDIR(sftp_stat.st_mode):
                self.path_history.append(self.current_path)
                self.current_path = filepath
                self.load_directory()
                self.path_label.config(text=self.current_path)
            else:
                self.download_file(filepath, filename)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_to_downloads(self, remote_path, local_path):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.downloads.append((remote_path, local_path, timestamp))
        self.downloads_tree.insert(
            "", 0, text=remote_path, values=(local_path, timestamp)
        )

    def open_selected_file(self):
        selection = self.downloads_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a downloaded file to open.")
            return

        local_path = self.downloads_tree.item(selection[0])["values"][0]
        try:
            if sys.platform == "win32":
                os.startfile(local_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["open", local_path])
            else:  # Linux and other Unix-like systems
                subprocess.run(["xdg-open", local_path])
        except Exception as e:
            messagebox.showerror("Error Opening File", f"Could not open file: {e}")

    def open_containing_folder(self):
        selection = self.downloads_tree.selection()
        if not selection:
            messagebox.showwarning(
                "No Selection", "Please select a downloaded file to open its folder."
            )
            return

        local_path = self.downloads_tree.item(selection[0])["values"][0]
        folder_path = os.path.dirname(local_path)

        if not os.path.exists(folder_path):
            messagebox.showerror("Error", "Containing folder does not exist.")
            return

        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux and other Unix-like systems
                subprocess.run(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("Error Opening Folder", f"Could not open folder: {e}")

    def download_file(self, filepath, filename):
        save_path = filedialog.asksaveasfilename(
            defaultextension="", initialfile=filename
        )
        if save_path:
            try:
                self.sftp.get(filepath, save_path)
                self.add_to_downloads(filepath, save_path)
                messagebox.showinfo("Success", "File downloaded successfully!")
            except Exception as e:
                messagebox.showerror("Download Error", str(e))

    def download_current_directory(self):
        if not self.sftp:
            messagebox.showerror("Error", "Not connected to SFTP server.")
            return

        save_dir = filedialog.askdirectory(
            title=f"Select Local Directory to Save '{os.path.basename(self.current_path)}'"
        )
        if save_dir:
            try:
                # Create a subdirectory within save_dir for the remote folder's contents
                remote_folder_name = os.path.basename(self.current_path.rstrip("/"))
                if not remote_folder_name:  # Handle root directory
                    remote_folder_name = "SFTP_Root"

                target_local_dir = os.path.join(save_dir, remote_folder_name)

                self.download_directory_recursive(self.current_path, target_local_dir)
                messagebox.showinfo(
                    "Success",
                    f"Directory '{self.current_path}' downloaded successfully to '{target_local_dir}'!",
                )
            except Exception as e:
                messagebox.showerror("Download Error", str(e))

    def download_directory_recursive(self, remote_dir, local_dir):
        os.makedirs(local_dir, exist_ok=True)
        for entry in self.sftp.listdir_attr(remote_dir):
            filename = entry.filename
            if filename in (".", ".."):
                continue  # Skip current and parent directory entries

            remote_path = os.path.join(remote_dir, filename).replace("\\", "/")
            local_path = os.path.join(local_dir, filename)

            if stat.S_ISDIR(entry.st_mode):
                self.download_directory_recursive(remote_path, local_path)
            else:
                self.sftp.get(remote_path, local_path)
                self.add_to_downloads(remote_path, local_path)

    def on_closing(self):
        if self.sftp:
            self.sftp.close()
        if self.transport:
            self.transport.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = SFTPBrowser(root)
    root.mainloop()


if __name__ == "__main__":
    main()