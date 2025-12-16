# chess_gui_minimax.py
# Full GUI Chess (Pygame) vs Minimax AI
# - Complete legal move generation (pieces, castling, en-passant, promotion)
# - GUI using pygame with Unicode piece glyphs (no external images required)
# - Minimax AI with alpha-beta pruning and simple evaluation
# Run: python chess_gui_minimax.py

import pygame
import sys
import time
import math
import copy

# --------------------------- SETTINGS --------------------------------
WINDOW_SIZE = 720
SQUARE = WINDOW_SIZE // 8
FPS = 60
AI_DEPTH = 3  # increase to make AI stronger (slower)
HUMAN_SIDE = 'w'  # set 'w' or 'b' for human color

# Colors
LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
HIGHLIGHT = (246, 246, 105)
SELECT = (100, 200, 150)

# Unicode pieces
UNICODE = {
    'K':'♔', 'Q':'♕', 'R':'♖', 'B':'♗', 'N':'♘', 'P':'♙',
    'k':'♚', 'q':'♛', 'r':'♜', 'b':'♝', 'n':'♞', 'p':'♟'
}

# Piece values for evaluation (centipawns)
PIECE_VALUES = {
    'P':100, 'N':320, 'B':330, 'R':500, 'Q':900, 'K':20000,
    'p':-100,'n':-320,'b':-330,'r':-500,'q':-900,'k':-20000
}

DIRS_KNIGHT = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
DIRS_BISHOP = [(-1,-1),(-1,1),(1,-1),(1,1)]
DIRS_ROOK = [(-1,0),(1,0),(0,-1),(0,1)]

# --------------------------- FEN helpers -------------------------------
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
FILES = 'abcdefgh'

def fen_to_board(fen):
    parts = fen.split()
    rows = parts[0].split('/')
    board = []
    for r in rows:
        row = []
        for ch in r:
            if ch.isdigit(): row += ['.']*int(ch)
            else: row.append(ch)
        board.append(row)
    side = parts[1]
    castling = parts[2]
    ep = parts[3] if parts[3] != '-' else None
    half = int(parts[4])
    full = int(parts[5])
    return board, side, castling, ep, half, full

