# import section
import json
import sys
import os
import logging
import time
import threading
from plexapi.server import PlexServer
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from contextlib import contextmanager
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QIcon
from main_ui import Ui_MainWindow
from dialog_ui import Ui_Dialog
from progress_bar_ui import Ui_Form
# from Custom_Widgets.Widgets import *

import playlist_module as pp

# <editor-fold desc="############### General TODOs ###############"
# TODO: Organize icons, rename files
# TODO: Clean up logic for calling playlist module
# TODO: Check plex server, and token input is correct
# TODO: Highlight lineEdits and combobox during tutorial
# TODO: Create custom window for pop ups
# TODO: Optimize library section to prepend and directory
# TODO: Allow user to view changes in local playlists vs plex playlists and pick and choose edits
# TODO: Add Spotify functionality
# TODO: Download and Upload playlists
# </editor-fold>


# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s: %(message)s')
file_handler = logging.FileHandler('main.log')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

basedir = os.path.dirname(__file__)


# <editor-fold desc="############### Generic functions ###############">
def create_export_directory(export_directory: str, service: str):
    service_directory = os.path.join(export_directory, service)
    if not os.path.exists(service_directory):
        logger.info(f"{service} folder not found in export path. Creating {service} folder: {service_directory}")
        os.mkdir(service_directory)
    return service_directory


# </editor-fold>


# class creation

