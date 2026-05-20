# analyze.py — Análisis semántico para C-
# Sigue el patrón de SemanticaTiny/analyze.py

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'parser'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lexer'))

from globalTypes import TokenType
from Parser import NodeKind, StmtKind, ExpKind, DeclKind
from symtab import scope_enter, scope_exit, st_insert, st_lookup, st_lookup_current, printSymTab

Error = False

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def semanticError(t, message):
    global Error
    lineno = t.lineno if t else '?'
    print(f"Error semántico en línea {lineno}: {message}")
    Error = True

def traverse(t, preProc, postProc):
    """Recorre el AST en preorden/postorden, igual que en SemanticaTiny."""
    if t is None:
        return
    preProc(t)
    for child in t.child:
        traverse(child, preProc, postProc)
    postProc(t)
    traverse(t.sibling, preProc, postProc)

def nullProc(t):
    pass

# ---------------------------------------------------------------------------
# Funciones built-in de C-
# ---------------------------------------------------------------------------
BUILTINS = {
    'input':  {'type': 'int',  'kind': 'fun', 'loc': None, 'lines': []},
    'output': {'type': 'void', 'kind': 'fun', 'loc': None, 'lines': []},
}

def _insert_builtins():
    for name, info in BUILTINS.items():
        st_insert(name, 0, info['type'], info['kind'], loc=None)

# ---------------------------------------------------------------------------
# Fase 1: Construcción de la tabla de símbolos
# ---------------------------------------------------------------------------

def insertNode(t):
    """Inserta declaraciones e identificadores en la tabla de símbolos."""
    if t.nodekind == NodeKind.DECL:
        if t.kind == DeclKind.FUN:
            if st_lookup_current(t.attr) is not None:
                semanticError(t, f"función '{t.attr}' ya declarada en este scope")
            else:
                st_insert(t.attr, t.lineno, t.type, 'fun')
            scope_enter()
        elif t.kind == DeclKind.VAR:
            name = t.attr if isinstance(t.attr, str) else t.attr[0]
            if st_lookup_current(name) is not None:
                semanticError(t, f"variable '{name}' ya declarada en este scope")
            else:
                st_insert(name, t.lineno, t.type, 'var')
        elif t.kind == DeclKind.PARAM:
            name = t.attr if isinstance(t.attr, str) else t.attr[0]
            if st_lookup_current(name) is not None:
                semanticError(t, f"parámetro '{name}' duplicado")
            else:
                st_insert(name, t.lineno, t.type, 'param')
    elif t.nodekind == NodeKind.STMT:
        if t.kind == StmtKind.COMPOUND:
            if not getattr(t, '_fun_scope', False):
                scope_enter()
    elif t.nodekind == NodeKind.EXP:
        if t.kind in (ExpKind.ID, ExpKind.VAR):
            name = t.attr if isinstance(t.attr, str) else t.attr[0]
            entry = st_lookup(name)
            if entry is None:
                semanticError(t, f"identificador '{name}' no declarado")
            else:
                st_insert(name, t.lineno, entry['type'], entry['kind'], entry['loc'])
        elif t.kind == ExpKind.CALL:
            entry = st_lookup(t.attr)
            if entry is None:
                semanticError(t, f"función '{t.attr}' no declarada")
            elif entry['kind'] != 'fun':
                semanticError(t, f"'{t.attr}' no es una función")
            else:
                st_insert(t.attr, t.lineno, entry['type'], entry['kind'], entry['loc'])

def exitNode(t):
    """Cierra scopes al salir de funciones y bloques compuestos."""
    if t.nodekind == NodeKind.DECL and t.kind == DeclKind.FUN:
        scope_exit()
    elif t.nodekind == NodeKind.STMT and t.kind == StmtKind.COMPOUND:
        if not getattr(t, '_fun_scope', False):
            scope_exit()

def _mark_fun_compound(t):
    """Marca el compound_stmt directo de una función para no duplicar scope."""
    if t is None:
        return
    if t.nodekind == NodeKind.DECL and t.kind == DeclKind.FUN:
        # t.child[0] = params, t.child[1] = compound_stmt
        if len(t.child) >= 2 and t.child[1] is not None:
            t.child[1]._fun_scope = True
    for child in t.child:
        _mark_fun_compound(child)
    _mark_fun_compound(t.sibling)

def buildSymtab(syntaxTree, imprime=True):
    _insert_builtins()
    _mark_fun_compound(syntaxTree)
    traverse(syntaxTree, insertNode, exitNode)
    if imprime:
        print()
        print("Tabla de Símbolos:")
        printSymTab()

# ---------------------------------------------------------------------------
# Fase 2: Verificación de tipos
# ---------------------------------------------------------------------------

def checkNode(t):
    """Verifica tipos en un nodo del AST (postorden)."""
    if t.nodekind == NodeKind.EXP:
        if t.kind == ExpKind.CONST:
            t.type = 'int'
        elif t.kind in (ExpKind.ID, ExpKind.VAR):
            name = t.attr if isinstance(t.attr, str) else t.attr[0]
            entry = st_lookup(name)
            t.type = entry['type'] if entry else 'int'
        elif t.kind == ExpKind.OP:
            left  = t.child[0].type if t.child else None
            right = t.child[1].type if len(t.child) > 1 else None
            if left != 'int' or right != 'int':
                semanticError(t, f"operación '{t.attr}' requiere operandos enteros")
            t.type = 'int'
        elif t.kind == ExpKind.ASSIGN:
            lhs = t.child[0].type if t.child else None
            rhs = t.child[1].type if len(t.child) > 1 else None
            if lhs != rhs:
                semanticError(t, f"tipos incompatibles en asignación: '{lhs}' = '{rhs}'")
            t.type = lhs
        elif t.kind == ExpKind.CALL:
            entry = st_lookup(t.attr)
            t.type = entry['type'] if entry else 'void'
    elif t.nodekind == NodeKind.STMT:
        if t.kind == StmtKind.IF:
            cond = t.child[0].type if t.child else None
            if cond == 'void':
                semanticError(t.child[0], "condición del if no puede ser void")
        elif t.kind == StmtKind.WHILE:
            cond = t.child[0].type if t.child else None
            if cond == 'void':
                semanticError(t.child[0], "condición del while no puede ser void")

def typeCheck(syntaxTree):
    traverse(syntaxTree, nullProc, checkNode)
