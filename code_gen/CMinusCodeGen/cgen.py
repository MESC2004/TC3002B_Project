# cgen.py — Generador de código MIPS para C-
# Genera ensamblador MIPS para correr en SPIM.
#
# Convenciones de registro:
#   $v0      — valor de retorno / resultado de expresión
#   $a0-$a3  — argumentos de función
#   $sp      — stack pointer (crece hacia abajo)
#   $fp      — frame pointer
#   $ra      — dirección de retorno
#
# Layout del frame (prólogo):
#   $fp+ 0  : $ra guardado
#   $fp- 4  : $fp anterior
#   $fp- 8  : param/local con loc más pequeño
#   ...
#   offset(var) = -(loc + 2) * 4  relativo a $fp
#
# Variables globales: etiqueta en .data, 1 palabra cada una.
# Arrays globales:    etiqueta en .data con .space N*4.

import sys
from parser import NodeKind, StmtKind, ExpKind, DeclKind
import symtab as _symtab   # access _symtab._all_entries via module to survive reset()

# ---------------------------------------------------------------------------
# Estado global del generador
# ---------------------------------------------------------------------------
_out        = None
TraceCode   = False

_label_counter = 0
_functions     = {}   # fname -> {params, is_void}
_current_func  = None
_global_vars   = {}   # name -> asm label
_func_locals   = {}   # fname -> {name -> loc}  (params + locales de esa función)

# ---------------------------------------------------------------------------
# Helpers de emisión
# ---------------------------------------------------------------------------

def _new_label(prefix="L"):
    global _label_counter
    _label_counter += 1
    return f"{prefix}{_label_counter}"

def emitComment(c):
    if TraceCode:
        _out.write(f"# {c}\n")

def emit(instr):
    _out.write(f"    {instr}\n")

def emitLabel(label):
    _out.write(f"{label}:\n")

def emitBlank():
    _out.write("\n")

# ---------------------------------------------------------------------------
# Lookup de variables locales/parámetros usando _symtab._all_entries
# (los scopes ya están cerrados después del análisis semántico)
# ---------------------------------------------------------------------------

def _local_offset(name):
    """
    Busca 'name' en _symtab._all_entries para el scope de la función actual.
    Retorna offset desde $fp, o None si no es local/param.
    offset = -(loc + 2) * 4
    """
    # Buscamos la entrada más reciente con ese nombre en depth > 0
    for n, depth, info in reversed(_symtab._all_entries):
        if n == name and depth > 0 and info['kind'] in ('param', 'var'):
            if info['loc'] is not None:
                return -(info['loc'] + 2) * 4
    return None

# ---------------------------------------------------------------------------
# Pre-scan del AST: recopilar globales y metadatos de funciones
# ---------------------------------------------------------------------------

def _collect_globals(tree):
    for child in tree.child:
        if child is None:
            continue
        if child.nodekind == NodeKind.DECL and child.kind == DeclKind.VAR:
            name = child.attr if isinstance(child.attr, str) else child.attr[0]
            _global_vars[name] = f"_{name}"
        elif child.nodekind == NodeKind.DECL and child.kind == DeclKind.FUN:
            _collect_func_info(child)

def _collect_func_info(fun_node):
    fname = fun_node.attr
    params = []
    pnode = fun_node.child[0] if fun_node.child else None
    if pnode and pnode.kind == "Param List":
        for p in pnode.child:
            pname = p.attr if isinstance(p.attr, str) else p.attr[0]
            params.append(pname)
    _functions[fname] = {'params': params, 'is_void': fun_node.type == 'void'}

# ---------------------------------------------------------------------------
# Sección .data
# ---------------------------------------------------------------------------

def _emit_data_section(tree):
    _out.write(".data\n")
    for child in tree.child:
        if child is None:
            continue
        if child.nodekind == NodeKind.DECL and child.kind == DeclKind.VAR:
            name = child.attr if isinstance(child.attr, str) else child.attr[0]
            label = _global_vars[name]
            if isinstance(child.attr, tuple):
                size = int(child.attr[1]) * 4
                _out.write(f"{label}: .space {size}\n")
            else:
                _out.write(f"{label}: .word 0\n")
    _out.write("_newline: .asciiz \"\\n\"\n")
    emitBlank()

