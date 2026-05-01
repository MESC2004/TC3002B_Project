import lexer.lexer as lex
from globalTypes import TokenType

# ---------------------------------------------------------------------------
# AST Node Definitions
# ---------------------------------------------------------------------------
class NodeKind:
    STMT = "Statement"
    EXP = "Expression"
    DECL = "Declaration"

class StmtKind:
    IF = "If"
    WHILE = "While"
    RETURN = "Return"
    COMPOUND = "Compound"
    EXPR = "Expression Stmt"

class ExpKind:
    OP = "Operation"
    CONST = "Constant"
    ID = "Id"
    VAR = "Variable"
    CALL = "Call"
    ASSIGN = "Assign"

class DeclKind:
    VAR = "Var Declaration"
    FUN = "Function Declaration"
    PARAM = "Parameter"

class TreeNode:
    def __init__(self, nodekind, kind, lineno):
        self.child = []
        self.sibling = None 
        self.nodekind = nodekind
        self.kind = kind
        self.lineno = lineno
        self.attr = None 
        self.type = None 

# ---------------------------------------------------------------------------
# Parser Globals
# ---------------------------------------------------------------------------
token = None
tokenString = None
error = False

def panic_mode(sync_tokens):
    """Consume tokens hasta encontrar uno que esté en el conjunto de sincronización."""
    global token, tokenString
    # Avanzamos al menos un token para asegurar progreso
    token, tokenString = lex.getToken(imprime=False)
    while token != TokenType.ENDFILE and token not in sync_tokens:
        token, tokenString = lex.getToken(imprime=False)

def syntaxError(message, sync_tokens=None):
    global error
    error = True
    
    prog_len = len(lex.programa)
    if prog_len == 0:
        if sync_tokens: panic_mode(sync_tokens)
        return

    # Calculamos la posición real del token erróneo
    pos = max(0, min(lex.posicion - len(tokenString), prog_len - 1))
    
    # Calcular el número de línea real contando \n hasta pos
    actual_lineno = lex.programa.count('\n', 0, pos) + 1
    
    print(f"\nLínea {actual_lineno}: Error sintáctico: {message}")
    
    line_start = lex.programa.rfind('\n', 0, pos) + 1
    line_end = lex.programa.find('\n', pos)
    if line_end == -1: line_end = prog_len
    
    source_line = lex.programa[line_start:line_end].replace('\t', ' ')
    col_in_line = max(0, pos - line_start)
    
    print(source_line)
    print(' ' * col_in_line + '^')
    
    if sync_tokens:
        panic_mode(sync_tokens)

def match(expected):
    global token, tokenString
    if token == expected:
        token, tokenString = lex.getToken(imprime=False)
    else:
        sync = {TokenType.TKN_SMC, TokenType.TKN_CLOSE, TokenType.INT, TokenType.VOID, 
                TokenType.IF, TokenType.WHILE, TokenType.RETURN, TokenType.ENDFILE}
        syntaxError(f"se esperaba '{expected.value if hasattr(expected, 'value') else expected}', se recibió '{tokenString}'", sync)

# ---------------------------------------------------------------------------
# Grammar Implementation
# (EBNF functions)
# ---------------------------------------------------------------------------

def program():
    global token, tokenString
    t = TreeNode(NodeKind.DECL, "Program", lex.lineno)
    decl_sync = {TokenType.INT, TokenType.VOID, TokenType.ENDFILE}
    
    while token != TokenType.ENDFILE:
        try:
            if token not in (TokenType.INT, TokenType.VOID):
                syntaxError("se esperaba el inicio de una declaración (int o void)", decl_sync)
                if token == TokenType.ENDFILE: break
            node = declaration()
            if node: t.child.append(node)
        except Exception:
            panic_mode(decl_sync)
    return t

def declaration():
    global token, tokenString
    line = lex.lineno
    t_type = type_specifier()
    id_name = tokenString
    match(TokenType.ID)
    if tokenString == '(':
        return fun_declaration(t_type, id_name, line)
    else:
        return var_declaration(t_type, id_name, line)

