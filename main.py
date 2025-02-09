from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, DirectoryTree, Input, Label, TextArea, Tree
from textual.binding import Binding
from textual import events
import paramiko
import os
from pathlib import Path, PurePosixPath
import subprocess
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
import threading
from textual.screen import Screen
from textual.widgets import Button
import re
from stat import S_ISDIR
import pyperclip

def parse_ssh_string(ssh_input: str) -> dict:
    """Parse SSH connection string in various formats."""
    connection_info = {
        "host": "",
        "port": "22",  # Default port
        "username": "",
        "password": ""
    }
    
    # Try SSH command format (ssh -p port user@host)
    cmd_pattern = r'ssh\s+(?:-p\s+(\d+))?\s*([^@\s]+)@([^\s]+)'
    cmd_match = re.match(cmd_pattern, ssh_input.strip())
    
    if cmd_match:
        port, username, host = cmd_match.groups()
        if port:  # Only update port if explicitly specified
            connection_info["port"] = port
        if username:
            connection_info["username"] = username
        if host:
            connection_info["host"] = host
        return connection_info
    
    # Try SSH config format
    config_lines = ssh_input.strip().split('\n')
    host_block = False
    
    for line in config_lines:
        line = line.strip()
        if line.startswith('Host '):
            host_block = True
            continue
        if host_block:
            key_value = line.split(None, 1)
            if len(key_value) != 2:
                continue
            key, value = key_value
            if key == 'HostName':
                connection_info['host'] = value
            elif key == 'Port':  # Only update port if explicitly specified
                connection_info['port'] = value
            elif key == 'User':
                connection_info['username'] = value
    
    return connection_info

