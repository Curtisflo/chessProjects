import chess
import numpy as np
from chess import pgn
import matplotlib.pyplot as plt


def calculateDefenseScore(board: chess.Board, pieceSq: int) -> float:
    color = board.color_at(pieceSq)
    pieceMap = board.piece_map()
    total = 0
    for square in board.attacks(pieceSq) & board.occupied:
        if square in pieceMap.keys():
            attackedPiece = pieceMap[square]
            if attackedPiece.color == color and 1 <= attackedPiece.piece_type: # Should pawns be included?
                total += 1
    return total


def countAttackedSquares(board: chess.Board, color: chess.Color) -> float:
    total = 0
    for square in chess.SQUARES:
        total += len(board.attackers(color, square))
    return total


def findBatteries(board: chess.Board, color: chess.Color):
    pieceMap = board.piece_map()
    for square, piece in pieceMap.items():
        if piece.piece_type == chess.BISHOP:
            for sq in board.attacks(square):
                if sq in pieceMap.keys():
                    if pieceMap[sq].piece_type == chess.QUEEN:
                        print('Queen-bishop battery')
            print(piece)


def getSquareAttackCounts(board: chess.Board) -> dict:
    """
    This calculates how often each square is attacked by each color
    board: chess.Board
        The position
    return -> dict
        Indexed by squares, having tuples as values with the attack count from White and Black
    """
    attackedSquares = dict()
    for square in chess.SQUARES:
        wCount = len([piece for piece in board.attackers(chess.WHITE, square)])
        bCount = len([piece for piece in board.attackers(chess.BLACK, square)])
        attackedSquares[square] = (wCount, bCount)
    return attackedSquares


def getSquareControl(board: chess.Board) -> dict:
    """
    This function calculates how well both sides are controlling the squares on the board.
    board: chess.Board
        The position of interest
    return -> dict:
        Dictionary with squares as keys and square control as values: 
            -1 -> full black control
            1 -> full white control
    """
    control = dict()
    pieceValues = [1, 3, 3, 5, 9, 12]
    for square in chess.SQUARES:
        wAttackers = [piece for piece in board.attackers(chess.WHITE, square) if not board.is_pinned(chess.WHITE, piece)]
        bAttackers = [piece for piece in board.attackers(chess.BLACK, square) if not board.is_pinned(chess.BLACK, piece)]

        # Detecting batteries to get the second piece also as an attacker
        wBatteryPiece = 0
        bBatteryPiece = 0
        for wa in wAttackers:
            if board.piece_type_at(wa) in [4, 5]:
                # detecting rook/queen batteries
                for p in board.attackers(chess.WHITE, square, board.occupied ^ (2**wa)):
                    if p not in wAttackers and board.piece_type_at(p) in [4, 5]:
                        wBatteryPiece = board.piece_type_at(p)
            elif board.piece_type_at(wa) in [1, 3, 5]:
                # detecting bishop/queen batteries
                for p in board.attackers(chess.WHITE, square, board.occupied ^ (2**wa)):
                    if p not in wAttackers and board.piece_type_at(p) in [3, 5]:
                        wBatteryPiece = board.piece_type_at(p)

        for ba in bAttackers:
            if board.piece_type_at(ba) in [4, 5]:
                # detecting rook/queen batteries
                for p in board.attackers(chess.BLACK, square, board.occupied ^ (2**ba)):
                    if p not in bAttackers and board.piece_type_at(p) in [4, 5]:
                        bBatteryPiece = board.piece_type_at(p)
            elif board.piece_type_at(ba) in [1, 3, 5]:
                # detecting bishop/queen batteries
                for p in board.attackers(chess.BLACK, square, board.occupied ^ (2**ba)):
                    if p not in bAttackers and board.piece_type_at(p) in [3, 5]:
                        bBatteryPiece = board.piece_type_at(p)

        wAttackerTypes = sorted([board.piece_type_at(p) for p in wAttackers])
        bAttackerTypes = sorted([board.piece_type_at(p) for p in bAttackers])

        if wBatteryPiece > 0:
            # adding the battery piece to the attackers TODO: in the correct spot 
            wAttackerTypes.append(wBatteryPiece)
        if bBatteryPiece > 0:
            bAttackerTypes.append(bBatteryPiece)

        # compare the attackers of both sides to see who controls the square
        c = 0

        for i in range(max(len(wAttackerTypes), len(bAttackerTypes))):
            if i == len(wAttackerTypes)-1 and i == len(bAttackerTypes)-1:
                break
            if i < len(wAttackerTypes) and i < len(bAttackerTypes):
                wa = pieceValues[wAttackerTypes[i]-1]
                ba = pieceValues[bAttackerTypes[i]-1]

                if wa == ba:
                    # pieces of the same value neutralise each other
                    continue

                if wa < ba and len(wAttackerTypes) > i+1:
                    # white has the less valuable piece and has another piece to recapture
                    for j in range(i, len(wAttackerTypes)):
                        wVal = pieceValues[wAttackerTypes[j]-1]
                        if j < len(bAttackerTypes):
                            bVal = pieceValues[bAttackerTypes[j]-1]
                            if wVal <= bVal:
                                c += 1/wVal - 1/bVal
                            else:
                                break
                        else:
                            c += 1/wVal
                    break
                if ba < wa and len(bAttackerTypes) > i+1:
                    for j in range(i, len(bAttackerTypes)):
                        bVal = pieceValues[bAttackerTypes[j]-1]
                        if j < len(wAttackerTypes):
                            wVal = pieceValues[wAttackerTypes[j]-1]
                            if bVal <= wVal:
                                c += 1/wVal - 1/bVal
                            else:
                                break
                        else:
                            c -= 1/bVal
                    break
            elif i < len(wAttackerTypes):
                # white has more attackers than black
                wa = pieceValues[wAttackerTypes[i]-1]
                c += 1/wa
            elif i < len(bAttackerTypes):
                ba = pieceValues[bAttackerTypes[i]-1]
                c -= 1/ba

        control[square] = min(max(c, -1), 1)
    return control


