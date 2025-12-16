import random
import config
from .evaluation import scoreBoard, pieceScore
from Engine.move import Move  

# Global variables to store the best move found and the search depth
nextMove = None
current_search_depth = 3 
transpositionTable = {}

"""
This function checks if we can play a specific opening strategy (e.g., Napoleon's Plan/Scholar's Mate).
It inspects the board state and returns a pre-calculated move if the conditions are met.
"""
def findOpeningMove(gs):
    # This specific plan is for White
    if gs.whiteToMove:
        
        # --- Step 1: Move King's Pawn (e2 -> e4) ---
        # Check if the pawn is still at e2 (row 6, col 4) and e4 (row 4, col 4) is empty
        if gs.board[6][4] == "wp" and gs.board[4][4] == "--":
            # Ensure it's the start of the game (Queen and Bishop are at home)
            if gs.board[7][3] == "wQ" and gs.board[7][5] == "wB":
                return Move((6, 4), (4, 4), gs.board)

        # --- Step 2: Bring out the Queen (d1 -> h5) ---
        # Check if we already pushed the pawn to e4 and the Queen is still at d1
        if gs.board[4][4] == "wp" and gs.board[7][3] == "wQ":
            # Check if the path to h5 is clear and h5 is empty
            if gs.board[3][7] == "--":
                # Note: A smarter book would check if Black played e5, but this forces the plan
                return Move((7, 3), (3, 7), gs.board)

        # --- Step 3: Develop the Bishop (f1 -> c4) ---
        # Check if Queen is at h5 and Bishop is still at f1
        if gs.board[3][7] == "wQ" and gs.board[7][5] == "wB":
            # Check if c4 is empty
            if gs.board[4][2] == "--":
                return Move((7, 5), (4, 2), gs.board)

        # --- Step 4: Deliver Checkmate (Qxh5 -> f7) ---
        # Check if pieces are in position: Queen at h5, Bishop at c4
        if gs.board[3][7] == "wQ" and gs.board[4][2] == "wB":
            # Target the weak f7 pawn
            if gs.board[1][5] == "bp":
                return Move((3, 7), (1, 5), gs.board)

    # --- BLACK STRATEGY (Classic Center Defense) ---
    else:
        # If White played e4 (Common opening), Black should respond with e5
        # Check if White pawn is at e4
        if gs.board[4][4] == "wp":
            # Check if Black pawn is still at home (e7)
            if gs.board[1][4] == "bp" and gs.board[3][4] == "--":
                return Move((1, 4), (3, 4), gs.board) # Play e7 -> e5

        # If White plays Queen to h5 (Early Attack), Black must defend!
        # This prevents the AI from falling for Napoleon's plan easily
        if gs.board[3][7] == "wQ":
            # Attack the Queen with Knight (g8 -> f6) if safe
            if gs.board[0][6] == "bN" and gs.board[2][5] == "--":
                 return Move((0, 6), (2, 5), gs.board)

    # If no opening pattern matches, return None to let the AI think normally
    return None

"""
This is a simple function to find a random move.
Used as a fallback if the AI cannot find a better move.
"""
def findRandomMoves(validMoves):
    return validMoves[random.randint(0, len(validMoves) - 1)]

"""
This is a helper method to make the first calls for the actual algorithm.
It initializes the global variables and starts the NegaMax search.
"""
def findBestMoveMinMax(gs, validMoves, returnQueue, depth):
    global nextMove, current_search_depth
    nextMove = None
    current_search_depth = depth # Update the global depth variable
    transpositionTable.clear() # Clear memory for the new turn
    
    # OPENING BOOK CHECK 
    # Before starting the heavy calculation, check if we have a prepared opening move
    openingMove = findOpeningMove(gs)
    if openingMove is not None:
        print("Playing from Opening Book (Napoleon's Plan)!")
        returnQueue.put(openingMove)
        return # Exit immediately, no need to calculate

    random.shuffle(validMoves)
    
    # Start the recursive search
    findMoveNegaMaxAlphaBeta(gs, validMoves, depth, -config.CHECKMATE, config.CHECKMATE, 1 if gs.whiteToMove else -1)
    
    # Return the best move found
    returnQueue.put(nextMove)

"""
Implementing the Nega-Max algorithm with Alpha-Beta pruning.
This function works recursively to find the best score for the current player.
"""
def findMoveNegaMaxAlphaBeta(gs, validMoves, depth, alpha, beta, turnMultiplier):
    global nextMove
    
    # Create a unique hash key for the current board state
    boardHash = str(gs.board) + str(gs.whiteToMove) 
    
    # Check Transposition Table
    if boardHash in transpositionTable:
        entry = transpositionTable[boardHash]
        if entry['depth'] >= depth:
            if entry['flag'] == 'exact':
                return entry['score']
            elif entry['flag'] == 'lower' and entry['score'] > alpha:
                alpha = entry['score']
            elif entry['flag'] == 'upper' and entry['score'] < beta:
                beta = entry['score']
            if alpha >= beta:
                return entry['score']
    
    # Base case: if we reached the maximum depth, return the board evaluation
    if depth == 0:
        return turnMultiplier * scoreBoard(gs)

    # Move Ordering: Search better moves first to improve Alpha-Beta pruning efficiency
    orderedMoves = orderMoves(validMoves)
    maxScore = -config.CHECKMATE
    originalAlpha = alpha
    
    for move in orderedMoves:
        gs.makeMove(move)
        nextMoves = gs.getValidMoves()
        
        # Recursive call: flip alpha and beta and negate the score
        score = -findMoveNegaMaxAlphaBeta(gs, nextMoves, depth - 1, -beta, -alpha, -turnMultiplier)
        
        if score > maxScore:
            maxScore = score
            
            # The Trick: We only want to update the 'nextMove' if we are at the top level 
            # of the recursion tree (when current depth matches the search depth).
            if depth == current_search_depth: 
                nextMove = move
                
        gs.undoMove()
        
        # Alpha-Beta Pruning logic
        if maxScore > alpha:
            alpha = maxScore
        if alpha >= beta:
            break
        
    # Store result in Transposition Table
    entryFlag = 'exact'
    if maxScore <= originalAlpha:
        entryFlag = 'upper'
    elif maxScore >= beta:
        entryFlag = 'lower'
        
    transpositionTable[boardHash] = {
        'score': maxScore,
        'depth': depth,
        'flag': entryFlag
    }
            
    return maxScore

"""
Orders the moves list based on a heuristic score.
Logic used: MVV-LVA (Most Valuable Victim - Least Valuable Aggressor).
Meaning: Capturing a Queen with a Pawn is better than capturing a Pawn with a Queen.
"""
def orderMoves(moves):
    def moveScore(move):
        score = 0
        if move.isCapture:
            # Get the value of the piece being captured (The Victim)
            victimValue = pieceScore.get(move.pieceCaptured[1], 0)
            
            # Get the value of the piece moving (The Aggressor)
            attackerValue = pieceScore.get(move.pieceMoved[1], 0)
            
            # Heuristic Formula: 10 * Victim - Aggressor
            score = 10 * victimValue - attackerValue
            
        return score

    # Sort the moves in descending order (highest score first)
    moves.sort(key=moveScore, reverse=True)
    return moves