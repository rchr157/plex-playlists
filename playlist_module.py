import os
import requests
import urllib
import datetime
import json
from collections import OrderedDict
import argparse
import pandas as pd

multidisc = ["CD1", "CD2", "Disc1", "Disc2"]


# Function to load variables from json file
def load_variables():
    cwd = os.path.dirname(os.path.abspath(__file__))
    varfile = os.path.join(cwd, 'settings.json')
    if os.path.exists(varfile):
        file = open(varfile)
        variables = json.load(file)
        return variables


# Function to push playlist to plex library
def push_plex(plex, v, prepend, section, playlists):
    # POST new playlists to Plex
    url = v['plex_server'] + '/playlists/upload?'
    headers = {'cache-control': "no-cache"}
    section_id = plex.library.section(section).key
    failed = []

    for playlist in playlists:
        if playlist.endswith('.m3u'):
            print('Sending updated playlist to Plex: ' + playlist)
            path = os.path.dirname(playlist)
            name = os.path.basename(playlist)
            folder = os.path.basename(os.path.normpath(path)) + "/"

            querystring = urllib.parse.urlencode(OrderedDict(
                [("sectionID", section_id), ("path", prepend + folder + name), ("X-Plex-Token", v['plex_token'])]))
            resp = requests.post(
                url, data="", headers=headers, params=querystring, verify=True)

            # If the post failed then print the return code and the reason for failing.
            if not resp.ok:
                print('ERROR: Return code: %d Reason: %s' %
                      (resp.status_code, resp.reason))
                failed.append(name)
        else:
            print('File format not accepted for: ' + playlist)
    # Scan Music Library for new items
    plex.library.section(section).update()
    return failed, resp


# Function to download playlists from plex library
def export_playlist(export_path, playlist, name):
    file = os.path.join(export_path, name + '.m3u')
    playlist_items = playlist.items()
    if not os.path.exists(export_path):
        print("Creating Folder: {}".format(export_path))
        os.mkdir(export_path)
    with open(file, 'w') as output:
        for item in playlist_items:
            # Open file and save location
            output.write(item.locations[0] + "\n")


# Function to handle prepend changes while exporting playlist
def reformat_playlist(playlist, prepend):

    with open(playlist, 'r') as fin:
        fdata = fin.read()
        track_info = fdata.split("\n")[0].split("/")
        # Determine current path format
        if all(disc not in track_info[-2].replace(" ", "") for disc in multidisc):
            current_pattern = os.path.normpath(fdata.split("\n")[0]).rsplit(os.sep, maxsplit=3)[0]
        else:
            current_pattern = os.path.normpath(fdata.split("\n")[0]).rsplit(os.sep, maxsplit=4)[0]

        if current_pattern == prepend:
            return

        output = fdata.replace(current_pattern, prepend)
        if "Z:" in fdata and "Z:" not in output:
            output = output.replace('\\', '/')
        elif "Z:" in output and "Z:" not in fdata:
            output = output.replace('/', "\\")

        return output


# function that
def format_playlist(export_path, playlists, prepend):
    # Define directory where to export updated playlists
    folder_name = datetime.date.today().strftime("%Y-%m-%d") + "_formatted"
    export_dir = os.path.join(export_path, folder_name)
    if not os.path.exists(export_dir):
        print("Creating Folder: {}".format(folder_name))
        os.mkdir(export_dir)  # if folder doesn't exist, create directory

    for playlist in playlists:
        filename = os.path.basename(playlist)
        export_path = os.path.join(export_dir, filename)

        with open(export_path, "w+") as fout:
            output = reformat_playlist(playlist, prepend)
            fout.write(output)


def combine_playlists(export_path, prepend, playlist1, playlist2):
    folder_name = datetime.date.today().strftime("%Y-%m-%d") + "_modified"
    export_dir = os.path.join(export_path, folder_name)
    if not os.path.exists(export_dir):
        print("Creating Folder: {}".format(folder_name))
        os.mkdir(export_dir)

    filename = os.path.basename(playlist1)
    export_folder = os.path.join(export_dir, filename)

    # reformat playlist1
    playlist1_lines = reformat_playlist(playlist1, prepend)
    # reformat playlist2
    playlist2_lines = reformat_playlist(playlist2, prepend)

    combined_playlist = playlist1_lines.split("\n")[:-1] + playlist2_lines.split("\n")[:-1]
    artists = []
    track = []
    trk_format = []
    for line in combined_playlist:
        if "Z:" in line:
            track_info = line.split("\\")
        else:
            track_info = line.split("/")
        # Get artist
        if all(disc not in track_info[-2].replace(" ", "") for disc in multidisc):
            artists.append(track_info[-3])
        else:
            artists.append(track_info[-4])
        # Get track name and format
        track_name, track_format = track_info[-1].rsplit('.', 1)
        track_name = track_name.replace(" - ", " ")
        # ignore track number
        if track_name[0].isdigit():
            track_name = track_name.replace(" - ", " ")[3:]
        track.append(track_name)
        trk_format.append(track_format)

    df = pd.DataFrame(data={"artist": artists, "track": track, "format": trk_format, "path": combined_playlist})
    df = df.sort_values(by=['format', 'track'])
    df = df.drop_duplicates(subset=['artist', 'track'], keep='first')
    df = df.sort_index()
    df['path'].to_csv(export_folder, header=None, index=None, sep='\t', mode='a')