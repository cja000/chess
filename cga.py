#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Analyze chess games against a chess engines to see de deviation.

Example::
    $ ./cga.py games.pgn -t 10
"""

import os
import sys
import argparse
import logging
import time
import re
import chess.pgn
import chess.uci

__author__ = "Carlos Alamo"
__email__ = "my@email.com"
__date__ = "2017-02-26"
__version__ = "1.00"


COLOURS = ['White', 'Black']
NONAME = 'Noname'
POSITIONS = [1, 2, 3]


class Move(object):
    """Class to store move information.

        :var self.move: Move done
        :vartype self.move: str
        :var self.best_move: Best move according the engine
        :vartype self.best_move: chess.uci.Score
        :var self.cp: Centipawns of the move
        :vartype self.cp: int
        :var self.bm_score: Score of the best move
        :vartype self.bm_cp: chess.uci.Score
        :var self.cp_diff: Difference between the move and the best move
        :vartype self.cp_diff: int
        :var self.best_move_position: Position of the move done in the list of
                                      MultiPV generated by the engine.
                                      Only count 3 first positions, the rest
                                      will be =0
        :vartype self.best_move_position: int
    """

    def __init__(self, move, cp, bm, bm_score, bmp=0):
        """Init definition for Move class."""
        self.move = move
        self.cp = cp
        self.bm = bm.strip()
        self.bm_score = bm_score
        self.cp_diff = self._cp_diff_calculation(self.cp, self.bm_score)
        self.best_move_position = bmp

    def _cp_diff_calculation(self, cp, bm_cp):
        """Calculate the difference score between the move and the best move.

           White is + and black is - so you will have to add to get the diff.
           Args:
                :arg cp:    Score of the move
                :type cp:   chess.uci.Score
                :arg bm_cp: Score of the best move
                :type bm_cp: chess.uci.Score
            Returns:
                :return diff_score: Score with the difference
                :rtype diff_score:  chess.uci.Score
        """
        if cp.mate is not None and bm_cp.mate is not None:
            diff_score = chess.uci.Score(0, bm_cp.mate + cp.mate)
        elif cp.cp is not None and bm_cp.cp is not None:
            diff_score = chess.uci.Score(bm_cp.cp + cp.cp, None)
        elif cp.mate is not None and bm_cp.cp is not None:
            diff_score = chess.uci.Score(bm_cp.cp, cp.mate)
        elif cp.cp is not None and bm_cp.mate is not None:
            diff_score = chess.uci.Score(cp.cp, bm_cp.mate)

        return diff_score

    def __str__(self):
        """Print the move and the best move with its stats."""
        return '{:5s} {{bm={:10s} cp={:7} diff={:7} pos={}}}'.\
            format(self.move,
                   self.bm,
                   parse_score(self.bm_score),
                   parse_score(self.cp_diff),
                   self.best_move_position)


class Player(object):
    """Information about a player.

        This information can be:
            * name
            * victories, defeats and draws
            * Centipawns average
            * Difference CP average
            * ...

        :var self.white_games: All the games of the player with white pieces
        :type self.white_games: list(Games)
        :var self.black_games: All the games of the player with black pieces
        :type self.black_games: list(Games)
        :var self.opponents:  Opponents of this player
        :type self.opponents: list[Player]
        :var self.name: Player's name
        :vartype self.name: str
    """

    def __init__(self, players_name):
        """Init definition for Player class.

            :arg players_name: Player's name
            :type players_name: str
        """
        self.all_games = []
        self.opponents = []
        self.name = players_name
        self.number_plys = 0
        self.initialize_stats()

    def insert_game(self, game):
        """Insert the games played by the player.

            Args:
                :arg game:     Game played by the player
                :type game:    [chess.pgn.Game]
        """
        self.all_games.append(game)
        # Update number of plys
        self.number_plys = 0
        self.total_number_plys()
        # Update statistics and average statistics
        self.initialize_stats()
        self.get_stats()
        self.avg_stats()

    def initialize_stats(self):
        """Initialize the stats of the player."""
        self.engine_stats = {'cp_avg': [],
                             'diff_avg': [],
                             'position': []}
        self.cp_avg = 0.0,
        self.diff_avg = 0.0,
        self.position_avg = {}
        for pos in POSITIONS:
            self.position_avg[pos] = 0.0
        self.top_3_avg = 0.0

    def get_stats(self):
        """Get statistics of all the games of this player."""
        for game in self.all_games:
            cp_avg, diff_avg, position =\
                game.average_analyzed_game()
            if self.name == NONAME:
                sides = COLOURS
            elif self.name == game.headers['White']:
                sides = ['White']
            elif self.name == game.headers['Black']:
                sides = ['Black']
            for side in sides:
                self.engine_stats['cp_avg'].append(cp_avg[side])
                self.engine_stats['diff_avg'].append(diff_avg[side])
                self.engine_stats['position'].append(position[side])

    def avg_stats(self):
        """Average statistics of all the games of the player."""
        def average(values):
            """Average of a list."""
            return sum(values) / len(values)

        cp_aux = 0.0
        diff_aux = 0.0
        pos_aux = {}
        for pos in POSITIONS:
            pos_aux[pos] = 0
        cp_aux += average(self.engine_stats['cp_avg'])
        diff_aux += average(self.engine_stats['diff_avg'])
        for game in self.engine_stats['position']:
            for pos in POSITIONS:
                if pos in game.keys():
                    pos_aux[pos] += game[pos]
        self.cp_avg = cp_aux
        self.diff_avg = diff_aux
        sum_top_3_aux = 0
        for pos in pos_aux.keys():
            sum_top_3_aux += pos_aux[pos]
            self.position_avg[pos] =\
                float(pos_aux[pos]) / self.number_plys * 100
        self.top_3_avg = float(sum_top_3_aux) / self.number_plys * 100

    def total_number_plys(self):
        """The total number of moves done by the player."""
        for game in self.all_games:
            for colour in COLOURS:
                if self.name == game.headers[colour]:
                    self.number_plys += game.number_plys[colour]

    def print_stats(self):
        """Print statistics of the player."""
        position_accumulative = 0
        stats_str = 'Player: {:s}\n'.format(self.name)
        stats_str += 'Number of games: {:d}\n'.format(len(self.all_games))
        stats_str += 'Number of plys: {:d}\n'.format(self.number_plys)
        stats_str += 'Averages:\n'
        stats_str += ' cp:   {:+5.2f}\n'.format(self.cp_avg)
        stats_str += ' diff: {:+5.2f}\n'.format(self.diff_avg)
        for pos in POSITIONS:
            position_accumulative += self.position_avg[pos]
            stats_str += ' pos {:d}: {:5.2f}% ({:5.2f}%)\n'.\
                format(pos,
                       self.position_avg[pos],
                       position_accumulative)
        stats_str += ' top 3: {:5.2f}%\n'.format(self.top_3_avg)
        return stats_str


class Engine(object):
    """Engine use for the analysis.

        You can access all the chess.uci methods calling <name>.engine.<method>

        :var multi_pv: MultiPV value
        :type multi_pv: int
    """

    def __init__(self, path):
        """Check that the engine executable exists and start it."""
        if not os.path.isfile(path):
            logger.error('Engine %s does not exists.', path)
            sys.exit(1)
        self.engine = chess.uci.popen_engine(path)
        self.engine.uci()
        self.name = self.engine.name
        self.multi_pv = self.engine.options['MultiPV'].default

    def set_multi_pv(self, multi_pv):
        """Manage MultiPV option.

        Check if the option MultiPV exisits and set it to the maximum allowed
        by the engine.
        """
        max_multi_pv = 0
        self.multi_pv = multi_pv
        if 'MultiPV' in self.engine.options.keys():
            try:
                max_multi_pv = self.engine.options['MultiPV'].max
            except:
                logger.warning('Not able to get maximum MultiPV.')
            if self.multi_pv > 0 and max_multi_pv > 1:
                self.engine.setoption({'MultiPV': self.multi_pv})
                logger.debug('Set MultiPV to: {}'.format(self.multi_pv))
            elif multi_pv == 0 and max_multi_pv > 1:
                self.engine.setoption({'MultiPV': max_multi_pv})
                logger.debug('Set MultiPV to: {}'.format(max_multi_pv))
            else:
                logger.warning('Error setting maximum MultiPV.')

    def quit(self):
        """Quit the engine."""
        self.engine.quit()


class Game(chess.pgn.Game):
    """Extend the chess.pgn.Game class to include statistics."""

    def __init__(self, chess_pgn_game):
        """Extend init from chess.pgn.Game class."""
        super(Game, self).__init__()
        # Copy the original game
        if chess_pgn_game is not None:
            self.headers = chess_pgn_game.headers
            self.variations = chess_pgn_game.variations
        self.analyzed_game = {}
        self.number_plys = {}
        self.pos_dict = {}
        self.avg_diff = {}
        self.avg_cp = {}
        self.pv_dict = {}

    def store_analyzed_game(self, white_moves, black_moves):
        """Store an analyzed game.

            An analyzed game is a dictionary with 2 keys: 'white' and 'black'
            The values are lists with Move elements.
            Initialize statistical variables.
            Args:
                :arg white_moves:   White moves analyzed
                :type white_moves:  list[Move]
                :arg black_moves:   Black moves analyzed
                :type black_moves:  list[Move]

            Returns:
        """
        self.analyzed_game = {'White': white_moves,
                              'Black': black_moves}
        self.number_plys = {'White': len(self.analyzed_game['White']),
                            'Black': len(self.analyzed_game['Black'])}
        self.pos_dict = {'White': {},
                         'Black': {}}
        self.avg_diff = {'White': 0.0,
                         'Black': 0.0}
        self.avg_cp = {'White': 0.0,
                       'Black': 0.0}

    def average_analyzed_game(self):
        """Calculate the averate for player's game.

            Returns:
                :return cp_avg:   Average of cp
                :rtype cp_avg:    float
                :return diff_avg: Average difference with best move
                :rtype diff_avg:  float
                :return pos_list: Dictionary with the number of times that the
                                  move was in that position of the best move
                :rtype pos_list:  dict{}
        """
        for side in COLOURS:
            move_cp = []
            cp_diff = []
            pos_dict = {}
            for move in self.analyzed_game[side]:
                if not isinstance(move, Move):
                    continue
                if move.move is not None:
                    cp_diff.append(move.cp_diff.cp / 100.0)
                    # score_value = parse_score(move.cp)
                    score_value = parse_score(move.bm_score)
                    if score_value[0] != 'M':
                        move_cp.append(float(score_value))
                    if move.best_move_position != 0:
                        if move.best_move_position not in pos_dict.keys():
                            pos_dict[move.best_move_position] = 1
                        else:
                            pos_dict[move.best_move_position] += 1
            total_moves = float(len(cp_diff))
            if total_moves != 0:
                self.pos_dict[side] = pos_dict
                self.avg_diff[side] = sum(cp_diff) / total_moves
                self.avg_cp[side] = sum(move_cp) / total_moves
            else:
                self.pos_dict[side] = pos_dict
                self.avg_diff[side] = 0
                self.avg_cp[side] = 0

        return self.avg_cp, self.avg_diff, self.pos_dict

    def analyze_pv_frecuency(self, pv_dict, total_moves):
        """Get % of matches between the engine and the player.

            Args:
                :arg pv_dict:       Dictionary with the frecuencies
                :type pv_dict:      dict{}
                :arg total_moves:   Total number of moves
                :type total_moves:  int
            Returns:
                :return result_str:    String with the printout
                :rtype result_str:     str
        """
        order = ['1st', '2nd', '3rd']
        result_str = ''
        percentage = 0.0
        top_3_sum = 0
        top_3_percentaje = 0.0
        self.pv_dict = pv_dict
        for i, _ in pv_dict.iteritems():
            percentage = self.pv_dict[i] / float(total_moves) * 100
            result_str += '  {}:   {:3} ({:5.2f}%)\n'.\
                format(order[i - 1], self.pv_dict[i], percentage)
            top_3_sum += self.pv_dict[i]
        top_3_percentaje = top_3_sum / float(total_moves) * 100
        result_str += '  Top 3: {:3} ({:5.2f}%)\n'.\
                      format(top_3_sum, top_3_percentaje)

        return result_str

    def print_analyzed_game(self):
        """Print the analyzed game.

            Args:
                Takes the analyzed_game from the Game
            Returns:
                Printout with verbose or debug:
                <mv #>. <mv> {white comment} - <mv> {black comment}
                comment = <mv #>. <bm> cp=<cp> diff=<diff> pos=<pos>
                With normal level only:
                White: avg cp <avg_cp> avg diff <avg_diff> <pos_dict>
                Black: avg cp <avg_cp> avg diff <avg_diff> <pos_dict>
                :return game_str:   String with the printout
                :type game_str:     str
        """
        game_str = ''
        for i in range(len(self.analyzed_game['White'])):
            # Move number. white - black
            white_move = self.analyzed_game['White'][i]
            if i > len(self.analyzed_game['Black']) - 1:
                black_move = ''
            else:
                black_move = self.analyzed_game['Black'][i]
            game_str += '{:3}. {} - {}\n'.\
                format(i + 1,
                       white_move,
                       black_move)
        return game_str

    def print_stats_game(self):
        """Print the stats of the game.

            Args:
                Takes the analyzed_game from the Game
            Returns:
                White: avg cp <avg_cp> avg diff <avg_diff> <pos_dict>
                Black: avg cp <avg_cp> avg diff <avg_diff> <pos_dict>
                :return game_str:   String with the printout
                :type game_str:     str
        """
        game_str = ''
        for side in COLOURS:
            _, _, _ = self.average_analyzed_game()
            game_str += ('{:s}({:s}): avg cp {:+5.2f} avg diff {:+5.2f}\n'.
                         format(side.capitalize(),
                                self.headers[side.capitalize()],
                                self.avg_cp[side],
                                self.avg_diff[side]))
            game_str += self.analyze_pv_frecuency(
                self.pos_dict[side],
                len(self.analyzed_game[side]))
        return game_str


def read_all_pgn(filename):
    """Read all the games of a PGN file.

        Args:
            :arg filename: Name of the PGN file
            :type filename: str
        Returns:
            :return all_games: List with all the games
            :rtype: list[chess.game]
    """
    logger.info(' Reading PGN file {} '.format(filename).
                center(80, '*'))
    all_games = []
    game_ok = True
    time_0 = time.time()
    with open(filename, 'r') as pgn_file:
        while game_ok:
            new_game = chess.pgn.read_game(pgn_file)
            if new_game:
                all_games.append(new_game)
            else:
                game_ok = False
    time_1 = time.time()
    logger.info('Total number of games: %d', len(all_games))
    logger.info('Time: %.2f seconds', (time_1 - time_0))
    logger.info(40 * '-')

    return all_games


def find_player(pgn_games, name):
    """Find a player in a pgn file using regular expressions.

        Args:
            pgn_games   (list[chess.pgn.Game]) list of pgn games to parse
            name        (str) Name or part of the name of the player
        Returns:
            If there are several matches, the list of coincidences
            If there is only one match, the name and the list of matches
    """
    logger.info('Searching for players matching: "%s"', name)
    all_found = []
    all_games = []
    for game in pgn_games:
        if re.search(name, game.headers['White'], flags=re.IGNORECASE):
            all_found.append(game.headers['White'])
            all_games.append(game)
        if re.search(name, game.headers['Black'], flags=re.IGNORECASE):
            all_found.append(game.headers['Black'])
            all_games.append(game)
    unique_players = list(set(all_found))
    if len(unique_players) > 1:
        logger.info('Several players found:')
        for name in unique_players:
            logger.info('\t%s', name)
        sys.exit(3)
    elif len(unique_players) == 1:
        logger.info('Player found:\n\t%s', unique_players[0])
        unique_players = unique_players[0]
    else:
        logger.info('No player found.')
    logger.info(40 * '-')

    return unique_players, all_games


def parse_score(score):
    """From chess.Score(pv, mate) tupla return the cp or M<n>.

        Args:
            :arg score:     Score to parse
            :type score:    chess.uci.Score
        Returns:
            :return rscore: Score value
            :rtype rscore:  str with cp or number of move to mate
    """
    rscore = '0.0'
    if isinstance(score, chess.uci.Score):
        if score.cp is not None:
            rscore = str(score.cp / 100.0)
        elif score.mate is not None:
            rscore = 'M' + str(score.mate)
        elif score.cp is not None and score.mate is not None:
            rscore = 'N/A'
            logger.info('There is cp (%f) and mate value (%f)',
                        score.cp, score.mate)
        else:
            rscore = 'N/A'
            logger.error('No score for this move.')
    return rscore


def analyze_game(game, machine, ply=None, tpm=None, player=None):
    """Analyze a game.

        Args:
            :arg game:      Game of the player to analyze read from the PGN
            :type game:     Game
            :arg machine:   Engine to analyze the game
            :type machine:  Engine
            :arg ply:       Depths of analysis
            :type ply:      int
            :arg tpm:       Time per move
            :type tpm:      int
            :arg player:    Name of the player to analyze
            :type player:   str
        Returns:
            :return analyzed_game:  Game analyzed with engine scores
            :rtype analyzed_game:   Game
    """
    analyzed_game = Game(game)
    white_moves = []
    black_moves = []
    # Board
    board = chess.Board()
    stats = chess.uci.InfoHandler()
    # Engine
    machine.engine.ucinewgame()
    machine.engine.info_handlers.append(stats)
    # Analyze moves
    node = game
    cp_score = chess.uci.Score(0, None)

    while not node.is_end():
        # Analyze current move
        machine.engine.position(board)
        machine.engine.go(movetime=tpm, depth=ply)
        # Info
        best_moves = {}
        for k, v in stats.info['pv'].iteritems():
            best_moves[k] = board.variation_san([v[0]]).split('.')[-1].strip()
            logger.debug('Pos {:d}: {:12} {:5} {:5}'.
                         format(k,
                                board.variation_san([v[0]]),
                                stats.info['score'][k].cp,
                                stats.info['score'][k].mate))
        # Push next move to the board
        node = node.variation(0)
        if len(stats.info['pv']) == 0:
            logger.warning('No data for: {} - {}: {}'.
                           format(game.headers['White'],
                                  game.headers['Black'],
                                  node.san()))
            continue
        new_move = Move(move=node.san(),
                        cp=cp_score,
                        bm=board.variation_san(
                            [stats.info['pv'][1][0]]).split('.')[-1],
                        bm_score=stats.info['score'][1])
        if new_move.move in best_moves.values():
            new_move.best_move_position =\
                best_moves.keys()[best_moves.values().index(new_move.move)]
        cp_score = new_move.bm_score
        logger.debug('bm: {:4s} cp={:7s} mv: {:4s} cp={:7s} pos={:<3d}'.
                     format(new_move.bm,
                            parse_score(new_move.bm_score),
                            new_move.move,
                            parse_score(new_move.cp),
                            new_move.best_move_position))
        board = node.board()
        if not board.turn:
            white_moves.append(new_move)
        else:
            black_moves.append(new_move)
        logger.debug('Next move done: {:5}\n'.format(node.san()) + 40 * '-')

    analyzed_game.store_analyzed_game(white_moves, black_moves)

    return analyzed_game


# ------------------------------------------------------------------------------
#  /\  _ _     _ _  _  _ _|_ _   _  _  _|   _ _  _ . _
# /~~\| (_||_|| | |(/_| | | _\  (_|| |(_|  | | |(_||| |
#        _|
# ------------------------------------------------------------------------------

def arguments():
    """Parse the arguments of the script.

    :returns args: Arguments for the program
    :rtype: Namespace parse_args
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('pgn_file',
                        action='store',
                        help='PGN file with the games to analyze.')
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Activate verbosity')
    parser.add_argument('-d', '--debug',
                        type=str,
                        action='store',
                        help='Activate debug logging to file')
    parser.add_argument('-e', '--engine',
                        action='store',
                        type=str,
                        default='SF8.exe',
                        help='Chess engine to use for the analysis.\n'
                              'Defalut: SF8.exe')
    parser.add_argument('-p', '--player',
                        required=True,
                        action='store',
                        type=str,
                        help='Name of the player to analyze.')
    parser.add_argument('-t', '--time',
                        action='store',
                        type=int,
                        default=1000,
                        help='Time per move for the engine. '
                             'Default: 1000 micro-seconds')
    args = parser.parse_args()

    return args


