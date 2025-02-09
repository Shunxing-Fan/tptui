# Teleport TUI (tptui)

A modern Terminal User Interface (TUI) for seamless file transfers between local and remote systems. Teleport TUI provides an intuitive visual interface for SCP and RSYNC operations, making file transfers as simple as possible.

![Project Status](https://img.shields.io/badge/status-stable-green)
![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

## Features

- 🖥️ Intuitive terminal-based user interface
- 📂 Visual file browser for both local and remote systems
- 🔄 Support for both SCP and RSYNC protocols
- 📋 Command preview and clipboard copy functionality
- 🔀 Easy switching between transfer directions (local→remote, remote→local)
- ⏸️ Resume support for interrupted transfers (with RSYNC)
- 🔒 Secure password handling

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tptui.git
cd tptui
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python main.py
```

2. Connect to your remote server:
   - Enter your SSH connection details in either format:
     ```
     ssh -p PORT USERNAME@HOSTNAME
     ```
     or
     ```
     Host myserver
     HostName example.com
     Port 22
     User username
     ```
   - Enter your password when prompted

3. Navigate the interface:
   - Use arrow keys to browse files
   - Press `Tab` to switch between local and remote panels
   - Press `Enter` to select files/directories
   - Press `T` to open transfer options
   - Press `C` to clear selection
   - Press `Q` to quit

4. Transfer files:
   - Select source and destination files/directories
   - Choose between SCP and RSYNC protocols
   - Set transfer direction (local→remote or remote→local)
   - Copy the generated command to clipboard
   - Execute the command in your terminal

## Keyboard Shortcuts

| Key   | Action                    |
|-------|---------------------------|
| Tab   | Switch between panels     |
| Enter | Select file/directory     |
| T     | Open transfer options     |
| C     | Clear current selection   |
| Q     | Quit                     |

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Textual](https://github.com/Textualize/textual)
- Uses [Paramiko](https://github.com/paramiko/paramiko) for SSH connectivity 