class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__(parent=None)
        logger.debug("Initiating Application.")
        self.variables = None
        self.plex = None
        self.spotify = None
        self.spotify_user = None

        self.main_win = QMainWindow()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self.main_win)

        # Apply JSON Style Sheet
        # loadJsonStyle(self, self.ui)  # For future use

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
        self.ui.btn_spotify_page.clicked.connect(lambda: self.page_clicked(self.ui.page_spotify,
                                                                           self.ui.btn_spotify_page))
        self.ui.btn_playlist_page.clicked.connect(lambda: self.page_clicked(self.ui.page_playlists,
                                                                            self.ui.btn_playlist_page))
        self.ui.btn_settings_page.clicked.connect(lambda: self.page_clicked(self.ui.page_settings,
                                                                            self.ui.btn_settings_page))

        # Main Page
        # handle Tutorial checkbox
        self.ui.btn_tutorial.clicked.connect(lambda: self.test_func())  # lambda: self.tutorial_btn_clicked()

        # Plex Page
        # handle plex buttons
        self.ui.btn_plex_connect.clicked.connect(lambda: self.plex_connect())
        self.ui.list_library_playlist.clicked.connect(lambda: self.update_plex_buttons())
        self.ui.btn_plex_download.clicked.connect(lambda: self.plex_download())
        self.ui.btn_plex_upload.clicked.connect(lambda: self.plex_upload())
        self.ui.btn_plex_update.clicked.connect(lambda: self.plex_transfer())

        # Spotify Page
        self.ui.btn_spotify_connect.clicked.connect(lambda: self.spotify_connect())
        self.ui.list_spotify_playlist.clicked.connect(lambda: self.spotify_update_buttons())
        self.ui.btn_spotify_download.clicked.connect(lambda: self.spotify_download())
        self.ui.btn_spotify_upload.clicked.connect(lambda: self.spotify_upload())
        self.ui.btn_spotify_update.clicked.connect(
            lambda: self.spotify_transfer())  # TODO:combine update and upload functionality

        # Playlist Page
        self.ui.cmb_library_sections.currentTextChanged.connect(lambda: self.plex_update_playlists())
        self.ui.btn_add_prepend.clicked.connect(lambda: self.add_prepend())
        self.ui.btn_playlist_convert.clicked.connect(lambda: self.convert_playlists())
        self.ui.btn_playlist_combine.clicked.connect(lambda: self.combine_playlists())

        # Settings Page
        # handle buttons & link
        self.ui.lned_plex_server.textChanged.connect(lambda: self.check_plex_connect_btn())
        self.ui.lned_plex_token.textChanged.connect(lambda: self.check_plex_connect_btn())
        self.ui.chkbx_ignore_all.toggled.connect(lambda: self.ignore_toggle())
        self.ui.btn_playlist_directory.clicked.connect(lambda: self.browse_playlist_directory())
        self.ui.btn_export_directory.clicked.connect(lambda: self.browse_export_directory())

    def show(self):
        self.main_win.show()

    # <editor-fold desc="############### Custom Functions ###############">
    def MessageBox(self, title, message, btns, msgtype, details=None):
        msg = MessageDialog()
        msg.set_details(title, message, btns)
        x = msg.exec_()
        return x

    def FileDialog(self, directory='', for_open=True, fmt=None, is_folder=False):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        options |= QFileDialog.DontUseCustomDirectoryIcons
        dialog = QFileDialog()
        dialog.setOptions(options)

        dialog.setFilter(dialog.filter() | QtCore.QDir.Hidden)

        # ARE WE TALKING ABOUT FILES OR FOLDERS
        if is_folder:
            dialog.setFileMode(QFileDialog.DirectoryOnly)
        else:
            dialog.setFileMode(QFileDialog.ExistingFiles)
        # OPENING OR SAVING
        dialog.setAcceptMode(QFileDialog.AcceptOpen) if for_open else dialog.setAcceptMode(QFileDialog.AcceptSave)

        # SET FORMAT, IF SPECIFIED
        if fmt and is_folder is False:
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

    # </editor-fold>

    # <editor-fold desc="############### General Functions ###############">
    def test_func(self):
        logger.debug("Creating Progress Bar Dialog box")
        progressbar = ProgressBar(func='test_func', **{"file": "test_file.m3u", "section": "plex_section"})
        logger.debug("Executing progressbar function: plex_to_m3u()")

        # Let user know downloads are complete
        logger.info("Downloading from Spotify completed!")
        title = "Download Complete"
        buttons = ['Ok']
        msgtype = QMessageBox.Information
        # First Message
        message = "Your downloads are complete!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    def get_directories(self, playlist=False, export=False):
        playlist_directory = self.ui.lned_playlist_directory.text()
        export_directory = self.ui.lned_export_directory.text()
        if export and not export_directory:
            title = "Select Export Directory"
            message = "Select a directory where you want your playlists to be saved at."
            btns = ['Ok']
            msgtype = QMessageBox.Information
            msg = self.MessageBox(title=title, message=message, btns=btns, msgtype=msgtype)
            export_directory = self.browse_export_directory()
            if not export_directory:
                export_directory = None
        if playlist and not playlist_directory:
            title = "Select Playlist Directory"
            message = "Select a directory where you want your playlists to be saved at."
            btns = ['Ok']
            msgtype = QMessageBox.Information
            msg = self.MessageBox(title=title, message=message, btns=btns, msgtype=msgtype)
            export_directory = self.browse_export_directory()
        return playlist_directory, export_directory

    def get_plex_selections(self):
        section = self.ui.cmb_library_sections.currentText()
        # if section == "Select a Music Library":
        #     title = "Select a music library"
        #     message = "Before transferring playlist to plex, make sure you have a library selected"
        #     btns = ['Ok']
        #     msg = self.MessageBox(title=title, message=message, btns=btns, msgtype=None)
        #     return
        logger.debug(f"Selected '{section}' Section")
        selected_section = self.plex.library.section(section)
        playlists = [item.text() for item in self.ui.list_library_playlist.selectedItems()]
        logger.debug(f"Selected {len(playlists)} Playlists")
        return selected_section, playlists

    def get_spotify_selections(self):
        return [playlist.text() for playlist in self.ui.list_spotify_playlist.selectedItems()]

    def get_files(self):
        directory, _ = self.get_directories(playlist=True)
        fmt_filter = ("M3U Files (*.m3u *.m3u8)", "All Files (*)")
        files = self.FileDialog(directory=directory, fmt=fmt_filter)
        if not files:
            return None
        elif type(files) is not list:
            logger.debug("File chosen not returned as list, will convert to list.")
            files = [files]
        return files

    # Save Settings to Json
    def save_json(self):
        cwd = os.path.dirname(os.path.abspath(__file__))
        data = {}
        data['plex_server'] = self.ui.lned_plex_server.text()
        data['plex_token'] = self.ui.lned_plex_token.text()
        data['playlist_directory'] = self.ui.lned_playlist_directory.text()
        data['export_directory'] = self.ui.lned_export_directory.text()
        data['prepends'] = [self.ui.cmb_playlist_prepend.itemText(i) for i in
                            range(self.ui.cmb_playlist_prepend.count())]
        data["spotify_client_id"] = self.ui.lned_spotify_clientid.text()
        data["spotify_client_secret"] = self.ui.lned_spotify_secret.text()
        data["spotify_redirect_uri"] = self.ui.lned_spotify_redirect.text()

        with open(os.path.join(cwd, 'settings.json'), 'w') as output:
            json.dump(data, output, indent=2, separators=(',', ': '))

        # Let user know Saving data is complete
        title = "Saving Complete!"
        buttons = ['Ok']
        msgtype = QMessageBox.Information
        # First Message
        message = "Your settings have been saved!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    def load_json(self):
        # if self.variables['plex_server'] == '':
        # Ask user to select file to load variables
        fmt_filter = ("JSON Files (*.json)", "All Files (*)")
        file = self.FileDialog(directory=basedir, fmt=fmt_filter)
        if file:
            self.load_variables(file[0])
            return

        # Let user know Saving data is complete
        title = "Loading Complete!"
        buttons = ['Ok']
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
            self.ui.lned_plex_server.setText(self.variables["plex_server"])
            self.change_button_ui(self.ui.lned_plex_server, stylesheet="color: white;")
            self.ui.lned_plex_token.setText(self.variables["plex_token"])
            self.ui.lned_playlist_directory.setText(self.variables["playlist_directory"])
            self.ui.lned_export_directory.setText(self.variables["export_directory"])
            self.ui.lned_spotify_clientid.setText(self.variables["spotify_client_id"])
            self.ui.lned_spotify_secret.setText(self.variables["spotify_client_secret"])
            self.ui.lned_spotify_redirect.setText(self.variables["spotify_redirect_uri"])

            self.check_plex_connect_btn()
            self.check_spotify_connect_btn()
        else:
            self.variables = None

    # Side Panel functions
    def page_clicked(self, page, btn):
        buttons = [self.ui.btn_home_page, self.ui.btn_plex_page, self.ui.btn_spotify_page,
                   self.ui.btn_playlist_page, self.ui.btn_settings_page]
        icons = {self.ui.btn_home_page: [":/golden/icons/gold/home-svgrepo-com.svg",
                                         ":/light/icons/light/home-svgrepo-com.svg"],
                 self.ui.btn_plex_page: [":/golden/icons/gold/plex-svgrepo-com.svg",
                                         ":/light/icons/light/plex-svgrepo-com.svg"],
                 self.ui.btn_spotify_page: [":/golden/icons/gold/spotify-svgrepo-com.svg",
                                            ":light/icons/light/spotify-svgrepo-com.svg"],
                 self.ui.btn_playlist_page: [":/golden/icons/gold/list-heart-svgrepo-com.svg",
                                             ":/light/icons/light/list-heart-svgrepo-com.svg"],
                 self.ui.btn_settings_page: [":/golden/icons/gold/settings-svgrepo-com.svg",
                                             ":/light/icons/light/settings-svgrepo-com.svg"],
                 }
        self.ui.stackedWidget.setCurrentWidget(page)
        for button in buttons:
            if button == btn:
                self.change_button_ui(button,
                                      stylesheet="background-color: black; border-color: black; color: #E5A00D;",
                                      icon=icons[button][0])
            else:
                self.change_button_ui(button,
                                      stylesheet="background-color: #1B1B1B; border-color: #1B1B1B; color: #BABABA;",
                                      icon=icons[button][1])

    def check_plex_connect_btn(self):
        logger.debug("Checking conditions to enable Plex Connect button.")
        # Grab plex server url and token to connect
        plex_server = self.ui.lned_plex_server.text()
        plex_token = self.ui.lned_plex_token.text()
        if plex_server and plex_token:
            logger.debug("All necessary Plex API details have been provided. Enabling Connect button.")
            self.change_button_ui(btn=self.ui.btn_plex_connect, enable=True,
                                  stylesheet="Background-color: Green; color: rgb(255, 255, 255)")
        else:
            logger.debug("One or more Plex API details missing. Disabling Connect button.")
            self.change_button_ui(btn=self.ui.btn_plex_connect, enable=False, stylesheet="")

    @staticmethod
    def change_button_ui(btn, enable=None, text=None, stylesheet=None, icon=None):
        if enable is not None:
            btn.setEnabled(enable)
        if text is not None:
            btn.setText(text)
        if stylesheet is not None:
            btn.setStyleSheet(stylesheet)
        if icon is not None:
            btn.setIcon(QIcon(QtGui.QPixmap(icon)))

    def update_plex_buttons(self):
        logger.debug("Updating Plex buttons. Checking Conditions.")
        icons = {"download": [":/golden/icons/gold/cloud-download-svgrepo-com.svg",
                              ":/light/icons/light/cloud-download-svgrepo-com.svg"],
                 "update": [":/golden/icons/gold/spotify-svgrepo-com.svg",
                            ":/light/icons/light/spotify-svgrepo-com.svg"]}
        if len(self.ui.list_library_playlist.selectedItems()) > 0 and self.ui.btn_plex_download.isEnabled():
            # if button is already activated, do nothing
            return
        elif not self.ui.list_library_playlist.selectedItems():
            # If no items are selected, Disable Download and Update Buttons
            logger.debug("No Items selected. Disabling Buttons")
            self.change_button_ui(self.ui.btn_plex_download, enable=False,
                                  stylesheet="border: 1px solid #51391B; color: #BABABA", icon=icons["download"][1])
            self.change_button_ui(self.ui.btn_plex_update, enable=False,
                                  stylesheet="border: 1px solid #51391B; color: #BABABA", icon=icons["update"][1])
        else:
            # Enable Download and Update Buttons
            logger.debug("Items selected. Enabling buttons.")
            self.change_button_ui(self.ui.btn_plex_download, enable=True,
                                  stylesheet="border: 1px solid #E5A00D; color: #E5A00D;", icon=icons["download"][0])
            self.change_button_ui(self.ui.btn_plex_update, enable=True,
                                  stylesheet="border: 1px solid #E5A00D; color: #E5A00D;", icon=icons["update"][0])

    # Main Page Functions
    def tutorial_btn_clicked(self):
        logger.debug("'Get Started' Button Pressed")
        title = "Getting Started"
        buttons = ['Ok', 'Cancel']
        msgtype = QMessageBox.Information
        # First Message
        message = ("Lets get started! \nStart by going to the settings tab and entering your plex info."
                   "\n\nNote: You can always end this guide by pressing cancel at any point.")
        msg = self.MessageBox(title, message, buttons, msgtype)
        if msg == QDialog.Rejected:
            return

        # Go to Setting page to enter
        self.page_clicked(self.ui.page_settings, self.ui.btn_settings_page)

        message = "This tab contains settings for handling your plex connection and your playlist."
        msg = self.MessageBox(title, message, buttons, msgtype)
        if msg == QDialog.Rejected:
            return

        message = "Enter your plex server and plex token in order to connect."
        msg = self.MessageBox(title, message, buttons, msgtype)
        if msg == QDialog.Rejected:
            return

        message = ("You can also enter the directory where your playlists are located at and where to export it. "
                   "\nNote: Your playlist directory should be visible to your plex.")
        msg = self.MessageBox(title, message, buttons, msgtype)
        if msg == QDialog.Rejected:
            return

        # self.ui.menuFile.window()
        message = (
            "You can save any changes made in this application. A 'settings.json' is generated whenever you save."
            "\n\nYou can also load any changes made manually in the json file as well.")
        msg = self.MessageBox(title, message, buttons, msgtype)
        if msg == QDialog.Rejected:
            return

        # Go to Plex page
        self.page_clicked(self.ui.page_plex, self.ui.btn_plex_page)

        message = (
            "On the Plex tab, you can select what music library you want to operate in.")
        msg = self.MessageBox(title, message, buttons, msgtype)
        if msg == QDialog.Rejected:
            return

        message = (
            "The download button lets you download playlists from your plex to your local folders.\n\n"
            "The upload button lets you upload from your local folder to your plex library.\n"
            "Note: Make sure your playlist is located in a folder your plex server has access to.")
        msg = self.MessageBox(title, message, buttons, msgtype)
        if msg == QDialog.Rejected:
            return

        # Go to Playlist Page
        self.page_clicked(self.ui.page_playlists, self.ui.btn_playlist_page)

        message = ("On the playlist tab, you can quickly format the song paths in your playlist so that plex can"
                   " find the songs.")
        msg = self.MessageBox(title, message, buttons, msgtype)
        if msg == QDialog.Rejected:
            return

        message = (
            "You can also combine playlists to keep your local and plex playlists synched.")
        msg = self.MessageBox(title, message, buttons, msgtype)
        if msg == QDialog.Rejected:
            return

    # </editor-fold>

    # <editor-fold desc="############### PLEX Page Functions ###############">
    # Plex Functions
    def plex_connect(self):
        logger.debug("Plex Connect button pressed")
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
        self.plex_update_sections()
        logger.info("Connected to Plex server successfully.")

        if self.ui.btn_spotify_connect.text() != 'Connected' and self.ui.btn_spotify_connect.isEnabled():
            self.spotify_connect()

    def plex_update_sections(self):
        # TODO: Refactor plex_update_sections function
        logger.info("Checking available library sections from Plex.")
        available_sections = [section.title for section in self.plex.library.sections() if
                              section.CONTENT_TYPE == 'audio']
        self.ui.cmb_library_sections.clear()
        # self.update_plex_buttons()
        if available_sections:
            logger.debug("Adding Plex Library sections to dropdown menu.")
            self.ui.cmb_library_sections.addItem('Select a Music Library')
            self.ui.cmb_library_sections.addItems(available_sections)
        self.ui.cmb_library_sections.update()
        self.plex_update_playlists()

    def plex_update_playlists(self):
        # TODO: Refactor plex_update_playlists function
        logger.info("Checking available playlist for selected Plex library section.")
        icons = [":/golden/icons/gold/cloud-upload-svgrepo-com.svg",
                 ":/light/icons/light/cloud-upload-svgrepo-com.svg"]
        # Grab selected section from dropdown
        selected_section = self.ui.cmb_library_sections.currentText()
        self.ui.cmb_library_prepend.clear()
        self.ui.list_library_playlist.clear()
        if selected_section != 'Select a Music Library':
            # Grab data path for selected library section
            self.ui.cmb_library_prepend.addItems(self.plex.library.section(selected_section).locations)
            self.ui.cmb_playlist_prepend.addItems(self.plex.library.section(selected_section).locations)
            # Grab available playlists for selected library section
            available_playlists = [playlist.title for playlist in
                                   self.plex.library.section(selected_section).playlists()]
            if not available_playlists:
                # If no playlists found
                logger.debug(f"No playlists found in {selected_section} library.")
                self.ui.list_library_playlist.addItems(["(Empty)"])
            else:
                logger.debug(
                    f"{len(available_playlists)} playlists found in {selected_section} library. Updating List View")
                if 'All Music' in available_playlists and self.ui.chkbx_ignore_all.isChecked():
                    # if "Ignore All Music" checkbox is checked, remove "All Music" Playlists
                    logger.debug("Ignoring 'All Music' playlist in library.")
                    available_playlists.remove('All Music')
                    # TODO: Add Heart Tracks, Fresh Tracks, other plex generated ones
                self.ui.list_library_playlist.addItems(available_playlists)

            self.ui.list_library_playlist.update()
            self.change_button_ui(self.ui.btn_plex_upload, enable=True,
                                  stylesheet="border: 1px solid #E5A00D; color: #E5A00D;", icon=icons[0])
        else:
            logger.debug(f"Dropdown still in 'Select a Music Library' option. Disabling Upload button.")
            self.change_button_ui(self.ui.btn_plex_upload, enable=False,
                                  stylesheet="border: 1px solid #51391B; color: #BABABA", icon=icons[1])

    def plex_upload(self):
        # TODO: Refactor plex_upload function
        # This function allows a user to select m3u playlist files to be uploaded to plex library
        logger.debug("Plex Upload button has been pressed!")
        # Get plex library details
        selected_section, _ = self.get_plex_selections()

        # Ask user to select files
        files = self.get_files()
        if files is None: return

        for file in files:
            logger.debug(f"Uploading '{file}' to Plex.")
            # pp.m3u_to_plex(section=selected_section, file=file)
            logger.debug("Creating Progress Bar Dialog box")
            ProgressBar(func='m3u_to_plex', **{"section": selected_section, "file": file})
            logger.info(f"Playlist '{file}' uploaded to Plex.")

        # Refresh playlist view
        logger.debug("Refreshing Plex playlist view.")
        self.plex_update_playlists()
        # Let user know upload is complete
        title = "Uploads Complete!"
        buttons = ['Ok']
        msgtype = QMessageBox.Information
        # First Message
        message = "Your uploads are complete!"
        detail = "\n".join(files)
        msg = self.MessageBox(title, message, buttons, msgtype, details=detail)

    def plex_download(self):
        # TODO: Refactor plex_download function
        # This function allows a user to download playlist from their plex library to their local computer
        logger.debug("Plex Download button has been pressed!")
        # Get export directory
        _, export_directory = self.get_directories(export=True)
        # Get selected section and playlists
        selected_section, selected_playlists = self.get_plex_selections()
        # Create plex directory if one does not exist
        plex_directory = create_export_directory(export_directory=export_directory, service='plex')

        # download all playlists
        for name in selected_playlists:
            # TODO: Check if file already exists if it needs to be overwritten or cancel operation
            file = os.path.join(plex_directory, f"{name}.m3u")
            # TODO: handle condition where file already exists, overwrite or cancel
            logger.debug(f"Downloading '{name}' playlist from Plex as m3u.")
            # pp.plex_to_m3u(section=selected_section, file=file)
            logger.debug("Creating Progress Bar Dialog box")
            ProgressBar(func='plex_to_m3u', **{"section": selected_section, "file": file})
            logger.info(f"Plex playlist '{name}' downloaded to {file}.")

        # Let user know downloads are complete
        logger.info("Downloading from Plex complete.")
        title = "Download Complete"
        buttons = ['Ok']
        msgtype = QMessageBox.Information
        # First Message
        message = "Your downloads are complete!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    def plex_transfer(self):
        # TODO: Refactor plex_update function
        # This function allows a user to select playlist files to be uploaded to plex library
        logger.debug("Plex Upload button pressed!")

        # Get plex library details
        logger.debug("Getting plex selection")
        selected_section, selected_playlists = self.get_plex_selections()

        # Upload files selected
        for name in selected_playlists:
            logger.debug(f"Transferring Plex playlist '{name}' to Spotify.")
            # pp.plex_to_spotify(sp=self.spotify, section=selected_section, playlist=name)  # push new playlist to plex
            logger.debug("Creating Progress Bar Dialog box")
            ProgressBar(func='plex_to_spotify', **{"sp": self.spotify, "section": selected_section,
                                                   "playlist": name})
            logger.info(f"Plex playlist '{name}' transferred to Spotify.")

        # Check that playlists were uploaded
        logger.debug("Refreshing Spotify playlist view.")
        self.spotify_update_playlists()
        # Notify user updating playlist complete
        title = "Playlists Updated"
        message = 'Playlist update completed without issues! '
        btns = ['Ok']
        msgtype = QMessageBox.Information
        detail = "\n".join(selected_playlists)
        msg = self.MessageBox(title, message, btns, msgtype, details=detail)

    # </editor-fold>

    # <editor-fold desc="############### Spotify Page Functions ###############">
    # Spotify Functions
    def check_spotify_connect_btn(self):
        # Grab plex server url and token to connect
        logger.debug("Checking conditions to enable Spotify Connect button.")
        spotify_clientid = self.ui.lned_spotify_clientid.text()
        spotify_secret = self.ui.lned_spotify_secret.text()
        spotify_redirect = self.ui.lned_spotify_redirect.text()
        if spotify_clientid and spotify_redirect and spotify_secret:
            logger.debug("All necessary Spotify API details have been provided. Enabling Connect button.")
            self.change_button_ui(btn=self.ui.btn_spotify_connect, enable=True,
                                  stylesheet="Background-color: Green; color: rgb(255, 255, 255)")
        else:
            logger.debug("One or more Spotify API details missing. Disabling Connect button.")
            self.change_button_ui(btn=self.ui.btn_spotify_connect, enable=False, stylesheet="")

    def spotify_connect(self):
        logger.debug("Connecting to Spotify")

        scope = "playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public"

        self.spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=self.variables["spotify_client_id"],
                                                                 client_secret=self.variables["spotify_client_secret"],
                                                                 redirect_uri=self.variables["spotify_redirect_uri"],
                                                                 scope=scope))
        self.spotify_user = self.spotify.me()['id']
        # Adjust UI components
        self.change_button_ui(self.ui.btn_spotify_connect, enable=False, text="Connected",
                              stylesheet="background-color: #51391B; color: #BABABA")  # Disable connect button
        self.change_button_ui(self.ui.cmb_spotify_prepend, enable=True,
                              stylesheet="background-color: white; color: black;")  # Enable Path Dropdown
        self.change_button_ui(self.ui.list_spotify_playlist, enable=True,
                              stylesheet="background-color: #565656; color: white;")  # Enable Playlist Dropdown
        # Update list view
        self.spotify_update_playlists()
        logger.info("Successfully connected to Spotify!")

        if self.ui.btn_plex_connect.text() != 'Connected' and self.ui.btn_plex_connect.isEnabled():
            self.plex_connect()

    def spotify_update_playlists(self):
        logger.debug("Updating Spotify playlists.")
        icons = [":/golden/icons/gold/cloud-upload-svgrepo-com.svg",
                 ":/light/icons/light/cloud-upload-svgrepo-com.svg"]
        # Clear objects and update libraries available on spotify
        self.ui.list_spotify_playlist.clear()
        self.ui.cmb_spotify_prepend.addItems(self.variables['prepends'])
        self.ui.cmb_spotify_prepend.setCurrentText(self.variables['prepends'][0])
        self.ui.cmb_playlist_prepend.addItems(self.variables['prepends'])
        self.ui.cmb_playlist_prepend.setCurrentText(self.variables['prepends'][0])
        # Grab available playlists for selected library section
        available_playlists = pp.spotify_get_available_playlists(self.spotify)
        if not available_playlists:
            # If no playlists found
            logger.debug("No playlists were returned from Spotify.")
            self.ui.list_spotify_playlist.addItems(["(Empty)"])
        else:
            logger.debug("List view has been updated with playlists returned by Spotify")
            self.ui.list_spotify_playlist.addItems(list(available_playlists.keys()))

        self.ui.list_spotify_playlist.update()
        self.change_button_ui(self.ui.btn_spotify_upload, enable=True,
                              stylesheet="border: 1px solid #E5A00D; color: #E5A00D;", icon=icons[0])
        return

    def spotify_update_buttons(self):
        logger.debug("Updating Buttons on Spotify page.")
        icons = {"download": [":/golden/icons/gold/cloud-download-svgrepo-com.svg",
                              ":/light/icons/light/cloud-download-svgrepo-com.svg"],
                 "update": [":/golden/icons/gold/plex-svgrepo-com.svg",
                            ":/light/icons/light/plex-svgrepo-com.svg"]}
        if len(self.ui.list_spotify_playlist.selectedItems()) > 0 and self.ui.btn_spotify_download.isEnabled():
            # if button is already activated, do nothing
            return
        elif not self.ui.list_spotify_playlist.selectedItems():
            # If no items are selected, Disable Download and Update Buttons
            self.change_button_ui(self.ui.btn_spotify_download, enable=False,
                                  stylesheet="border: 1px solid #51391B; color: #BABABA", icon=icons["download"][1])
            self.change_button_ui(self.ui.btn_spotify_update, enable=False,
                                  stylesheet="border: 1px solid #51391B; color: #BABABA", icon=icons["update"][1])
        else:
            # Enable Download and Update Buttons
            self.change_button_ui(self.ui.btn_spotify_download, enable=True,
                                  stylesheet="border: 1px solid #E5A00D; color: #E5A00D;", icon=icons["download"][0])
            self.change_button_ui(self.ui.btn_spotify_update, enable=True,
                                  stylesheet="border: 1px solid #E5A00D; color: #E5A00D;", icon=icons["update"][0])

    def spotify_download(self):
        # TODO: Refactor spotify_download function
        logger.debug("Spotify Download Button has been pressed!")
        # Get export path
        logger.debug("Getting export path.")
        _, export_directory = self.get_directories(export=True)

        # Get prepend to include in download
        logger.debug("Getting prepend path to add to tracks.")
        prepend = self.ui.cmb_spotify_prepend.currentText()

        # Get playlist selections
        logger.debug("Getting playlist selections.")
        selected_playlists = self.get_spotify_selections()
        logger.debug(f"{len(selected_playlists)} playlist selected.")
        # Create folder if one does not exist
        spotify_directory = create_export_directory(export_directory=export_directory, service='spotify')

        # Download selected playlists
        logger.info(f"Downloading {len(selected_playlists)} playlist(s) from Spotify.")
        for name in selected_playlists:
            # create export file
            logger.debug(f"Creating export path for playlist '{name}'.")
            export_file = os.path.join(spotify_directory, f"{name}.m3u")

            logger.debug(f"Downloading Spotify playlist '{name}' as m3u.")
            # pp.spotify_to_m3u(sp=self.spotify, playlist=name, prepend=prepend, export_file=export_file)
            logger.debug("Creating Progress Bar Dialog box")
            ProgressBar(func='spotify_to_m3u', **{"sp": self.spotify, "playlist": name, "prepend": prepend,
                                                  "export_file": export_file})
            logger.info(f"Playlist '{name}' has been downloaded to {export_file}.")

        # Let user know downloads are complete
        logger.info("Downloading from Spotify completed!")
        title = "Download Complete"
        buttons = ['Ok']
        msgtype = QMessageBox.Information
        # First Message
        message = "Your downloads are complete!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    def spotify_upload(self):
        # TODO: Refactor spotify_upload function
        logger.debug("Spotify Upload button has been pressed!")
        # Ask user to select files
        logger.debug("Asking user to select files to upload.")
        files = self.get_files()
        if files is None: return

        logger.info(f"{len(files)} Files selected.")

        for file in files:
            name = os.path.basename(os.path.splitext(file)[0])
            logger.debug(f"Uploading playlist '{name}' to Spotify.")
            # pp.m3u_to_spotify(sp=self.spotify, file=file)
            logger.debug("Creating Progress Bar Dialog box")
            ProgressBar(func='m3u_to_spotify', **{"sp": self.spotify, "file": file})
            logger.info(f"Playlist '{name}' has been uploaded to Spotify.")

            logger.debug("Updating List view of playlists for spotify.")
            self.spotify_update_playlists()

        # Let user know uploading is complete
        title = "Upload Complete"
        message = ("Upload Complete!")
        btns = ['Ok']
        msgtype = QMessageBox.Warning
        # detail = "\n".join(failed)
        msg = self.MessageBox(title=title, message=message, btns=btns, msgtype=msgtype)

    def spotify_transfer(self):
        # TODO: Refactor plex_update function
        # This function allows a user to select playlist files to be uploaded to plex library
        logger.debug("Plex Upload button pressed!")

        # Get spotify details
        logger.debug("Getting selected Plex Section")
        selected_section, _ = self.get_plex_selections()

        logger.debug("Getting selected Spotify Playlists")
        selected_playlists = self.get_spotify_selections()
        logger.debug("Selected Playlists:" "\n".join(selected_playlists))

        for name in selected_playlists:
            logger.debug(f"Transferring Spotify playlist '{name}' to Plex")
            # pp.spotify_to_plex(sp=self.spotify, section=selected_section, playlist=name)
            logger.debug("Creating Progress Bar Dialog box")
            ProgressBar(func='spotify_to_plex', **{"sp": self.spotify, "section": selected_section,
                                                   "playlist": name})
            logger.info(f"Spotify playlist '{name}' has been transferred to Plex")

        # Check that playlists were uploaded
        logger.debug("Refreshing Plex playlist view.")
        self.plex_update_playlists()

        # Notify user updating playlist complete
        title = "Playlists Updated"
        message = 'Playlist update completed without issues! '
        btns = ['Ok']
        msgtype = QMessageBox.Information
        detail = "\n".join(selected_playlists)
        msg = self.MessageBox(title, message, btns, msgtype, details=detail)

    # </editor-fold>

    # <editor-fold desc="############### Playlist Page Functions ###############">
    # Playlist Functions
    def convert_playlists(self):
        # TODO: Refactor convert_playlist function
        # This function changes the prepend (path to file) for a playlist
        logger.debug("Convert button has been pressed!")
        prepend = self.ui.cmb_playlist_prepend.currentText()
        playlist_directory = self.ui.lned_playlist_directory.text()
        export_directory = self.ui.lned_export_directory.text()
        fmt_filter = ("M3U Files (*.m3u *.m3u8)", "All Files (*)")
        playlists = self.FileDialog(directory=playlist_directory, fmt=fmt_filter)
        logger.debug(f"Prepend in playlists will be replaced with {prepend}")
        pp.format_playlist(export_directory=export_directory, prepend=prepend, playlists=playlists)
        logger.info("Path to tracks inside playlists have successfully been updated.")
        # Let user know playlists are ready
        title = "Playlist Conversion Complete!"
        buttons = ['Ok']
        msgtype = QMessageBox.Information
        # First Message
        message = "Your playlists are ready!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    def combine_playlists(self):
        # TODO: Refactor combine_playlists function
        # This function combines two playlists, keeping only one copy of duplicate songs
        # Good for comparing different versions of playlist
        logger.debug("Combine Button has been pressed!")
        print("combined button pressed!")
        # Get playlist info
        prepend = self.ui.cmb_playlist_prepend.currentText()
        playlist_directory = self.ui.lned_playlist_directory.text()
        export_directory = self.ui.lned_export_directory.text()
        # Ask user for playlists
        fmt_filter = ("M3U Files (*.m3u *.m3u8)", "All Files (*)")
        playlist1 = self.FileDialog(directory=playlist_directory, fmt=fmt_filter)
        playlist2 = self.FileDialog(directory=playlist_directory, fmt=fmt_filter)
        logger.debug(f"Combining two selected playlists:\n{playlist1}\n{playlist2}")
        pp.combine_playlists(export_directory=export_directory, prepend=prepend, playlist1=playlist1,
                             playlist2=playlist2)
        logger.info("Playlists were successfully combined.")
        # Let user know playlists are combined
        title = "Combinging Playlist complete!"
        buttons = ['Ok']
        msgtype = QMessageBox.Information
        # First Message
        message = "The combined playlist is ready!"
        msg = self.MessageBox(title, message, buttons, msgtype)

    # </editor-fold>

    # <editor-fold desc="############### Settings Page Function###############">
    def ignoring_toggle(self):
        logger.debug("Ignore 'All Music' Playlist Checkbox has been toggled!")
        if self.ui.btn_plex_connect.text() == 'Connected':
            self.plex_update_sections()

    def browse_playlist_directory(self):
        # TODO: Refactor browse_playlist_directory
        logger.debug("Browse button for playlist path has been pressed!")
        playlist_directory = self.FileDialog(directory=self.ui.lned_playlist_directory.text(), is_folder=True)
        if playlist_directory:
            self.ui.lned_playlist_directory.setText(playlist_directory)
        return playlist_directory

    def browse_export_directory(self):
        # TODO: Refactor browse_export_directory function
        logger.debug("Browse button for export path has been pressed!")
        export_directory = self.FileDialog(directory=self.ui.lned_export_directory.text(), is_folder=True)
        if export_directory:
            self.ui.lned_export_directory.setText(export_directory)
        return export_directory

    def add_prepend(self):
        # This function adds a new preppend option in the dropdown box
        logger.debug("Add button for prepend has been pressed!")
        new_prepend = self.ui.lned_custom_prepend.text()
        if new_prepend:
            self.variables["prepends"].append(new_prepend)  # Add to saved variables
            # Add to dropdown in Playlist page
            self.ui.cmb_playlist_prepend.addItem(new_prepend)
            self.ui.cmb_playlist_prepend.update()
            self.ui.cmb_playlist_prepend.setCurrentText(new_prepend)
            # Add to Plex page dropdown
            self.ui.cmb_library_prepend.addItem(new_prepend)
            self.ui.cmb_library_prepend.update()
            self.ui.cmb_library_prepend.setCurrentText(new_prepend)
            # Add to Spotify page dropdown
            self.ui.cmb_spotify_prepend.addItem(new_prepend)
            self.ui.cmb_spotify_prepend.update()
            self.ui.cmb_spotify_prepend.setCurrentText(new_prepend)
            # clear the line edit widget
            self.ui.lned_custom_prepend.clear()
            logger.debug(f"New prepend added: {new_prepend}")

    # </editor-fold>

    # END OF CODE #
    def do_nothing(self):
        pass


