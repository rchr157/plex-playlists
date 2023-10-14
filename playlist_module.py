import os

import plexapi.library
import plexapi.playlist
import requests
import urllib
import datetime
import json
import re
import logging
import time
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


# <editor-folding desc="############### General Functions ###############">
def load_variables(varfile=None):
    if varfile is None:
        return None
    if os.path.exists(varfile):
        logger.debug(f"Loading file: {varfile}")
        file = open(varfile)
        variables = json.load(file)
        logger.info(f"Settings file successfully loaded.")
        return variables


# </editor-fold>

# <editor-folding desc="############### Playlist Functions ###############">
# Function to handle prepend changes while exporting playlist
def read_from_file(file: str):
    """
    This function reads each line from a m3u file. Expects only the paths to each track in the palylist.
    :param file: full path to the m3u file
    :return: returns a list containing the path to each track on the list
    """
    logger.debug(f"Reading from file: {file}")
    with open(file, 'r') as fin:
        output = fin.read().splitlines()
    return output


def write_to_file(file: str, data: str):
    """
    This function writes the path to each track on a playlist to a m3u file.
    :param file: full path to the m3u file
    :param data: single string containing the paths to tracks on the playlist.
    :return: returns nothing, but creates a m3u file of the playlist.
    """
    logger.debug(f"Writing to file: {file}")
    with open(file, 'w') as output:
        output.write(data)


def reformat_playlist(playlist, prepend):
    # TODO: Refactor reformat_playlist function
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
    # TODO: Refactor format_playlist function
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
    # TODO: Refactor combine_playlists function
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
        if "\\" in line:
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


def create_export_file(path: str, playlist_name: str):
    return os.path.join(path, f"{playlist_name}.m3u")


# </editor-fold>


# <editor-fold desc="############### PLEX Functions ###############">
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


# Function to download playlists from plex library
def plex_download_playlist(file: str, playlist, name: str):
    # Export file name
    # file = os.path.join(export_directory, name + '.m3u')
    logger.info(f"Exporting {name} playlist from plex to {file}.")
    # playlist_items = playlist.items()
    playlist_items = "\n".join([item.locations[0] for item in playlist.items()])

    write_to_file(file=file, data=playlist_items)


# </editor-fold>


