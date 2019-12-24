import json
import urllib.request
import os
from urllib.error import HTTPError


class ChessCom(object):
    '''
    Class to wrap the API from chess.com website
    '''
    URL_ROOT = 'https://api.chess.com/pub/player/'
    ARCHIVES_PATH = 'games/archives'
    GAMES_PATH = 'games'
    GAMES_TO_MOVE_PATH = 'games/to-move'
    
    def __init__(self, user):
        '''
            :param user: Name of the user in chess.com
            :type user: str
        '''
        self.user = user

    def _get_from_url(self, url):
        '''
            Get JSON data from a URL
            :param url: URL to query
            :type url: str
            :return: JSON data from the query
            :rtype: json (python dict)
        '''
        try:
            with urllib.request.urlopen(url) as url_desc:
                json_data = json.loads(url_desc.read().decode())
        except HTTPError as ex:
            print(ex.read())
        return json_data

    def _read_profile(self):
        '''
            Query for the profile
            :return: Profile of the user
            :rtype: JSON
        '''
        url_profile = os.path.join(self.URL_ROOT, self.user)
        return self._get_from_url(url_profile)

    def _read_archives(self):
        '''
            Query for the archives stored of the users
            :return: List with the year/months archive of the user
            :rtype: JSON
        '''
        url_archives = os.path.join(self.URL_ROOT,
                                    self.user,
                                    self.ARCHIVES_PATH)
        return self._get_from_url(url_archives)

    def read_current_games(self):
        '''
            Query for the current games of the user
            :return: List with the games currently active
            :rtype: JSON
        '''
        url_games = os.path.join(self.URL_ROOT,
                                 self.user,
                                 self.GAMES_PATH)
        return self._get_from_url(url_games)

    def read_games_to_move(self):
        '''
            Query for the games with user turn to move
            :return: List with games to move
            :rtype: JSON
        '''
        url_games = os.path.join(self.URL_ROOT,
                                 self.user,
                                 self.GAMES_TO_MOVE_PATH)
        return self._get_from_url(url_games)

    def get_fen_to_move(self):
        '''
            Join the games to move and the information of those games to be
            able to return a list with the FEN position of the games.
            :return: List with the FEN of the games to move
            :rtype: list
        '''
        games_to_move = self.read_games_to_move()
        current_games = self.read_current_games()
        fen_to_move = []
        for game_to_move in games_to_move['games']:
            last_activity = game_to_move['last_activity']
            for game in current_games['games']:
                if game['last_activity'] == last_activity:
                    fen_to_move.append(game['fen'])
        return fen_to_move
