import sys
import os
from multiprocessing import Process, Queue
import pygame as p

# --- Import Project Files ---
import config
from Engine.gameState import GameState
from Engine.move import Move
from AI import moveFinder

# --- Path Setup ---
current_path = os.path.dirname(__file__)
image_path = os.path.join(current_path, "images")

# --- Global Variables ---
IMAGES = {}

def loadImages():
    pieces = ["wp", "wN", "wB", "wR", "wQ", "wK", "bp", "bN", "bB", "bR", "bQ", "bK"]
    for piece in pieces:
        img = os.path.join(image_path, piece + ".png")
        IMAGES[piece] = p.transform.scale(p.image.load(img), (config.SQ_SIZE, config.SQ_SIZE))

def main():
    p.init()
    p.display.set_caption("ChessEngine")
    screen = p.display.set_mode((config.BOARD_WIDTH, config.BOARD_HEIGHT))
    clock = p.time.Clock()
    screen.fill(p.Color("white"))
    
    # Initialize Fonts
    moveLogFont = p.font.SysFont("Arial", 20, False, False)
    menuFont = p.font.SysFont("Arial", 24, True, False)
    
    # Initialize Game State
    gs = GameState()
    validMoves = gs.getValidMoves()
    moveMade = False
    animate = False
    
    loadImages()
    
    running = True
    sqSelected = ()
    playerClicks = []
    gameOver = False

    # --- Menu State Management ---
    # States: 'MODE' -> 'SIDE' -> 'DIFFICULTY' -> 'GAME'
    menuState = 'MODE' 
    gameStarted = False 

    # Player Configuration (Defaults)
    playerOne = True   # White (True = Human, False = AI)
    playerTwo = False  # Black (True = Human, False = AI)
    
    # AI Variables
    AIThinking = False
    moveFinderProcess = None
    moveUndone = False
    current_difficulty = config.DIFFICULTY['MEDIUM']

    while running:
        
        # -----------------------------------------
        # MENU LOGIC (Multi-Stage)
        # -----------------------------------------
        if not gameStarted:
            screen.fill(p.Color("black")) # Clear screen for menu
            
            # Stage 1: Select Game Mode
            if menuState == 'MODE':
                btn1, btn2 = drawMenuButtons(screen, menuFont, "Select Game Mode", "PvP", "Player vs AI")
                for e in p.event.get():
                    if e.type == p.QUIT: running = False
                    elif e.type == p.MOUSEBUTTONDOWN:
                        location = p.mouse.get_pos()
                        if btn1.collidepoint(location): # PvP
                            playerOne = True
                            playerTwo = True
                            gameStarted = True # Skip other menus for PvP
                        elif btn2.collidepoint(location): # PvAI
                            menuState = 'SIDE' # Go to next menu
            
            # Stage 2: Select Side (Color) - Only for PvAI
            elif menuState == 'SIDE':
                btn1, btn2 = drawMenuButtons(screen, menuFont, "Choose Your Color", "Play as White", "Play as Black")
                for e in p.event.get():
                    if e.type == p.QUIT: running = False
                    elif e.type == p.MOUSEBUTTONDOWN:
                        location = p.mouse.get_pos()
                        if btn1.collidepoint(location): # White
                            playerOne = True  # Human plays White
                            playerTwo = False # AI plays Black
                            menuState = 'DIFFICULTY'
                        elif btn2.collidepoint(location): # Black
                            playerOne = False # AI plays White
                            playerTwo = True  # Human plays Black
                            menuState = 'DIFFICULTY'

            # Stage 3: Select Difficulty - Only for PvAI
            elif menuState == 'DIFFICULTY':
                easyBtn, mediumBtn, hardBtn = drawDifficultyMenu(screen, menuFont)
                for e in p.event.get():
                    if e.type == p.QUIT: running = False
                    elif e.type == p.MOUSEBUTTONDOWN:
                        location = p.mouse.get_pos()
                        if easyBtn.collidepoint(location):
                            current_difficulty = config.DIFFICULTY['EASY']
                            gameStarted = True
                        elif mediumBtn.collidepoint(location):
                            current_difficulty = config.DIFFICULTY['MEDIUM']
                            gameStarted = True
                        elif hardBtn.collidepoint(location):
                            current_difficulty = config.DIFFICULTY['HARD']
                            gameStarted = True
                            
            p.display.flip()
            continue # Skip the game loop

        # -----------------------------------------
        # GAME LOOP
        # -----------------------------------------
        # Check whose turn it is
        humanTurn = (gs.whiteToMove and playerOne) or (not gs.whiteToMove and playerTwo)
        
        for e in p.event.get():
            if e.type == p.QUIT:
                running = False
            
            # --- Mouse Handling ---
            elif e.type == p.MOUSEBUTTONDOWN:
                if not gameOver and humanTurn:
                    location = p.mouse.get_pos()
                    col = location[0] // config.SQ_SIZE
                    row = location[1] // config.SQ_SIZE
                    
                    if sqSelected == (row, col) or col >= 8: 
                        sqSelected = ()
                        playerClicks = []
                    else:
                        sqSelected = (row, col)
                        playerClicks.append(sqSelected)
                    
                    if len(playerClicks) == 2: 
                        move = Move(playerClicks[0], playerClicks[1], gs.board)
                        for i in range(len(validMoves)):
                            if move == validMoves[i]:
                                targetMove = validMoves[i]
                                if targetMove.isPawnPromotion:
                                    promotedType = userSelectPromotion(screen, gs, targetMove)
                                    targetMove.promotedPiece = promotedType
                                
                                gs.makeMove(targetMove)
                                moveMade = True
                                animate = True
                                sqSelected = ()
                                playerClicks = []
                        if not moveMade:
                            playerClicks = [sqSelected]

            # --- Key Handling ---
            elif e.type == p.KEYDOWN:
                if e.key == p.K_z: # Undo
                    gs.undoMove()
                    moveMade = True
                    animate = False
                    gameOver = False
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = True
                
                elif e.key == p.K_r: # Reset Logic
                    # Reset everything including menu
                    gs = GameState()
                    validMoves = gs.getValidMoves()
                    sqSelected = ()
                    playerClicks = []
                    moveMade = False
                    animate = False
                    gameOver = False
                    gameStarted = False # Go back to menu
                    menuState = 'MODE' # Reset menu state
                    if AIThinking:
                        moveFinderProcess.terminate()
                        AIThinking = False
                    moveUndone = False

        # --- AI Turn Logic ---
        if not gameOver and not humanTurn and not moveUndone:
            if not AIThinking:
                AIThinking = True
                print("AI is thinking...")
                returnQueue = Queue()
                moveFinderProcess = Process(
                    target=moveFinder.findBestMoveMinMax,
                    args=(gs, validMoves, returnQueue, current_difficulty)
                )
                moveFinderProcess.start()
                
                AIMove = returnQueue.get()
                
                if AIMove is None:
                    AIMove = moveFinder.findRandomMoves(validMoves)
                
                gs.makeMove(AIMove)
                moveMade = True
                animate = True
                AIThinking = False

        if moveMade:
            if animate:
                animateMove(gs.moveLog[-1], screen, gs.board, clock)
            validMoves = gs.getValidMoves()
            moveMade = False
            animate = False
            moveUndone = False

        drawGameState(screen, gs, validMoves, sqSelected, moveLogFont)

        if gs.checkmate or gs.stalemate:
            gameOver = True
            text = "Stalemate" if gs.stalemate else ("Black wins" if gs.whiteToMove else "White wins")
            drawEndGameText(screen, text)

        clock.tick(config.MAX_FPS)
        p.display.flip()

