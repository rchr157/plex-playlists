import os
import requests
import urllib
import datetime
import json
import re
import logging
from collections import OrderedDict
import pandas as pd

# Setup Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(name)s:%(levelname)s: %(message)s')
file_handler = logging.FileHandler('module.log')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

multidisc = ["CD1", "CD2", "Disc1", "Disc2"]


# Function to load variables from json file
def load_variables(varfile=None):
    if varfile is None:
        cwd = os.path.dirname(os.path.abspath(__file__))
        varfile = os.path.join(cwd, 'settings.json')
    if os.path.exists(varfile):
        logger.debug(f"Loading file: {varfile}")
        file = open(varfile)
        variables = json.load(file)
        logger.info(f"Settings file successfully loaded.")
        return variables


# Function to push playlist to plex library
def plex_push_playlist(plex, v: dict, prepend: str, section: str, playlists: list):
    # POST new playlists to Plex
    logger.info("Pushing playlists to Plex server.")
    url = v['plex_server'] + '/playlists/upload?'
    headers = {'cache-control': "no-cache"}
    section_id = plex.library.section(section).key
    failed = []
    response = []
    query = []

    for playlist in playlists:
        if playlist.endswith('.m3u'):
            # TODO: Accept other formats aside from .m3u
            logger.info(f"Sending updated playlist to Plex: {playlist}")
            path = os.path.dirname(playlist)
            name = os.path.basename(playlist)
            folder = os.path.basename(os.path.normpath(path))
            plex_path = os.path.join(prepend, folder, name)

            querystring = urllib.parse.urlencode(OrderedDict(
                [("sectionID", section_id), ("path", plex_path), ("X-Plex-Token", v['plex_token'])]))
            logger.debug(f"Sending request for {name}. url:{url}, query:{querystring[:-20]}")
            resp = requests.post(
                url, data="", headers=headers, params=querystring, verify=True)

            response.append(resp)
            query.append(resp.url)

            # If request fails return the response code and reason for failure.
            if not resp.ok:
                logger.error(f"Request was not successful. Response: {resp.status_code} {resp.reason}")
                failed.append(name)

        else:
            logger.error(f"File extension not accepted for {playlist}")
    # Scan Music Library for new items
    plex.library.section(section).update()
    logger.debug(f"Plex Library {section} updated.")
    return failed, response


def read_from_file(file: str):
    logger.debug(f"Reading from file: {file}")
    with open(file, 'r') as fin:
        output = fin.read().splitlines()
    return output


def write_to_file(file: str, data: str):
    logger.debug(f"Writing to file: {file}")
    with open(file, 'w') as output:
        output.write(data)


# Function to download playlists from plex library
def plex_export_playlist(file: str, playlist, name: str):
    # Export file name
    # file = os.path.join(export_directory, name + '.m3u')
    logger.info(f"Exporting {name} playlist from plex to {file}.")
    # playlist_items = playlist.items()
    playlist_items = "\n".join([item.locations[0] for item in playlist.items()])

    # if not os.path.exists(export_directory):
    #     logger.debug("Creating Folder: {}".format(export_directory))
    #     os.mkdir(export_directory)
    write_to_file(file=file, data=playlist_items)


def check_playlist_availability(local_playlists: list, server_playlists: list):
    logger.debug(f"Checking playlist availability in Plex.")
    available = []
    not_available = []
    # Compare selected files to playlists available
    for file in local_playlists:
        new_file = os.path.basename(os.path.splitext(file)[0])
        if new_file in server_playlists:
            available.append(file)
        else:
            not_available.append(file)

    return available, not_available


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
        if "\\" in fdata and "\\" not in output:
            output = output.replace('\\', '/')
        elif "\\" in output and "\\" not in fdata:
            output = output.replace('/', "\\")

        return output


