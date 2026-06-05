# symtab.py — Tabla de símbolos con scopes para C-
# Cada scope es un dict: name -> {'type': ..., 'kind': ..., 'loc': ..., 'lines': [...]}
# Los scopes se apilan; el global es el primero.
# _all_entries guarda todas las entradas para impresión final.

_scopes = [{}]   # pila de scopes; _scopes[0] = global
_location = 0    # contador de ubicaciones de memoria
_all_entries = []  # registro plano para impresión: (name, scope_depth, info)

def reset():
    global _scopes, _location, _all_entries
    _scopes = [{}]
    _location = 0
    _all_entries = []

def scope_enter():
    _scopes.append({})

def scope_exit():
    if len(_scopes) > 1:
        _scopes.pop()

_AUTO = object()  # sentinel: auto-assign location

def st_insert(name, lineno, var_type, kind, loc=_AUTO):
    """Inserta o actualiza una entrada en el scope actual."""
    global _location
    scope = _scopes[-1]
    if name in scope:
        scope[name]['lines'].append(lineno)
        for entry in _all_entries:
            if entry[0] == name and entry[1] == len(_scopes) - 1 and entry[2] is scope[name]:
                break
    else:
        if loc is _AUTO:
            loc = _location
            _location += 1
        info = {'type': var_type, 'kind': kind, 'loc': loc, 'lines': [lineno]}
        scope[name] = info
        _all_entries.append((name, len(_scopes) - 1, info))

def st_lookup(name):
    """Busca name en todos los scopes (del más interno al global).
    Retorna el dict de la entrada o None si no existe."""
    for scope in reversed(_scopes):
        if name in scope:
            return scope[name]
    return None

def st_lookup_current(name):
    """Busca solo en el scope actual (para detectar redeclaraciones)."""
    return _scopes[-1].get(name, None)

def printSymTab():
    print(f"{'Nombre':<16} {'Tipo':<8} {'Clase':<8} {'Scope':>5} {'Loc':>4}  Líneas")
    print("-" * 60)
    for name, depth, info in _all_entries:
        lines_str = " ".join(str(l) for l in info['lines'] if l != 0)
        scope_label = "global" if depth == 0 else f"  {depth}"
        loc_str = "-" if info['loc'] is None else str(info['loc'])
        print(f"{name:<16} {str(info['type']):<8} {str(info['kind']):<8} {scope_label:>6} {loc_str:>4}  {lines_str}")
