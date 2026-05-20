# analyze.py — Análisis semántico para C-

import lexer as lex
from globalTypes import TokenType
from Parser import NodeKind, StmtKind, ExpKind, DeclKind
from symtab import scope_enter, scope_exit, st_insert, st_lookup, st_lookup_current, printSymTab, _all_entries, _scopes

Error = False
_current_function = None  # Track current function for return type checking
_top_level_decls = []     # Track top-level declarations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def semanticError(t, message):
    global Error
    lineno = t.lineno if t else 1
    
    # Try to find a better line number by searching for the token in code lines
    token_pos = 0
    if hasattr(t, 'attr') and t.attr and hasattr(lex, 'programa') and lex.programa:
        lines = lex.programa.split('\n')
        for i, line in enumerate(lines, 1):
            # Skip comment lines and empty lines
            stripped = line.strip()
            if (stripped.startswith('/*') or stripped.startswith('*') or 
                stripped.endswith('*/') or not stripped):
                continue
            
            # Remove inline comments
            code_part = line.split('/*')[0]
            if str(t.attr) in code_part:
                lineno = i
                token_pos = code_part.find(str(t.attr))
                break
    
    print(f"Línea {lineno}: Error semántico: {message}")
    
    # Find and print source line with caret
    if hasattr(lex, 'programa') and lex.programa:
        lines = lex.programa.split('\n')
        if 1 <= lineno <= len(lines):
            print(lines[lineno - 1])
            print(' ' * token_pos + '^')
    
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
    global _current_function, _top_level_decls
    if t.nodekind == NodeKind.DECL:
        if t.kind == DeclKind.FUN:
            if st_lookup_current(t.attr) is not None:
                semanticError(t, f"función '{t.attr}' ya declarada en este scope")
            else:
                st_insert(t.attr, t.lineno, t.type, 'fun')
                if len(_scopes) == 1:  # top-level
                    _top_level_decls.append(t)
            _current_function = t
            scope_enter()
        elif t.kind == DeclKind.VAR:
            name = t.attr if isinstance(t.attr, str) else t.attr[0]
            if t.type == 'void':
                semanticError(t, f"variable '{name}' no puede ser de tipo void")
            elif st_lookup_current(name) is not None:
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
                entry['lines'].append(t.lineno)
        elif t.kind == ExpKind.CALL:
            entry = st_lookup(t.attr)
            if entry is None:
                semanticError(t, f"función '{t.attr}' no declarada")
            elif entry['kind'] != 'fun':
                semanticError(t, f"'{t.attr}' no es una función")
            else:
                entry['lines'].append(t.lineno)

def exitNode(t):
    """Cierra scopes al salir de funciones y bloques compuestos."""
    global _current_function
    if t.nodekind == NodeKind.DECL and t.kind == DeclKind.FUN:
        scope_exit()
        _current_function = None
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

def tabla(syntaxTree, imprime=True):
    global _top_level_decls
    _top_level_decls = []
    _insert_builtins()
    _mark_fun_compound(syntaxTree)
    traverse(syntaxTree, insertNode, exitNode)
    
    # Check main is last declaration
    if _top_level_decls and _top_level_decls[-1].attr != 'main':
        semanticError(_top_level_decls[-1], "la función 'main' debe ser la última declaración")
    
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
            
            # Check argument count (skip builtins)
            if entry and entry['loc'] is not None:
                # Find function declaration to count parameters
                for name, depth, info in _all_entries:
                    if name == t.attr and info['kind'] == 'fun' and depth == 0:
                        # Count parameters in same scope as function
                        param_count = sum(1 for n, d, i in _all_entries 
                                        if i['kind'] == 'param' and d == depth + 1)
                        
                        # Count arguments
                        arg_count = 0
                        if t.child and t.child[0].kind != "Args":  # not empty args
                            arg_count = len(t.child[0].child) if t.child[0].child else 1
                        
                        if arg_count != param_count:
                            semanticError(t, f"función '{t.attr}' espera {param_count} argumentos, recibió {arg_count}")
                        break
    elif t.nodekind == NodeKind.STMT:
        if t.kind == StmtKind.RETURN:
            ret_type = t.child[0].type if t.child else 'void'
            if _current_function:
                expected = _current_function.type
                if expected == 'void' and ret_type != 'void':
                    semanticError(t, "función void no puede retornar un valor")
                elif expected != 'void' and ret_type == 'void':
                    semanticError(t, f"función '{expected}' debe retornar un valor")
        elif t.kind == StmtKind.IF:
            cond = t.child[0].type if t.child else None
            if cond == 'void':
                semanticError(t.child[0], "condición del if no puede ser void")
        elif t.kind == StmtKind.WHILE:
            cond = t.child[0].type if t.child else None
            if cond == 'void':
                semanticError(t.child[0], "condición del while no puede ser void")

def typeCheck(syntaxTree):
    traverse(syntaxTree, nullProc, checkNode)

def semantica(syntaxTree, imprime=True):
    """Public interface: builds symbol table then runs type checking."""
    tabla(syntaxTree, imprime)
    if imprime:
        print("\nVerificando tipos...")
    typeCheck(syntaxTree)