# function that
def format_playlist(export_directory, playlists, prepend):
    # Define directory where to export updated playlists
    folder_name = datetime.date.today().strftime("%Y-%m-%d") + "_formatted"
    export_dir = os.path.join(export_directory, folder_name)
    if not os.path.exists(export_dir):
        logger.info("Creating Folder: {}".format(folder_name))
        os.mkdir(export_dir)  # if folder doesn't exist, create directory

    for playlist in playlists:
        filename = os.path.basename(playlist)
        export_directory = os.path.join(export_dir, filename)

        with open(export_directory, "w+") as fout:
            output = reformat_playlist(playlist, prepend)
            fout.write(output)


def combine_playlists(export_directory, prepend, playlist1, playlist2):
    # TODO: Reformat to accept more than 2 playlists?
    folder_name = datetime.date.today().strftime("%Y-%m-%d") + "_modified"
    export_dir = os.path.join(export_directory, folder_name)
    # TODO: Move this to browse_export_directory function, add dialog window if path doesn't exists
    if not os.path.exists(export_dir):
        logger.info("Creating Folder: {}".format(folder_name))
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


def get_track_info(item):
    """
    This function takes in a line on a m3u file and parses it to get the artist, album, and track info.
    :param item: single string for path to track on a m3u file. Assumes path is in format: ../artist/album/track
    :return: tuple of artist, album, track
    """
    # format string to get artist, album, track names
    item_parsed = item.split(os.sep)
    if all(disc not in item_parsed[-2].replace(" ", "") for disc in multidisc):
        # check if path has an added folder for cd, such that the path is /artist/album/cd1/track
        artist = item_parsed[-3]
        album = item_parsed[-2]
    else:
        # if there is an added folder for cd, artist and album are one level above
        artist = item_parsed[-4]
        album = item_parsed[-3]

    track = os.path.splitext(item_parsed[-1])[0].split(' - ')[1]
    track_number = os.path.splitext(item_parsed[-1])[0].split(' - ')[0]
    return (artist, album, track)


def spotify_create_playlist(sp, user, playlist_name, public=False, collaborative=False):
    # Create new playlist on spotify
    sp.user_playlist_create(user=user, name=playlist_name, public=public, collaborative=collaborative)
    # Grab existing playlists
    available_playlist = spotify_get_available_playlists(sp)
    # Get URI for newly created playlist
    playlist_uri = available_playlist[playlist_name]
    return playlist_uri


def spotify_get_available_playlists(sp):
    result = sp.current_user_playlists()
    playlists = {}
    for item in result['items']:
        playlists[item['name']] = item['uri']
    return playlists


def spotify_get_playlist_items(sp, playlist_uri):
    item_list = sp.playlist_items(playlist_uri)
    playlist_items = {}
    for item in item_list['items']:
        track_info = spotify_get_track_info(item['track'])
        playlist_items[track_info['track_uri']] = [track_info['artist_name'], track_info['album_name'],
                                                               track_info['track_number'], track_info['track_name']]

    return playlist_items


def convert_item_from_spotify_to_playlist(item, prepend):
    item_entry = os.path.join(prepend, item[0], item[1], f"{item[2]:02d} - "
                                                                  f"{item[3]}")
    return item_entry


