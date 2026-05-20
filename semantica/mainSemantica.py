import sys, os

# Ajustar paths para importar lexer y parser
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
sys.path.insert(1, os.path.join(root, 'lexer'))
sys.path.insert(2, os.path.join(root, 'parser'))

import lexer.lexer as lex
from parser.Parser import parser, globales
import semantica.analyze as analyze

def run(file_path):
    with open(file_path, 'r') as f:
        programa = f.read()

    progLong = len(programa)
    globales(programa + '$', 0, progLong)

    print("Analizando:", file_path)
    syntaxTree = parser(imprime=False)

    if not syntaxTree:
        print("Error: el parser no produjo un árbol.")
        return

    print("\nConstruyendo tabla de símbolos...")
    analyze.buildSymtab(syntaxTree, imprime=True)

    print("\nVerificando tipos...")
    analyze.typeCheck(syntaxTree)

    if not analyze.Error:
        print("\nAnálisis semántico completado sin errores.")
    else:
        print("\nSe encontraron errores semánticos.")

if __name__ == '__main__':
    file_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'lexer', 'sample.c-')
    run(file_path)