# ---------------------------------------------------
# Graphic & UI Functions
# ---------------------------------------------------

def drawGameState(screen, gs, validMoves, sqSelected, moveLogFont):
    drawBoard(screen)
    highlightSquares(screen, gs, validMoves, sqSelected)
    drawPieces(screen, gs.board)

def drawBoard(screen):
    colors = config.COLORS
    font = p.font.SysFont("Arial", 14, True, False)
    for r in range(config.DIMENSION):
        for c in range(config.DIMENSION):
            color = colors[(r + c) % 2]
            p.draw.rect(screen, color, p.Rect(c * config.SQ_SIZE, r * config.SQ_SIZE, config.SQ_SIZE, config.SQ_SIZE))
            
            if c == 0:
                colorText = colors[0] if color == colors[1] else colors[1]
                label = font.render(str(8 - r), True, colorText)
                screen.blit(label, (c * config.SQ_SIZE + 2, r * config.SQ_SIZE + 2))
            
            if r == 7:
                colorText = colors[0] if color == colors[1] else colors[1]
                label = font.render(chr(ord('a') + c), True, colorText)
                screen.blit(label, (c * config.SQ_SIZE + config.SQ_SIZE - 12, r * config.SQ_SIZE + config.SQ_SIZE - 15))

def highlightSquares(screen, gs, validMoves, sqSelected):
    if gs.inCheck:
        s = p.Surface((config.SQ_SIZE, config.SQ_SIZE))
        s.set_alpha(150)
        s.fill(p.Color("red"))
        if gs.whiteToMove:
            r, c = gs.whiteKingLocation
        else:
            r, c = gs.blackKingLocation
        screen.blit(s, (c * config.SQ_SIZE, r * config.SQ_SIZE))

    if sqSelected != ():
        r, c = sqSelected
        if gs.board[r][c][0] == ("w" if gs.whiteToMove else "b"):
            s = p.Surface((config.SQ_SIZE, config.SQ_SIZE))
            s.set_alpha(100)
            s.fill(p.Color("blue"))
            screen.blit(s, (c * config.SQ_SIZE, r * config.SQ_SIZE))
            
            for move in validMoves:
                if move.startRow == r and move.startCol == c:
                    if move.isCapture:
                        s.fill(p.Color("red"))
                    else:
                        s.fill(p.Color("yellow"))
                    screen.blit(s, (move.endCol * config.SQ_SIZE, move.endRow * config.SQ_SIZE))

