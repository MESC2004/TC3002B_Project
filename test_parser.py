import sys
import os

# Añadir la raíz y los subdirectorios al path para máxima compatibilidad con las importaciones actuales
root_dir = os.getcwd()
sys.path.insert(0, root_dir)
sys.path.insert(1, os.path.join(root_dir, 'lexer'))
sys.path.insert(2, os.path.join(root_dir, 'parser'))

# Ahora podemos importar directamente o vía paquete
try:
    from globalTypes import *
    from Parser import parser, globales
except ImportError:
    from lexer.globalTypes import *
    from parser.Parser import parser, globales

def run_test(file_path):
    print(f"--- Analizando archivo: {file_path} ---")
    try:
        with open(file_path, 'r') as f:
            programa = f.read()
            
        progLong = len(programa)
        programa_con_eof = programa + '$'
        posicion = 0
        
        # Inicializar globales
        globales(programa_con_eof, posicion, progLong)
        
        # Ejecutar el parser
        resultado = parser(imprime=True)
        
        if isinstance(resultado, str):
            print(f"\nResultado del Parser: {resultado}")
        else:
            print("\nAnálisis completado exitosamente.")
            
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {file_path}")
    except Exception as e:
        print(f"\nError inesperado durante las pruebas: {e}")
        # traceback para debug
        import traceback
        # traceback.print_exc()

if __name__ == "__main__":
    sample_file = "lexer/sample.c-"
    run_test(sample_file)
