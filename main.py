# import section
import json
import sys
import os
from plexapi.server import PlexServer
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from main_ui import Ui_MainWindow

import playlist_module as pp

basedir = os.path.dirname(__file__)


# class creation
class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.plex = None
        self.main_win = QMainWindow()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self.main_win)

        # load variables
        self.load_json()

        # Menus
        self.ui.actionLoad_Settings.triggered.connect(lambda: self.load_json())
        self.ui.actionSave_Settings.triggered.connect(lambda: self.save_json())

        # Side Panel
        # handle page buttons
        self.ui.stackedWidget.setCurrentWidget(self.ui.page_home)
        self.ui.btn_home_page.clicked.connect(lambda: self.page_clicked(self.ui.page_home, self.ui.btn_home_page))
        self.ui.btn_plex_page.clicked.connect(lambda: self.page_clicked(self.ui.page_plex, self.ui.btn_plex_page))
        self.ui.btn_playlist_page.clicked.connect(lambda: self.page_clicked(self.ui.page_playlists, self.ui.btn_playlist_page))
        self.ui.btn_settings_page.clicked.connect(lambda: self.page_clicked(self.ui.page_settings, self.ui.btn_settings_page))

        # Main Page
        # handle Tutorial checkbox
        self.ui.btn_tutorial.clicked.connect(lambda: self.tutorial_btn_clicked())

        # Plex Page
        self.ui.cmb_library_sections.currentTextChanged.connect(lambda: self.update_library_playlists())
        # handle plex buttons
        self.ui.btn_plex_connect.clicked.connect(lambda: self.connect_plex())
        self.ui.btn_plex_upload.clicked.connect(lambda: self.plex_upload())
        self.ui.btn_plex_download.clicked.connect(lambda: self.plex_download())

        # Playlist Page
        self.ui.btn_add_prepend.clicked.connect(lambda: self.add_prepend())
        self.ui.btn_playlist_convert.clicked.connect(lambda: self.convert_playlists())
        self.ui.btn_playlist_combine.clicked.connect(lambda: self.combine_playlists())

        # Settings Page
        # handle buttons & link
        self.ui.lned_plex_server.textChanged.connect(lambda: self.check_connect_btn())
        self.ui.lned_plex_token.textChanged.connect(lambda: self.check_connect_btn())
        self.ui.chkbx_ignore_all.toggled.connect(lambda: self.ignore_toggle())
        self.ui.btn_playlist_directory.clicked.connect(lambda: self.browse_playlist_directory())
        self.ui.btn_export_directory.clicked.connect(lambda: self.browse_export_directory())

    def show(self):
        self.main_win.show()

    def MessageBox(self, title, message, btns, msgtype):
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(btns)
        msg.setIcon(msgtype)
        x = msg.exec_()
        return x

    def FileDialog(self, directory='', forOpen=True, fmt='', isFolder=False):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.DontUseCustomDirectoryIcons
        dialog = QFileDialog()
        dialog.setOptions(options)

        dialog.setFilter(dialog.filter() | QtCore.QDir.Hidden)

        # ARE WE TALKING ABOUT FILES OR FOLDERS
        if isFolder:
            dialog.setFileMode(QFileDialog.DirectoryOnly)
        else:
            dialog.setFileMode(QFileDialog.AnyFile)
        # OPENING OR SAVING
        dialog.setAcceptMode(QFileDialog.AcceptOpen) if forOpen else dialog.setAcceptMode(QFileDialog.AcceptSave)

        # SET FORMAT, IF SPECIFIED
        if fmt != '' and isFolder is False:
            # dialog.setDefaultSuffix(fmt)
            dialog.setNameFilters(fmt)

        # SET THE STARTING DIRECTORY
        if directory != '':
            dialog.setDirectory(str(directory))
        else:
            dialog.setDirectory(str(os.path.dirname(os.path.abspath(__file__))))

        if dialog.exec_() == QDialog.Accepted:
            path = dialog.selectedFiles()[0]  # returns a list
            return path
        else:
            return ''

    # Save Settings to Json
    def save_json(self):
        cwd = os.path.dirname(os.path.abspath(__file__))
        data = {}
        data['plex_server'] = self.ui.lned_plex_server.text()
        data['plex_token'] = self.ui.lned_plex_token.text()
        data['playlist_directory'] = self.ui.lned_playlist_directory.text()
        data['export_directory'] = self.ui.lned_export_directory.text()
        data['prepends'] = [self.ui.cmbbx_prepend.itemText(i) for i in range(self.ui.cmbbx_prepend.count())]
        with open(os.path.join(cwd,'settings.json'), 'w') as output:
            json.dump(data, output, indent=2, separators=(',', ': '))
        pass

    def load_json(self):
        self.variables = pp.load_variables()
        if self.variables:
            # Playlist page
            self.ui.cmbbx_prepend.addItems(self.variables["prepends"])
            # Settings Page
            self.ui.lned_plex_server.setText(self.variables['plex_server'])
            self.ui.lned_plex_token.setText(self.variables['plex_token'])
            self.ui.lned_playlist_directory.setText(self.variables['playlist_directory'])
            self.ui.lned_export_directory.setText(self.variables['export_directory'])
            self.check_connect_btn()
        else:
            self.variables = {"plex_server": "",
                    "plex_token": "",
                    "playlist_directory": "",
                    "export_path": "",
                    "prepends": []}

    # Side Panel functions
    def page_clicked(self, page, btn):
        buttons = [self.ui.btn_home_page, self.ui.btn_plex_page, self.ui.btn_playlist_page, self.ui.btn_settings_page]
        self.ui.stackedWidget.setCurrentWidget(page)
        btn.setStyleSheet("background-color: rgb(229, 160, 13); color: rgb(0, 0, 0);")
        for button in buttons:
            if button == btn:
                button.setStyleSheet("background-color: rgb(229, 160, 13); color: rgb(0, 0, 0); border: none;")
            else:
                button.setStyleSheet("border: none")

    def check_connect_btn(self):
        plex_server = self.ui.lned_plex_server.text()
        plex_token = self.ui.lned_plex_token.text()
        if plex_server and plex_token:
            self.ui.btn_plex_connect.setEnabled(True)
            self.ui.btn_plex_connect.setStyleSheet("Background-color: Green; color: rgb(255, 255, 255)")
        else:
            self.ui.btn_plex_connect.setEnabled(False)
            self.ui.btn_plex_connect.setStyleSheet("")

    # Main Page Functinos
    def tutorial_btn_clicked(self):
        print("check box toggled!")
        title = "Getting Started"
        buttons = QMessageBox.Ok | QMessageBox.Cancel
        msgtype = QMessageBox.Information
        # First Message
        message = ("Lets get started! \nStart by going to the settings tab and entering your plex info."
                   "\n\nNote: You can always end this guide by pressing cancel at any point.")
        msg1 = self.MessageBox(title, message, buttons, msgtype)
        if msg1 == QMessageBox.Cancel:
            return

        # Go to Setting page to enter
        self.page_clicked(self.ui.page_settings, self.ui.btn_settings_page)

        message = "This tab contains settings for handling your plex connection and your playlist."
        msg2 = self.MessageBox(title, message, buttons, msgtype)
        if msg2 == QMessageBox.Cancel:
            return

        message = "Enter your plex server and plex token in order to connect."
        msg3 = self.MessageBox(title, message, buttons, msgtype)
        if msg3 == QMessageBox.Cancel:
            return

        message = ("You can also enter the directory where your playlists are located at and where to export it. "
                   "\nNote: Your playlist directory should be visible to your plex.")
        msg4 = self.MessageBox(title, message, buttons, msgtype)
        if msg4 == QMessageBox.Cancel:
            return

        # self.ui.menuFile.window()
        message = ("You can save any changes made in this application. A 'settings.json' is generated whenever you save."
                   "\n\nYou can also load any changes made manually in the json file as well.")
        msg4 = self.MessageBox(title, message, buttons, msgtype)
        if msg4 == QMessageBox.Cancel:
            return

        # Go to Plex page
        self.page_clicked(self.ui.page_plex, self.ui.btn_plex_page)

        message = (
            "On the Plex tab, you can select what music library you want to operate in.")
        msg5 = self.MessageBox(title, message, buttons, msgtype)
        if msg5 == QMessageBox.Cancel:
            return

        message = (
            "The download button lets you download playlists from your plex to your local folders.\n\n"
            "The upload button lets you upload from your local folder to your plex library.\n"
            "Note: Make sure your playlist is located in a folder your plex server has access to.")
        msg6 = self.MessageBox(title, message, buttons, msgtype)
        if msg6 == QMessageBox.Cancel:
            return

        # Go to Playlist Page
        self.page_clicked(self.ui.page_playlists, self.ui.btn_playlist_page)

        message = (
            "On the playlist tab, you can quickly format the song paths in your playlist so that plex can find the songs.")
        msg7 = self.MessageBox(title, message, buttons, msgtype)
        if msg7 == QMessageBox.Cancel:
            return

        message = (
            "You can also combine playlists to keep your local and plex playlists synched.")
        msg7 = self.MessageBox(title, message, buttons, msgtype)
        if msg7 == QMessageBox.Cancel:
            return

    # Settings Function
    def ignore_toggle(self):
        if self.ui.btn_plex_connect.text() == 'Connected':
            self.update_library_sections(self.plex)

    def connect_plex(self):
        print("Button Pressed")
        self.plex = PlexServer(self.variables['plex_server'], self.variables['plex_token'])
        self.ui.btn_plex_connect.setStyleSheet('Background-color: Grey')
        self.ui.btn_plex_connect.setText('Connected')
        self.ui.btn_plex_connect.setEnabled(False)
        self.ui.cmb_library_sections.setEnabled(True)
        self.ui.list_library_playlist.setEnabled(True)
        self.update_library_sections(self.plex)

    def update_library_sections(self, plex):
        library_list = [section.title for section in plex.library.sections() if section.CONTENT_TYPE == 'audio']
        self.ui.cmb_library_sections.clear()
        if library_list:
            self.ui.cmb_library_sections.addItem('Select a Music Library')
            self.ui.cmb_library_sections.addItems(library_list)
        self.ui.cmb_library_sections.update()
        self.update_library_playlists()

    def update_library_playlists(self):
        section = self.ui.cmb_library_sections.currentText()
        if section != 'Select a Music Library':
            playlist_list = [playlist.title for playlist in self.plex.library.section(section).playlists()]
            self.ui.list_library_playlist.clear()
            if not playlist_list:
                self.ui.list_library_playlist.addItems(["(empty)"])
                self.ui.btn_plex_download.setEnabled(False)
            else:
                if 'All Music' in playlist_list and self.ui.chkbx_ignore_all.isChecked():
                    playlist_list.remove('All Music')
                self.ui.list_library_playlist.addItems(playlist_list)
                self.ui.btn_plex_download.setEnabled(True)
            self.ui.list_library_playlist.update()

            self.ui.btn_plex_upload.setEnabled(True)
        else:
            self.ui.btn_plex_upload.setEnabled(False)
            self.ui.btn_plex_download.setEnabled(False)

    def browse_playlist_directory(self):
        print("browse_button pressed!")
        directory = self.FileDialog(directory=self.ui.lned_playlist_directory.text(), isFolder=True)
        if directory:
            self.ui.lned_playlist_directory.setText(directory)

    def browse_export_directory(self):
        print("browse button pressed!")
        directory = self.FileDialog(directory=self.ui.lned_export_directory.text(), isFolder=True)
        if directory:
            self.ui.lned_export_directory.setText(directory)

    # Playlist Functions
    def add_prepend(self):
        # This function adds a new prepend option in the dropdown box
        new_prepend = self.ui.lned_custom_prepend.text()
        if new_prepend:
            print('Add button pressed!')
            if not os.path.exists(new_prepend):
                pass
                #TODO: handle non existent directory
                #TODO: add dialog window to acknowledge directory does not exist, show directory to see if its mispelled
                #TODO: add option to create directory if its missing
            self.variables["prepends"].append(new_prepend)
            self.ui.cmbbx_prepend.addItem(new_prepend)
            self.ui.cmbbx_prepend.update()
            self.ui.cmbbx_prepend.setCurrentText(new_prepend)
            self.ui.lned_custom_prepend.clear()

    def convert_playlists(self):
        # This function changes the prepend (path to file) for a playlist
        # Example: Change "Z:\home\user\data\media\music\main" to "/volume1/media/Music/All Music"
        prepend = self.ui.cmbbx_prepend.currentText()
        playlist_directory = self.ui.lned_playlist_directory.text()
        export_path = self.ui.lned_export_directory.text()
        filter = ("M3U Files (*.m3u *.m3u8)", "All Files (*)")
        playlists = self.FileDialog(directory=playlist_directory, fmt=filter)
        pp.format_playlist(export_path=export_path, prepend=prepend, playlists=playlists)
        # Let user know playlists are ready
        title = "Playlist Conversion Complete!"
        buttons = QMessageBox.Ok
        msgtype = QMessageBox.Information
        # First Message
        message = "Your playlists are ready!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    def combine_playlists(self):
        # This function combines two playlists, keeping only one copy of duplicate songs
        # Good for comparing different versions of playlist
        print("combined button pressed!")
        # Get playlist info
        prepend = self.ui.cmbbx_prepend.currentText()
        playlist_directory = self.ui.lned_playlist_directory.text()
        export_path = self.ui.lned_export_directory.text()
        # Ask user for playlists
        filter = ("M3U Files (*.m3u *.m3u8)", "All Files (*)")
        playlist1 = self.FileDialog(directory=playlist_directory, fmt=filter)
        playlist2 = self.FileDialog(directory=playlist_directory, fmt=filter)
        pp.combine_playlists(export_path=export_path, prepend=prepend, playlist1=playlist1, playlist2=playlist2)
        # Let user know playlists are combined
        title = "Combinging Playlist complete!"
        buttons = QMessageBox.Ok
        msgtype = QMessageBox.Information
        # First Message
        message = "The combined playlist is ready!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    # Plex Functions
    def plex_upload(self):
        # This function allows a user to select playlist files to be uploaded to plex library
        print("upload button pressed!")
        # Get plex library details
        section = self.ui.cmb_library_sections.currentText()
        prepend = self.ui.cmbbx_prepend.currentText()
        # Ask user to select files
        directory = self.ui.lned_playlist_directory.text()
        filter = ("M3U Files (*.m3u *.m3u8)", "All Files (*)")
        files = self.FileDialog(directory=directory, fmt=filter)
        # Upload files selected
        if files:
            if type(files) is str:
                files = [files]
            # TODO: Add status bar or window to let user know its processing playlists
            failed, response = pp.push_plex(plex=self.plex, prepend=prepend, section=section, v=self.variables, playlists=files)
            self.update_library_playlists(self.plex)
            if failed > 0:
                title = "Uh Oh!"
                buttons = QMessageBox.Ok
                msgtype = QMessageBox.Critical
                message = "{} error(s) encountered while trying to download playlists. \nResponse: {}".format(failed,
                                                                                                          response)
                msg = self.MessageBox(title, message, buttons, msgtype)
            else:
                # Let user know upload is complete
                title = "Uploads Complete!"
                buttons = QMessageBox.Ok
                msgtype = QMessageBox.Information
                # First Message
                message = "Your uploads are complete!"
                msg = self.MessageBox(title, message, buttons, msgtype)
        else:
            return

    def plex_download(self):
        # This function allows a user to download playlist from their plex library to their local computer
        print("download button pressed!")
        directory = self.ui.lned_export_directory.text()
        section = self.ui.cmb_library_sections.currentText()
        playlists = [playlist.text() for playlist in self.ui.list_library_playlist.selectedItems()]
        for name in playlists:
            playlist = self.plex.library.section(section).playlist(name)
            pp.export_playlist(directory, playlist, name)
        # Let user know downloads are complete
        title = "Download Complete"
        buttons = QMessageBox.Ok
        msgtype = QMessageBox.Information
        # First Message
        message = "Your downloads are complete!"
        msg = self.MessageBox(title, message, buttons, msgtype)


# main section
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(basedir, "icons", "plex-playlists.svg")))
    MainWindow = MainWindow()
    MainWindow.show()
    sys.exit(app.exec_())
