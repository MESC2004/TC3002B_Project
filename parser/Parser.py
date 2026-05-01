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
        self.sibling = None # Not strictly needed if using a list for children, but kept for compatibility
        self.nodekind = nodekind
        self.kind = kind
        self.lineno = lineno
        self.attr = None # To store IDs, values, or operators
        self.type = None # For 'int' or 'void'

# ---------------------------------------------------------------------------
# Parser Globals
# ---------------------------------------------------------------------------
token = None
tokenString = None
error = False

def syntaxError(message):
    global error
    error = True
    print(f"\nLínea {lex.lineno}: Error sintáctico: {message}")
    # Localizar la línea en el programa para mostrar el marcador ^
    line_start = lex.programa.rfind('\n', 0, lex.posicion) + 1
    line_end = lex.programa.find('\n', lex.posicion)
    if line_end == -1: line_end = len(lex.programa)
    source_line = lex.programa[line_start:line_end]
    col_in_line = lex.posicion - line_start - len(tokenString)
    if col_in_line < 0: col_in_line = 0
    print(source_line)
    print(' ' * col_in_line + '^')

def match(expected):
    global token, tokenString
    if token == expected:
        token, tokenString = lex.getToken(imprime=False)
    else:
        # Improved error message for TKN_OPEN / TKN_CLOSE
        expected_msg = expected.value if hasattr(expected, 'value') else str(expected)
        
        if expected == TokenType.TKN_OPEN:
            expected_msg = "un delimitador de apertura ('(', '[' o '{')"
        elif expected == TokenType.TKN_CLOSE:
            expected_msg = "un delimitador de cierre (')', ']' o '}')"
        elif hasattr(expected, 'name'):
            expected_msg = f"'{expected.value}'" if hasattr(expected, 'value') else expected.name

        syntaxError(f"se esperaba {expected_msg}, se recibió '{tokenString}'")
        # Panic mode: consume until a likely synchronisation point
        token, tokenString = lex.getToken(imprime=False)

# ---------------------------------------------------------------------------
# Grammar Implementation (EBNF based)
# ---------------------------------------------------------------------------

# (* 1 *) program = declaration , { declaration } ;
def program():
    global token, tokenString
    t = TreeNode(NodeKind.DECL, "Program", lex.lineno)
    t.child.append(declaration())
    while token != TokenType.ENDFILE:
        node = declaration()
        if node:
            t.child.append(node)
    return t

# (* 2 *) declaration = var-declaration | fun-declaration ;
# (* 3, 5 *) Factorized prefix: type-specifier ID
def declaration():
    global token, tokenString
    t_type = type_specifier()
    id_name = tokenString
    line = lex.lineno
    match(TokenType.ID)
    
    if tokenString == '(': # '(' -> fun-declaration
        return fun_declaration(t_type, id_name, line)
    else: # ';' or '[' -> var-declaration
        return var_declaration(t_type, id_name, line)

# (* 3 *) var-declaration = type-specifier , ID , [ "[" , NUM , "]" ] , ";" ;
def var_declaration(t_type, id_name, line):
    global token, tokenString
    t = TreeNode(NodeKind.DECL, DeclKind.VAR, line)
    t.type = t_type
    t.attr = id_name
    
    if tokenString == '[': 
        match(TokenType.TKN_OPEN) # consume '['
        array_size = tokenString
        match(TokenType.NUM)
        if tokenString == ']':
            match(TokenType.TKN_CLOSE) # consume ']'
        else:
            syntaxError("se esperaba ']'")
        t.attr = (id_name, array_size) # Store as tuple if array
    
    match(TokenType.TKN_SMC)
    return t

# (* 4 *) type-specifier = "int" | "void" ;
def type_specifier():
    global token, tokenString
    t_type = tokenString
    if token in (TokenType.INT, TokenType.VOID):
        match(token)
    else:
        syntaxError("se esperaba un especificador de tipo (int o void)")
    return t_type

