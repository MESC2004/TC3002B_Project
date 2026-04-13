"""
Miguel Soria A01028033
lexer.py  –  Table-driven lexical analyser for C-

Usage (from an external script):
    from globalTypes import *
    from lexer import *

    globales(programa, posicion, progLong)
    token, tokenString = getToken()          # imprime=True by default
    while token != TokenType.ENDFILE:
        token, tokenString = getToken()
"""

from globalTypes import *

# ---------------------------------------------------------------------------
# Module-level globals (set via globales() before the first getToken() call)
# ---------------------------------------------------------------------------
programa    = ''   # complete source string (source code)
posicion    = 0    # index of the *next* character to consume
progLong    = 0    # length of the source WITHOUT the '$' sentinel
lineno      = 1    # current line number (1-based)


def globales(prog: str, pos: int, long: int) -> None:
    """Initialise shared globals from the driver script."""
    global programa, posicion, progLong, lineno
    programa = prog
    posicion = pos
    progLong = long
    lineno   = 1


# ---------------------------------------------------------------------------
# Column-index helper
# ---------------------------------------------------------------------------
# Columns of the transition table (0-based), matching the CSV order:
#   d  l  SPACE  +  -  /  *  <  >  =  !  (,[,{  ),],}  ,  ;  $  else
#   0  1    2    3  4  5  6  7  8  9  10   11    12    13  14  15   16

SPACE = ' \t\n'
def _col(c: str) -> int:
    """Return the column index for character *c*."""
    if c.isdigit():          return 0   # d
    if c.isalpha():          return 1   # l
    if c in SPACE:           return 2   # SPACE / whitespace
    if c == '+':             return 3
    if c == '-':             return 4
    if c == '/':             return 5
    if c == '*':             return 6
    if c == '<':             return 7
    if c == '>':             return 8
    if c == '=':             return 9
    if c == '!':             return 10
    if c in ('(', '[', '{'): return 11   # open brackets
    if c in (')', ']', '}'): return 12   # close brackets
    if c == ',':             return 13
    if c == ';':             return 14
    if c == '$':             return 15   # EOF sentinel
    return 16                            # anything else → error


# ---------------------------------------------------------------------------
# Transition table
# OPN = ( [ {
# CLOSE = ) ] }
# ---------------------------------------------------------------------------
#         d    l  SPC   +    -    /    *    <    >    =    !  OPN  CLO   ,    ;    $  else
TABLE = [
    #  0 – START
    [ 1,  2,   0,  12,  13,   4,  14,   3,   7,   8,   9,  26,  27,  25,  24,  28,  29],
    #  1 – in NUM
    [ 1,  29,  10,  10,  10,  10,  10,  10,  10,  10,  10,  10,  10,  10,  10,  10,  29],
    #  2 – in ID
    [29,   2,  11,  11,  11,  11,  11,  11,  11,  11,  11,  11,  11,  11,  11,  11,  29],
    #  3 – seen '<'
    [16,  16,  16,  16,  16,  16,  16,  16,  16,  15,  16,  16,  16,  16,  16,  16,  29],
    #  4 – seen '/'
    [17,  17,  17,  17,  17,  17,   5,  17,  17,  17,  17,  17,  17,  17,  17,  17,  29],
    #  5 – inside block comment  /* … (waiting for *)
    [ 5,   5,   5,   5,   5,   5,   6,   5,   5,   5,   5,   5,   5,   5,   5,   5,  5],
    #  6 – seen '*' inside comment (waiting for /)
    [ 5,   5,   5,   5,   5,  18,   5,   5,   5,   5,   5,   5,   5,   5,   5,   5,  5],
    #  7 – seen '>'
    [20,  20,  20,  20,  20,  20,  20,  20,  20,  19,  20,  20,  20,  20,  20,  20,  29],
    #  8 – seen '='
    [22,  22,  22,  22,  22,  22,  22,  22,  22,  21,  22,  22,  22,  22,  22,  22,  29],
    #  9 – seen '!'
    [29,  29,  29,  29,  29,  29,  29,  29,  29,  23,  29,  29,  29,  29,  29,  29,  29],
]

# States that are accepting AND require the last character to be "put back"
# AKA, the character that caused the state to go back to 0 is not part of the token (+1 or not in the if)
# OPTIMIZATION FROM FEEDBACK FROM CLAUDE, makes code more readable and clean
UNGET_STATES = {10, 11, 15, 16, 17, 19, 20, 22, 29}

