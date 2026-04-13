"""
main.py  –  Driver script for the C- lexer.

Usage:
    python main.py

The source file is expected to be named 'sample.c-' and located in the same
directory.  Change *fileName* below to use a different file.
"""

from globalTypes import *
from lexer import *

fileName = "sample"          # change to your test-file name (without extension)
extension = ".c-"            # C- source files use the .c- extension

with open(fileName + extension, 'r') as f:
    programa = f.read()       # read the entire source file into a string

progLong  = len(programa)    # original length (without the EOF sentinel)
programa  = programa + '$'   # append '$' to mark End-Of-File
posicion  = 0                # start scanning from position 0

# Pass initial globals to the lexer module
globales(programa, posicion, progLong)

# Repeatedly call getToken() until ENDFILE is reached
token, tokenString = getToken()
while token != TokenType.ENDFILE:
    token, tokenString = getToken()