# (* 5 *) fun-declaration = type-specifier , ID , "(" , params , ")" , compound-stmt ;
def fun_declaration(t_type, id_name, line):
    global token, tokenString
    t = TreeNode(NodeKind.DECL, DeclKind.FUN, line)
    t.type = t_type
    t.attr = id_name
    
    if tokenString != '(':
        syntaxError("se esperaba '('")
    match(TokenType.TKN_OPEN) # '('
    
    t.child.append(params())
    
    if tokenString != ')':
        syntaxError("se esperaba ')'")
    match(TokenType.TKN_CLOSE) # ')'
    
    t.child.append(compound_stmt())
    return t

# (* 6 *) params = param-list | "void" ;
def params():
    global token, tokenString
    line = lex.lineno
    if token == TokenType.VOID:
        # Check if it's just 'void' or if it's 'void ID' (which would be a param-list)
        # We need a lookahead. Lexer's getToken can be tricky here.
        # But in C-, params is either 'void' or a list.
        # Simple heuristic: if next is ')', it's the 'void' case.
        # We use a global lookahead hack or just check current.
        # If current is VOID and we match it, we check if next is ')'.
        pass 
    
    # Let's handle 'void' properly
    if token == TokenType.VOID:
        # Lookahead: is it 'void )' or 'void ID'?
        # For simplicity in this basic parser, we'll try to peek.
        # But since we don't have a peek, let's assume if it's VOID and next is ')', it's (void).
        # We'll peek at the lexer's position or just call getToken and put back if needed.
        # In this project's lexer, we can't easily put back.
        # Let's use the fact that param-list MUST start with type-specifier ID.
        if token == TokenType.VOID:
            # We match VOID. If next is ')', we are done. If next is ID, it was a param.
            # This is where a LL(1) or a more advanced lookahead is needed.
            # Let's implement a simple peek:
            old_pos = lex.posicion
            next_t, next_s = lex.getToken(imprime=False)
            lex.globales(lex.programa, old_pos, lex.progLong) # Restore lexer state
            
            if next_t == TokenType.TKN_CLOSE and next_s == ')':
                match(TokenType.VOID)
                t = TreeNode(NodeKind.DECL, "Params", lex.lineno)
                t.attr = "void"
                return t

    return param_list()

# (* 7 *) param-list = param , { "," , param } ;
def param_list():
    global token, tokenString
    t = TreeNode(NodeKind.DECL, "Param List", lex.lineno)
    t.child.append(param())
    while token == TokenType.TKN_CMA:
        match(TokenType.TKN_CMA)
        t.child.append(param())
    return t

# (* 8 *) param = type-specifier , ID , [ "[" , "]" ] ;
def param():
    global token, tokenString
    t = TreeNode(NodeKind.DECL, DeclKind.PARAM, lex.lineno)
    t.type = type_specifier()
    t.attr = tokenString
    match(TokenType.ID)
    if tokenString == '[':
        match(token)
        if tokenString == ']':
            match(token) # ']'
        else:
            syntaxError("se esperaba ']'")
        t.attr = (t.attr, "[]")
    return t

# (* 9 *) compound-stmt = "{" , local-declarations , statement-list , "}" ;
def compound_stmt():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, StmtKind.COMPOUND, lex.lineno)
    if tokenString != '{':
        syntaxError("se esperaba '{'")
    match(TokenType.TKN_OPEN) # '{'
        
    t.child.append(local_declarations())
    t.child.append(statement_list())
    
    if tokenString != '}':
        syntaxError("se esperaba '}'")
    match(TokenType.TKN_CLOSE) # '}'
    return t

# (* 10 *) local-declarations = { var-declaration } ;
def local_declarations():
    global token, tokenString
    t = TreeNode(NodeKind.DECL, "Local Declarations", lex.lineno)
    # var-declaration starts with type-specifier (int, void)
    while token in (TokenType.INT, TokenType.VOID):
        # We need to distinguish between var-decl and start of a statement if it was allowed
        # But in C-, local-declarations must come first.
        t_type = type_specifier()
        id_name = tokenString
        line = lex.lineno
        match(TokenType.ID)
        t.child.append(var_declaration(t_type, id_name, line))
    return t