def drawPieces(screen, board):
    for r in range(config.DIMENSION):
        for c in range(config.DIMENSION):
            piece = board[r][c]
            if piece != "--":
                screen.blit(IMAGES[piece], p.Rect(c * config.SQ_SIZE, r * config.SQ_SIZE, config.SQ_SIZE, config.SQ_SIZE))

def drawEndGameText(screen, text):
    font = p.font.SysFont("Helvitca", 32, True, False)
    textObject = font.render(text, 0, p.Color("Gray"))
    textLocation = p.Rect(0, 0, config.BOARD_WIDTH, config.BOARD_HEIGHT).move(
        config.BOARD_WIDTH / 2 - textObject.get_width() / 2,
        config.BOARD_HEIGHT / 2 - textObject.get_height() / 2,
    )
    screen.blit(textObject, textLocation)
    textObject = font.render(text, 0, p.Color("Black"))
    screen.blit(textObject, textLocation.move(2, 2))

def animateMove(move, screen, board, clock):
    colors = [p.Color("white"), p.Color("light blue")]
    dR = move.endRow - move.startRow
    dC = move.endCol - move.startCol
    framesPerSquare = 10 
    frameCount = (abs(dR) + abs(dC)) * framesPerSquare
    
    for frame in range(frameCount + 1):
        r, c = (
            move.startRow + dR * frame / frameCount,
            move.startCol + dC * frame / frameCount,
        )
        drawBoard(screen)
        drawPieces(screen, board)
        color = colors[(move.endRow + move.endCol) % 2]
        endSquare = p.Rect(move.endCol * config.SQ_SIZE, move.endRow * config.SQ_SIZE, config.SQ_SIZE, config.SQ_SIZE)
        p.draw.rect(screen, color, endSquare)
        
        if move.pieceCaptured != "--":
            if move.isEnpassantMove:
                enpassantRow = (move.endRow + 1) if move.pieceCaptured[0] == "b" else (move.endRow - 1)
                endSquare = p.Rect(move.endCol * config.SQ_SIZE, enpassantRow * config.SQ_SIZE, config.SQ_SIZE, config.SQ_SIZE)
            screen.blit(IMAGES[move.pieceCaptured], endSquare)
        
        screen.blit(IMAGES[move.pieceMoved], p.Rect(c * config.SQ_SIZE, r * config.SQ_SIZE, config.SQ_SIZE, config.SQ_SIZE))
        p.display.flip()
        clock.tick(120)