def plotHeatmap(squareControl: dict, filename: str = None):
    """
    This fucntion plots a heatmap of the square control
    """
    files = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    ranks = [8, 7, 6, 5, 4, 3, 2, 1]

    # reversing to get the squares to line up correctly
    data = np.reshape(list(reversed(squareControl.values())), (8, 8))
    data = [list(reversed(l)) for l in data]
    fig, ax = plt.subplots(figsize=(6, 6))
    im = ax.imshow(data, cmap='plasma')
    plt.title('Square control')

    ax.set_xticks(np.arange(8), labels=files)
    ax.set_yticks(np.arange(8), labels=ranks)
    # add minor ticks for the grid
    ax.set_xticks(np.arange(9)-.5, minor=True)
    ax.set_yticks(np.arange(9)-.5, minor=True)
    ax.grid(which='minor', color='black', linestyle='-', linewidth=1)
    # ax.figure.colorbar(im, fraction=0.046, pad=0.04)
    fig.tight_layout()
    ax.figure.patch.set_facecolor('#e6f7f2')

    if filename:
        plt.savefig(filename, dpi=500)
    else:
        plt.show()


def countDefendedSquares(board: chess.Board, attackedSquares: dict) -> tuple:
    """
    This function counts the number of squares each side is defending around their king
    board: chess.Board
        The position
    attackedSquares: dict
        Generated by getSquareAttackCounts
    return -> tuple
        Number of defended squares around the king for White and Black
    """
    wCount = 0
    bCount = 0
    wKing = board.king(chess.WHITE)
    bKing = board.king(chess.BLACK)
    for square, (wAttackers, bAttackers) in attackedSquares.items():
        if chess.square_distance(wKing, square) == 1 and wAttackers > 1:
            for i in range(max(0, wAttackers-bAttackers)):
                wCount += 1/(2**(i+1))
        if chess.square_distance(bKing, square) == 1 and bAttackers > 1:
            for i in range(max(0, bAttackers-wAttackers)):
                bCount += 1/(2**(i+1))
    return (wCount/len(board.attacks(wKing)), bCount/len(board.attacks(bKing)))


