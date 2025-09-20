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
import threading
import time
import platform
import sv_ttk

class ThemedToplevel(tk.Toplevel):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        try:
            self.attributes("-alpha", 0.95)
        except tk.TclError:
            pass

class SFTPBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("SFTP Browser")
        self.root.geometry("1400x900")

        # Apply Sun Valley theme
        sv_ttk.set_theme("light")  # Start with light theme

        # SFTP client
        self.sftp = None
        self.transport = None
        self.current_path = "/"
        self.path_history = []

        # Progress tracking
        self.current_operation = None
        self.progress_var = tk.DoubleVar()
        self.progress_text = tk.StringVar(value="Ready")

        # Connection panel state
        self.connection_expanded = True

        # Downloads tracking
        self.downloads = []

        # Directory download progress tracking
        self.download_stats = {
            'total_files': 0,
            'downloaded_files': 0,
            'total_size': 0,
            'downloaded_size': 0
        }

        # GUI elements
        self.setup_gui()

        # Register protocol handler
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Check for initial connection
        self.initial_connect()

    def setup_gui(self):
        # Main container with Sun Valley spacing
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Main content area with sidebar
        content_paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        content_paned.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Left side - File browser
        browser_frame = ttk.Frame(content_paned)
        content_paned.add(browser_frame, weight=3)

        # Right side - Downloads sidebar
        sidebar_frame = ttk.Frame(content_paned)
        content_paned.add(sidebar_frame, weight=1)
        self.setup_sidebar(sidebar_frame)

        # Navigation frame with integrated buttons
        nav_frame = ttk.Frame(browser_frame)
        nav_frame.pack(fill=tk.X, padx=8, pady=8)

        # Back button
        self.back_btn = ttk.Button(nav_frame, text="◀ Back", 
                                 command=self.go_back, 
                                 state=tk.DISABLED)
        self.back_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Path label
        self.path_label = ttk.Label(nav_frame, text="Not Connected", font=('Segoe UI', 10))
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Action buttons integrated into navigation
        self.refresh_btn = ttk.Button(nav_frame, text="🔄 Refresh", 
                                    command=self.refresh_directory, 
                                    state=tk.DISABLED)
        self.refresh_btn.pack(side=tk.RIGHT, padx=(4, 0))

        self.download_btn = ttk.Button(nav_frame, text="⬇ Download Selected", 
                                     command=self.download_selected, 
                                     state=tk.DISABLED)
        self.download_btn.pack(side=tk.RIGHT, padx=(0, 4))

        # File browser
        browser_container = ttk.Frame(browser_frame)
        browser_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self.tree = ttk.Treeview(browser_container, columns=("size", "modified", "permissions"), show="tree headings", selectmode="extended")
        self.tree.heading("#0", text="Name", anchor="c")
        self.tree.heading("size", text="Size", anchor="c")
        self.tree.heading("modified", text="Modified", anchor="c")
        self.tree.heading("permissions", text="Permissions", anchor="c")

        self.tree.column("#0", width=300, anchor="w")
        self.tree.column("size", width=100, anchor="c")
        self.tree.column("modified", width=140, anchor="c")
        self.tree.column("permissions", width=100, anchor="c")

        # Scrollbars for treeview
        tree_scroll_y = ttk.Scrollbar(browser_container, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(browser_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        tree_scroll_x.grid(row=1, column=0, sticky="ew")

        browser_container.grid_rowconfigure(0, weight=1)
        browser_container.grid_columnconfigure(0, weight=1)

        # Bind events
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Return>", self.on_double_click)
        
        # Add context menu for multi-select operations
        self.browser_menu = tk.Menu(self.root, tearoff=0, font=('Segoe UI', 9))
        self.browser_menu.add_command(label="Download Selected", command=self.download_selected)
        self.browser_menu.add_separator()
        self.browser_menu.add_command(label="Select All", command=self.select_all)
        self.browser_menu.add_command(label="Clear Selection", command=self.clear_selection)
        
        self.tree.bind("<Button-3>", self.show_browser_context_menu)
        self.tree.bind("<Control-a>", self.select_all)
        self.tree.bind("<Escape>", self.clear_selection)

        # Bottom section - Connection panel
        self.setup_connection_panel(main_frame)

        # Progress bar section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X)

        progress_content = ttk.Frame(progress_frame)
        progress_content.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(progress_content, textvariable=self.progress_text, font=('Segoe UI', 9)).pack(side=tk.LEFT)

        self.progress_bar = ttk.Progressbar(progress_content, variable=self.progress_var, mode='determinate')
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(8, 0))

    def setup_sidebar(self, parent):
        """Setup the downloads sidebar"""
        # Header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, padx=6, pady=6)

        ttk.Label(header_frame, text="Downloads", font=('Segoe UI', 12, 'bold')).pack(side=tk.LEFT)

        self.clear_btn = ttk.Button(header_frame, text="🗑 Clear", 
                                  command=self.clear_downloads)
        self.clear_btn.pack(side=tk.RIGHT)

        # Downloads list
        downloads_container = ttk.Frame(parent)
        downloads_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

        self.downloads_tree = ttk.Treeview(downloads_container, columns=("size",), show="tree headings", height=10)
        self.downloads_tree.heading("#0", text="File", anchor="c")
        self.downloads_tree.heading("size", text="Size", anchor="c")
        
        self.downloads_tree.column("#0", width=180, anchor="c")
        self.downloads_tree.column("size", width=60, anchor="e")

        # Scrollbar for downloads
        downloads_scroll = ttk.Scrollbar(downloads_container, orient=tk.VERTICAL, command=self.downloads_tree.yview)
        self.downloads_tree.configure(yscrollcommand=downloads_scroll.set)

        self.downloads_tree.grid(row=0, column=0, sticky="nsew")
        downloads_scroll.grid(row=0, column=1, sticky="ns")

        downloads_container.grid_rowconfigure(0, weight=1)
        downloads_container.grid_columnconfigure(0, weight=1)

        # Bind double-click to open file
        self.downloads_tree.bind("<Double-1>", self.open_downloaded_file)

        # Context menu for downloads
        self.downloads_menu = tk.Menu(self.root, tearoff=0, font=('Segoe UI', 9))
        self.downloads_menu.add_command(label="Open File", command=self.open_downloaded_file)
        self.downloads_menu.add_command(label="Show in Folder", command=self.show_in_folder)
        self.downloads_menu.add_separator()
        self.downloads_menu.add_command(label="Remove from List", command=self.remove_from_downloads)

        self.downloads_tree.bind("<Button-3>", self.show_downloads_context_menu)

    def setup_connection_panel(self, parent):
        # Connection panel container
        connection_container = ttk.Frame(parent)
        connection_container.pack(fill=tk.X, pady=(0, 8))

        # Header with toggle button
        header_frame = ttk.Frame(connection_container)
        header_frame.pack(fill=tk.X, padx=8, pady=6)

        self.toggle_btn = ttk.Button(header_frame, text="▼ Connection", 
                                   command=self.toggle_connection_panel)
        self.toggle_btn.pack(side=tk.LEFT)

        self.disconnect_btn = ttk.Button(header_frame, text="🔌 Disconnect", 
                                       command=self.disconnect, 
                                       state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.RIGHT)

        # Connection content (collapsible)
        self.connection_content = ttk.Frame(connection_container)
        
        # Manual connection section
        manual_frame = ttk.LabelFrame(self.connection_content, text="Manual Connection", padding=8)
        manual_frame.pack(fill=tk.X, padx=8, pady=(0, 6))

        # Grid layout for manual connection
        ttk.Label(manual_frame, text="Host:", font=('Segoe UI', 8)).grid(row=0, column=0, sticky="w", padx=(0, 4), pady=2)
        self.hostname_entry = ttk.Entry(manual_frame, width=20)
        self.hostname_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=2)

        ttk.Label(manual_frame, text="Port:", font=('Segoe UI', 8)).grid(row=0, column=2, sticky="w", padx=(0, 4), pady=2)
        self.port_entry = ttk.Entry(manual_frame, width=6)
        self.port_entry.grid(row=0, column=3, sticky="ew", padx=(0, 10), pady=2)
        self.port_entry.insert(0, "22")

        ttk.Label(manual_frame, text="User:", font=('Segoe UI', 8)).grid(row=1, column=0, sticky="w", padx=(0, 4), pady=2)
        self.username_entry = ttk.Entry(manual_frame, width=20)
        self.username_entry.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=2)

        ttk.Label(manual_frame, text="Pass:", font=('Segoe UI', 8)).grid(row=1, column=2, sticky="w", padx=(0, 4), pady=2)
        self.password_entry = ttk.Entry(manual_frame, show="*", width=20)
        self.password_entry.grid(row=1, column=3, sticky="ew", pady=2)

        self.connect_btn = ttk.Button(manual_frame, text="🔗 Connect", 
                                    command=self.connect_manual_gui)
        self.connect_btn.grid(row=2, column=0, columnspan=4, pady=6)

        manual_frame.grid_columnconfigure(1, weight=1)
        manual_frame.grid_columnconfigure(3, weight=1)

        # Quick connect section
        quick_frame = ttk.LabelFrame(self.connection_content, text="Quick Connect", padding=8)
        quick_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        ttk.Label(quick_frame, text="SFTP URL:", font=('Segoe UI', 8)).pack(anchor="w", pady=(0, 2))
        
        url_frame = ttk.Frame(quick_frame)
        url_frame.pack(fill=tk.X, pady=(0, 4))
        
        self.url_entry = ttk.Entry(url_frame, font=('Consolas', 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        
        self.go_btn = ttk.Button(url_frame, text="🚀 Go", 
                               command=self.connect_url_gui)
        self.go_btn.pack(side=tk.RIGHT)

        ttk.Label(quick_frame, text="Format: sftp://user:pass@host:port/path", 
                 font=('Segoe UI', 8)).pack(anchor="w")

        # Bind Enter keys
        self.hostname_entry.bind("<Return>", lambda e: self.port_entry.focus())
        self.port_entry.bind("<Return>", lambda e: self.username_entry.focus())
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        self.password_entry.bind("<Return>", lambda e: self.connect_manual_gui())
        self.url_entry.bind("<Return>", lambda e: self.connect_url_gui())

        # Show connection panel by default
        self.show_connection_panel()

    def toggle_connection_panel(self):
        if self.connection_expanded:
            self.hide_connection_panel()
        else:
            self.show_connection_panel()

    def show_connection_panel(self):
        self.connection_content.pack(fill=tk.X, padx=0, pady=(0, 8))
        self.toggle_btn.config(text="▼ Connection")
        self.connection_expanded = True

    def hide_connection_panel(self):
        self.connection_content.pack_forget()
        self.toggle_btn.config(text="▶ Connection")
        self.connection_expanded = False

    def update_ui_state(self, connected=False):
        """Update UI elements based on connection state"""
        if connected:
            # Enable browser controls
            self.back_btn.config(state=tk.NORMAL)
            self.refresh_btn.config(state=tk.NORMAL)
            self.download_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.NORMAL)
            
            # Disable connection controls
            self.connect_btn.config(state=tk.DISABLED)
            self.go_btn.config(state=tk.DISABLED)
            self.hostname_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.username_entry.config(state=tk.DISABLED)
            self.password_entry.config(state=tk.DISABLED)
            self.url_entry.config(state=tk.DISABLED)
            
            # Hide connection panel when connected
            if self.connection_expanded:
                self.hide_connection_panel()
        else:
            # Disable browser controls
            self.back_btn.config(state=tk.DISABLED)
            self.refresh_btn.config(state=tk.DISABLED)
            self.download_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.DISABLED)
            
            # Enable connection controls
            self.connect_btn.config(state=tk.NORMAL)
            self.go_btn.config(state=tk.NORMAL)
            self.hostname_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            self.username_entry.config(state=tk.NORMAL)
            self.password_entry.config(state=tk.NORMAL)
            self.url_entry.config(state=tk.NORMAL)
            
            # Show connection panel when disconnected
            if not self.connection_expanded:
                self.show_connection_panel()

    def update_progress(self, value=0, text="Ready"):
        """Update progress bar and status text"""
        self.progress_var.set(value)
        self.progress_text.set(text)
        self.root.update_idletasks()

    def _clear_browser_state(self):
        """Clears the browser's view, path history, and closes the SFTP connection."""
        if self.sftp:
            try:
                self.sftp.close()
            except Exception:
                pass
            self.sftp = None
        if self.transport:
            try:
                self.transport.close()
            except Exception:
                pass
            self.transport = None
        
        self.current_path = "/"
        self.path_history = []
        self.path_label.config(text="Not Connected")
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.update_ui_state(connected=False)
        self.update_progress(0, "Disconnected")

    def connect_manual_gui(self):
        """Connect using manual entry fields"""
        hostname = self.hostname_entry.get().strip()
        port = self.port_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not all([hostname, port, username, password]):
            messagebox.showwarning("Input Error", "Please fill in all connection fields.")
            return

        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("Input Error", "Port must be a number.")
            return

        self.connect_manual(hostname, port, username, password)

    def connect_url_gui(self):
        """Connect using URL entry"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter an SFTP URL.")
            return

        self.connect_sftp(url)

    def connect_manual(self, hostname, port, username, password, retry_count=0):
        """Connect to SFTP server with manual credentials"""
        self._clear_browser_state()
        
        def connect_thread():
            try:
                self.update_progress(25, f"Connecting to {hostname}...")
                
                self.transport = paramiko.Transport((hostname, port))
                self.update_progress(50, "Authenticating...")
                
                self.transport.connect(username=username, password=password)
                self.sftp = paramiko.SFTPClient.from_transport(self.transport)
                
                self.update_progress(75, "Loading directory...")
                self.current_path = "/"
                
                # Switch to main thread for UI updates
                self.root.after(0, lambda: self.finish_connection())
                
            except paramiko.AuthenticationException:
                self.root.after(0, lambda: self.handle_auth_error(hostname, port, username, retry_count))
            except Exception as e:
                self.root.after(0, lambda: self.handle_connection_error(str(e)))

        threading.Thread(target=connect_thread, daemon=True).start()

    def finish_connection(self):
        """Finish connection setup in main thread"""
        try:
            self.load_directory()
            self.update_ui_state(connected=True)
            self.update_progress(100, f"Connected to {self.hostname_entry.get()}")
            
            # Clear password for security
            self.password_entry.delete(0, tk.END)
            
        except Exception as e:
            self.handle_connection_error(str(e))

    def handle_auth_error(self, hostname, port, username, retry_count):
        """Handle authentication errors"""
        self._clear_browser_state()
        if retry_count < 3:
            retry = messagebox.askretrycancel(
                "Authentication Failed",
                "Invalid credentials. Would you like to try again?"
            )
            if retry:
                self.password_entry.delete(0, tk.END)
                self.password_entry.focus()
                return
        
        messagebox.showerror("Authentication Failed", "Unable to authenticate with provided credentials.")
        self.update_progress(0, "Authentication failed")

    def handle_connection_error(self, error_msg):
        """Handle general connection errors"""
        self._clear_browser_state()
        messagebox.showerror("Connection Error", f"Failed to connect: {error_msg}")
        self.update_progress(0, "Connection failed")

    def connect_sftp(self, url, retry_count=0):
        """Connect using SFTP URL"""
        self._clear_browser_state()

        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme != "sftp":
                raise ValueError("URL must start with 'sftp://'")

            username = urllib.parse.unquote(parsed.username or "")
            password = urllib.parse.unquote(parsed.password or "")
            hostname = parsed.hostname or ""
            port = parsed.port or 22
            path = parsed.path or "/"

            if not username or not password or not hostname:
                raise ValueError("URL must include username, password, and hostname")

            # Fill in the manual fields for reference
            self.hostname_entry.delete(0, tk.END)
            self.hostname_entry.insert(0, hostname)
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, str(port))
            self.username_entry.delete(0, tk.END)
            self.username_entry.insert(0, username)

            def connect_thread():
                try:
                    self.update_progress(25, f"Connecting to {hostname}...")
                    
                    self.transport = paramiko.Transport((hostname, port))
                    self.update_progress(50, "Authenticating...")
                    
                    self.transport.connect(username=username, password=password)
                    self.sftp = paramiko.SFTPClient.from_transport(self.transport)
                    
                    self.update_progress(75, "Loading directory...")
                    self.current_path = path
                    
                    self.root.after(0, lambda: self.finish_connection())
                    
                except paramiko.AuthenticationException:
                    self.root.after(0, lambda: self.handle_auth_error(hostname, port, username, retry_count))
                except Exception as e:
                    self.root.after(0, lambda: self.handle_connection_error(str(e)))

            threading.Thread(target=connect_thread, daemon=True).start()

        except Exception as e:
            messagebox.showerror("URL Error", f"Invalid SFTP URL: {e}")
            self.update_progress(0, "Invalid URL")

    def disconnect(self):
        """Disconnect from SFTP server"""
        self._clear_browser_state()
        
        # Clear connection fields
        self.hostname_entry.delete(0, tk.END)
        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, "22")
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.url_entry.delete(0, tk.END)

    def normalize_path(self, *parts):
        """Properly normalize SFTP paths"""
        # Join parts and convert backslashes to forward slashes
        path = "/".join(str(part) for part in parts if part)
        
        # Replace multiple slashes with single slash
        while "//" in path:
            path = path.replace("//", "/")
        
        # Ensure it starts with /
        if not path.startswith("/"):
            path = "/" + path
            
        return path

    def load_directory(self):
        """Load directory contents"""
        if not self.sftp:
            return

        try:
            # Clear current items
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Update path display
            self.path_label.config(text=self.current_path)

            # List directory contents
            items = self.sftp.listdir_attr(self.current_path)
            
            # Sort items: directories first, then files
            items.sort(key=lambda x: (not stat.S_ISDIR(x.st_mode), x.filename.lower()))

            for item in items:
                is_dir = stat.S_ISDIR(item.st_mode)
                icon = "📁" if is_dir else "📄"
                
                # Format size
                if is_dir:
                    size = "<DIR>"
                else:
                    size = self.format_size(item.st_size)
                
                # Format date
                try:
                    modified = datetime.datetime.fromtimestamp(item.st_mtime).strftime("%Y-%m-%d %H:%M")
                except (OSError, ValueError):
                    modified = "Unknown"
                
                # Format permissions
                permissions = stat.filemode(item.st_mode)

                self.tree.insert("", tk.END, text=f"{icon} {item.filename}", 
                                values=(size, modified, permissions))

        except Exception as e:
            messagebox.showerror("Directory Error", f"Failed to load directory: {e}")

    def format_size(self, size):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def on_double_click(self, event=None):
        """Handle double click on tree item"""
        if not self.sftp:
            return

        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        item_text = self.tree.item(item, "text")
        filename = item_text.split(" ", 1)[1]  # Remove icon

        try:
            # Get file attributes
            item_path = self.normalize_path(self.current_path, filename)
            attrs = self.sftp.stat(item_path)
            
            if stat.S_ISDIR(attrs.st_mode):
                # It's a directory, navigate to it
                self.navigate_to_directory(filename)
            else:
                # It's a file, download it
                self.download_file(filename)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to access item: {e}")

    def navigate_to_directory(self, dirname):
        """Navigate to a directory"""
        if not self.sftp:
            return

        try:
            # Save current path to history
            self.path_history.append(self.current_path)
            
            # Update current path
            self.current_path = self.normalize_path(self.current_path, dirname)
            
            self.load_directory()
            self.update_progress(0, f"Browsing: {self.current_path}")

        except Exception as e:
            # Restore previous path if navigation fails
            if self.path_history:
                self.current_path = self.path_history.pop()
            messagebox.showerror("Navigation Error", f"Cannot access directory: {e}")

    def go_back(self):
        """Go back to previous directory"""
        if not self.sftp or not self.path_history:
            return

        self.current_path = self.path_history.pop()
        self.load_directory()
        self.update_progress(0, f"Browsing: {self.current_path}")

    def refresh_directory(self):
        """Refresh current directory"""
        if not self.sftp:
            return
            
        self.load_directory()
        self.update_progress(0, f"Refreshed: {self.current_path}")

    def show_browser_context_menu(self, event):
        """Show context menu for browser items"""
        # Select item under cursor if not already selected
        item = self.tree.identify_row(event.y)
        if item and item not in self.tree.selection():
            self.tree.selection_set(item)
        
        # Update menu labels based on selection
        selection_count = len(self.tree.selection())
        if selection_count == 0:
            self.browser_menu.entryconfig(0, label="Download Selected", state="disabled")
        elif selection_count == 1:
            self.browser_menu.entryconfig(0, label="Download Selected", state="normal")
        else:
            self.browser_menu.entryconfig(0, label=f"Download {selection_count} Items", state="normal")
        
        self.browser_menu.post(event.x_root, event.y_root)

    def select_all(self, event=None):
        """Select all items in the current directory"""
        if not self.sftp:
            return "break"  # Prevent default handling
        
        for child in self.tree.get_children():
            self.tree.selection_add(child)
        return "break"

    def clear_selection(self, event=None):
        """Clear all selections"""
        self.tree.selection_remove(*self.tree.selection())
        return "break"

    def download_selected(self):
        """Download selected files and directories"""
        if not self.sftp:
            return

        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select files or directories to download.")
            return

        # Choose local save location for all downloads
        local_dir = filedialog.askdirectory(title="Choose directory to save downloads to...")
        if not local_dir:
            return

        # Process each selected item
        for item in selection:
            item_text = self.tree.item(item, "text")
            filename = item_text.split(" ", 1)[1]  # Remove icon
            
            # Check if it is a directory
            if item_text.startswith("📁"):
                self.download_directory_to_path(filename, local_dir)
            else:
                self.download_file_to_path(filename, local_dir)

    def download_file_to_path(self, filename, local_dir):
        """Download a file to a specific local directory"""
        if not self.sftp:
            return

        try:
            # Construct remote path
            remote_path = self.normalize_path(self.current_path, filename)
            
            # Create local file path
            local_path = os.path.join(local_dir, filename)

            # Start download in separate thread
            def download_thread():
                try:
                    # Get file size for progress tracking
                    file_attrs = self.sftp.stat(remote_path)
                    file_size = file_attrs.st_size
                    
                    self.root.after(0, lambda: self.update_progress(0, f"Downloading {filename}..."))
                    
                    def progress_callback(transferred, total):
                        if total > 0:
                            progress = (transferred / total) * 100
                            self.root.after(0, lambda: self.update_progress(
                                progress, 
                                f"Downloading {filename}: {self.format_size(transferred)}/{self.format_size(total)}"
                            ))

                    # Download file with progress callback
                    self.sftp.get(remote_path, local_path, callback=progress_callback)
                    
                    # Add to downloads list
                    download_info = {
                        "filename": filename,
                        "local_path": local_path,
                        "remote_path": remote_path,
                        "size": file_size,
                        "timestamp": datetime.datetime.now(),
                        "is_directory": False
                    }
                    self.downloads.append(download_info)
                    
                    # Update downloads sidebar
                    self.root.after(0, lambda: self.update_downloads_list())
                    self.root.after(0, lambda: self.update_progress(100, f"Downloaded {filename} successfully"))
                    
                except Exception as e:
                    self.root.after(0, lambda error=str(e): messagebox.showerror("Download Error", f"Failed to download file {filename}: {error}"))

            threading.Thread(target=download_thread, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to initiate download of {filename}: {e}")

    def download_directory_to_path(self, dirname, local_dir):
        """Download a directory to a specific local directory"""
        if not self.sftp:
            return

        try:
            # Create local directory path
            local_path = os.path.join(local_dir, dirname)
            os.makedirs(local_path, exist_ok=True)

            # Remote directory path
            remote_path = self.normalize_path(self.current_path, dirname)

            # Start download in separate thread
            def download_thread():
                try:
                    # First, scan the directory structure
                    self.root.after(0, lambda: self.update_progress(5, f"Scanning directory {dirname}..."))
                    
                    total_files, total_size, file_list = self.scan_directory_structure(remote_path)
                    
                    # Initialize download stats
                    self.download_stats = {
                        "total_files": total_files,
                        "downloaded_files": 0,
                        "total_size": total_size,
                        "downloaded_size": 0
                    }
                    
                    self.root.after(0, lambda: self.update_progress(10, f"Found {total_files} files ({self.format_size(total_size)}) - Starting download..."))
                    
                    # Download the directory recursively
                    self._download_directory_recursive(remote_path, local_path)
                    
                    # Add directory to downloads list
                    download_info = {
                        "filename": dirname,
                        "local_path": local_path,
                        "remote_path": remote_path,
                        "size": total_size,
                        "timestamp": datetime.datetime.now(),
                        "is_directory": True
                    }
                    self.downloads.append(download_info)
                    
                    # Final UI updates
                    self.root.after(0, lambda: self.update_downloads_list())
                    self.root.after(0, lambda: self.update_progress(100, f"Downloaded directory {dirname} successfully ({total_files} files)"))
                    
                except Exception as e:
                    self.root.after(0, lambda error=str(e): messagebox.showerror("Download Error", f"Failed to download directory {dirname}: {error}"))
                    self.root.after(0, lambda: self.update_progress(0, "Download failed"))

            threading.Thread(target=download_thread, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to initiate directory download of {dirname}: {e}")

    def scan_directory_structure(self, remote_path):
        """Scan directory structure to get total files and size"""
        total_files = 0
        total_size = 0
        file_list = []
        
        def scan_recursive(path):
            nonlocal total_files, total_size
            try:
                items = self.sftp.listdir_attr(path)
                for item in items:
                    item_path = self.normalize_path(path, item.filename)
                    
                    if stat.S_ISDIR(item.st_mode):
                        # It's a directory, scan recursively
                        scan_recursive(item_path)
                    else:
                        # It's a file
                        total_files += 1
                        total_size += item.st_size
                        file_list.append((item_path, item.st_size))
            except Exception as e:
                print(f"Error scanning {path}: {e}")
        
        scan_recursive(remote_path)
        return total_files, total_size, file_list

    def download_directory(self, dirname):
        """Download an entire directory with improved progress tracking"""
        if not self.sftp:
            return

        try:
            # Choose local save location
            local_dir = filedialog.askdirectory(title="Choose directory to save to...")
            if not local_dir:
                return

            # Create local directory
            local_path = os.path.join(local_dir, dirname)
            os.makedirs(local_path, exist_ok=True)

            # Remote directory path
            remote_path = self.normalize_path(self.current_path, dirname)

            # Start download in separate thread
            def download_thread():
                try:
                    # First, scan the directory structure
                    self.root.after(0, lambda: self.update_progress(5, f"Scanning directory {dirname}..."))
                    
                    total_files, total_size, file_list = self.scan_directory_structure(remote_path)
                    
                    # Initialize download stats
                    self.download_stats = {
                        'total_files': total_files,
                        'downloaded_files': 0,
                        'total_size': total_size,
                        'downloaded_size': 0
                    }
                    
                    self.root.after(0, lambda: self.update_progress(10, f"Found {total_files} files ({self.format_size(total_size)}) - Starting download..."))
                    
                    # Download the directory recursively
                    self._download_directory_recursive(remote_path, local_path)
                    
                    # Add directory to downloads list
                    download_info = {
                        'filename': dirname,
                        'local_path': local_path,
                        'remote_path': remote_path,
                        'size': total_size,
                        'timestamp': datetime.datetime.now(),
                        'is_directory': True
                    }
                    self.downloads.append(download_info)
                    
                    # Final UI updates
                    self.root.after(0, lambda: self.update_downloads_list())
                    self.root.after(0, lambda: self.update_progress(100, f"Downloaded directory {dirname} successfully ({total_files} files)"))
                    self.root.after(0, lambda: messagebox.showinfo("Download Complete", 
                        f"Directory saved to:\n{local_path}\n\nFiles downloaded: {total_files}\nTotal size: {self.format_size(total_size)}"))
                    
                    # Reset progress after a delay
                    self.root.after(3000, lambda: self.update_progress(0, "Ready"))
                    
                except Exception as e:
                    self.root.after(0, lambda error=str(e): messagebox.showerror("Download Error", f"Failed to download directory: {error}"))
                    self.root.after(0, lambda: self.update_progress(0, "Download failed"))

            threading.Thread(target=download_thread, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to initiate directory download: {e}")

    def _download_directory_recursive(self, remote_dir, local_dir):
        """Recursively download directory contents with proper progress tracking"""
        try:
            # Ensure local directory exists
            os.makedirs(local_dir, exist_ok=True)
            
            # List directory contents
            items = self.sftp.listdir_attr(remote_dir)
            
            for item in items:
                remote_item_path = self.normalize_path(remote_dir, item.filename)
                local_item_path = os.path.join(local_dir, item.filename)
                
                if stat.S_ISDIR(item.st_mode):
                    # It's a directory, create it locally and recurse
                    os.makedirs(local_item_path, exist_ok=True)
                    self._download_directory_recursive(remote_item_path, local_item_path)
                else:
                    # It's a file, download it
                    try:
                        def progress_callback(transferred, total):
                            # Update stats
                            if transferred == total:
                                self.download_stats['downloaded_files'] += 1
                                self.download_stats['downloaded_size'] += total
                                
                                # Update progress bar
                                if self.download_stats['total_size'] > 0:
                                    progress = (self.download_stats['downloaded_size'] / self.download_stats['total_size']) * 90 + 10
                                else:
                                    progress = 90
                                
                                files_progress = f"{self.download_stats['downloaded_files']}/{self.download_stats['total_files']}"
                                size_progress = f"{self.format_size(self.download_stats['downloaded_size'])}/{self.format_size(self.download_stats['total_size'])}"
                                
                                self.root.after(0, lambda p=progress, fp=files_progress, sp=size_progress: 
                                    self.update_progress(p, f"Downloading: {fp} files, {sp}"))
                        
                        # Download the file
                        self.sftp.get(remote_item_path, local_item_path, callback=progress_callback)
                        
                    except Exception as e:
                        print(f"Error downloading {remote_item_path}: {e}")
                        # Continue with other files even if one fails
                        
        except Exception as e:
            raise Exception(f"Error downloading directory {remote_dir}: {e}")

    def download_file(self, filename):
        """Download a file from the server"""
        if not self.sftp:
            return

        try:
            # Construct remote path
            remote_path = self.normalize_path(self.current_path, filename)

            # Choose local save location
            local_path = filedialog.asksaveasfilename(
                title="Save file as...",
                initialfile=filename,
                defaultextension=""
            )
            
            if not local_path:
                return

            # Start download in separate thread
            def download_thread():
                try:
                    # Get file size for progress tracking
                    file_attrs = self.sftp.stat(remote_path)
                    file_size = file_attrs.st_size
                    
                    self.root.after(0, lambda: self.update_progress(0, f"Downloading {filename}..."))
                    
                    def progress_callback(transferred, total):
                        if total > 0:
                            progress = (transferred / total) * 100
                            self.root.after(0, lambda: self.update_progress(
                                progress, 
                                f"Downloading {filename}: {self.format_size(transferred)}/{self.format_size(total)}"
                            ))

                    # Download file with progress callback
                    self.sftp.get(remote_path, local_path, callback=progress_callback)
                    
                    # Add to downloads list
                    download_info = {
                        'filename': filename,
                        'local_path': local_path,
                        'remote_path': remote_path,
                        'size': file_size,
                        'timestamp': datetime.datetime.now(),
                        'is_directory': False
                    }
                    self.downloads.append(download_info)
                    
                    # Update downloads sidebar
                    self.root.after(0, lambda: self.update_downloads_list())
                    self.root.after(0, lambda: self.update_progress(100, f"Downloaded {filename} successfully"))
                    self.root.after(0, lambda: messagebox.showinfo("Download Complete", f"File saved to:\n{local_path}"))
                    
                    # Reset progress after a delay
                    self.root.after(3000, lambda: self.update_progress(0, "Ready"))
                    
                except Exception as e:
                    self.root.after(0, lambda error=str(e): messagebox.showerror("Download Error", f"Failed to download file: {error}"))

            threading.Thread(target=download_thread, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to initiate download: {e}")

    def update_downloads_list(self):
        """Update the downloads list in sidebar"""
        # Clear existing items
        for item in self.downloads_tree.get_children():
            self.downloads_tree.delete(item)

        # Add downloads to the tree (most recent first)
        for download in reversed(self.downloads):
            # Get just the filename from the local path
            if download.get('is_directory', False):
                display_name = f"📁 {download['filename']}"
            else:
                display_name = f"📄 {os.path.basename(download['local_path'])}"
            
            size_str = self.format_size(download['size'])
            
            # Check if file/directory still exists
            if os.path.exists(download['local_path']):
                icon = ""
            else:
                icon = "❌ "
                display_name = icon + display_name
            
            self.downloads_tree.insert("", tk.END, text=display_name, values=(size_str,))

    def clear_downloads(self):
        """Clear downloads list"""
        if messagebox.askyesno("Clear Downloads", "Remove all files from downloads list?"):
            self.downloads.clear()
            self.update_downloads_list()

    def show_downloads_context_menu(self, event):
        """Show context menu for downloads"""
        item = self.downloads_tree.identify_row(event.y)
        if item:
            self.downloads_tree.selection_set(item)
            self.downloads_menu.post(event.x_root, event.y_root)

    def get_selected_download(self):
        """Get the selected download item"""
        selection = self.downloads_tree.selection()
        if not selection:
            return None
        
        # Get the index of the selected item (reversed order)
        selected_index = len(self.downloads) - 1 - self.downloads_tree.index(selection[0])
        
        if 0 <= selected_index < len(self.downloads):
            return self.downloads[selected_index]
        return None

    def open_downloaded_file(self, event=None):
        """Open downloaded file with default application"""
        download = self.get_selected_download()
        if not download:
            return

        local_path = download['local_path']
        
        if os.path.exists(local_path):
            try:
                if platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', local_path])
                elif platform.system() == 'Windows':  # Windows
                    os.startfile(local_path)
                else:  # Linux
                    subprocess.call(['xdg-open', local_path])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open file: {e}")
        else:
            messagebox.showerror("File Not Found", f"The file no longer exists:\n{local_path}")

    def show_in_folder(self):
        """Show file in folder/finder"""
        download = self.get_selected_download()
        if not download:
            return

        local_path = download['local_path']
        
        if os.path.exists(local_path):
            try:
                folder_path = os.path.dirname(local_path)
                if platform.system() == 'Darwin':  # macOS
                    subprocess.call(['open', '-R', local_path])
                elif platform.system() == 'Windows':  # Windows
                    subprocess.call(['explorer', '/select,', local_path])
                else:  # Linux
                    subprocess.call(['xdg-open', folder_path])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open folder: {e}")
        else:
            messagebox.showerror("File Not Found", f"The file no longer exists:\n{local_path}")

    def remove_from_downloads(self):
        """Remove selected item from downloads list"""
        download = self.get_selected_download()
        if not download:
            return

        self.downloads.remove(download)
        self.update_downloads_list()

    def initial_connect(self):
        """Check for initial connection from command line"""
        if len(sys.argv) > 1:
            self.url_entry.insert(0, sys.argv[1])
            self.connect_sftp(sys.argv[1])
        else:
            # Show connection panel by default when no connection
            self.update_ui_state(connected=False)

    def on_closing(self):
        """Handle application closing"""
        if self.sftp:
            try:
                self.sftp.close()
            except:
                pass
        if self.transport:
            try:
                self.transport.close()
            except:
                pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = SFTPBrowser(root)
    root.mainloop()

if __name__ == "__main__":
    main()