# State 29 → error (unget is already handled; we still emit ERROR)
ERROR_STATE = 29


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def getToken(imprime: bool = True):
    """
    Consume characters from *programa* starting at *posicion* and return the
    next (token, lexema) pair.  Updates *posicion* and *lineno* as globals.

    Returns
    -------
    token       : TokenType
    tokenString : str   – the lexeme (empty string for single-char tokens that
                          were already captured, or for errors)
    """
    global posicion, lineno

    state      = 0
    lexema     = ''  # accumulate the lexeme character by character
    token      = None

    prev_state = 0   # track where we came from
    while state not in ACCEPTING_STATE_TOKEN:
        c   = programa[posicion]
        col = _col(c) # obtained from the abstracted helper function
        next_state = TABLE[state][col]

        in_comment = state in (5, 6)   # inside /* … */

        if next_state in UNGET_STATES:
            # CLAUDE FEEDBACK OPTIMIZATION
            # The current char caused us to leave the token – put it back.
            # Do NOT advance posicion; do NOT accumulate c. (no +1)
            prev_state = state
            state = next_state
            break

        # Advance and optionally accumulate
        posicion += 1

        if not (state == 0 and c in (' ', '\t', '\n')) and not in_comment:
            # skip whitespace, accumulate otherwise
            lexema += c
        if c == '\n':
            lineno += 1

        prev_state = state
        state = next_state

    if state == ERROR_STATE:
        bad_char = programa[posicion]

        if prev_state == 1 and bad_char.isalpha():
            line_start = programa.rfind('\n', 0, posicion) + 1
            line_end = programa.rfind('\n', posicion)
            if line_end == -1:
                line_end = progLong
            source_line = programa[line_start:line_end]
            col_in_line = posicion - line_start

            print(f"\nLinea {lineno}: Error al formar un numero: '{lexema}{bad_char}'")
            print(source_line) # Error Line
            print(' ' * col_in_line + '^') # Error marker

            posicion   += 1
            token       = TokenType.ERROR
            tokenString = lexema + bad_char

            if imprime:
                print(f"{lineno}\t{token}\t= '{tokenString}'")
            return token, tokenString

        elif prev_state == 2 and bad_char.isdigit():
            # digit immediately after an identifier → error
            line_start  = programa.rfind('\n', 0, posicion) + 1
            line_end    = programa.find('\n', posicion)
            if line_end == -1:
                line_end = progLong
            source_line = programa[line_start:line_end]
            col_in_line = posicion - line_start

            print(f"\nLínea {lineno}: Error al formar un ID: '{lexema}{bad_char}'")
            print(source_line)
            print(' ' * col_in_line + '^')

            posicion   += 1
            token       = TokenType.ERROR
            tokenString = lexema + bad_char
            if imprime:
                print(f"{lineno}\t{token}\t= '{tokenString}'")
            return token, tokenString

        elif prev_state == 2 and bad_char.isdigit():
            # exclamation mark alone → error
            line_start  = programa.rfind('\n', 0, posicion) + 1
            line_end    = programa.find('\n', posicion)
            if line_end == -1:
                line_end = progLong
            source_line = programa[line_start:line_end]
            col_in_line = posicion - line_start

            print(f"\nLínea {lineno}: Error lexico, exclamacion debe llevar un signo igual despues: '{lexema}{bad_char}'")
            print(source_line)
            print(' ' * col_in_line + '^')

            posicion   += 1
            token       = TokenType.ERROR
            tokenString = lexema + bad_char
            if imprime:
                print(f"{lineno}\t{token}\t= '{tokenString}'")
            return token, tokenString


        elif prev_state in (1,2):
            # We were mid-token (NUM or ID) and hit an invalid continuation.
            # The lexema is already built; resolve the token type normally.
            token = ACCEPTING_STATE_TOKEN.get(
                {1: 10, 2: 11}.get(prev_state, prev_state),
                TokenType.ERROR
            )
            if token == TokenType.ID:
                token = RESERVED_WORDS.get(lexema, TokenType.ID)
            tokenString = lexema
            if imprime:
                print(f"{lineno}\t{token}\t= '{tokenString}'")
            return token, tokenString

        else:
        # True error: unexpected character at START state
            bad_char = programa[posicion]
            line_start = programa.rfind('\n', 0, posicion) + 1
            line_end   = programa.find('\n', posicion)
            if line_end == -1:
                line_end = progLong
            source_line = programa[line_start:line_end]
            col_in_line = posicion - line_start

            print(f"\nLínea {lineno}: Error léxico – carácter inesperado: '{bad_char}'")
            print(source_line)
            print(' ' * col_in_line + '^')

            # Recovery: skip the bad character and continue scanning
            posicion += 1
            if bad_char == '\n':
                lineno += 1
            token       = TokenType.ERROR
            tokenString = bad_char
            if imprime:
                print(f"{lineno}\t{token}\t= '{tokenString}'")
            return token, tokenString

    # Normal accepting state
    token = ACCEPTING_STATE_TOKEN[state]

    # lexema always reflects the actual source text.
    if token not in (TokenType.NUM, TokenType.ID):
        tokenString = token.value          # e.g. '+', '<=', …
    else:
        tokenString = lexema

        # Check reserved words for IDs
        if token == TokenType.ID:
            token = RESERVED_WORDS.get(tokenString, TokenType.ID)

    if imprime:
        print(f"{lineno}\t{token}\t= '{tokenString}'")

    return token, tokenString
