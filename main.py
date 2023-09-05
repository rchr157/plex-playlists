# import section
import json
import sys
import os
from plexapi.server import PlexServer
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QIcon
from main_ui import Ui_MainWindow
# from Custom_Widgets.Widgets import *

import playlist_module as pp
# TODO: Clean up logic for calling playlist module
# TODO: Check plex server, and token input is correct
# TODO: Highlight lineEdits and combobox during tutorial
# TODO: Create custom window for pop ups
# TODO: Optimize library section to prepend and directory
# TODO: Allow user to view changes in local playlists vs plex playlists and pick and choose edits
# TODO: Add Spotify functionality
    # TODO: Download and Upload playlists


basedir = os.path.dirname(__file__)


# class creation
class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.plex = None
        self.main_win = QMainWindow()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self.main_win)

        # Apply JSON Style Sheet
        # loadJsonStyle(self, self.ui)

        self.ui.stackedWidget.setCurrentWidget(self.ui.page_home)

        # load variables
        self.load_variables()

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
        # handle plex buttons
        self.ui.list_library_playlist.clicked.connect(lambda: self.update_plex_buttons())
        self.ui.btn_plex_connect.clicked.connect(lambda: self.connect_plex())
        self.ui.btn_plex_upload.clicked.connect(lambda: self.plex_upload())
        self.ui.btn_plex_download.clicked.connect(lambda: self.plex_download())
        self.ui.btn_plex_update.clicked.connect(lambda: self.plex_update())

        # Playlist Page
        self.ui.cmb_library_sections.currentTextChanged.connect(lambda: self.update_library_playlists())
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

    def MessageBox(self, title, message, btns, msgtype, details=None):
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(btns)
        msg.setIcon(msgtype)
        if details:
            msg.setDetailedText(details)
        x = msg.exec_()
        return x

    def FileDialog(self, directory='', forOpen=True, fmt=None, isFolder=False):
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
            dialog.setFileMode(QFileDialog.ExistingFiles)
        # OPENING OR SAVING
        dialog.setAcceptMode(QFileDialog.AcceptOpen) if forOpen else dialog.setAcceptMode(QFileDialog.AcceptSave)

        # SET FORMAT, IF SPECIFIED
        if fmt and isFolder is False:
            # dialog.setDefaultSuffix(fmt)
            dialog.setNameFilters(fmt)

        # SET THE STARTING DIRECTORY
        if directory != '':
            dialog.setDirectory(str(directory))
        else:
            dialog.setDirectory(str(os.path.dirname(os.path.abspath(__file__))))

        if dialog.exec_() == QDialog.Accepted:
            path = dialog.selectedFiles()  # returns a list
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
        data['prepends'] = [self.ui.cmb_playlist_prepend.itemText(i) for i in range(self.ui.cmb_playlist_prepend.count())]
        with open(os.path.join(cwd, 'settings.json'), 'w') as output:
            json.dump(data, output, indent=2, separators=(',', ': '))

        # Let user know Saving data is complete
        title = "Saving Complete!"
        buttons = QMessageBox.Ok
        msgtype = QMessageBox.Information
        # First Message
        message = "Your settings have been saved!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    def load_json(self):
        if self.variables['plex_server'] == '':
            # Ask user to select file to load variables
            filter = ("JSON Files (*.json)", "All Files (*)")
            file = self.FileDialog(directory=basedir, fmt=filter)
            if file:
                self.load_variables(file[0])
                return
        # Let user know Saving data is complete
        title = "Loading Complete!"
        buttons = QMessageBox.Ok
        msgtype = QMessageBox.Information
        # First Message
        message = "Your settings have been loaded!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    def load_variables(self, file=None):
        self.variables = pp.load_variables(file)
        if self.variables:
            # Playlist page
            self.ui.cmb_playlist_prepend.addItems(self.variables["prepends"])
            # Settings Page
            self.ui.lned_plex_server.setText(self.variables['plex_server'])
            self.change_button_ui(self.ui.lned_plex_server, stylesheet="color: white;")
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
        icons = {self.ui.btn_home_page: [":/golden/icons/gold/home-svgrepo-com.svg",":/light/icons/light/home-svgrepo-com.svg"],
                 self.ui.btn_plex_page: [":/golden/icons/gold/vinyl-svgrepo-com.svg", ":/light/icons/light/vinyl-svgrepo-com.svg"],
                 self.ui.btn_playlist_page: [":/golden/icons/gold/list-heart-svgrepo-com.svg", ":/light/icons/light/list-heart-svgrepo-com.svg"],
                 self.ui.btn_settings_page: [":/golden/icons/gold/settings-svgrepo-com.svg", ":/light/icons/light/settings-svgrepo-com.svg"],
                 }
        self.ui.stackedWidget.setCurrentWidget(page)
        for button in buttons:
            if button == btn:
                self.change_button_ui(button, stylesheet="background-color: black; border-color: black; color: #E5A00D;",
                                      icon=icons[button][0])
            else:
                self.change_button_ui(button,
                                      stylesheet="background-color: #1B1B1B; border-color: #1B1B1B; color: #BABABA;",
                                      icon=icons[button][1])

    def check_connect_btn(self):
        # Grab plex server url and token to connect
        plex_server = self.ui.lned_plex_server.text()
        plex_token = self.ui.lned_plex_token.text()
        if plex_server and plex_token:
            # self.ui.btn_plex_connect.setEnabled(True)
            # self.ui.btn_plex_connect.setStyleSheet("Background-color: Green; color: rgb(255, 255, 255)")
            self.change_button_ui(btn=self.ui.btn_plex_connect, enable=True, stylesheet="Background-color: Green; color: rgb(255, 255, 255)")
        else:
            # self.ui.btn_plex_connect.setEnabled(False)
            # self.ui.btn_plex_connect.setStyleSheet("")
            self.change_button_ui(btn=self.ui.btn_plex_connect, enable=False, stylesheet="")

    def change_button_ui(self, btn, enable=None, text=None, stylesheet=None, icon=None):
        if enable is not None:
            btn.setEnabled(enable)
        if text is not None:
            btn.setText(text)
        if stylesheet is not None:
            btn.setStyleSheet(stylesheet)
        if icon is not None:
            btn.setIcon(QIcon(QtGui.QPixmap(icon)))

    def update_plex_buttons(self):
        icons = {"download": [":/golden/icons/gold/cloud-download-svgrepo-com.svg",
                              ":/light/icons/light/cloud-download-svgrepo-com.svg"],
                 "update": [":/golden/icons/gold/refresh-svgrepo-com.svg",
                            ":/light/icons/light/refresh-svgrepo-com.svg"]}
        if len(self.ui.list_library_playlist.selectedItems()) > 0 and self.ui.btn_plex_download.isEnabled():
            # if button is already activated, do nothing
            return
        elif not self.ui.list_library_playlist.selectedItems():
            # If no items are selected, Disable Download and Update Buttons
            self.change_button_ui(self.ui.btn_plex_download, enable=False,
                                  stylesheet="border: 1px solid #51391B; color: #BABABA", icon=icons["download"][1])
            self.change_button_ui(self.ui.btn_plex_update, enable=False,
                                  stylesheet="border: 1px solid #51391B; color: #BABABA", icon=icons["update"][1])
        else:
            # Enable Download and Update Buttons
            self.change_button_ui(self.ui.btn_plex_download, enable=True,
                                  stylesheet="border: 1px solid #E5A00D; color: #E5A00D;", icon=icons["download"][0])
            self.change_button_ui(self.ui.btn_plex_update, enable=True,
                                  stylesheet="border: 1px solid #E5A00D; color: #E5A00D;", icon=icons["update"][0])

    # Main Page Functions
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

    # Plex Functions
    def connect_plex(self):
        print("Button Pressed")
        # Connect to Plex
        self.plex = PlexServer(self.variables['plex_server'], self.variables['plex_token'])
        # Adjust UI components
        self.change_button_ui(self.ui.btn_plex_connect, enable=False, text="Connected",
                              stylesheet="background-color: #51391B; color: #BABABA")  # Disable connect button
        self.change_button_ui(self.ui.cmb_library_sections, enable=True,
                              stylesheet="background-color: white; color: black;")  # Enable Section Dropdown
        self.change_button_ui(self.ui.cmb_library_prepend, enable=True,
                              stylesheet="background-color: white; color: black;")  # Enable Path Dropdown
        self.change_button_ui(self.ui.list_library_playlist, enable=True,
                              stylesheet="background-color: #565656; color: white;")  # Enable Playlist Dropdown
        self.update_library_sections(self.plex)

    def update_library_sections(self, plex):
        library_list = [section.title for section in plex.library.sections() if section.CONTENT_TYPE == 'audio']
        self.ui.cmb_library_sections.clear()
        self.update_plex_buttons()
        if library_list:
            self.ui.cmb_library_sections.addItem('Select a Music Library')
            self.ui.cmb_library_sections.addItems(library_list)
        self.ui.cmb_library_sections.update()
        self.update_library_playlists()

    def update_library_playlists(self):
        icons = [":/golden/icons/gold/cloud-upload-svgrepo-com.svg",
                 ":/light/icons/light/cloud-upload-svgrepo-com.svg"]
        # Grab selected section from dropdown
        section = self.ui.cmb_library_sections.currentText()
        self.ui.cmb_library_prepend.clear()
        self.ui.list_library_playlist.clear()
        if section != 'Select a Music Library':
            # Grab data path for selected library section
            self.ui.cmb_library_prepend.addItems(self.plex.library.section(section).locations)
            self.ui.cmb_playlist_prepend.addItems(self.plex.library.section(section).locations)
            # Grab available playlists for selected library section
            playlist_list = [playlist.title for playlist in self.plex.library.section(section).playlists()]
            if not playlist_list:
                # If no playlists found
                self.ui.list_library_playlist.addItems(["(Empty)"])
            else:
                if 'All Music' in playlist_list and self.ui.chkbx_ignore_all.isChecked():
                    # if "Ignore All Music" checkbox is checked, remove "All Music" Playlists
                    playlist_list.remove('All Music')
                    # TODO: Add Heart Tracks, Fresh Tracks, other plex generated ones
                self.ui.list_library_playlist.addItems(playlist_list)

            self.ui.list_library_playlist.update()
            self.change_button_ui(self.ui.btn_plex_upload, enable=True,
                                  stylesheet="border: 1px solid #E5A00D; color: #E5A00D;", icon=icons[0])
        else:
            self.change_button_ui(self.ui.btn_plex_upload, enable=False,
                                  stylesheet="border: 1px solid #51391B; color: #BABABA", icon=icons[1])

    def plex_upload(self):
        # This function allows a user to select playlist files to be uploaded to plex library
        print("upload button pressed!")
        # Get plex library details
        section = self.ui.cmb_library_sections.currentText()
        prepend = self.ui.cmb_library_prepend.currentText()
        # Ask user to select files
        directory = self.ui.lned_playlist_directory.text()
        filter = ("M3U Files (*.m3u *.m3u8)", "All Files (*)")
        files = self.FileDialog(directory=directory, fmt=filter)
        if not files:
            return

        # Upload files selected
        # TODO: Add status bar or window to let user know its processing playlists
        failed, response = pp.push_plex(plex=self.plex, prepend=prepend, section=section, v=self.variables,
                                        playlists=files)
        # Refresh playlist view
        self.update_library_playlists()
        if len(failed) > 0:
            title = "Uh Oh!"
            buttons = QMessageBox.Ok
            msgtype = QMessageBox.Critical
            message = "{} error(s) encountered while trying to download playlists. \nResponse: {}".format(failed,
                                                                                                          response)
            detail = "\n".join(failed)
            msg = self.MessageBox(title, message, buttons, msgtype, details=detail)
        else:
            # Let user know upload is complete
            title = "Uploads Complete!"
            buttons = QMessageBox.Ok
            msgtype = QMessageBox.Information
            # First Message
            message = "Your uploads are complete!"
            detail = "\n".join(files)
            msg = self.MessageBox(title, message, buttons, msgtype, details=detail)

    def plex_download(self):
        # This function allows a user to download playlist from their plex library to their local computer
        print("download button pressed!")
        directory = self.ui.lned_export_directory.text()
        if not directory:
            self.browse_export_directory()
            if not directory:
                return
        section = self.ui.cmb_library_sections.currentText()
        playlists = [playlist.text() for playlist in self.ui.list_library_playlist.selectedItems()]
        for name in playlists:
            # TODO: Add status bar or window to let user know its processing playlists
            playlist = self.plex.library.section(section).playlist(name)
            pp.export_playlist(directory, playlist, name)
        # Let user know downloads are complete
        title = "Download Complete"
        buttons = QMessageBox.Ok
        msgtype = QMessageBox.Information
        # First Message
        message = "Your downloads are complete!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    def plex_update(self):
        # This function allows a user to select playlist files to be uploaded to plex library
        print("upload button pressed!")

        # Get plex library details
        section = self.ui.cmb_library_sections.currentText()
        prepend = self.ui.cmb_library_prepend.currentText()
        playlists = [item.text() for item in self.ui.list_library_playlist.selectedItems()]

        # Confirm with user that the following playlists will be deleted, allow user to cancel
        title = "Replacing Playlists"
        message = ("This operation will delete your playlists on your plex server. It is recommended you download "
                   "copies incase this operation encounters any issues. See details for playlists.")
        btns = QMessageBox.Ok | QMessageBox.Cancel
        msgtype = QMessageBox.Warning
        detail = "\n".join(playlists)
        msg = self.MessageBox(title, message, btns, msgtype, details=detail)
        if msg == QMessageBox.Cancel:
            return

        # Ask user to select files
        directory = self.ui.lned_playlist_directory.text()
        filter = ("M3U Files (*.m3u *.m3u8)", "All Files (*)")
        files = self.FileDialog(directory=directory, fmt=filter)
        if not files:
            return

        # Compare selected files to playlists available
        new_list, pre_notavail = pp.check_playlist_availability(files, playlists)

        # Upload files selected
        tempdir = os.path.join(basedir, "temp")  # temp directory for download
        for name in playlists:
            playlist = self.plex.library.section(section).playlist(name)
            pp.export_playlist(tempdir, playlist, name)  # download copy of playlist prior to deleting
            self.plex.library.section(section).playlist(name).delete()  # delete playlist from plex
        # TODO: Add status bar or window to let user know its processing playlists
        failed, response = pp.push_plex(plex=self.plex, prepend=prepend, section=section, v=self.variables,
                                        playlists=new_list)  # push new playlist to plex
        # notify user of playlists not available to update
        if len(pre_notavail) > 0:
            title = "Playlists Not Available"
            message = ('Oh!\nLooks like some files were not located on your server.\n\nWould you '
                       'like to upload them?\n\nSee details for list of files.')
            btns = QMessageBox.Ok | QMessageBox.Cancel
            msgtype = QMessageBox.Warning
            detail = "\n".join(pre_notavail)
            msg_up = self.MessageBox(title, message, btns, msgtype, details=detail)
            if msg_up == QMessageBox.Ok:
                failed, response = pp.push_plex(plex=self.plex, prepend=prepend, section=section, v=self.variables,
                                                playlists=pre_notavail)

        # Check that playlists were uploaded
        self.update_library_playlists()
        # Get updated list of playlists
        playlists = [item.text() for item in self.ui.list_library_playlist.selectedItems()]
        match, post_notavail = pp.check_playlist_availability(files, playlists)

        # notify user of playlists not available to update
        if len(post_notavail) > 0:
            title = "Playlists Updated with Issues"
            message = ('Playlist updated with some issues. Some files failed to be replaced. See details for list. Downloaded copies located: '
                       '\n{}'.format(tempdir))
            btns = QMessageBox.Ok | QMessageBox.Cancel
            msgtype = QMessageBox.Warning
            detail = "\n".join(post_notavail)
            msg = self.MessageBox(title, message, btns, msgtype, details=detail)
        else:
            # Clean up downloaded copies of playlists
            for file in files:
               check_file = os.path.join(tempdir, os.path.basename(file))
               if check_file:
                   os.remove(check_file)

            # Notify user updating playlist complete
            title = "Playlists Updated"
            message = 'Playlist update completed without issues! '
            btns = QMessageBox.Ok
            msgtype = QMessageBox.Information
            detail = "\n".join(files)
            msg = self.MessageBox(title, message, btns, msgtype, details=detail)


    # Playlist Functions
    def convert_playlists(self):
        # This function changes the prepend (path to file) for a playlist
        # Example: Change "Z:\home\user\data\media\music\main" to "/volume1/media/Music/All Music"
        prepend = self.ui.cmb_playlist_prepend.currentText()
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
        prepend = self.ui.cmb_playlist_prepend.currentText()
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

    # Settings Function
    def ignore_toggle(self):
        if self.ui.btn_plex_connect.text() == 'Connected':
            self.update_library_sections(self.plex)

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

    def add_prepend(self):
        # This function adds a new prepend option in the dropdown box
        new_prepend = self.ui.lned_custom_prepend.text()
        if new_prepend:
            print('Add button pressed!')
            self.variables["prepends"].append(new_prepend)
            self.ui.cmb_playlist_prepend.addItem(new_prepend)
            self.ui.cmb_playlist_prepend.update()
            self.ui.cmb_playlist_prepend.setCurrentText(new_prepend)
            self.ui.cmb_library_prepend.addItem(new_prepend)
            self.ui.cmb_library_prepend.update()
            self.ui.cmb_library_prepend.setCurrentText(new_prepend)
            self.ui.lned_custom_prepend.clear()


# main section
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(basedir, "icons", "dark", "plex-playlists.svg")))
    MainWindow = MainWindow()
    MainWindow.show()
    sys.exit(app.exec_())
