from globalTypes import *
from parser import parser, globales
from semantica import semantica
from cgen import codeGen

f = open('sample.c-', 'r')
programa = f.read()              # lee todo el archivo a compilar
f.close()
progLong = len(programa)         # longitud original del programa
programa = programa + '$'        # agregar un caracter $ que represente EOF
posicion = 0                     # posición del caracter actual del string

# función para pasar los valores iniciales de las variables globales
globales(programa, posicion, progLong)
AST = parser(True)
semantica(AST, True)
codeGen(AST, "file.s")
