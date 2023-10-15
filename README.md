Plex Playlists [WIP]
==============
<img src="https://github.com/rchr157/plex-playlists/blob/main/icons/plex-playlists.svg" width="200" />

# Description
Plex Playlist is a desktop app that allows users to easily manage their playlists on their plex servers. It provides a user interface to make downloading and uploading as easy and painless as possible.

# Features
- Download playlists from plex server as m3u file
- Upload playlists to plex server from m3u file
- Download playlist from Spotify account as m3u file
- Upload playlist to Spotify account from m3u file
- Transfer playlist between services (Plex/Spotify)
- Upload playlist to plex from Spotify Playlist URL
- Upload playlist to Plex via POST
- Format track paths inside m3u playlists
- Combine multiple m3u files to a single playlist

## Upcoming Additions
- Allow user to review changes between upload playlist and service playlist
- Allow user to update tracks inside playlist
- Sync ratings between MusicBee and Plex
- Potentially add integration for:
    - Apple Music
    - Itunes
    - Tidal
    - Youtube Music
    - Amazon Music
    - Soundcloud
    - Bandcamp
    - Deezer
    - Qobuz
    - Jellyfin 

# Installing [WIP]
Coming Soon
clone repository
## Linux Releases
AppImage (Recommended)
Deb package

# Quick Guide
## Pre-requisites
The 5 things you need to get started

| |Item | Description |
|-----:|---------------|---------------| 
|     1| Plex Server URL | URL to access your plex server, should be the IP of the machine where its hosted at and the port exposed |
|     2| Plex Token | Plex token allows you to communicate with your plex server and make requests (upload, download, etc). Click here to see how to obtain a plex token |
|     3| Spotify Client ID | Spotify client ID required to use Spotify API. Click here to see how to obtain spotify client id.   |
|     4| Spotify Secret Key | Spotify Secret Key required to use Spotify API. Click here to see how to obtain spotify secrete key. |
|     5| Redirect URI | Spotify Redirect URI required to use Spotify API. Click here to see how to obtain spotify |
|     6| Playlist Directory  | (Optional) Directory where to look for M3U playlist files. |
|     7| Export Directory  | (Optional) Directory where you want playlists to be downloaded from plex or exported after formating. It will automatically create a 'plex' and 'spotify' folder when exporting playlists from each service. |
|     8| Playlist prepend  | (Optional) This is the path that is appended to the front of each track to give the location of the track in an M3U file. You can add different paths to create different versions of the m3u files.|



![2023-10-13 11-48-00_Settings_filled-edited](https://github.com/rchr157/plex-playlists/assets/31231317/4a3dad95-3454-4a48-b4f1-3670c850f111)


## Get Started
Once you've entered your details in the settings page you can connect to each service (plex, spotify, etc.), you are now able to access and manage your playlists.

1. On the Plex tab, press the `Connect` button. On the Spotify tab, press the `Connect` button.
2. On the Plex tab, select the library section you want to operate in.

From there you can:
- Use the `M3U` Button to download playlists as m3u file.
- Use the `Upload` Button to upload playlist from an m3u file.
- Use the `Transfer` Button to transfer playlist from one service to another (Plex/Spotify)



# Troubleshooting
If you encounter any issues, take a look at the [troubleshooting section](https://github.com/rchr157/plex-playlists/wiki#troubleshooting-tips). If that does not resolve your issue, submit an issue.

# APIs that make this possible
- [Python-PlexAPI](https://github.com/pkkid/python-plexapi)
- [Spotipy](https://github.com/spotipy-dev/spotipy)

# Attributions
Vectors and icons by <a href="https://www.figma.com/community/file/1166831539721848736?ref=svgrepo.com" target="_blank">
Solar Icons</a> in CC Attribution License via <a href="https://www.svgrepo.com/" target="_blank">SVG Repo</a>