def var_declaration(t_type, id_name, line):
    global token, tokenString
    t = TreeNode(NodeKind.DECL, DeclKind.VAR, line)
    t.type = t_type
    t.attr = id_name
    if tokenString == '[':
        match(TokenType.TKN_OPEN)
        array_size = tokenString
        match(TokenType.NUM)
        if tokenString == ']':
            match(TokenType.TKN_CLOSE)
        else:
            syntaxError("se esperaba ']'", {TokenType.TKN_SMC})
        t.attr = (id_name, array_size)
    match(TokenType.TKN_SMC)
    return t

def type_specifier():
    global token, tokenString
    t_type = tokenString
    if token in (TokenType.INT, TokenType.VOID):
        match(token)
    else:
        syntaxError("especificador de tipo esperado (int o void)", {TokenType.ID, TokenType.TKN_SMC})
    return t_type

def fun_declaration(t_type, id_name, line):
    global token, tokenString
    t = TreeNode(NodeKind.DECL, DeclKind.FUN, line)
    t.type = t_type
    t.attr = id_name
    match(TokenType.TKN_OPEN) # '('
    t.child.append(params())
    if tokenString == ')':
        match(TokenType.TKN_CLOSE) # ')'
    else:
        syntaxError("se esperaba ')'", {TokenType.TKN_OPEN})
    t.child.append(compound_stmt())
    return t

def params():
    global token, tokenString
    if token == TokenType.VOID:
        old_pos = lex.posicion
        next_t, next_s = lex.getToken(imprime=False)
        lex.globales(lex.programa, old_pos, lex.progLong)
        if next_t == TokenType.TKN_CLOSE and next_s == ')':
            match(TokenType.VOID)
            t = TreeNode(NodeKind.DECL, "Params", lex.lineno)
            t.attr = "void"
            return t
    return param_list()

def param_list():
    global token, tokenString
    t = TreeNode(NodeKind.DECL, "Param List", lex.lineno)
    t.child.append(param())
    while token == TokenType.TKN_CMA:
        match(TokenType.TKN_CMA)
        t.child.append(param())
    return t

def param():
    global token, tokenString
    t = TreeNode(NodeKind.DECL, DeclKind.PARAM, lex.lineno)
    t.type = type_specifier()
    t.attr = tokenString
    match(TokenType.ID)
    if tokenString == '[':
        match(TokenType.TKN_OPEN)
        if tokenString == ']':
            match(TokenType.TKN_CLOSE)
        else:
            syntaxError("se esperaba ']'", {TokenType.TKN_CMA, TokenType.TKN_CLOSE})
        t.attr = (t.attr, "[]")
    return t

def compound_stmt():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, StmtKind.COMPOUND, lex.lineno)
    if tokenString == '{':
        match(TokenType.TKN_OPEN)
    else:
        syntaxError("se esperaba '{'", {TokenType.IF, TokenType.WHILE, TokenType.RETURN, TokenType.ID, TokenType.TKN_CLOSE})
        
    t.child.append(local_declarations())
    t.child.append(statement_list())
    
    if tokenString == '}':
        match(TokenType.TKN_CLOSE)
    else:
        syntaxError("se esperaba '}'", {TokenType.INT, TokenType.VOID, TokenType.ENDFILE})
    return t

def local_declarations():
    global token, tokenString
    t = TreeNode(NodeKind.DECL, "Local Declarations", lex.lineno)
    while token in (TokenType.INT, TokenType.VOID):
        try:
            t_type = tokenString
            line = lex.lineno
            match(token)
            id_name = tokenString
            if token == TokenType.ID:
                match(TokenType.ID)
                node = var_declaration(t_type, id_name, line)
                if node: t.child.append(node)
            else:
                syntaxError("ID esperado", {TokenType.TKN_SMC, TokenType.INT, TokenType.VOID})
        except Exception:
            panic_mode({TokenType.TKN_SMC, TokenType.INT, TokenType.VOID})
    return t

