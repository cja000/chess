#!/usr/bin/env python
import argparse
import os
import chess.pgn
import chess.uci
import sys
import re
import time

__author__ = "Carlos Alamo"
__date__ = "2016-03-20"
__version__ = "0.01"


class Player:
    """
        Player class with name, victories, defeats and draws.
    """

    def __init__(self, players_name):
        self.white_games = []
        self.black_games = []
        self.opponents = []
        self.name = players_name


class Move:
    """
        Moves of a game with statistics
    """

    def __init__(self):
        self.ply = 0
        self.move = ''
        self.cp = 0.0
        self.mate = 0
        self.nodes = 0
        self.time = 0.0

    def fill(self, stats):
        """
            Fill the move with the data of stats
        """
        self.ply = stats.info.get('depth', None)
        self.move = stats.info['pv'][1][0]
        self.mate = stats.info['score'][1][1]
        if not self.mate:
            self.cp = float(stats.info['score'][1][0]) / 100
        else:
            self.cp = 100.0
        self.nodes = stats.info['nodes']
        # self.time = stats.info['time']


class Engine:
    """
        Engine use for the analysis.
    """

    def __init__(self, path):
        """
            Check that the engine executable exists and start it
        """
        if not os.path.isfile(path):
            print 'Engine {} does not exists.'.format(path)
            sys.exit(1)
        self.engine = chess.uci.popen_engine(path)
        self.engine.uci()
        self.name = self.engine.name

    def quit(self):
        """
            Quit the engine
        """
        self.engine.quit()


def read_all_pgn(filename):
    """
        Read all the games of a pgn file
        Input:
        :param filename: [string] Name of the pgn file
        :return: all_games [list] List with all the games
    """
    print ' Reading PGN file '.center(40, '*')
    all_games = []
    game_ok = True
    t0 = time.time()
    with open(filename, 'r') as pgn_file:
        while game_ok:
            new_game = chess.pgn.read_game(pgn_file)
            if new_game:
                all_games.append(new_game)
            else:
                game_ok = False
    t1 = time.time()
    print 'Total number of games: {}'.format(len(all_games))
    print 'Time: {:.2f} seconds'.format(t1 - t0)
    print 40 * '-'

    return all_games


def find_player(pgn_games, name):
    """
    Find a player in a pgn file using regular expressions.
    :param pgn_games: list of pgn games to parse
    :param name: Name or part of the name of the player
    :return: If there are several matches, the list of coincidences
             If there is only one match, the name and the list of matches
    """
    print 'Searching for players matching: "{}"'.format(name)
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
        print 'Several players found:'
        for name in unique_players:
            print '\t{}'.format(name)
        sys.exit()
    elif len(unique_players) == 1:
        print 'Player found:\n\t{}'.format(unique_players[0])
        unique_players = unique_players[0]
        # player = player(name_found[0])
    else:
        print 'No player found.'
    print 40 * '-'

    return unique_players, all_games


def find_all_players(pgn_games):
    """
        Find all the players in the pgn matches.
    :param pgn_games: [list] List with all the games
    :return: List with all the players
    """
    all_players = []
    for game in pgn_games:
        all_players.append(game.headers['White'])
        all_players.append(game.headers['Black'])
    return list(set(all_players))


def game_to_paired_list(game):
    """
        Create a list with the movements grouped in pairs of the game.
    :param game: Game to print
    :return: List with the movements of the game in pairs [(w1,b1),(w2,b2)...]
    """
    move_list = []
    # print '{} vs {}'.format(game.headers['white'], game.headers['black'])
    node = game
    # move_number = 1
    while not node.is_end():
        # white move
        next_node = node.variation(0)
        white_move = node.board().san(next_node.move)
        node = next_node
        # black move
        if not node.is_end():
            next_node = node.variation(0)
            black_move = node.board().san(next_node.move)
            node = next_node
        else:
            black_move = ''
        move_list.append((white_move, black_move))
        # print '{:3}.  {:6}\t{:6}'.format(move_number, white_move, black_move)
        # move_number = move_number + 1

    return move_list


def game_to_list(game):
    """
        Create a list with the movements of the game.
    :param game: Game(chess.pgn.Game) to print
    :return: List with the movements of the game [w1,b1,w2,b2,...]
    """
    move_list = []
    node = game
    while not node.is_end():
        next_node = node.variation(0)
        move = node.board().san(next_node.move)
        node = next_node
        move_list.append(move)
    return move_list