# (* 11 *) statement-list = { statement } ;
def statement_list():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, "Statement List", lex.lineno)
    # Predict statement start
    while token in (TokenType.IF, TokenType.WHILE, TokenType.RETURN, 
                    TokenType.TKN_OPEN, TokenType.ID, TokenType.NUM, TokenType.TKN_SMC):
        # Note: TKN_OPEN for compound-stmt '{' or '(' for expression
        t.child.append(statement())
    return t

# (* 12 *) statement = expression-stmt | compound-stmt | selection-stmt | iteration-stmt | return-stmt ;
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
    else:
        return expression_stmt()

# (* 13 *) expression-stmt = [ expression ] , ";" ;
def expression_stmt():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, StmtKind.EXPR, lex.lineno)
    if token != TokenType.TKN_SMC:
        t.child.append(expression())
    match(TokenType.TKN_SMC)
    return t

# (* 14 *) selection-stmt = "if" , "(" , expression , ")" , statement , [ "else" , statement ] ;
def selection_stmt():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, StmtKind.IF, lex.lineno)
    match(TokenType.IF)
    if tokenString != '(':
        syntaxError("se esperaba '('")
    match(TokenType.TKN_OPEN) # '('
    
    t.child.append(expression())
    
    if tokenString != ')':
        syntaxError("se esperaba ')'")
    match(TokenType.TKN_CLOSE) # ')'
    
    t.child.append(statement())
    if token == TokenType.ELSE:
        match(TokenType.ELSE)
        t.child.append(statement())
    return t

# (* 15 *) iteration-stmt = "while" , "(" , expression , ")" , statement ;
def iteration_stmt():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, StmtKind.WHILE, lex.lineno)
    match(TokenType.WHILE)
    if tokenString != '(':
        syntaxError("se esperaba '('")
    match(TokenType.TKN_OPEN) # '('
    
    t.child.append(expression())
    
    if tokenString != ')':
        syntaxError("se esperaba ')'")
    match(TokenType.TKN_CLOSE) # ')'
    
    t.child.append(statement())
    return t

# (* 16 *) return-stmt = "return" , [ expression ] , ";" ;
def return_stmt():
    global token, tokenString
    t = TreeNode(NodeKind.STMT, StmtKind.RETURN, lex.lineno)
    match(TokenType.RETURN)
    if token != TokenType.TKN_SMC:
        t.child.append(expression())
    match(TokenType.TKN_SMC)
    return t

# (* 17 *) expression = var "=" expression | simple-expression ;
def expression():
    global token, tokenString
    # Both start with ID. This needs lookahead to see if '=' is coming.
    if token == TokenType.ID:
        # Peek to see if it's an assignment
        old_pos = lex.posicion
        old_lineno = lex.lineno
        
        # We need to skip potential array indexing to find if there is an '='
        # For simplicity, we'll try to find an '=' before a ';' or other delimiters
        is_assign = False
        temp_pos = lex.posicion
        bracket_count = 0
        while temp_pos < len(lex.programa):
            char = lex.programa[temp_pos]
            if char == '[': bracket_count += 1
            elif char == ']': bracket_count -= 1
            elif char == '=' and bracket_count == 0:
                if temp_pos + 1 < len(lex.programa) and lex.programa[temp_pos+1] == '=':
                    # It's '==', not '=', so we skip the second '=' to avoid misidentifying it
                    temp_pos += 1
                else:
                    is_assign = True
                    break
            elif (char == ';' or char == ')' or char == ',') and bracket_count == 0:
                break
            temp_pos += 1
        
        if is_assign:
            t = TreeNode(NodeKind.EXP, ExpKind.ASSIGN, lex.lineno)
            t.child.append(var())
            match(TokenType.TKN_EQ)
            t.child.append(expression())
            return t

    return simple_expression()