class MessageDialog(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)

        self.dlg_ui = Ui_Dialog()
        self.dlg_ui.setupUi(self)

        self.dlg_ui.btn_dlg_ok.clicked.connect(self.accept)
        self.dlg_ui.btn_dlg_cancel.clicked.connect(self.reject)

        self.center()
        self.dlg_ui.frame.mouseMoveEvent = self.move_window

    def set_details(self, title, message, btns):
        self.dlg_ui.dlg_title.setText(title)
        self.dlg_ui.dlg_msg.setText(message)
        if 'Ok' not in btns:
            self.dlg_ui.btn_dlg_ok.hide()
        if 'Cancel' not in btns:
            self.dlg_ui.btn_dlg_cancel.hide()

    def center(self):
        screen = QtGui.QGuiApplication.screenAt(QtGui.QCursor().pos())
        qr = self.frameGeometry()
        # cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(screen.geometry().center())
        self.move(qr.topLeft())

    def move_window(self, event):
        if self.isMaximized() is False:
            self.move(self.pos() + event.globalPos() - self.clickPosition)
            self.clickPosition = event.globalPos()
            event.accept()

    def mousePressEvent(self, event):
        self.clickPosition = event.globalPos()


class ProgressBar(MessageDialog):
    def __init__(self, func, **kwargs):
        QDialog.__init__(self, parent=None)
        self.setWindowFlag(QtCore.Qt.FramelessWindowHint)  # Remove frame
        self.setWindowModality(QtCore.Qt.ApplicationModal)  # Make window Application modal

        # Load UI
        self.dlg_ui = Ui_Form()
        self.dlg_ui.setupUi(self)

        # Connect Cancel Button
        self.dlg_ui.btn_progress_cancel.clicked.connect(self.close_window)

        # Save parameters
        self.func = func
        self.kwargs = kwargs

        # Create Thread
        logger.debug("Creating Thread")
        self.thread = QtCore.QThread()

        # Create Worker and pass parameters
        logger.debug("Creating Worker")
        self.worker = Worker(**self.kwargs)

        # Center window and handle window dragging
        self.center()
        self.dlg_ui.frame.mouseMoveEvent = self.move_window

        logger.debug("Splitting Thread")
        self.run_func()
        self.exec_()

    @QtCore.pyqtSlot(int)
    def update_progressbar(self, val):
        self.dlg_ui.progressBar.setValue(val)

    @QtCore.pyqtSlot(str)
    def update_message(self, msg):
        self.dlg_ui.lbl_progress_msg.setText(msg)

    @QtCore.pyqtSlot()
    def finished_task(self):
        self.close_window()

    def show_window(self):
        # TODO: Delete this
        self.show()
        self.run_func()

    def close_window(self):
        # TODO: Delete This
        self.close()

    def run_func(self):


        # Move worker to thread
        logger.debug("Moving worker to thread)")
        self.worker.moveToThread(self.thread)  # Connect worker to thread

        # Connect Signals and Slots
        logger.debug("Connecting Signals and Slots")
        # Once thread starts, run function
        # TODO: Make more Robust
        if self.func == "m3u_to_plex":
            self.thread.started.connect(self.worker.m3u_to_plex)
        elif self.func == "m3u_to_spotify":
            self.thread.started.connect(self.worker.m3u_to_spotify)
        elif self.func == "plex_to_m3u":
            self.thread.started.connect(self.worker.plex_to_m3u)
        elif self.func == "plex_to_spotify":
            self.thread.started.connect(self.worker.plex_to_spotify)
        elif self.func == "spotify_to_m3u":
            self.thread.started.connect(self.worker.spotify_to_m3u)
        elif self.func == "spotify_to_plex":
            self.thread.started.connect(self.worker.spotify_to_plex)
        elif self.func == "test_func":
            self.thread.started.connect(self.worker.test_func)

        self.worker.finished.connect(self.thread.quit)  # Once worker finishes, quit thread
        self.worker.finished.connect(self.worker.deleteLater)  # Once worker finishes, delete worker
        self.thread.finished.connect(self.finished_task)  # Once thread finishes, close window
        self.thread.finished.connect(self.thread.deleteLater)  # Once thread is finished, delete thread

        self.worker.progress_changed.connect(self.update_progressbar)  # Connect progress status to progressbar
        self.worker.msg_changed.connect(self.update_message)  # Connect message changes to text label

        # Start thread
        logger.debug("Starting Thread")
        self.thread.start()


