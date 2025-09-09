import utils

class Themes:
    
    # themes
    dark = "Dark"
    incognito = "Incognito"

    # styles within themes
    class Section:
        mainWindow = "mainWindow"
        titleBar = "titleBar"
        horizontalTabs = "horizontalTabs"
        verticalTabs = "verticalTabs"
        searchWidget = "searchWidget"
        downloadManager = "downloadManager"
        dialog = "dialog"
        contextmenu = "contextmenu"
        mediaplayer = "mediaplayer"

    _themes = {
        "Dark": {
            "mainWindow": 'main.qss',
            "titleBar": 'titlebar.qss',
            "horizontalTabs": 'h_tabs.qss',
            "verticalTabs": 'v_tabs.qss',
            "searchWidget": 'search_widget.qss',
            "downloadManager": 'download_manager.qss',
            "dialog": 'dialog.qss',
            "contextmenu": "contextmenu.qss",
            "mediaplayer": "mediaplayer.qss"
        },
        "Incognito": {
            "mainWindow": 'main.qss',
            "titleBar": 'titlebar_incognito.qss',
            "horizontalTabs": 'h_tabs.qss',
            "verticalTabs": 'v_tabs.qss',
            "searchWidget": 'search_widget.qss',
            "downloadManager": 'download_manager.qss',
            "dialog": 'dialog.qss',
            "contextmenu": "contextmenu.qss",
            "mediaplayer": "mediaplayer.qss"
        }
    }

    @staticmethod
    def styleSheet(theme, section):
        styleSheet = Themes._themes[theme][section]
        with open(utils.resource_path("qss/" + styleSheet)) as f:
            style = f.read()
        return style


