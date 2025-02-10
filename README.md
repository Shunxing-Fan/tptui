# Teleport TUI

A Terminal User Interface (TUI) application for secure file transfer between local and remote systems using SSH. The application supports both SCP and RSYNC protocols with an intuitive interface for file selection and command generation.

## Features

- Interactive file browser for both local and remote systems
- Support for both SCP and RSYNC protocols
- Command preview and clipboard integration
- Breakpoint continuation support for interrupted transfers
- Easy direction switching between local-to-remote and remote-to-local transfers
- Support for SSH connection strings and config formats

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/scp_tui.git
cd scp_tui
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the packaged application:
```bash
tptui
```

## Usage

1. Launch the application by typing `tptui` in any terminal window.

2. Enter your SSH connection details in either format:
   - SSH command format: `ssh -p PORT USERNAME@HOSTNAME`
   - SSH config format:
     ```
     Host myserver
     HostName example.com
     Port 22
     User username
     ```

3. Enter your password when prompted.

4. Use the file browser to select source and destination files:
   - Press `Tab` to switch focus between local and remote file trees
   - Navigate using arrow keys
   - Press `Enter` to select a file or expand/collapse directories
   - Press `t` to preview the transfer command
   - Press `c` to clear selection

5. In the command preview screen:
   - Switch between SCP and RSYNC protocols
   - Toggle transfer direction (local-to-remote or remote-to-local)
   - Copy the generated command to clipboard
   - Edit the command if needed

6. Execute the copied command in your terminal to start the transfer.

## Keyboard Shortcuts

- `Tab`: Switch focus between local and remote file trees
- `t`: Open transfer command preview
- `c`: Clear current selection
- `q`: Quit current screen
- Arrow keys: Navigate file trees
- `Enter`: Select file or expand/collapse directory

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual)
- Uses [Paramiko](https://github.com/paramiko/paramiko) for SSH connectivity 