def statement_list():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, "Statement List", lex.lineno)
    while token != TokenType.ENDFILE and tokenString != '}':
        try:
            node = statement()
            if node: t.child.append(node)
        except Exception:
            sync = {TokenType.TKN_SMC, TokenType.IF, TokenType.WHILE, TokenType.RETURN, TokenType.TKN_CLOSE, TokenType.ENDFILE}
            syntaxError("error en sentencia", sync)
            if token == TokenType.TKN_SMC: match(TokenType.TKN_SMC)
    return t

def statement():
    global token, tokenString
    if token == TokenType.IF: 
        return selection_stmt()
    elif token == TokenType.WHILE: 
        return iteration_stmt()
    elif token == TokenType.RETURN: 
        return return_stmt()
    elif tokenString == '{': 
        return compound_stmt()
    elif token in (TokenType.ID, TokenType.NUM, TokenType.TKN_OPEN) or tokenString == '(':
        # Only if new exp can be made (panic mode)
        return expression_stmt()
    elif token == TokenType.TKN_CLOSE and tokenString != '}':
        # ) or ] orphan (close with no open)
        sync = {TokenType.TKN_SMC, TokenType.IF, TokenType.WHILE, TokenType.RETURN, TokenType.TKN_CLOSE, TokenType.ENDFILE}
        syntaxError(f"delimitador de cierre '{tokenString}' huérfano o inesperado", sync)
        return None
    else:
        # Fallback to not assume expressions
        sync = {TokenType.TKN_SMC, TokenType.IF, TokenType.WHILE, TokenType.RETURN, TokenType.TKN_CLOSE, TokenType.ENDFILE}
        syntaxError(f"se encontró un token inesperado '{tokenString}' fuera de una sentencia válida", sync)
        return None

def expression_stmt():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, StmtKind.EXPR, lex.lineno)
    if token != TokenType.TKN_SMC:
        t.child.append(expression())
    match(TokenType.TKN_SMC)
    return t

def selection_stmt():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, StmtKind.IF, lex.lineno)
    match(TokenType.IF)
    match(TokenType.TKN_OPEN)
    t.child.append(expression())
    match(TokenType.TKN_CLOSE)
    t.child.append(statement())
    if token == TokenType.ELSE:
        match(TokenType.ELSE)
        t.child.append(statement())
    return t

def iteration_stmt():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, StmtKind.WHILE, lex.lineno)
    match(TokenType.WHILE)
    match(TokenType.TKN_OPEN)
    t.child.append(expression())
    match(TokenType.TKN_CLOSE)
    t.child.append(statement())
    return t

def return_stmt():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, StmtKind.RETURN, lex.lineno)
    match(TokenType.RETURN)
    if token != TokenType.TKN_SMC:
        t.child.append(expression())
    match(TokenType.TKN_SMC)
    return t

def expression():
    global token, tokenString
    if token == TokenType.ID:
        is_assign = False
        temp_pos = lex.posicion
        bracket_count = 0
        while temp_pos < len(lex.programa):
            char = lex.programa[temp_pos]
            if char == '[': bracket_count += 1
            elif char == ']': bracket_count -= 1
            elif char == '=' and bracket_count == 0:
                if temp_pos + 1 < len(lex.programa) and lex.programa[temp_pos+1] == '=':
                    temp_pos += 1
                else:
                    is_assign = True
                    break
            elif (char == ';' or char == ')' or char == ',') and bracket_count == 0: break
            temp_pos += 1
        if is_assign:
            t = TreeNode(NodeKind.EXP, ExpKind.ASSIGN, lex.lineno)
            t.child.append(var())
            match(TokenType.TKN_EQ)
            t.child.append(expression())
            return t
    return simple_expression()

def var():
    global token, tokenString
    t = TreeNode(NodeKind.EXP, ExpKind.VAR, lex.lineno)
    t.attr = tokenString
    match(TokenType.ID)
    if tokenString == '[':
        match(TokenType.TKN_OPEN)
        t.child.append(expression())
        if tokenString == ']':
            match(TokenType.TKN_CLOSE)
        else:
            syntaxError("se esperaba ']'")
    return t