# --------------------------- GAME STATE --------------------------------
class GameState:
    def __init__(self, fen=START_FEN):
        self.board, self.side, self.castling, self.ep_square, self.halfmove, self.fullmove = fen_to_board(fen)
        self.history = []
        self.update_kings()

    def update_kings(self):
        self.white_king = None
        self.black_king = None
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == 'K': self.white_king = (r,c)
                if self.board[r][c] == 'k': self.black_king = (r,c)

    def clone(self):
        return copy.deepcopy(self)

    def in_bounds(self, r,c):
        return 0 <= r < 8 and 0 <= c < 8

    def is_white(self, ch):
        return ch.isupper()

    def is_black(self, ch):
        return ch.islower()

    def make_move(self, move):
        # move = dict {from:(r,c), to:(r,c), promotion:char|None, special: 'ep'/'castle'|'normal'}
        snap = (copy.deepcopy(self.board), self.side, self.castling, self.ep_square, self.halfmove, self.fullmove)
        self.history.append(snap)
        fr,fc = move['from']
        tr,tc = move['to']
        piece = self.board[fr][fc]
        captured = self.board[tr][tc]
        # handle en-passant capture
        if move.get('special') == 'ep':
            if piece == 'P':
                self.board[tr+1][tc] = '.'
            else:
                self.board[tr-1][tc] = '.'
        # move
        self.board[fr][fc] = '.'
        # handle castling rook move
        if move.get('special') == 'castle':
            if tc == 6: # king side
                self.board[tr][5] = self.board[tr][7]
                self.board[tr][7] = '.'
            else: # queen side
                self.board[tr][3] = self.board[tr][0]
                self.board[tr][0] = '.'
        # promotion
        if move.get('promotion'):
            self.board[tr][tc] = move['promotion']
        else:
            self.board[tr][tc] = piece
        # update castling rights
        if piece == 'K':
            self.castling = self.castling.replace('K','').replace('Q','')
        if piece == 'k':
            self.castling = self.castling.replace('k','').replace('q','')
        # rook moves/captures
        if (fr,fc) == (7,0) or (tr,tc) == (7,0):
            self.castling = self.castling.replace('Q','')
        if (fr,fc) == (7,7) or (tr,tc) == (7,7):
            self.castling = self.castling.replace('K','')
        if (fr,fc) == (0,0) or (tr,tc) == (0,0):
            self.castling = self.castling.replace('q','')
        if (fr,fc) == (0,7) or (tr,tc) == (0,7):
            self.castling = self.castling.replace('k','')
        if self.castling == '': self.castling = '-'
        # en-passant target
        self.ep_square = None
        if piece.upper() == 'P' and abs(tr-fr) == 2:
            er = (fr+tr)//2
            ec = fc
            self.ep_square = coords_to_algebraic(er,ec)
        # halfmove/fullmove
        if piece.upper() == 'P' or captured != '.':
            self.halfmove = 0
        else:
            self.halfmove += 1
        if self.side == 'b':
            self.fullmove += 1
        # switch side
        self.side = 'b' if self.side == 'w' else 'w'
        self.update_kings()

    def undo_move(self):
        if not self.history: return
        b, side, castling, ep, half, full = self.history.pop()
        self.board = b
        self.side = side
        self.castling = castling
        self.ep_square = ep
        self.halfmove = half
        self.fullmove = full
        self.update_kings()

    def generate_legal_moves(self):
        moves = self.generate_pseudo_legal_moves()
        legal = []
        for m in moves:
            self.make_move(m)
            # check king safety for side that moved (opposite of current side)
            if not self.is_in_check('b' if self.side=='w' else 'w'):
                legal.append(m)
            self.undo_move()
        return legal

    def is_in_check(self, side):
        # check whether side ('w' or 'b') king is attacked
        king_pos = self.white_king if side=='w' else self.black_king
        if not king_pos: return True
        kr,kc = king_pos
        # knight attacks
        for dr,dc in DIRS_KNIGHT:
            r,c = kr+dr, kc+dc
            if self.in_bounds(r,c):
                p = self.board[r][c]
                if p != '.':
                    if side=='w' and p=='n': return True
                    if side=='b' and p=='N': return True
        # pawn attacks
        if side=='w':
            for dr,dc in [(-1,-1),(-1,1)]:
                r,c = kr+dr, kc+dc
                if self.in_bounds(r,c) and self.board[r][c] == 'p': return True
        else:
            for dr,dc in [(1,-1),(1,1)]:
                r,c = kr+dr, kc+dc
                if self.in_bounds(r,c) and self.board[r][c] == 'P': return True
        # sliding pieces: bishops/queens
        for dr,dc in DIRS_BISHOP:
            r,c = kr+dr, kc+dc
            while self.in_bounds(r,c):
                p = self.board[r][c]
                if p != '.':
                    if side=='w' and p in ('b','q'): return True
                    if side=='b' and p in ('B','Q'): return True
                    break
                r+=dr; c+=dc
        # rooks/queens
        for dr,dc in DIRS_ROOK:
            r,c = kr+dr, kc+dc
            while self.in_bounds(r,c):
                p = self.board[r][c]
                if p != '.':
                    if side=='w' and p in ('r','q'): return True
                    if side=='b' and p in ('R','Q'): return True
                    break
                r+=dr; c+=dc
        # king adjacency
        for dr in (-1,0,1):
            for dc in (-1,0,1):
                if dr==0 and dc==0: continue
                r,c = kr+dr, kc+dc
                if self.in_bounds(r,c):
                    p = self.board[r][c]
                    if p != '.':
                        if side=='w' and p=='k': return True
                        if side=='b' and p=='K': return True
        return False

    def generate_pseudo_legal_moves(self):
        moves = []
        white_to_move = (self.side == 'w')
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p == '.': continue
                if white_to_move and p.isupper(): moves += self._piece_moves(r,c,p)
                if (not white_to_move) and p.islower(): moves += self._piece_moves(r,c,p)
        return moves

    def _piece_moves(self, r, c, p):
        moves = []
        up = p.isupper()
        dir_forward = -1 if up else 1
        def push(fr,fc,tr,tc,special=None,promotion=None):
            m = {'from':(fr,fc),'to':(tr,tc)}
            if special: m['special']=special
            if promotion: m['promotion']=promotion
            moves.append(m)
        # Pawn
        if p.upper() == 'P':
            nr = r + dir_forward
            # single step
            if self.in_bounds(nr,c) and self.board[nr][c]=='.':
                if (up and nr==0) or (not up and nr==7):
                    for promo in (['Q','R','B','N'] if up else ['q','r','b','n']):
                        push(r,c,nr,c,promotion=promo)
                else:
                    push(r,c,nr,c)
                # double
                start_row = 6 if up else 1
                nr2 = r + 2*dir_forward
                if r == start_row and self.in_bounds(nr2,c) and self.board[nr2][c]=='.':
                    push(r,c,nr2,c)
            # captures
            for dc in (-1,1):
                nc = c+dc; nr = r + dir_forward
                if self.in_bounds(nr,nc):
                    target = self.board[nr][nc]
                    if target != '.':
                        if up and target.islower() or (not up and target.isupper()):
                            if (up and nr==0) or (not up and nr==7):
                                for promo in (['Q','R','B','N'] if up else ['q','r','b','n']):
                                    push(r,c,nr,nc,promotion=promo)
                            else:
                                push(r,c,nr,nc)
            # en-passant
            if self.ep_square:
                er,ec = algebraic_to_coords(self.ep_square)
                if er == r + dir_forward and abs(ec - c) == 1:
                    adj = self.board[r][ec]
                    if adj != '.' and ((up and adj=='p') or (not up and adj=='P')):
                        push(r,c,er,ec,special='ep')
        # Knight
        elif p.upper() == 'N':
            for dr,dc in DIRS_KNIGHT:
                nr, nc = r+dr, c+dc
                if self.in_bounds(nr,nc):
                    t = self.board[nr][nc]
                    if t=='.' or (t.islower() if p.isupper() else t.isupper()):
                        push(r,c,nr,nc)
        # Bishop
        elif p.upper() == 'B':
            for dr,dc in DIRS_BISHOP:
                nr, nc = r+dr, c+dc
                while self.in_bounds(nr,nc):
                    t = self.board[nr][nc]
                    if t=='.': push(r,c,nr,nc)
                    else:
                        if (t.islower() if p.isupper() else t.isupper()): push(r,c,nr,nc)
                        break
                    nr+=dr; nc+=dc
        # Rook
        elif p.upper() == 'R':
            for dr,dc in DIRS_ROOK:
                nr, nc = r+dr, c+dc
                while self.in_bounds(nr,nc):
                    t = self.board[nr][nc]
                    if t=='.': push(r,c,nr,nc)
                    else:
                        if (t.islower() if p.isupper() else t.isupper()): push(r,c,nr,nc)
                        break
                    nr+=dr; nc+=dc
        # Queen
        elif p.upper() == 'Q':
            for dr,dc in DIRS_BISHOP+DIRS_ROOK:
                nr, nc = r+dr, c+dc
                while self.in_bounds(nr,nc):
                    t = self.board[nr][nc]
                    if t=='.': push(r,c,nr,nc)
                    else:
                        if (t.islower() if p.isupper() else t.isupper()): push(r,c,nr,nc)
                        break
                    nr+=dr; nc+=dc
        # King
        elif p.upper() == 'K':
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    if dr==0 and dc==0: continue
                    nr, nc = r+dr, c+dc
                    if self.in_bounds(nr,nc):
                        t = self.board[nr][nc]
                        if t=='.' or (t.islower() if p.isupper() else t.isupper()):
                            push(r,c,nr,nc)
            # castling
            if p == 'K' or p == 'k':
                if self.castling and self.castling != '-':
                    if p == 'K':
                        # white king-side
                        if 'K' in self.castling and self.board[7][5]=='.' and self.board[7][6]=='.':
                            safe = True
                            for sq in [(7,4),(7,5),(7,6)]:
                                saved = copy.deepcopy(self.board)
                                self.board[7][4] = '.'
                                self.board[sq[0]][sq[1]] = 'K'
                                self.update_kings()
                                if self.is_in_check('w'): safe=False
                                self.board = saved; self.update_kings()
                                if not safe: break
                            if safe: push(r,c,7,6,special='castle')
                        # white queen-side
                        if 'Q' in self.castling and self.board[7][3]=='.' and self.board[7][2]=='.' and self.board[7][1]=='.':
                            safe = True
                            for sq in [(7,4),(7,3),(7,2)]:
                                saved = copy.deepcopy(self.board)
                                self.board[7][4] = '.'
                                self.board[sq[0]][sq[1]] = 'K'
                                self.update_kings()
                                if self.is_in_check('w'): safe=False
                                self.board = saved; self.update_kings()
                                if not safe: break
                            if safe: push(r,c,7,2,special='castle')
                    else:
                        # black
                        if 'k' in self.castling and self.board[0][5]=='.' and self.board[0][6]=='.':
                            safe = True
                            for sq in [(0,4),(0,5),(0,6)]:
                                saved = copy.deepcopy(self.board)
                                self.board[0][4] = '.'
                                self.board[sq[0]][sq[1]] = 'k'
                                self.update_kings()
                                if self.is_in_check('b'): safe=False
                                self.board = saved; self.update_kings()
                                if not safe: break
                            if safe: push(r,c,0,6,special='castle')
                        if 'q' in self.castling and self.board[0][3]=='.' and self.board[0][2]=='.' and self.board[0][1]=='.':
                            safe = True
                            for sq in [(0,4),(0,3),(0,2)]:
                                saved = copy.deepcopy(self.board)
                                self.board[0][4] = '.'
                                self.board[sq[0]][sq[1]] = 'k'
                                self.update_kings()
                                if self.is_in_check('b'): safe=False
                                self.board = saved; self.update_kings()
                                if not safe: break
                            if safe: push(r,c,0,2,special='castle')
        return moves

    def game_status(self):
        legal = self.generate_legal_moves()
        if legal: return 'ongoing'
        else:
            if self.is_in_check(self.side): return 'checkmate'
            else: return 'stalemate'

    def evaluate(self):
        # material + simple mobility (white perspective)
        score = 0
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p != '.': score += PIECE_VALUES.get(p,0)
        # mobility
        cur = self.side
        self.side = 'w'; wm = len(self.generate_pseudo_legal_moves())
        self.side = 'b'; bm = len(self.generate_pseudo_legal_moves())
        self.side = cur
        score += (wm - bm) * 1
        return score