# ---------------------------------------------------------------------------
# genDecl
# ---------------------------------------------------------------------------

def _func_frame_size(fname):
    """
    Calcula el tamaño del frame buscando el loc máximo de params/vars de esta función.
    frame_size = (max_loc + 3) * 4   [slots 0..max_loc para vars, más $ra y $fp]
    """
    max_loc = -1
    for n, depth, info in _symtab._all_entries:
        if depth > 0 and info['kind'] in ('param', 'var') and info['loc'] is not None:
            # Determinar a qué función pertenece esta entrada
            # Las entradas están en orden; buscar la función propietaria
            if info['loc'] > max_loc:
                max_loc = info['loc']
                # No podemos saber aquí de qué función es sin más info,
                # así que recopilamos todos y filtramos por rango al llamar
    return max_loc

def _locs_for_func(fun_node):
    """Retorna el loc mínimo y máximo de params+vars de esta función."""
    pnode = fun_node.child[0]
    compound = fun_node.child[1]
    local_decl_node = compound.child[0]

    locs = []
    if pnode.kind == "Param List":
        for p in pnode.child:
            pname = p.attr if isinstance(p.attr, str) else p.attr[0]
            for n, d, info in _symtab._all_entries:
                if n == pname and d > 0 and info['kind'] == 'param' and info['loc'] is not None:
                    locs.append(info['loc'])
                    break
    for v in local_decl_node.child:
        vname = v.attr if isinstance(v.attr, str) else v.attr[0]
        for n, d, info in _symtab._all_entries:
            if n == vname and d > 0 and info['kind'] == 'var' and info['loc'] is not None:
                locs.append(info['loc'])
                break
    return locs

def genDecl(tree):
    global _current_func
    if tree.kind != DeclKind.FUN:
        return

    fname = tree.attr
    _current_func = fname
    emitComment(f"función: {fname}")

    locs = _locs_for_func(tree)
    max_loc = max(locs) if locs else -1
    # frame: slot para $ra, $fp, y todos los params/locales
    # El slot con loc=L está en offset -(L+2)*4 desde $fp
    # El slot más profundo es max_loc → offset -(max_loc+2)*4
    # frame_size debe cubrir desde $sp hasta $fp+4 (donde se guarda $ra)
    # $fp = $sp + frame_size - 4  →  frame_size = max_loc*4 + 12  si max_loc >= 0
    frame_size = (max_loc + 3) * 4 if max_loc >= 0 else 8  # mínimo: $ra + $fp

    pnode    = tree.child[0]
    compound = tree.child[1]

    emitLabel(fname)
    emitComment("prólogo")
    emit(f"subu $sp, $sp, {frame_size}")
    emit(f"sw   $ra, {frame_size - 4}($sp)")
    emit(f"sw   $fp, {frame_size - 8}($sp)")
    emit(f"addu $fp, $sp, {frame_size - 4}")

    # Guardar argumentos recibidos ($a0..$a3) en el frame
    if pnode.kind == "Param List":
        for i, p in enumerate(pnode.child):
            pname = p.attr if isinstance(p.attr, str) else p.attr[0]
            off = _local_offset(pname)
            if off is not None and i < 4:
                emit(f"sw   $a{i}, {off}($fp)   # param {pname}")
    emitBlank()

    # Cuerpo
    cGen(compound)

    # Epílogo
    emitLabel(f"{fname}_exit")
    emitComment("epílogo")
    emit(f"lw   $ra, {frame_size - 4}($sp)")
    emit(f"lw   $fp, {frame_size - 8}($sp)")
    emit(f"addu $sp, $sp, {frame_size}")
    if fname == 'main':
        emit("li   $v0, 10")
        emit("syscall               # exit")
    else:
        emit("jr   $ra")
    emitBlank()

    _current_func = None

# ---------------------------------------------------------------------------
# genStmt
# ---------------------------------------------------------------------------