def simple_expression():
    global token, tokenString
    t = additive_expression()
    if token in (TokenType.TKN_LEQ, TokenType.TKN_LT, TokenType.TKN_GEQ, TokenType.TKN_GT, TokenType.TKN_DEQ, TokenType.TKN_NEQ):
        p = TreeNode(NodeKind.EXP, ExpKind.OP, lex.lineno)
        p.attr = tokenString
        p.child.append(t)
        match(token)
        p.child.append(additive_expression())
        t = p
    return t

def additive_expression():
    global token, tokenString
    t = term()
    while token in (TokenType.TKN_PLUS, TokenType.TKN_MINUS):
        p = TreeNode(NodeKind.EXP, ExpKind.OP, lex.lineno)
        p.attr = tokenString
        p.child.append(t)
        match(token)
        p.child.append(term())
        t = p
    return t

def term():
    global token, tokenString
    t = factor()
    while token in (TokenType.TKN_MULT, TokenType.TKN_DIV):
        p = TreeNode(NodeKind.EXP, ExpKind.OP, lex.lineno)
        p.attr = tokenString
        p.child.append(t)
        match(token)
        p.child.append(factor())
        t = p
    return t

def factor():
    global token, tokenString
    if tokenString == '(':
        match(TokenType.TKN_OPEN)
        t = expression()
        if tokenString == ')':
            match(TokenType.TKN_CLOSE)
        else:
            syntaxError("se esperaba ')'")
        return t
    elif token == TokenType.NUM:
        t = TreeNode(NodeKind.EXP, ExpKind.CONST, lex.lineno)
        t.attr = tokenString
        match(TokenType.NUM)
        return t
    elif token == TokenType.ID:
        old_pos = lex.posicion
        next_t, next_s = lex.getToken(imprime=False)
        lex.globales(lex.programa, old_pos, lex.progLong)
        if next_t == TokenType.TKN_OPEN and next_s == '(':
            return call()
        else:
            return var()
    else:
        syntaxError(f"factor inesperado: '{tokenString}'")
        return None

def call():
    global token, tokenString
    t = TreeNode(NodeKind.EXP, ExpKind.CALL, lex.lineno)
    t.attr = tokenString
    match(TokenType.ID)
    match(TokenType.TKN_OPEN)
    t.child.append(args())
    if tokenString == ')':
        match(TokenType.TKN_CLOSE)
    else:
        syntaxError("se esperaba ')'")
    return t

def args():
    global token, tokenString
    if tokenString == ')':
        t = TreeNode(NodeKind.EXP, "Args", lex.lineno)
        t.attr = "empty"
        return t
    return arg_list()

def arg_list():
    global token, tokenString
    t = TreeNode(NodeKind.EXP, "Arg List", lex.lineno)
    t.child.append(expression())
    while token == TokenType.TKN_CMA:
        match(TokenType.TKN_CMA)
        t.child.append(expression())
    return t

def printTree(node, indent=0):
    if node is None: return
    spacing = "  " * indent
    attr_str = f" [{node.attr}]" if node.attr else ""
    type_str = f" <{node.type}>" if node.type else ""
    print(f"{spacing}{node.nodekind}: {node.kind}{attr_str}{type_str}")
    for c in node.child:
        if isinstance(c, list):
            for item in c: printTree(item, indent + 1)
        else: printTree(c, indent + 1)

def parser(imprime=True):
    global token, tokenString, error
    error = False
    token, tokenString = lex.getToken(imprime=False)
    ast = program()
    if imprime:
        print("\n--- Árbol Sintáctico (AST) ---")
        printTree(ast)
    if error: print("\nHubo errores durante el análisis sintáctico.")
    else: print("\nAnálisis completado exitosamente.")
    return ast

def globales(prog, pos, long):
    # Forzar el reinicio de la instancia correcta del lexer (GLOBALS)
    lex.globales(prog, pos, long)
