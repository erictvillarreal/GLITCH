"""V2 — mapa de variables de entorno por componente, desde el grafo de imports REAL (AST, sin ejecutar nada).
    cd glitch && python experimentos/parteF/env_map.py   -> imprime la tabla (variable -> archivos:linea) por punto de entrada."""
import ast, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENTRY = {"Scheduler MES/MGC-main (scheduler/geometry_scheduler.py)": "scheduler/geometry_scheduler.py",
         "Pi (pi/pi_executor.py)": "pi/pi_executor.py", "manual_signal (propuesto)": None,
         "Legacy GLITCH (scheduler/glitch_scheduler.py)": "scheduler/glitch_scheduler.py"}
def local(mod):
    for cand in (mod.replace(".", "/") + ".py", mod.replace(".", "/") + "/__init__.py"):
        if os.path.exists(os.path.join(ROOT, cand)): return cand
def walk(entry):
    seen, todo, envs = set(), [entry], {}
    while todo:
        f = todo.pop()
        if f in seen: continue
        seen.add(f)
        src = open(os.path.join(ROOT, f)).read()
        tree = ast.parse(src)
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                fn = ast.unparse(n.func) if hasattr(ast, "unparse") else ""
                if fn in ("os.getenv", "os.environ.get") and n.args and isinstance(n.args[0], ast.Constant):
                    envs.setdefault(n.args[0].value, []).append(f"{f}:{n.lineno}")
            if isinstance(n, ast.Subscript) and ast.unparse(n.value) == "os.environ" and isinstance(n.slice, ast.Constant):
                envs.setdefault(n.slice.value, []).append(f"{f}:{n.lineno}")
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.isupper() and ("_KEY" in n.value or "_TOKEN" in n.value or n.value.endswith("_ID")) and len(n.value) < 30:
                pass
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module] + [f"{n.module}.{a.name}" for a in n.names]
                for m in names:
                    p = local(m) if m else None
                    if p: todo.append(p)
    return seen, envs
for label, entry in ENTRY.items():
    if entry is None: continue
    files, envs = walk(entry)
    print(f"\n## {label}\nmodulos locales alcanzados: {sorted(files)}")
    for k in sorted(envs): print(f"  {k:28s} {', '.join(sorted(set(envs[k])))}")