def genStmt(tree):
    if tree.kind == StmtKind.IF:
        emitComment("-> if")
        cGen(tree.child[0])
        l_else = _new_label("else")
        l_end  = _new_label("endif")
        emit(f"beq  $v0, $zero, {l_else}")
        cGen(tree.child[1])
        emit(f"j    {l_end}")
        emitLabel(l_else)
        if len(tree.child) > 2 and tree.child[2] is not None:
            cGen(tree.child[2])
        emitLabel(l_end)
        emitComment("<- if")

    elif tree.kind == StmtKind.WHILE:
        emitComment("-> while")
        l_top = _new_label("while")
        l_end = _new_label("endwhile")
        emitLabel(l_top)
        cGen(tree.child[0])
        emit(f"beq  $v0, $zero, {l_end}")
        cGen(tree.child[1])
        emit(f"j    {l_top}")
        emitLabel(l_end)
        emitComment("<- while")

    elif tree.kind == StmtKind.RETURN:
        emitComment("-> return")
        if tree.child:
            cGen(tree.child[0])
        emit(f"j    {_current_func}_exit")
        emitComment("<- return")

    elif tree.kind == StmtKind.COMPOUND:
        cGen(tree.child[1])   # statement list

    elif tree.kind == StmtKind.EXPR:
        if tree.child:
            cGen(tree.child[0])

    elif tree.kind == "Statement List":
        for child in tree.child:
            cGen(child)

    elif tree.kind == "Local Declarations":
        pass   # espacio ya reservado en prólogo

# ---------------------------------------------------------------------------
# genExp  — resultado siempre en $v0
# ---------------------------------------------------------------------------

def _load_var(name, subscript_child=None):
    """Emite instrucciones para cargar una variable en $v0."""
    if name in _global_vars:
        label = _global_vars[name]
        if subscript_child is not None:
            cGen(subscript_child)
            emit("sll  $t0, $v0, 2")
            emit(f"la   $t1, {label}")
            emit("add  $t1, $t1, $t0")
            emit(f"lw   $v0, 0($t1)   # {name}[i]")
        else:
            emit(f"lw   $v0, {label}  # global {name}")
    else:
        off = _local_offset(name)
        if off is not None:
            if subscript_child is not None:
                # parámetro arreglo: el frame guarda la dirección base
                emit(f"lw   $t1, {off}($fp)  # base arreglo {name}")
                cGen(subscript_child)
                emit("sll  $t0, $v0, 2")
                emit("add  $t1, $t1, $t0")
                emit(f"lw   $v0, 0($t1)  # {name}[i]")
            else:
                emit(f"lw   $v0, {off}($fp)  # local {name}")

def _store_var(name, subscript_child=None):
    """Emite instrucciones para almacenar $t0 en una variable."""
    if name in _global_vars:
        label = _global_vars[name]
        if subscript_child is not None:
            cGen(subscript_child)
            emit("sll  $t1, $v0, 2")
            emit(f"la   $t2, {label}")
            emit("add  $t2, $t2, $t1")
            emit("sw   $t0, 0($t2)")
        else:
            emit(f"sw   $t0, {label}   # global {name}")
    else:
        off = _local_offset(name)
        if off is not None:
            if subscript_child is not None:
                emit(f"lw   $t2, {off}($fp)  # base arreglo {name}")
                cGen(subscript_child)
                emit("sll  $t1, $v0, 2")
                emit("add  $t2, $t2, $t1")
                emit("sw   $t0, 0($t2)")
            else:
                emit(f"sw   $t0, {off}($fp)  # local {name}")

