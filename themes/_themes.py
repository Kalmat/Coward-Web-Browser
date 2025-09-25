from enum import Enum

import utils


class Themes:

    class Theme(Enum):

        # themes
        dark = "Dark"
        incognito = "Incognito"

    # styles within themes
    class Section:
        mainWindow = "mainWindow"
        horizontalTitleBar = "horizontalTitleBar"
        verticalTitleBar = "verticalTitleBar"
        horizontalTabs = "horizontalTabs"
        verticalTabs = "verticalTabs"
        searchWidget = "searchWidget"
        downloadManager = "downloadManager"
        dialog = "dialog"
        messagebox = "messagebox"
        contextmenu = "contextmenu"
        mediaplayer = "mediaplayer"
        historyWidget = "historyWidget"

    _themes = {
        "Dark": {
            "mainWindow": 'main.qss',
            "horizontalTitleBar": 'h_titlebar.qss',
            "verticalTitleBar": 'v_titlebar.qss',
            "horizontalTabs": 'h_tabs.qss',
            "verticalTabs": 'v_tabs.qss',
            "searchWidget": 'search_widget.qss',
            "downloadManager": 'download_manager.qss',
            "dialog": 'dialog.qss',
            "messagebox": 'messagebox.qss',
            "contextmenu": "contextmenu.qss",
            "mediaplayer": "mediaplayer.qss",
            "historyWidget": "history_widget.qss"
        },
        "Incognito": {
            "mainWindow": 'main.qss',
            "horizontalTitleBar": 'h_titlebar_incognito.qss',
            "verticalTitleBar": 'v_titlebar_incognito.qss',
            "horizontalTabs": 'h_tabs.qss',
            "verticalTabs": 'v_tabs.qss',
            "searchWidget": 'search_widget.qss',
            "downloadManager": 'download_manager.qss',
            "dialog": 'dialog.qss',
            "messagebox": 'messagebox.qss',
            "contextmenu": "contextmenu.qss",
            "mediaplayer": "mediaplayer.qss",
            "historyWidget": "history_widget.qss"
        }
    }

    @staticmethod
    def styleSheet(theme, section):
        theme: Themes.Theme = theme
        styleSheet = Themes._themes[theme][section]
        with open(utils.resource_path("qss/" + styleSheet)) as f:
            style = f.read()
        return style