# (* 18 *) var = ID , [ "[" , expression , "]" ] ;
def var():
    global token, tokenString
    t = TreeNode(NodeKind.EXP, ExpKind.VAR, lex.lineno)
    t.attr = tokenString
    match(TokenType.ID)
    if tokenString == '[':
        match(TokenType.TKN_OPEN) # '['
        t.child.append(expression())
        if tokenString == ']':
            match(TokenType.TKN_CLOSE) # ']'
        else:
            syntaxError("se esperaba ']'")
    return t

# (* 19 *) simple-expression = additive-expression , [ relop , additive-expression ] ;
def simple_expression():
    global token, tokenString
    t = additive_expression()
    if token in (TokenType.TKN_LEQ, TokenType.TKN_LT, TokenType.TKN_GEQ, 
                 TokenType.TKN_GT, TokenType.TKN_DEQ, TokenType.TKN_NEQ):
        p = TreeNode(NodeKind.EXP, ExpKind.OP, lex.lineno)
        p.attr = tokenString
        p.child.append(t)
        match(token)
        p.child.append(additive_expression())
        t = p
    return t

# (* 21 *) additive-expression = term , { addop , term } ;
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

# (* 23 *) term = factor , { mulop , factor } ;
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

# (* 25 *) factor = "(" expression ")" | var | call | NUM ;
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
        # ID could be var or call. Lookahead to see if next is '('
        old_pos = lex.posicion
        next_t, next_s = lex.getToken(imprime=False)
        lex.globales(lex.programa, old_pos, lex.progLong) # Restore lexer state
        
        if next_t == TokenType.TKN_OPEN and next_s == '(':
            return call()
        else:
            return var()
    else:
        syntaxError(f"factor inesperado: '{tokenString}'")
        temp_token, _ = lex.getToken(imprime=False)
        return None

# (* 26 *) call = ID , "(" , args , ")" ;
def call():
    global token, tokenString
    t = TreeNode(NodeKind.EXP, ExpKind.CALL, lex.lineno)
    t.attr = tokenString
    match(TokenType.ID)
    if tokenString != '(':
        syntaxError("se esperaba '('")
    match(TokenType.TKN_OPEN) # '('
    
    t.child.append(args())
    
    if tokenString != ')':
        syntaxError("se esperaba ')'")
    match(TokenType.TKN_CLOSE) # ')'
    return t

# (* 27 *) args = [ arg-list ] ;
def args():
    global token, tokenString
    if tokenString == ')':
        t = TreeNode(NodeKind.EXP, "Args", lex.lineno)
        t.attr = "empty"
        return t
    return arg_list()

# (* 28 *) arg-list = expression , { "," , expression } ;
def arg_list():
    global token, tokenString
    t = TreeNode(NodeKind.EXP, "Arg List", lex.lineno)
    t.child.append(expression())
    while token == TokenType.TKN_CMA:
        match(TokenType.TKN_CMA)
        t.child.append(expression())
    return t

# ---------------------------------------------------------------------------
# AST Printer
# ---------------------------------------------------------------------------
def printTree(node, indent=0):
    if node is None:
        return
    
    spacing = "  " * indent
    # Format node info
    attr_str = f" [{node.attr}]" if node.attr else ""
    type_str = f" <{node.type}>" if node.type else ""
    
    print(f"{spacing}{node.nodekind}: {node.kind}{attr_str}{type_str}")
    
    for c in node.child:
        if isinstance(c, list):
            for item in c:
                printTree(item, indent + 1)
        else:
            printTree(c, indent + 1)
    
    if node.sibling:
        printTree(node.sibling, indent)

# ---------------------------------------------------------------------------
# Main Entry Points
# ---------------------------------------------------------------------------
def parser(imprime=True):
    global token, tokenString, error
    error = False
    
    # Get first token
    token, tokenString = lex.getToken(imprime=False)
    
    # Start parsing
    ast = program()
    
    if error:
        return "Hubo errores durante el análisis sintáctico."
    
    if imprime:
        printTree(ast)
    
    return ast

# This function is required by the project specs to sync with lexer globals
def globales(prog, pos, long):
    global programa
    global posicion
    global progLong
    programa = prog
    posicion = pos
    progLong = long
    lex.globales(prog, pos, long)