class LoginScreen(Screen):
    def compose(self) -> ComposeResult:
        yield Container(
            Label("SSH Connection Details", id="login-title"),
            Label("Enter SSH connection string in either format:\n1. ssh -p PORT USERNAME@HOSTNAME\n2. Host myserver\n   HostName example.com\n   Port 22\n   User username", id="instructions"),
            TextArea(id="ssh-input"),
            Input(placeholder="Password", password=True, id="password"),
            Button("Connect", id="connect"),
            id="login-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "connect":
            ssh_input = self.query_one("#ssh-input").text
            password = self.query_one("#password").value
            
            connection_info = parse_ssh_string(ssh_input)
            connection_info["password"] = password
            
            if not connection_info["host"]:
                self.app.notify("Invalid SSH connection string")
                return
                
            self.app.ssh_details = connection_info
            self.app.push_screen("file_transfer")

class RemoteDirectoryTree(Tree):
    def __init__(self, sftp, path="/"):
        """Initialize the remote directory tree."""
        super().__init__("Remote Files", id="remote-tree")
        self.sftp = sftp
        self.root_path = path
        self._load_directory("/root")

    def _load_directory(self, path: str) -> None:
        """Load the contents of a directory into the tree root."""
        try:
            entries = sorted(self.sftp.listdir_attr(path),
                           key=lambda x: (not S_ISDIR(x.st_mode), x.filename))
            
            for entry in entries:
                full_path = str(PurePosixPath(path) / entry.filename)
                is_dir = S_ISDIR(entry.st_mode)

                label = f"{'📁' if is_dir else '📄'} {entry.filename}"
                node = self.root.add(      
                    label,
                    data={"path": full_path, "is_dir": is_dir},
                    expand=False,
                )
                
                if is_dir:
                    # Add a placeholder child node to show it's expandable
                    node.add("Loading...")

        except Exception as e:
            self.root.add(f"Error: {str(e)}")

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle node expansion."""
        node = event.node
        if not node.data:
            return
        
        if node.data.get("is_dir", False):
            node.remove_children()
            path = node.data["path"]
            try:
                entries = sorted(self.sftp.listdir_attr(path),
                               key=lambda x: (not S_ISDIR(x.st_mode), x.filename))
                
                for entry in entries:
                    full_path = str(PurePosixPath(path) / entry.filename)
                    is_dir = S_ISDIR(entry.st_mode)
                    
                    child_label = f"{'📁' if is_dir else '📄'} {entry.filename}"
                    child = node.add(
                        child_label,
                        data={"path": full_path, "is_dir": is_dir},
                        expand=False,
                    )
                    if is_dir:
                        child.add("Loading...")

            except Exception as e:
                node.add(f"Error: {str(e)}")

    def get_node_path(self, node):
        """Get the full path for a node."""
        if node and node.data:
            return node.data["path"]
        return None

class CommandPreviewScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def action_quit(self) -> None:
        self.app.pop_screen()

    def __init__(self, command_type="scp"):
        super().__init__()
        self.command_type = command_type
        self.direction = "local_to_remote"  # Default direction

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Transfer Command Preview", id="preview-title"),
            TextArea(id="command-preview", language="bash"),
            Horizontal(
                Button("Copy", id="copy", variant="primary"),
                Button("Switch Direction", id="switch-direction", variant="primary"),
                Button("Switch to " + ("rsync" if self.command_type == "scp" else "scp"), id="switch-type", variant="default"),
            ),
            Horizontal(
                Button("Back", id="back", variant="warning"),
                Button("Exit", id="exit", variant="error"),
            ),
            id="preview-container",
        )

    def on_mount(self) -> None:
        # Make command preview editable by default
        preview = self.query_one("#command-preview")
        preview.read_only = False
        # Generate initial command
        self.generate_command()

    def generate_command(self) -> None:
        local_path = self.app.local_selected
        remote_path = self.app.remote_selected
        
        if not local_path or not remote_path:
            return

        # Quote local path to handle spaces
        local_path = f'"{local_path}"'
        # Construct remote path with SSH details
        remote_path = f"{self.app.ssh_details['username']}@{self.app.ssh_details['host']}:{remote_path}"

        if self.direction == "local_to_remote":
            source = local_path
            dest = remote_path
        else:
            source = remote_path
            dest = local_path

        if self.command_type == "scp":
            command = f"scp -P {self.app.ssh_details['port']} {source} {dest}"
        else:
            command = f"rsync -avz --partial --progress -e 'ssh -p {self.app.ssh_details['port']}' {source} {dest}"

        self.query_one("#command-preview").text = command

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "switch-type":
            self.command_type = "rsync" if self.command_type == "scp" else "scp"
            self.generate_command()
            self.query_one("#switch-type").label = f"Switch to {('rsync' if self.command_type == 'scp' else 'scp')}"
        elif event.button.id == "switch-direction":
            self.direction = "remote_to_local" if self.direction == "local_to_remote" else "local_to_remote"
            direction_text = "Remote → Local" if self.direction == "remote_to_local" else "Local → Remote"
            self.app.notify(f"Transfer direction: {direction_text}")
            self.generate_command()
        elif event.button.id == "copy":
            command = self.query_one("#command-preview").text
            try:
                pyperclip.copy(command)
                self.app.notify("Command copied to clipboard!")
            except Exception as e:
                self.app.notify(f"Failed to copy to clipboard: {str(e)}")
        elif event.button.id == "exit":
            self.app.exit()

class FileTransferScreen(Screen):
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "switch_focus", "Switch Focus"),
        Binding("t", "transfer", "Transfer"),
        Binding("c", "clear_selection", "Clear Selection"),
    ]

    def action_quit(self) -> None:
        self.app.exit()

    def compose(self) -> ComposeResult:
        yield Container(
            Header(),
            Horizontal(
                Container(
                    Label("Local Files"),
                    DirectoryTree(Path.home(), id="local-tree"),
                ),
                Container(
                    Label("Remote Files"),
                    Container(id="remote-container"),
                ),
            ),
            Footer(),
        )

    def on_mount(self) -> None:
        self.local_selected = None
        self.remote_selected = None
        self.setup_sftp()

    def setup_sftp(self):
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                self.app.ssh_details["host"],
                port=int(self.app.ssh_details["port"]),
                username=self.app.ssh_details["username"],
                password=self.app.ssh_details["password"]
            )
            self.sftp = self.ssh.open_sftp()
            
            # Create and mount the remote directory tree
            remote_tree = RemoteDirectoryTree(self.sftp, "/root")
            self.query_one("#remote-container").mount(remote_tree)
        except Exception as e:
            self.app.notify(f"SSH connection failed: {str(e)}")
            # Show error in the container
            error_label = Label(f"Connection Error:\n{str(e)}")
            self.query_one("#remote-container").mount(error_label)

    def action_switch_focus(self) -> None:
        if self.focused == "#local-tree":
            self.query_one("#remote-tree").focus()
        else:
            self.query_one("#local-tree").focus()

    def action_clear_selection(self) -> None:
        """Clear current selection and start over."""
        self.local_selected = None
        self.remote_selected = None
        self.app.notify("Selection cleared.")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle local file selection."""
        path = str(event.path)
        self.local_selected = path
        self.app.notify(f"Local selected: {os.path.basename(path)}")

    def on_directory_tree_directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        """Handle local directory selection."""
        path = str(event.path)
        self.local_selected = path
        self.app.notify(f"Local selected: {os.path.basename(path)}")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle remote file/directory selection."""
        node = event.node
        if hasattr(node, "data") and node.data:
            path = node.data.get("path")
            if path:
                self.remote_selected = path
                self.app.notify(f"Remote selected: {os.path.basename(path)}")

    def action_transfer(self) -> None:
        if not self.local_selected:
            self.app.notify("Please select a local file/directory")
            return
        if not self.remote_selected:
            self.app.notify("Please select a remote file/directory")
            return
            
        # Store paths in app for access by preview screen
        self.app.local_selected = self.local_selected
        self.app.remote_selected = self.remote_selected
        # Push the command preview screen
        self.app.push_screen(CommandPreviewScreen())

    def _transfer_file(self, file_path: str):
        def transfer():
            try:
                # Determine if it's local->remote or remote->local
                is_local = os.path.exists(file_path)
                if is_local:
                    # Local to remote transfer
                    filename = os.path.basename(file_path)
                    remote_path = str(PurePosixPath(self.app.ssh_details.get("remote_dir", "/root")) / filename)
                    self.sftp.put(file_path, remote_path, callback=lambda x, y: None)
                else:
                    # Remote to local transfer
                    filename = os.path.basename(file_path)
                    local_path = os.path.join(str(Path.home()), filename)
                    self.sftp.get(file_path, local_path, callback=lambda x, y: None)
                
                self.app.notify(f"Transfer completed: {filename}")
            except Exception as e:
                self.app.notify(f"Transfer failed: {str(e)}")

        thread = threading.Thread(target=transfer)
        thread.start()

class SCPApp(App):
    CSS = """
    Screen {
        align: center middle;
    }

    FileTransferScreen {
        align: left top;
        height: 100%;
        width: 100%;
    }

    #login-container, #preview-container {
        width: 100;
        height: auto;
        border: solid green;
        padding: 1 2;
    }

    #preview-title {
        content-align: center middle;
        width: 100%;
        padding: 1;
        background: $boost;
    }

    #command-preview {
        height: 5;
        margin: 1 0;
        border: solid grey;
    }

    Input {
        margin: 1 0;
    }

    TextArea {
        height: 8;
        margin: 1 0;
        border: solid grey;
    }

    Button {
        width: 16;
        margin: 1 1;
    }

    Horizontal {
        align: center middle;
        width: 100%;
        padding: 1 1;
    }

    DirectoryTree, Tree {
        width: 100%;
        height: 100%;
        border: solid grey;
        scrollbar-size: 1 1;
    }

    #remote-container {
        width: 100%;
        height: 100%;
    }

    Container {
        height: 100%;
    }

    FileTransferScreen Container {
        height: 100%;
    }

    Horizontal > Container {
        width: 50%;
        height: 100%;
        margin: 0 1;
    }

    Label {
        text-align: center;
        width: 100%;
        padding: 1;
        background: $panel;
    }

    Header {
        dock: top;
        height: 1;
    }

    Footer {
        dock: bottom;
        height: 1;
    }

    #preview-container {
        background: $surface;
        height: auto;
        min-height: 20;
        margin: 1 2;
    }

    #preview-container Horizontal {
        height: auto;
        margin: 1 0;
    }
    """

    SCREENS = {
        "login": LoginScreen,
        "file_transfer": FileTransferScreen,
    }

    def on_mount(self) -> None:
        self.push_screen("login")

    def action_quit(self) -> None:
        self.exit()

if __name__ == "__main__":
    app = SCPApp()
    app.run() 