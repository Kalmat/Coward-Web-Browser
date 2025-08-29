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

#### Known issues (due to QtWebEngine limitations or web sites constraints)

- Some videos from some web sites will not offer HD quality option
- Live videos will not load unless QtWebEngine is compiled in your own system, adding all required codecs
- Some videos with strict DRM protection will not play

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