def userSelectPromotion(screen, gs, move):
    color = move.pieceMoved[0]
    promotionPieces = ["Q", "R", "B", "N"]
    direction = 1 if move.endRow == 0 else -1
    while True:
        for i, pieceCode in enumerate(promotionPieces):
            rowPos = move.endRow + (i * direction)
            colPos = move.endCol
            p.draw.rect(screen, p.Color("white"), p.Rect(colPos * config.SQ_SIZE, rowPos * config.SQ_SIZE, config.SQ_SIZE, config.SQ_SIZE))
            pieceImage = IMAGES[color + pieceCode]
            screen.blit(pieceImage, p.Rect(colPos * config.SQ_SIZE, rowPos * config.SQ_SIZE, config.SQ_SIZE, config.SQ_SIZE))
        p.display.flip()
        for e in p.event.get():
            if e.type == p.MOUSEBUTTONDOWN:
                location = p.mouse.get_pos()
                clickRow = location[1] // config.SQ_SIZE
                clickCol = location[0] // config.SQ_SIZE
                if clickCol == move.endCol:
                    clickedIndex = (clickRow - move.endRow) * direction
                    if 0 <= clickedIndex < len(promotionPieces):
                        return promotionPieces[int(clickedIndex)]

# --- Helper Functions for Menu Drawing ---

def drawMenuButtons(screen, font, titleText, btn1Text, btn2Text):
    # Title
    titleFont = p.font.SysFont("Arial", 40, True, False)
    title = titleFont.render(titleText, True, p.Color("white"))
    titleRect = title.get_rect(center=(config.BOARD_WIDTH // 2, 100))
    screen.blit(title, titleRect)
    
    # Button Dimensions
    buttonWidth, buttonHeight = 220, 60
    centerX = config.BOARD_WIDTH // 2
    
    # Button 1
    rect1 = p.Rect(0, 0, buttonWidth, buttonHeight)
    rect1.center = (centerX, 250)
    p.draw.rect(screen, p.Color("light gray"), rect1)
    text1 = font.render(btn1Text, True, p.Color("black"))
    textRect1 = text1.get_rect(center=rect1.center)
    screen.blit(text1, textRect1)
    
    # Button 2
    rect2 = p.Rect(0, 0, buttonWidth, buttonHeight)
    rect2.center = (centerX, 350)
    p.draw.rect(screen, p.Color("light gray"), rect2)
    text2 = font.render(btn2Text, True, p.Color("black"))
    textRect2 = text2.get_rect(center=rect2.center)
    screen.blit(text2, textRect2)
    
    return rect1, rect2

def drawDifficultyMenu(screen, font):
    # Title
    titleFont = p.font.SysFont("Arial", 40, True, False)
    title = titleFont.render("Select Difficulty", True, p.Color("white"))
    titleRect = title.get_rect(center=(config.BOARD_WIDTH // 2, 100))
    screen.blit(title, titleRect)
    
    # Buttons
    buttonWidth, buttonHeight = 200, 50
    centerX = config.BOARD_WIDTH // 2
    
    easyRect = p.Rect(0, 0, buttonWidth, buttonHeight)
    easyRect.center = (centerX, 200)
    p.draw.rect(screen, p.Color("green"), easyRect)
    text = font.render("Easy", True, p.Color("black"))
    screen.blit(text, text.get_rect(center=easyRect.center))
    
    mediumRect = p.Rect(0, 0, buttonWidth, buttonHeight)
    mediumRect.center = (centerX, 300)
    p.draw.rect(screen, p.Color("yellow"), mediumRect)
    text = font.render("Medium", True, p.Color("black"))
    screen.blit(text, text.get_rect(center=mediumRect.center))
    
    hardRect = p.Rect(0, 0, buttonWidth, buttonHeight)
    hardRect.center = (centerX, 400)
    p.draw.rect(screen, p.Color("red"), hardRect)
    text = font.render("Hard", True, p.Color("black"))
    screen.blit(text, text.get_rect(center=hardRect.center))
    
    return easyRect, mediumRect, hardRect

if __name__ == "__main__":
    main()