def countOffensiveAttackedSquares(board: chess.Board, attackedSquares: dict) -> tuple:
    """
    This function calculates the squares that both sides attack, focusing on the offensive, which means:
        - only counting squares starting from the third rank
        - discount squares occupied by the own pieces
        - favour squares around the opponent's king
        - reduce the value of additional attackers #TODO
    board: chess.Board
        The position, needed to check where specific pieces are
    attackedSquares: dict
        Generated by getSquareAttackCounts
    return -> tuple
        The offensiveAttackedSquares for both sides
    """
    wCount = 0
    bCount = 0
    for square, (wAttackers, bAttackers) in attackedSquares.items():
        if square >= 16 and board.color_at(square) != chess.WHITE:
            for i in range(wAttackers):
                wCount += 1/(2**i)
        if square <= 48 and board.color_at(square) != chess.BLACK:
            for i in range(bAttackers):
                bCount += 1/(2**i)
    return (wCount/48, bCount/48)


def calculatePieceCoordination(board: chess.Board) -> tuple:
    """
    This calculates the piece coordination for a single position
    board: chess.Board
        The position
    return -> tuple
        The piece coordination score for white and black
    """
    factors = [0.5, 0.5]
    whiteCoord = countAttackedSquares(board, chess.WHITE) * factors[0]
    blackCoord = countAttackedSquares(board, chess.BLACK) * factors[0]
    for square in chess.SquareSet(board.occupied):
        if board.piece_type_at(square) != chess.PAWN:
            if board.color_at(square) == chess.WHITE:
                whiteCoord += calculateDefenseScore(board, square) * factors[1]
            elif board.color_at(square) == chess.BLACK:
                blackCoord += calculateDefenseScore(board, square) * factors[1]
    return (whiteCoord, blackCoord)


def plotGameCoordination(pgnPath: str, filename: str = None):
    colors = ['#689bf2', '#5afa8d', '#f8a978', '#fa5a5a']

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor('#e6f7f2')

    coordination = list()

    with open(pgnPath, 'r') as pgn:
        game = chess.pgn.read_game(pgn)
        white = game.headers['White']
        black = game.headers['Black']
        
        board = chess.Board()
        coordination.append(calculatePieceCoordination(board))

        for move in game.mainline_moves():
            board.push(move)
            coordination.append(calculatePieceCoordination(board))

    wCoord = [c[0] for c in coordination]
    bCoord = [c[1] for c in coordination]
    ax.plot(wCoord, color=colors[0], label=f"{white}'s coordination")
    ax.plot(bCoord, color=colors[1], label=f"{black}'s coordination")
    fig.subplots_adjust(bottom=0.1, top=0.95, left=0.1, right=0.95)
    ax.legend()

    if filename:
        plt.savefig(filename, dpi=400)
    else:
        plt.show()


if __name__ == '__main__':
    board = chess.Board('2bqr1k1/1p3ppp/p2b1n2/3p4/8/1P2PN2/PB2NPPP/3Q1RK1 b - - 1 17')
    dragon = chess.Board('rnbq1rk1/pp2ppbp/3p1np1/8/3NP3/2N1BP2/PPPQ2PP/R3KB1R b KQ - 2 8')
    # for piece in chess.SquareSet(board.occupied):
        # print(calculateDefenseScore(board, piece))
    # print(countAttackedSquares(board, board.turn))
    # findBatteries(dragon, chess.WHITE)
    # print(calculatePieceCoordination(dragon))
    # attackedSqs = getSquareAttackCounts(dragon)
    pos = chess.Board('2k5/7R/3K1p2/3P1P2/8/7p/7r/8 b - - 1 53')
    study = chess.Board('k6n/1p6/1K6/7B/8/P7/8/8 b - - 3 2')
    study2 = chess.Board('8/8/3b2k1/8/2B1K3/6P1/2N3n1/8 w - - 1 1')
    weakDS = chess.Board('2r1r1k1/1pq1np1p/p3p1p1/3pP3/5Q2/P1P5/1P1NRPPP/4R1K1 b - - 4 22')
    sqc = getSquareControl(weakDS)
    print(sqc)
    plotHeatmap(sqc, filename='../out/squareControlDarkSquares-nb.png')
    # print(countOffensiveAttackedSquares(dragon, attackedSqs))
    # plotGameCoordination('../resources/karpov-spassky-1974.pgn')
