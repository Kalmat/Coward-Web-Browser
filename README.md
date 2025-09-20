# Coward

This is an evolution of the many 'Simple Web Browser' examples built with PyQt5/PyQt6 you can find on the Internet, adding:

- Tabs, which can be added, moved and removed
- Vertical and Horizontal tabs positioning
- URL bar as address bar for search and navigation
- "Expanded" view, which enables auto-hide in all navigation and tab bars (not the same as fullscreen or maximized)
- Custom title bar, whilst still allowing to move and resize window
- Open non-compatible media in external player: MPV (not included)
- Incognito mode
- Enable / Disable cookies
- Wipe all cookies, history, permissions and cache
- Navigation History which can be enabled/disabled, as well as deleted one by one or entirely
- Download pages
- Download files
- Open a page in new tab
- Open a page in new window

Rationally, this will never be a good replacement for any of the commercial web browsers around. It is intended to serve as a reference for those looking for:
- Pieces of working code to complete their own projects
- Safe browsing: all data is stored locally, and easily wiped with just one click
- A way to run a reasonably-functional browser in those environments in which they can only install Python ;)

### Keyboard shortcuts

| Shortcut             | Action                        |
|----------------------|-------------------------------|
| `Ctrl` `T`           | Open new tab                  |
| `Ctrl` `N`           | Open new window               |
| `Ctrl` `Shift` `N`   | Open new incognito window     |
| `Ctrl` `W`           | Close current tab             |
| `Alt` `F4`           | Close current window          |
| `F11`                | Enter fullscreen              |
| `Esc`                | Exit fullscreen               |
| `Esc`                | Cancel url input (in url bar) |
| `Ctrl` `Tab`         | Select tab Forward            |
| `Ctrl` `Shift` `Tab` | Select tab Backward           |
| `Ctrl` `1` - `9`     | Select tab 1 to 9             |
| `Ctrl` `F`           | Show search box               |
| `Ctrl` `H`           | Show / hide History           |

### Mouse shortcuts

| Shortcut                     | Action                                    |
|------------------------------|-------------------------------------------|
| `Button` `Left`              | Click                                     |
| `Button` `Left`              | Open new Tab (in "+" option)              |
| `Button` `Right`             | Show contextual Menu                      |
| `Button` `Right`             | Show close Tab Menu (in tab icon)         |
| `Button` `Right`             | Show open new Window Menu (in "+" option) |
| `Wheel` `Up` / `Down`        | Scroll Up / Down                          |
| `Ctrl` `Wheel` `Up` / `Down` | Zoom In / Out                             |
| `Ctrl` `Wheel` `Up` / `Down` | Select tab Forward / Back (in tab bar)    |

### Known issues (due to QtWebEngine limitations or web sites constraints)

QtWebEngine built-in codecs for audio and video have some limitations:
- Some videos will not offer HD quality option
- Media using proprietary codecs (e.g. H.264 and MP3) will not play 
- Media with DRM protection will fail to load

#### Possible solutions (not easy and not guaranteed at all) are:

#### Alternative 1
Include additional codecs and software within QtWebEngine installation

- Build QtWebEngine with option -webengine-proprietary-codecs ([see here](https://doc.qt.io/qt-6/qtwebengine-features.html#audio-and-video-codecs))
- In addition to that, for pages requiring widevine:
  - Get `widevinecdm.dll` file. Check if you have a copy in your system or download (a safe) one
  - Set the environment variable: `QTWEBENGINE_CHROMIUM_FLAGS=--widevine-path="path/to/widevinecdm.dll"` (replace "path/to/" by the actual folder containing the .dll file)
  - Alternatively to setting this variable, create a folder named `externalplayer` inside the folder in which you placed coward script and/or executable, inside this one create another named `widevine`, and place the .dll there

#### Alternative 2
Use an external player (MPV works quite well, and it's really lightweight), together with a tool to stream content onto it (streamlink is fantastic for that)

- Download mpv player from [here](https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20250827/mpv-aarch64-20250827-git-9f153e2.7z) or [here](https://github.com/zhongfly/mpv-winbuild/releases/download/2025-09-01-efb70d7/mpv-aarch64-20250901-git-efb70d7.7z)
- Inside the directory in which you placed coward.py script and/or coward.exe, create a folder named `externalplayer`
- Inside `externalplayer` folder, create another folder named `mpv`
- [Unzip your downloaded mpv player, and] place the mpv.exe file inside `mpv` folder you created in previous step

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
