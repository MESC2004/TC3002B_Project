from enum import Enum

# ---------------------------------------------------------------------------
# TokenType – Individual tokens for the lexer
# ---------------------------------------------------------------------------
class TokenType(Enum):
    # End of file ($) / error
    ENDFILE = 'ENDFILE' # Technically state 28 in the table
    ERROR   = 'ERROR' # Technically state 29 in the table

    # Nums and IDs (letter array)
    NUM = 'NUM'   # integer literal  (state 10)
    ID  = 'ID'    # identifier        (state 11)

    # Operators
    TKN_PLUS  = '+'   # state 12
    TKN_MINUS = '-'   # state 13
    TKN_MULT  = '*'   # state 14
    TKN_DIV   = '/'   # state 17

    # Relational operators
    TKN_LEQ = '<='  # state 15
    TKN_LT  = '<'   # state 16
    TKN_GEQ = '>='  # state 19
    TKN_GT  = '>'   # state 20
    TKN_DEQ = '=='  # state 21
    TKN_EQ  = '='   # state 22
    TKN_NEQ = '!='  # state 23

    # Punctuation
    TKN_SMC   = ';'  # semicolon   state 24
    TKN_CMA   = ','  # comma       state 25
    TKN_OPEN  = '('  # open  bracket group: ( [ {   state 26
    TKN_CLOSE = ')'  # close bracket group: ) ] }   state 27
    TKN_COMMENT = '/* ... */' # block comment (summarized) state 18

    # Reserved words of C-
    INT    = 'int'
    VOID   = 'void'
    IF     = 'if'
    ELSE   = 'else'
    WHILE  = 'while'
    RETURN = 'return'


# ---------------------------------------------------------------------------
# Reserved-word lookup table (dict for speed)  (identifier → TokenType)
# ---------------------------------------------------------------------------
RESERVED_WORDS = {
    'int':    TokenType.INT,
    'void':   TokenType.VOID,
    'if':     TokenType.IF,
    'else':   TokenType.ELSE,
    'while':  TokenType.WHILE,
    'return': TokenType.RETURN,
}


# ---------------------------------------------------------------------------
# Final states → TokenType mapping
# State 29 is the generic error / unget state, also handled in code.
# ---------------------------------------------------------------------------
ACCEPTING_STATE_TOKEN = {
    10: TokenType.NUM,
    11: TokenType.ID,
    12: TokenType.TKN_PLUS,
    13: TokenType.TKN_MINUS,
    14: TokenType.TKN_MULT,
    15: TokenType.TKN_LEQ,
    16: TokenType.TKN_LT,
    17: TokenType.TKN_DIV,
    18: TokenType.TKN_COMMENT,
    19: TokenType.TKN_GEQ,
    20: TokenType.TKN_GT,
    21: TokenType.TKN_DEQ,
    22: TokenType.TKN_EQ,
    23: TokenType.TKN_NEQ,
    24: TokenType.TKN_SMC,
    25: TokenType.TKN_CMA,
    26: TokenType.TKN_OPEN,
    27: TokenType.TKN_CLOSE,
    28: TokenType.ENDFILE,
    # 29 = error / needs unget → handled in lexer
}