def genExp(tree):
    if tree.kind == ExpKind.CONST:
        emit(f"li   $v0, {tree.attr}")

    elif tree.kind in (ExpKind.ID, ExpKind.VAR):
        name = tree.attr if isinstance(tree.attr, str) else tree.attr[0]
        sub  = tree.child[0] if isinstance(tree.attr, tuple) and tree.child else None
        _load_var(name, sub)

    elif tree.kind == ExpKind.ASSIGN:
        lhs  = tree.child[0]
        name = lhs.attr if isinstance(lhs.attr, str) else lhs.attr[0]
        sub  = lhs.child[0] if isinstance(lhs.attr, tuple) and lhs.child else None

        cGen(tree.child[1])              # rhs → $v0
        emit("move $t0, $v0")
        _store_var(name, sub)
        emit("move $v0, $t0")            # asignación retorna el valor

    elif tree.kind == ExpKind.OP:
        op = tree.attr
        # Evaluar izquierdo, empujar; evaluar derecho; operar
        cGen(tree.child[0])
        emit("subu $sp, $sp, 4")
        emit("sw   $v0, 0($sp)")         # push left
        cGen(tree.child[1])
        emit("lw   $t0, 0($sp)")         # pop left → $t0
        emit("addu $sp, $sp, 4")
        emit("move $t1, $v0")            # right → $t1

        if   op == '+': emit("add  $v0, $t0, $t1")
        elif op == '-': emit("sub  $v0, $t0, $t1")
        elif op == '*': emit("mul  $v0, $t0, $t1")
        elif op == '/':
            emit("div  $t0, $t1")
            emit("mflo $v0")
        elif op == '<':  emit("slt  $v0, $t0, $t1")
        elif op == '>':  emit("slt  $v0, $t1, $t0")
        elif op == '<=':
            emit("slt  $v0, $t1, $t0")
            emit("xori $v0, $v0, 1")
        elif op == '>=':
            emit("slt  $v0, $t0, $t1")
            emit("xori $v0, $v0, 1")
        elif op == '==': emit("seq  $v0, $t0, $t1")
        elif op == '!=': emit("sne  $v0, $t0, $t1")

    elif tree.kind == ExpKind.CALL:
        fname = tree.attr
        emitComment(f"-> call {fname}")

        if fname == 'input':
            emit("li   $v0, 5")
            emit("syscall               # read_int → $v0")

        elif fname == 'output':
            args_node = tree.child[0]
            if args_node.kind == "Arg List":
                cGen(args_node.child[0])
            emit("move $a0, $v0")
            emit("li   $v0, 1")
            emit("syscall               # print_int")
            emit("la   $a0, _newline")
            emit("li   $v0, 4")
            emit("syscall               # print newline")

        else:
            # Evaluar argumentos y empujarlos en stack temporalmente,
            # luego moverlos a $a0..$a3 para no sobreescribirlos durante evaluación
            args_node = tree.child[0]
            arg_list  = args_node.child if args_node.kind == "Arg List" else []

            # Evaluar cada argumento y empujar en stack (orden izquierda-derecha)
            for arg in arg_list:
                cGen(arg)
                emit("subu $sp, $sp, 4")
                emit("sw   $v0, 0($sp)")

            # Sacar del stack en orden inverso → $a_n...$a0
            n = len(arg_list)
            for i in range(n - 1, -1, -1):
                if i < 4:
                    emit(f"lw   $a{i}, 0($sp)")
                emit("addu $sp, $sp, 4")

            emit(f"jal  {fname}")

        emitComment(f"<- call {fname}")

# ---------------------------------------------------------------------------
# cGen — dispatcher recursivo
# ---------------------------------------------------------------------------

def cGen(tree):
    if tree is None:
        return
    if tree.nodekind == NodeKind.DECL:
        if tree.kind == DeclKind.FUN:
            genDecl(tree)
        elif tree.kind == "Program":
            for child in tree.child:
                cGen(child)
        # DeclKind.VAR global, params, local_decls → manejados por su padre
    elif tree.nodekind == NodeKind.STMT:
        genStmt(tree)
    elif tree.nodekind == NodeKind.EXP:
        genExp(tree)

# ---------------------------------------------------------------------------
# codeGen — función pública principal
# ---------------------------------------------------------------------------

def codeGen(syntaxTree, codefile, trace=False):
    global _out, TraceCode, _label_counter, _functions, _current_func, _global_vars
    TraceCode      = trace
    _label_counter = 0
    _functions     = {}
    _current_func  = None
    _global_vars   = {}

    _out = open(codefile, 'w')

    _collect_globals(syntaxTree)

    _out.write(f"# Código MIPS generado por cgen.py para C-\n")
    _out.write(f"# Archivo fuente compilado a: {codefile}\n\n")

    _emit_data_section(syntaxTree)

    _out.write(".text\n")
    _out.write(".globl main\n")
    emit("j    main")   # MARS/SPIM start at first instruction; jump to main
    emitBlank()

    for child in syntaxTree.child:
        cGen(child)

    _out.close()
