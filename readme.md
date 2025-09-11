# A Very Simple SFTP Browser

A straightforward SFTP client built using Python's Tkinter for the GUI and Paramiko for SFTP connectivity. This application allows you to connect to an SFTP server, browse directories, download files and entire folders, and keeps a persistent list of your downloaded items. It features a modern, Catppuccin-inspired theme for a pleasant user experience.

## Features

*   **SFTP Connection:** Connect to SFTP servers using hostname, port, username, and password.
*   **Quick Connect URL:** Paste `sftp://user:pass@host:port/path` URLs for rapid connections.
*   **Directory Browsing:** Navigate remote file systems.
*   **File and Directory Download:** Download individual files or entire directory structures.
*   **Persistent Download List:** Keep track of downloaded files even after new SFTP sessions.
*   **Open Downloaded Files/Folders:** Quickly open downloaded files or their containing local folders.
*   **Catppuccin Theme:** A visually appealing theme based on the Catppuccin Macchiato palette.
*   **Minimalist Scrollbars:** Scrollbars only appear when content exceeds the visible area.
*   **Clean Session Management:** New SFTP connections clear the previous browser state (except downloaded files).


## Installation and Setup

### Prerequisites

*   Python 3.x
*   `paramiko` library

### Steps

1.  **Clone or Download:**
    Clone this repository or download the `A Very Simple SFTP Browser.py` file to your local machine.

    ```bash
    git clone https://github.com/crakA2/a-very-simple-sftp-browser.git
    cd a-very-simple-sftp-browser
    ```

2.  **Install Dependencies:**
    Open your terminal or command prompt and navigate to the directory where you saved the script. Install `paramiko` using pip:

    ```bash
    pip install paramiko
    ```

3.  **Run the Application:**
    Execute the Python script:

    ```bash
    python "sftp_browser.py"
    ```

### Command-line Quick Connect

You can also launch the application and connect to an SFTP server directly by providing an SFTP URL as a command-line argument:

```bash
python "sftp_browser.py" sftp://username:password@hostname:port/remote/path
```

*   If `username` or `password` are missing from the URL, the login dialog will pre-fill available information and prompt you for the rest.
*   Remember to URL-encode special characters in the username or password if necessary (e.g., `@` becomes `%40`).

## Usage

1.  **New Connection:** Click the "New Connection" button to open the login dialog.
2.  **Manual Login:** Enter your hostname, port, username, and password, then click "Connect".
3.  **Quick Connect URL:** Alternatively, paste a full SFTP URL (e.g., `sftp://user:pass@host:port/folder`) into the "Quick Connect URL" field and click "Go".
4.  **Browse Files:** Double-click on directories to navigate into them. Use the "← Back" button to go up a directory.
5.  **Download Files:** Double-click on a file to initiate a download to a local path.
6.  **Download Directory:** Click "Download Directory" to download the entire contents of the current remote directory to a chosen local folder.
7.  **Downloaded Files:** The right sidebar lists all files you've downloaded during the current and previous sessions.
8.  **Open Downloaded:** Select a downloaded item in the right sidebar and click "Open File" to open it with your system's default application, or "Open Folder" to open its containing directory.

## Contributing

Feel free to fork the repository, make improvements, and submit pull requests!

## License

```text
MIT License

Copyright (c) 2025 CrakA2

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```