# <editor-fold desc="############### Get Functions ###############">
def m3u_get_track_info(item: str):
    """
    This function takes in a line on a m3u file and parses it to get the artist, album, and track info.
    :param item: single string for path to track on a m3u file. Expects path is in format: ../artist/album/track
    :return: tuple of artist, album, track, track number
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
    return [artist, album, track, track_number, item]


def plex_get_track_info(item):
    """
    This function extracts the Artist, Album, and Track info from a plex playlist item.
    :param item: Single Plex Track object
    :return: artist: str, album: str, track: str
    """
    artist = item.artist().title
    album = item.album().title
    track = item.title
    track_number = item.trackNumber
    path = item.locations[0]
    return [artist, album, track, track_number, path]


def plex_get_sections(plex):
    return [item.title for item in plex.library.sections() if item.CONTENT_TYPE == 'audio']


def plex_get_available_playlists(section: plexapi.library.MusicSection):
    return [item.title for item in section.playlists()]


def plex_get_playlist_items(playlist: plexapi.playlist.Playlist):
    return playlist.items()


def spotify_get_track_info(item):
    artist = item['artists'][0]['name']
    album = item['album']['name']
    track = item['name']
    track_number = item['track_number']
    return [artist, album, track, track_number]


def spotify_get_available_playlists(sp):
    user = sp.current_user_playlists()
    featured = sp.featured_playlists()
    combined = user['items'] + featured['playlists']['items']
    playlists = {}
    for item in combined:
        if item is not None:
            playlists[item['name']] = item['uri']
    return playlists


def spotify_get_playlist_items(sp, playlist):
    tracks = []
    offset = 0
    sp_playlist = sp.playlist_items(playlist_id=playlist, limit=100, offset=offset)
    tracks = tracks + [item['track'] for item in sp_playlist['items']]
    # Handle condition if playlist has more than 100 tracks (limited by api)
    if sp_playlist['next'] is not None:
        while sp_playlist['next'] is not None:
            offset += 100
            sp_playlist = sp.playlist_items(playlist_id=playlist, limit=100, offset=offset)
            tracks = tracks + [item['track'] for item in sp_playlist['items']]

    return tracks


def spotify_get_track_uri(item):
    return item['uri']

#</editor-fold>


# <editor-fold desc="############### Search Tracks ###############">
def compare_str(item, query: str):
    return item.title.lower() == query.lower()


def plex_search(section: plexapi.library.MusicSection, query: tuple):
    # TODO: Refactor plex search function
    results = section.hubSearch(query=f"{query[0]} - {query[2]}", mediatype='track')
    prepend = section.locations[0]
    for item in results:
        # Check if artist, album, and track match
        if (compare_str(item.artist(), query[0]) and compare_str(item.album(), query[1])
                and compare_str(item, query[2])):
            if re.search(prepend, item.locations[0]) is not None:
                # Check that its in the correct library path
                logger.info(f"Found match on Plex for Artist:{query[0]} | Album: {query[1]} | Track: {query[2]}")
                return item

    for item in results:
        # Check if artist and title match, may be from different album
        if compare_str(item.artist(), query[0]) and compare_str(item, query[2]):
            if re.search(prepend, item.locations[0]) is not None:
                # Check that its in the correct library path
                logger.info(f"Found match on Plex for Artist: {query[0]} | Track: {query[2]}")
                return item
    # Otherwise, return nothing
    logger.info(f"Did not find any match on Plex for Artist: {query[0]} | Album: {query[1]} | Track: {query[2]}")
    return None


def spotify_search(sp, query: list):
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
        result = sp.search(f"artist: {artist} track: {track}")
        if not result['tracks']['items']:
            # If still no results, try without 'artist:' and 'track:'
            result = sp.search(f"{artist} {track}")
        if not result['tracks']['items']:
            if 'Various' in artist:
                # Use album instead for various artist
                result = sp.search(f"album: {album} track: {track}")
    if not result['tracks']['items']:
        # if still no results, track might be unavailable in spotify
        return None
    else:
        # track_info = spotify_get_track_info(result['tracks']['items'][0])
        return result['tracks']['items'][0]


# </editor-fold>


# <editor-fold desc="############### Playlist Management ###############">
# PLEX Playlist Functions
def plex_create_playlist(section: plexapi.library.MusicSection, playlist_name: str, items: list):
    """
    This function creates a playlist in plex. It requires to have a list of tracks that will be added,
    plex won't allow to create an empty playlist.
    :param section: Plex Section the playlist will be created in.
    :param playlist_name: Name of the playlist.
    :param items: list of tracks that will be added to new playlist
    :return:
    """
    section.createPlaylist(title=playlist_name, items=items)
    logger.info(f"Creating New Playlist: {playlist_name}, with {len(items)} tracks")


def plex_add_to_playlist(section: plexapi.library.MusicSection, playlist: str, items: list):
    section.playlist(playlist).addItems(items=items)
    logger.info(f"{len(items)} Tracks added to playlist {playlist}")


def plex_remove_from_playlist(section: plexapi.library.MusicSection, playlist: str, items: list):
    section.playlist(playlist).removeItems(items=items)
    logger.info(f"{len(items)} Tracks removed to playlist {playlist}")
    pass


# Spotify Playlist functions
def spotify_create_playlist(sp, user, playlist_name, public=False, collaborative=False):
    # Create new playlist on spotify
    sp.user_playlist_create(user=user, name=playlist_name, public=public, collaborative=collaborative)
    # Grab existing playlists
    available_playlist = spotify_get_available_playlists(sp)
    # Get URI for newly created playlist
    playlist_uri = available_playlist[playlist_name]
    return playlist_uri


def spotify_add_to_playlist(sp, playlist_uri, items: list):
    if len(items) > 100:
        # handle request if playlist has more than 100 tracks to be added
        split_uris = [items[i * 100:(i + 1) * 100] for i in range((len(items) + 100 - 1) // 100)]
        for chunk in split_uris:
            sp.playlist_add_items(playlist_uri, chunk)
    else:
        sp.playlist_add_items(playlist_uri, items)
    return


def spotify_remove_from_playlist(sp, playlist_uri, items: list):
    sp.playlist_remove_all_occurrences_of_items(
        playlist_uri, items)

#</editor-fold>


# <editor-fold desc="############### Check and Compare Playlists ###############">
def compare_plex_playlists(source: list, destination: list):
    new_tracks = []
    removed_tracks = []
    for item in source:
        if item not in destination:
            # If item from source is not in destination, item is new
            new_tracks.append(item)
    for item in destination:
        if item not in source:
            # if item from destination is not in source, item was removed
            removed_tracks.append(item)
    logger.info(f"{len(new_tracks)} New tracks in latest playlist. "
                f"{len(removed_tracks)} tracks were removed in latest playlist.")
    return new_tracks, removed_tracks


def compare_spotify_playlists(source: list, destination: list):
    new_tracks = []
    removed_tracks = []
    source_list = [spotify_get_track_uri(item) for item in source]
    destination_list = [spotify_get_track_uri(item) for item in destination]
    for item in source_list:
        if item not in destination_list:
            # If item from source is not in destination, item is new
            new_tracks.append(item)
    for item in destination_list:
        if item not in source_list:
            # if item from destination is not in source, item was removed
            removed_tracks.append(item)
    logger.info(f"{len(new_tracks)} New tracks in latest playlist. "
                f"{len(removed_tracks)} tracks were removed in latest playlist.")
    return new_tracks, removed_tracks


def plex_check_tracks(section, tracks, worker):
    found_tracks = []
    missing_tracks = []
    for ind, track in enumerate(tracks):
        val = int(100 * (ind/len(tracks)))
        worker.progress_changed.emit(val)
        result = plex_search(section=section, query=track)
        if result is not None:
            found_tracks.append(result)
            logger.info(f"Track found: Artist: {track[0]} | Album: {track[1]} | Track: {track[2]}")
            worker.msg_changed.emit(f"Track Available: {track[0]} - {track[2]}")
        else:
            missing_tracks.append(f"{track[0]} - {track[1]} - {track[2]}")
            logger.info(f"**********Track not found: "
                        f"Artist: {track[0]} | Album: {track[1]} | Track: {track[2]} **********")
            worker.msg_changed.emit(f"Track not found. Skipping: {track[0]} - {track[2]}")
    msg = f"{len(found_tracks)} Tracks available on Plex. {len(missing_tracks)} tracks were not found in Plex."
    logger.info(msg)
    worker.msg_changed.emit(msg)
    return found_tracks, missing_tracks


def spotify_check_tracks(sp, tracks: list, worker):
    found_tracks = []
    missing_tracks = []
    for ind, track in enumerate(tracks):
        val = int(100 * (ind / len(tracks)))
        worker.progress_changed.emit(val)
        result = spotify_search(sp, track)
        if result is not None:
            found_tracks.append(result)
            logger.info(f"Track found: Artist: {track[0]} | Album: {track[1]} | Track: {track[2]}")
            worker.msg_changed.emit(f"Track Available: {track[0]} - {track[2]}")
        else:
            missing_tracks.append(f"{track[0]} - {track[1]} - {track[2]}")
            logger.info(f"**********Track not found: "
                        f"Artist: {track[0]} | Album: {track[1]} | Track: {track[2]} **********")
            worker.msg_changed.emit(f"Track not found. Skipping: {track[0]} - {track[2]}")
    msg = f"{len(found_tracks)} Tracks available on Spotify.{len(missing_tracks)} tracks were not found in Spotify."
    logger.info(msg)
    worker.msg_changed.emit(msg)
    return found_tracks, missing_tracks


#</editor-fold>


# <editor-fold desc="############### Import Functions ###############">
def test_import_func(worker):
    # TODO: Delete test function
    logger.debug("entering test_import_func:")
    for i in range(10):
        val = int(100 * (i + 1) / 10)
        msg = f"Current Progress: {val}%"
        logger.debug(msg)
        worker.msg_changed.emit(msg)
        worker.progress_changed.emit(val)
        time.sleep(0.4)
    logger.debug("Function complete")
    worker.msg_changed.emit("Function complete")
    worker.progress_changed.emit(100)


def import_from_m3u(file, worker):
    # Get playlist tracks from m3u file
    name = os.path.basename(os.path.splitext(file)[0])
    src_playlist = read_from_file(file)
    tracks = []
    logger.info(f"Loading {len(tracks)} tracks from m3u file: {name}")
    for ind, item in enumerate(src_playlist):
        val = int(100 * ind / len(src_playlist))
        logger.debug(f"Current Progress: {val}%")
        worker.msg_changed.emit(f"Loading {ind}/{len(src_playlist)} tracks from playlist: {name}")
        worker.progress_changed.emit(val)

        # convert to universal format to use later
        tracks.append(m3u_get_track_info(item))
    worker.msg_changed.emit("Import Complete!")
    worker.progress_changed.emit(100)
    return tracks


def import_from_plex(playlist: plexapi.playlist.Playlist, worker):
    # Get playlist tracks from Plex
    name = playlist.title
    src_playlist = plex_get_playlist_items(playlist)
    tracks = []
    for ind, item in enumerate(src_playlist):
        val = int(100 * ind / len(src_playlist))
        logger.debug(f"Current Progress: {val}%")
        worker.msg_changed.emit(f"Loading {ind}/{len(src_playlist)} tracks from playlist: {name}")
        worker.progress_changed.emit(val)

        # convert to universal format to use later
        tracks.append(plex_get_track_info(item))
    logger.info(f"Loaded {len(tracks)} tracks from Plex playlist: {name}")
    worker.msg_changed.emit("Import Complete!")
    worker.progress_changed.emit(100)
    return tracks


def import_from_spotify(sp, playlist: str, worker):
    available_playlists = spotify_get_available_playlists(sp)
    # Get playlist tracks from spotify
    src_playlist = spotify_get_playlist_items(sp, playlist=available_playlists[playlist])
    tracks = []
    for ind, item in enumerate(src_playlist):
        val = int(100 * ind / len(src_playlist))
        logger.debug(f"Current Progress: {val}%")
        worker.msg_changed.emit(f"Loading {ind}/{len(src_playlist)} tracks from playlist: {playlist}")
        worker.progress_changed.emit(val)

        # convert to universal format to use later
        tracks.append(spotify_get_track_info(item))

    logger.info(f"Loading {len(tracks)} tracks from Spotify playlist: {playlist}")
    worker.msg_changed.emit("Import Complete!")
    worker.progress_changed.emit(100)
    return tracks


#</editor-fold>


# <editor-fold desc="############### Export Functions ###############">
def add_location(prepend, tracks):
    for track in tracks:
        track.append(os.path.join(prepend, track[0], track[1], f"{track[3]} - {track[2]}.mp3"))
    return tracks


def export_to_m3u(prepend, export_file, tracks, worker):
    if len(tracks[0]) != 5:
        # Add location prepend
        tracks = add_location(prepend, tracks)
        logger.info(f"Added location path to tracks for exporting.")
    data = "\n".join([track[-1] for track in tracks])
    worker.msg_changed.emit(f"Exporting to M3U file: {export_file}")
    worker.progress_changed.emit(10)
    write_to_file(file=export_file, data=data)
    worker.msg_changed.emit("Exporting Complete!")
    worker.progress_changed.emit(100)
    return tracks, None


def export_to_plex(section, destination: str, source_tracks: list, worker):
    worker.progress_changed.emit(10)
    worker.msg_changed.emit(f"Exporting {destination} playlist to Plex")
    # Check if playlist already exists or if it needs to be created
    available_playlists = plex_get_available_playlists(section)
    # Check if tracks are available on Plex
    available_tracks, unavailable_tracks = plex_check_tracks(section=section, tracks=source_tracks, worker=worker)

    if destination not in available_playlists:
        worker.msg_changed.emit(f"Creating New Playlist: {destination}")
        worker.progress_changed.emit(50)
        # if playlist does not exist, create it
        logger.info(f"{destination} playlist not found in Plex server, creating new playlist.")
        plex_create_playlist(section=section, playlist_name=destination, items=available_tracks)
        worker.msg_changed.emit("Exporting Complete!")
        worker.progress_changed.emit(100)
        return available_tracks, None

    # If playlist already exists, compare items in playlist
    msg = f"Updating {destination} playlist for new and or removed items."
    logger.debug(msg)
    worker.msg_changed.emit(msg)

    destination_tracks = plex_get_playlist_items(section.playlist(destination))
    new_tracks, removed_tracks = compare_plex_playlists(source=available_tracks, destination=destination_tracks)
    worker.progress_changed.emit(50)

    # for new items
    if not new_tracks:
        plex_add_to_playlist(section=section, playlist=destination, items=new_tracks)
    worker.progress_changed.emit(75)
    # for removed items, remove
    if not removed_tracks:
        plex_remove_from_playlist(section=section, playlist=destination, items=removed_tracks)

    msg = f"{destination} playlist on PLEX has been updated!"
    logger.info(msg)
    worker.msg_changed.emit(msg)
    worker.progress_changed.emit(100)
    return new_tracks, removed_tracks


def export_to_spotify(sp, source_tracks: list, destination: str, worker):
    worker.progress_changed.emit(10)
    worker.msg_changed.emit(f"Exporting {destination} playlist to Spotify")
    available_playlists = spotify_get_available_playlists(sp)
    available_tracks, unavailable_tracks = spotify_check_tracks(sp,
                                                                source_tracks, worker=worker)  # expects list for
    # query, returns spotify track info

    if destination not in available_playlists:
        worker.msg_changed.emit(f"Creating new playlist {destination}")
        worker.progress_changed.emit(50)
        # If playlist does not exist, create new playlist and add items
        logger.info(f"Playlist '{destination}' not found in Spotify account, creating new playlist.")
        new_playlist = spotify_create_playlist(sp, user=sp.me()['id'], playlist_name=destination)
        available_track_uris = [track['uri'] for track in available_tracks]
        spotify_add_to_playlist(sp, playlist_uri=new_playlist, items=available_track_uris)
        logger.info(f"{len(available_track_uris)} tracks added to '{destination}' playlist on Spotify.")
        worker.msg_changed.emit("Exporting Complete!")
        worker.progress_changed.emit(100)
        return available_tracks, None

    # If playlist already exists, compare items in playlist
    msg = f"Updating {destination} playlist with new and removed items."
    logger.debug(msg)
    worker.msg_changed.emit(msg)
    worker.progress_changed.emit(50)

    destination_tracks = spotify_get_playlist_items(sp, available_playlists[destination])
    new_tracks, removed_tracks = compare_spotify_playlists(source=available_tracks, destination=destination_tracks)

    # for new items
    if len(new_tracks) > 0:
        spotify_add_to_playlist(sp, playlist_uri=available_playlists[destination], items=new_tracks)
        logger.info(f"Adding {len(new_tracks)} to playlist {destination}")

    worker.progress_changed.emit(75)

    # for removed items, remove
    if len(removed_tracks) > 0:
        spotify_remove_from_playlist(sp, playlist_uri=available_playlists[destination], items=removed_tracks)
        logger.info(f"Removing {len(removed_tracks)} to playlist {destination}")

    msg = f"{destination} playlist on Spotify has been updated!"
    logger.info(msg)
    worker.msg_changed.emit(msg)
    worker.progress_changed.emit(100)
    return new_tracks, removed_tracks

# </editor-fold>


# <editor-fold desc="############### Testing FUnctions ###############">
########################################################################################################################
def m3u_to_spotify(sp, file, worker):
    playlist = os.path.basename(os.path.splitext(file)[0])
    src_tracks = import_from_m3u(file=file, worker=worker)
    new_tracks, removed_tracks = export_to_spotify(sp=sp, source_tracks=src_tracks, destination=playlist, worker=worker)
    return new_tracks, removed_tracks


def m3u_to_plex(section, file: str, worker):
    playlist_name = os.path.basename(os.path.splitext(file)[0])
    # Get playlist track from source m3u file
    src_tracks = import_from_m3u(file=file, worker=worker)
    # Exports tracks to desired destination playlist
    new_tracks, removed_tracks = export_to_plex(section=section, destination=playlist_name, source_tracks=src_tracks,
                                                worker=worker)
    return new_tracks, removed_tracks


def plex_to_spotify(sp, section, playlist: str, worker):
    src_tracks = import_from_plex(playlist=section.playlist(playlist), worker=worker)
    new_tracks, removed_tracks = export_to_spotify(sp, destination=playlist, source_tracks=src_tracks, worker=worker)
    return new_tracks, removed_tracks


def plex_to_m3u(section, file: str, worker):
    playlist = os.path.basename(os.path.splitext(file)[0])
    prepend = section.locations[0]
    src_tracks = import_from_plex(playlist=section.playlist(playlist), worker=worker)
    new_tracks, removed_tracks = export_to_m3u(prepend=prepend, export_file=file, tracks=src_tracks, worker=worker)
    return new_tracks, removed_tracks


def spotify_to_m3u(sp, playlist: str, prepend: str, export_file: str, worker):
    src_tracks = import_from_spotify(sp=sp, playlist=playlist, worker=worker)
    new_tracks, removed_tracks = export_to_m3u(prepend, export_file, tracks=src_tracks, worker=worker)
    return new_tracks, removed_tracks


def spotify_to_plex(sp, section, playlist: str, worker):
    src_tracks = import_from_spotify(sp=sp, playlist=playlist, worker=worker)
    new_tracks, removed_tracks = export_to_plex(section=section, destination=playlist, source_tracks=src_tracks,
                                                worker=worker)
    return new_tracks, removed_tracks


########################################################################################################################
#</editor-fold>
