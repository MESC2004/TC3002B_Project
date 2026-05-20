import lexer as lex
from Parser import parser, globales
import analyze

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
    analyze.semantica(syntaxTree, imprime=True)

    if not analyze.Error:
        print("\nAnálisis semántico completado sin errores.")
    else:
        print("\nSe encontraron errores semánticos.")

if __name__ == '__main__':
    import sys
    file_path = sys.argv[1] if len(sys.argv) > 1 else 'sample.c-'
    run(file_path)