class Worker(QtCore.QObject):
    # Signals to connect to ProgressBar window
    finished = QtCore.pyqtSignal()
    progress_changed = QtCore.pyqtSignal(int)
    msg_changed = QtCore.pyqtSignal(str)

    def __init__(self, **kwargs):
        super().__init__(parent=None)

        self.kwargs = kwargs

    #TODO: Make functions more Robust (split into import and export)
    def m3u_to_plex(self):
        self.msg_changed.emit("Transferring M3u to Plex")
        section = self.kwargs["section"]
        file = self.kwargs["file"]
        logger.debug(f"Running m3u_to_plex function. Parameters: Plex Section, File")

        pp.m3u_to_plex(section=section, file=file, worker=self)
        self.finished.emit()
        logger.debug("function complete")

    def m3u_to_spotify(self):
        self.msg_changed.emit("Transferring M3u to Spotify")
        sp = self.kwargs["sp"]
        file = self.kwargs["file"]
        logger.debug(f"Running m3u_to_spotify function. Parameters: Spotify Session, File")

        pp.m3u_to_spotify(sp, file, worker=self)
        self.finished.emit()
        logger.debug("function complete")

    def plex_to_m3u(self):
        self.msg_changed.emit("Transferring Plex to M3U")
        file = self.kwargs['file']
        section = self.kwargs['section']
        logger.debug(f"Running plex_to_m3u function. Parameters: Plex Section, File")

        pp.plex_to_m3u(section=section, file=file, worker=self)
        self.finished.emit()
        logger.debug("function complete")

    def plex_to_spotify(self):
        self.msg_changed.emit("Transferring Plex to Spotify")
        sp = self.kwargs["sp"]
        section = self.kwargs["section"]
        playlist = self.kwargs["playlist"]
        logger.debug(f"Running plex_to_spotify function. Parameters: Spotify Session, Plex Section, Playlist")

        pp.plex_to_spotify(sp, section, playlist, worker=self)
        self.finished.emit()
        logger.debug("function complete")

    def spotify_to_m3u(self):
        self.msg_changed.emit("Transferring Spotify to M3U")
        sp = self.kwargs["sp"]
        playlist = self.kwargs["playlist"]
        prepend = self.kwargs["prepend"]
        file = self.kwargs["export_file"]
        logger.debug(f"Running spotify_to_m3u function. Parameters: Spotify Session, Playlist, Prepend, File")

        pp.spotify_to_m3u(sp, playlist=playlist, prepend=prepend, export_file=file, worker=self)
        self.finished.emit()
        logger.debug("function complete")

    def spotify_to_plex(self):
        self.msg_changed.emit("Transferring Spotify to Plex")
        sp = self.kwargs["sp"]
        section = self.kwargs["section"]
        playlist = self.kwargs["playlist"]
        logger.debug(f"Running spotify_to_plex function. Parameters: Spotify Session, Plex Section, Playlist")

        pp.spotify_to_plex(sp, section, playlist, worker=self)
        self.finished.emit()
        logger.debug("function complete")

    def test_func(self):
        logger.debug(f"Running test function.")
        self.msg_changed.emit("Trying out test function")
        pp.test_import_func(worker=self)
        self.finished.emit()
        logger.debug("function complete")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(basedir, "icons", "dark", "plex-playlists.svg")))
    MainWindow = MainWindow()
    MainWindow.show()
    sys.exit(app.exec_())