# --------------------------- UTILS ------------------------------------

def algebraic_to_coords(s):
    file = s[0]; rank = int(s[1])
    col = FILES.index(file); row = 8 - rank
    return row, col

def coords_to_algebraic(r,c):
    return f"{FILES[c]}{8-r}"

# --------------------------- AI (minimax w/ alpha-beta) ----------------

def score_move_order(game, move):
    tr,tc = move['to']
    piece = game.board[move['from'][0]][move['from'][1]]
    target = game.board[tr][tc]
    if target != '.':
        return 1000 + abs(PIECE_VALUES.get(target,0))
    if move.get('promotion'): return 800
    return 0


def minimax(game, depth, alpha, beta, maximizing):
    status = game.game_status()
    if depth == 0 or status != 'ongoing':
        return game.evaluate()
    moves = game.generate_legal_moves()
    moves.sort(key=lambda m: score_move_order(game,m), reverse=True)
    if maximizing:
        maxEval = -math.inf
        for m in moves:
            game.make_move(m)
            val = minimax(game, depth-1, alpha, beta, False)
            game.undo_move()
            maxEval = max(maxEval, val)
            alpha = max(alpha, val)
            if beta <= alpha: break
        return maxEval
    else:
        minEval = math.inf
        for m in moves:
            game.make_move(m)
            val = minimax(game, depth-1, alpha, beta, True)
            game.undo_move()
            minEval = min(minEval, val)
            beta = min(beta, val)
            if beta <= alpha: break
        return minEval


