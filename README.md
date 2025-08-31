# Coward

This is an evolution of the many 'Simple Web Browser' examples built with PyQt5/PyQt6 you can find on the Internet, adding:

- Tabs, which can be added, moved and removed
- Vertical and Horizontal tabs positioning
- URL bar as address bar for search and navigation
- "Expanded" view, which enables auto-hide in all navigation and tab bars (not the same as fullscreen or maximized)
- Custom or standard title bar, whilst still allowing to move and resize window
- Enable / Disable cookies
- Wipe all cookies, history, permissions and cache
- Download pages
- Download files
- Open a page in new tab
- Open a page in new window

Rationally, this will never be a good replacement for any of the commercial web browsers around. It is intended to serve as a reference for those looking for:
- Pieces of working code to complete their own projects
- Safe browsing: all data is stored locally, and easily wiped with just one click
- A way to run a reasonably-functional browser in those environments in which they can only install Python ;)

#### Keyboard shortcuts

| Shortcut           | Action                        |  
|--------------------|-------------------------------|
| `Ctrl` `F`         | Open search box               |
| `Ctrl` `T`         | Open new tab                  |
| `Ctrl` `N`         | Open new window               |
| `Ctrl` `Shift` `N` | Open new incognito window     |
| `Ctrl` `W`         | Close current tab             |
| `Alt` `F4`         | Close current window          |
| `F11`              | Enter fullscreen              |
| `Esc`              | Exit fullscreen               |
| `Esc`              | Cancel url input (in url bar) |

#### Known issues (due to QtWebEngine limitations or web sites constraints)

QtWebEngine built-in codecs for audio and video have some limitations:
- Some videos will not offer HD quality option
- Media using proprietary codecs (e.g. H.264 and MP3) will not play 
- Media with DRM protection will fail to load

The only possible solutions (not easy at all) are:
- Build QtWebEngine with option -webengine-proprietary-codecs ([see here](https://doc.qt.io/qt-6/qtwebengine-features.html#audio-and-video-codecs))
- In addition to that, for pages requiring widevine:
  - Get `widevinecdm.dll` file. Check if you have a copy in your system or download a (safe) one
  - Set the environment variable: `QTWEBENGINE_CHROMIUM_FLAGS=--widevine-path="path/to/widevinecdm.dll"` (replace "path/to/" by the actual folder containing the .dll file)
  - Alternatively to setting this variable, create a folder named `widevine` within the coward-browser folder, and place the .dll there  

### Support

In case you have a problem, comments or suggestions, do not hesitate to [open issues](https://github.com/Kalmat/Coward/issues) on the [project homepage](https://github.com/Kalmat/Coward)

### Using this code

If you want to use this code or contribute, you can either:

- Create a fork of the [repository](https://github.com/Kalmat/Coward), or
- [Download the repository](https://github.com/Kalmat/Coward/archive/refs/heads/master.zip), uncompress, and open it on your IDE of choice (e.g. PyCharm)

Be sure you install all dependencies described on "requirements.txt" by using pip:

    python -m pip install -r requirements.txt

### Run or Test this

To run or test this module on your own system, cd to the project folder and run:

    python coward.py