def analyze_game(game, machine, depths, player):
    """
        Analyze a game
        :param game: Game of the player to analyze read from the PGN file
        :param machine: Engine object
        :param depths: List with the depths of analysis
        :param player: Name of the player to analyze

        :return: Game analyzed
    """

    def analyze_move(machine, stats, ply, move):
        """
            Analyze one move and its best move

            :param machine: Machine with the position to analyze
            :param move:    Move to analyze
            :param stats:   InfoHandler to store statistics
            :param ply:     Depth of analysis
            :return: best move, move and new status of the machine
        """
        best_move = Move()
        played_move = Move()

        # Play best move
        machine.engine.go(depth=ply).bestmove
        best_move.fill(stats)
        best_move.move = board.san(best_move.move)
        machine.engine.go(depth=ply,
                          searchmoves=[board.parse_san(move)]
                          )
        played_move.fill(stats)
        played_move.move = board.san(played_move.move)

        return best_move, played_move

    analyzed_game = []
    paired_moves = game_to_paired_list(game)
    board = chess.Board()
    machine.engine.ucinewgame()
    machine.engine.position(board)
    stats = chess.uci.InfoHandler()
    machine.engine.info_handlers.append(stats)

    for position, move in enumerate(paired_moves):
        if game.headers['White'] == player:
            # Before analyze the next withe move, push the previous black move
            # Except for the first move
            if position > 0:
                board.push(board.parse_san(previous_black_move))
                machine.engine.position(board)
            column = 0
        elif game.headers['Black'] == player:
            # White goes first
            board.push(board.parse_san(move[0]))
            machine.engine.position(board)
            column = 1
        csv_move = str(move[column])
        # In case that there is black time and it draws without doing the move
        if move[column] != '':
            for ply in depths:
                best_move, played_move = analyze_move(machine,
                                                      stats,
                                                      ply,
                                                      move[column]
                                                      )
                csv_move = csv_move + ';' + \
                                      ';'.join([str(ply),
                                                str(played_move.cp),
                                                str(best_move.move),
                                                str(best_move.cp)
                                               ]
                                              )
            analyzed_game.append(csv_move)
            # print csv_move
            # Push move
            board.push(board.parse_san(move[column]))
            machine.engine.position(board)
            previous_black_move = move[1]
    return analyzed_game


def output_result(output_file, all_analyzed_games, plys):
    """
        Print or save result
        :param output_file: Name of the outpufile or None
        :param all_analyzed_games: All the games analyzed to print
        :param plys: All the plys that have been requested
        :return: Printed or saved results
    """
    print 'Printing results '.center(40, '*')
    all_difs = []
    # Header for the CSV file
    csv_header = 'Move;'
    for p in plys:
        csv_header += 'ply;cp move;best move;cp best move;'
        all_difs.append([])
    if output_file:
        csv_file = open(output_file, 'w')
        csv_file.write(csv_header[:-1] + '\n')
    else:
        print csv_header[:-1]
    # Values
    for game in all_analyzed_games:
        for move in game:
            if output_file:
                csv_file.write(move + '\n')
            else:
                print move
            aux = move.split(';')[2::2]
            for p in range(len(plys)):
                all_difs[p] = all_difs[p] + \
                              [(float(aux[2 * p + 1]) - float(aux[2 * p]))]
    # Averages per ply
    for d in range(len(all_difs)):
        print 'Average for {} plys: {:+.2f}' \
            .format(plys[d], sum(all_difs[d]) / len(all_difs[d]))


def main():
    """
        Main procedure
    """
    args = arguments()
    all_analyzed_games = []

    # Read games from .pgn file
    all_games = read_all_pgn(args.pgn_file)

    # Search for player
    player_name, games_of_the_player = find_player(all_games, args.player)

    # Create chess engine
    chess_engine = Engine(args.engine)

    # Begin of analysis
    t0 = time.time()
    game_number = 1
    for game in games_of_the_player:
        print 'Analyzing game {} of {}\r'.format(game_number, len(all_games)),
        analyzed_game = analyze_game(game, chess_engine, args.ply, player_name)
        game_number += 1
        all_analyzed_games.append(analyzed_game)
    t1 = time.time()
    chess_engine.quit()
    print 'Analysis time: {:.2f} seconds ({:.3f} sec / game)' \
        .format(t1 - t0, (t1 - t0) / len(all_games))
    # Results
    output_result(args.output_file, all_analyzed_games, args.ply)



def arguments():
    """
        Parse the arguments of the script.
        :return
            options: Options used.
            args:    Arguments used.
    """
    usage = 'usage: %(prog)s <pgn file>'
    desc = 'Read pgn file and get stats.'
    parser = argparse.ArgumentParser(usage=usage, description=desc)
    parser.add_argument('--version',
                        action='version',
                        version=__version__)
    parser.add_argument('pgn_file')
    parser.add_argument('-p', '--player',
                        action='store',
                        type=str,
                        help='Name of the player to analyze.')
    parser.add_argument('-ply',
                        action='store',
                        nargs="+",
                        type=int,
                        default=2,
                        help='Number of ply to calculate by the engine.')
    parser.add_argument('-e', '--engine',
                        action='store',
                        type=str,
                        help='Chess engine to use for the analysis.')
    parser.add_argument('-o', '--output_file',
                        action='store',
                        type=str,
                        help='Output filename to store the CSV result.')
    args = parser.parse_args()

    return args


if __name__ == '__main__':
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
    # sys.tracebacklimit=0
    if sys.version_info < (2, 7):
        print 'Python 2.7 or higher required'
        sys.exit(9)
    # Main function
    try:
        main()
    except KeyboardInterrupt:
        print "\nProgram interrupted by CTRL-C.\n"
        sys.exit()