def spotify_search(sp, query: tuple):
    # Query tuple is (Artist Name, Album Name, Track Title)
    ptrn_and = "\s\&\s|\sand\s"
    ptrn_paren = "\(.*\)"
    result = sp.search(f"artist:{query[0]} track: {query[2]}")
    # TODO: develop logic for ensuring track found matches track searched for, for now use first result
    if not result['tracks']['items']:
        # TODO: try to find best way to catch edge cases
        artist = query[0]
        album = query[1]
        track = query[2]
        # If search comes back empty try different stuff
        if re.search(ptrn_and, artist) is not None:
            # Replace & or 'and' in artists for multiple artists
            match = re.search(ptrn_and, artist)
            artist = artist.replace(match.group(), ',')
        if re.search(ptrn_paren, artist) is not None:
            # remove parenthesis
            match = re.search(ptrn_paren, artist)
            artist.replace(match.group(), '')
        if 'Various' in artist:
            # Use album instead for various artist
            result = sp.search(f"album: {query[1]} track: {query[2]}")
        if re.search(ptrn_paren, track) is not None:
            match = re.search(ptrn_paren, track)
            track = track.replace(match.group(), '')
        result = sp.search(f"artist: {artist} track: {track}")
    if not result['tracks']['items']:
        # If still no results, try without 'artist:' and 'track:'
        result = sp.search(f"{artist} {track}")
    if not result['tracks']['items']:
        # if still no results, track might be unavailable in spotify
        return None
    else:
        track_info = spotify_get_track_info(result['tracks']['items'][0])
        return track_info['track_uri']


def spotify_get_track_info(item):
    # Todo: Test function
    # Repackage track info for easier handling
    track_item = {"artist_name": item['artists'][0]['name'],
                  "album_name": item['album']['name'],
                  "track_name": item['name'],
                  "track_number": item['track_number'],
                  "track_uri": item['uri']
                  }
    # track_item = item['uri']
    return track_item


def spotify_add_to_playlist(sp, playlist_uri, items: list):
    sp.playlist_add_items(playlist_uri, items)
    return


def spotify_remove_from_playlist(sp, playlist_uri, items: list):
    sp.playlist_remove_all_occurrences_of_items(
        playlist_uri, items)


def spotify_reset_playlist(sp, playlist_uri):
    playlist_items = spotify_get_playlist_items(sp, playlist_uri)
    if not playlist_items:
        # if playlist is already empty
        return
    spotify_remove_from_playlist(sp, playlist_uri, list(playlist_items.keys()))


def spotify_download_playlist(sp, prepend, playlist_uri, export_file):
    # Get items from spotify playlists
    playlist_items = spotify_get_playlist_items(sp=sp, playlist_uri=playlist_uri)

    # format playlist items to be used in plex or desktop (add prepend)
    playlist_items = "\n".join([convert_item_from_spotify_to_playlist(item, prepend) for item in playlist_items.values()])
    write_to_file(export_file, playlist_items)


def spotify_upload_playlist(sp, playlist_uri, playlist_file):
    """
    :param sp: spotify session
    :param playlist_uri: uri for playlist on spotify that will be updated with m3u file
    :param playlist_file: full path to m3u file that will be uploaded to spotify
    :return: list of tracks that failed to upload
    """
    # Get items from m3u file
    playlist_items = read_from_file(file=playlist_file)
    name = os.path.basename(os.path.splitext(playlist_file)[0])
    # Get items from spotify playlist
    existing_items = spotify_get_playlist_items(sp=sp, playlist_uri=playlist_uri)
    track_uris = []
    failed = []
    for i, item in enumerate(playlist_items):
        logger.info(f"processing item {i}: {item}")
        query = get_track_info(item)  # convert line to searchable query
        logger.info(f"track info: \nArtist: {query[0]} | Album: {query[1]} | Track: {query[2]}")
        result = spotify_search(sp, query)
        if result is None:
            logger.info(f"*******************\nSearch failed for: \nArtist: {query[0]} | Album: {query[1]} | Track: {query[2]} \nSkipping track...\n*******************")
            failed.append(item)
        elif result in list(existing_items.keys()):
            logger.info("track already in playlist")
            continue
        else:
            logger.info("track added successfully")
            track_uris.append(result)  # Get track URI
    if not track_uris:
        logger.info(f"No new tracks added to {name} playlist")
        return failed
    else:
        spotify_add_to_playlist(sp, playlist_uri, track_uris)  # add track to destination playlist
        logger.info(f"Playlist {name} upload complete. {len(failed)} out of {len(playlist_items)} items failed to upload. ")
        return failed