def find_best_move(game, depth):
    best = None
    maximizing = (game.side == 'w')
    best_val = -math.inf if maximizing else math.inf
    moves = game.generate_legal_moves()
    if not moves: return None
    moves.sort(key=lambda m: score_move_order(game,m), reverse=True)
    for m in moves:
        game.make_move(m)
        val = minimax(game, depth-1, -math.inf, math.inf, not maximizing)
        game.undo_move()
        if maximizing and val > best_val:
            best_val = val; best = m
        if not maximizing and val < best_val:
            best_val = val; best = m
    return best

# --------------------------- GUI & MAIN --------------------------------

def draw_board(screen, game, selected_sq, legal_moves):
    for r in range(8):
        for c in range(8):
            color = LIGHT if (r+c)%2==0 else DARK
            rect = pygame.Rect(c*SQUARE, r*SQUARE, SQUARE, SQUARE)
            pygame.draw.rect(screen, color, rect)
    # highlights
    if selected_sq:
        sr,sc = selected_sq
        pygame.draw.rect(screen, SELECT, (sc*SQUARE, sr*SQUARE, SQUARE, SQUARE), 5)
    for m in legal_moves:
        tr,tc = m['to']
        pygame.draw.circle(screen, HIGHLIGHT, (tc*SQUARE+SQUARE//2, tr*SQUARE+SQUARE//2), 10)
    # pieces
    font = pygame.font.SysFont('dejavusans', SQUARE - 8)
    for r in range(8):
        for c in range(8):
            p = game.board[r][c]
            if p != '.':
                glyph = UNICODE.get(p, '?')
                text = font.render(glyph, True, (0,0,0))
                text_rect = text.get_rect(center=(c*SQUARE + SQUARE//2, r*SQUARE + SQUARE//2))
                screen.blit(text, text_rect)


def coord_from_mouse(pos):
    x,y = pos
    return y // SQUARE, x // SQUARE


def pretty_move(m):
    return coords_to_algebraic(*m['from']) + coords_to_algebraic(*m['to']) + (m.get('promotion','') if m.get('promotion') else '')


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    pygame.display.set_caption('Chess vs AI')
    clock = pygame.time.Clock()

    game = GameState()
    selected = None
    legal_moves_for_selected = []
    status = 'ongoing'
    ai_thinking = False

    global HUMAN_SIDE
    HUMAN_SIDE = HUMAN_SIDE

    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN and not ai_thinking:
                pos = pygame.mouse.get_pos()
                r,c = coord_from_mouse(pos)
                if selected is None:
                    # pick piece
                    if 0<=r<8 and 0<=c<8 and game.board[r][c] != '.':
                        piece = game.board[r][c]
                        if (game.side == 'w' and piece.isupper()) or (game.side=='b' and piece.islower()):
                            selected = (r,c)
                            legal_moves_for_selected = [m for m in game.generate_legal_moves() if m['from']==selected]
                else:
                    # try move
                    mv = None
                    for m in legal_moves_for_selected:
                        if m['to'] == (r,c): mv = m; break
                    if mv:
                        # promotion prompt if needed
                        if mv.get('promotion'):
                            # simple auto-queen promotion; could add GUI choice
                            mv['promotion'] = 'Q' if game.side=='w' else 'q'
                        game.make_move(mv)
                        selected = None; legal_moves_for_selected = []
                        status = game.game_status()
                        # if game continues and AI is to move, set thinking
                        if status == 'ongoing' and game.side != HUMAN_SIDE:
                            ai_thinking = True
                    else:
                        # change selection
                        if 0<=r<8 and 0<=c<8 and game.board[r][c] != '.':
                            piece = game.board[r][c]
                            if (game.side == 'w' and piece.isupper()) or (game.side=='b' and piece.islower()):
                                selected = (r,c)
                                legal_moves_for_selected = [m for m in game.generate_legal_moves() if m['from']==selected]
                            else:
                                selected = None; legal_moves_for_selected = []
                        else:
                            selected = None; legal_moves_for_selected = []
        # AI move
        if ai_thinking:
            start = time.time()
            mv = find_best_move(game, AI_DEPTH)
            dur = time.time() - start
            if mv:
                # if promotion exists and not set, set to queen
                if mv.get('promotion') is None and ((mv['to'][0] == 0 and game.board[mv['from'][0]][mv['from'][1]] == 'P') or (mv['to'][0] == 7 and game.board[mv['from'][0]][mv['from'][1]] == 'p')):
                    mv['promotion'] = 'q' if game.side=='b' else 'Q'
                game.make_move(mv)
                print(f"AI played {pretty_move(mv)} in {dur:.2f}s")
            else:
                print('AI has no move')
            ai_thinking = False
            status = game.game_status()

        draw_board(screen, game, selected, legal_moves_for_selected)
        # short status display
        font2 = pygame.font.SysFont('dejavusans', 20)
        if status == 'ongoing':
            txt = f"Side: {'White' if game.side=='w' else 'Black'} - Your side: {'White' if HUMAN_SIDE=='w' else 'Black'}"
        else:
            txt = 'Game over: ' + status
        surf = font2.render(txt, True, (10,10,10))
        screen.blit(surf, (10, WINDOW_SIZE-30))

        pygame.display.flip()

if __name__ == '__main__':
    main()