def logging_init(verbose, debug_file):
    """Configure the logging levels based in the arguments of the script.

    :arg verbose: Activate the verbosity of the logs
    :varg verbose: boolean
    :arg debug_file: Write debug information to a file
    :varg debug_file: str
    """
    file_fmt = '%(asctime)s.%(msecs)03d - %(levelname)-8s - %(message)s'
    console_fmt = '%(message)s'
    # Default logger
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(console_fmt)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

    if debug_file is not None:
        # Logging to a file
        file_handler = logging.FileHandler(debug_file)
        file_formatter = logging.Formatter(file_fmt,
                                           datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)
    if verbose:
        # Increase the logging level to DEBUG
        logger.setLevel(logging.DEBUG)


def main():
    """"Steps.

        1. Arguments and logging
        2. Read all teh games
        3. Find player and his/her games
        4. Create chess engine
        5. Analysis begin
        6. Statistics
        7. Quit engine
    """
    # 1. Arguments and logging
    args = arguments()
    logging_init(args.verbose, args.debug)

    # 2. Read all the games
    all_games = read_all_pgn(args.pgn_file)

    # 3. Find player and his/her games
    if args.player is not None:
        player_name, games_to_analyze = find_player(all_games, args.player)
    else:
        player_name = NONAME
        games_to_analyze = all_games
    player = Player(player_name)

    # 4. Create chess engine
    chess_engine = Engine(args.engine)
    chess_engine.set_multi_pv(3)

    # 5. Analysis begin
    game_number = 1
    t0 = time.time()
    for game in games_to_analyze:
        # logger.info('Analyzing game {} of {}'.
        print('Analyzing game {} of {}\r'.
              format(game_number, len(games_to_analyze))),
        game_extended = analyze_game(game, chess_engine, tpm=args.time)
        logger.debug('{:s}'.format(game_extended.print_analyzed_game()))
        player.insert_game(game_extended)
        game_number += 1
    t1 = time.time()
    logger.info('\nTime: {:.2f} seconds'.format(t1 - t0))
    logger.info(40 * '-')

    # 6. Statistics
    logger.info(player.print_stats())

    # 7. Quit engine
    chess_engine.quit()


###############################################################################
#         __  __       _
#        |  \/  | __ _(_)_ __
#        | |\/| |/ _` | | '_ \
#        | |  | | (_| | | | | |
#        |_|  |_|\__,_|_|_| |_|
#
###############################################################################
if __name__ == "__main__":
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    # sys.tracebacklimit = 0
    if sys.version_info < (2, 7):
        print "Python 2.7 or higher required"
        sys.exit(9)
    # General logger
    logger = logging.getLogger(__name__)

    # Main funtion
    try:
        main()
    except KeyboardInterrupt:
        print "\nProgram interrupted by CTRL-C.\n"
        sys.exit()

