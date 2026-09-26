import ast
import os
import subprocess
import sys
import tempfile
from collections import deque

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OS_DIR = os.path.join(ROOT, "os")
APPS_DIR = os.path.join(OS_DIR, "apps")
FRAMEWORK_METHODS = {"layout", "draw", "key", "tick", "pause", "resume", "focus", "paint", "step"}


def python_files():
    for folder, _, files in os.walk(OS_DIR):
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(folder, name)


def view_members():
    tree = ast.parse(open(os.path.join(OS_DIR, "system", "ui.py")).read())
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "View":
            return {item.name for item in node.body if isinstance(item, ast.FunctionDef)} - {"__init__"}
    return set()


def check_syntax(problems):
    for path in python_files():
        try:
            compile(open(path).read(), path, "exec")
        except SyntaxError as error:
            problems.append("syntax: {}:{}: {}".format(path, error.lineno, error.msg))


def check_shadowing(problems):
    reserved = view_members() - FRAMEWORK_METHODS
    for name in sorted(os.listdir(APPS_DIR)):
        if not name.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(APPS_DIR, name)).read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name in reserved:
                    problems.append("shadowing: {} {}.{}() hides ui.View.{}".format(name, node.name, item.name, item.name))
                if isinstance(item, ast.FunctionDef):
                    for sub in ast.walk(item):
                        if (isinstance(sub, ast.Attribute) and isinstance(sub.ctx, ast.Store)
                                and isinstance(sub.value, ast.Name) and sub.value.id == "self" and sub.attr in reserved):
                            problems.append("shadowing: {} {} assigns self.{}".format(name, node.name, sub.attr))
                if isinstance(item, ast.FunctionDef) and any(
                        isinstance(d, ast.Name) and d.id == "property" for d in item.decorator_list) and item.name in reserved:
                    problems.append("shadowing: {} {}.{} property".format(name, node.name, item.name))


def icon_table():
    source = open(os.path.join(OS_DIR, "system", "icondata.py")).read()
    return ast.literal_eval(source.split("=", 1)[1])


def icon_exists(table, icon):
    if ":" in icon:
        category, name = icon.split(":", 1)
        return name in table.get(category, {})
    return any(icon in names for names in table.values())


def check_icons(problems):
    table = icon_table()
    targets = [os.path.join(APPS_DIR, n) for n in os.listdir(APPS_DIR) if n.endswith(".py")]
    targets.append(os.path.join(OS_DIR, "system", "shell.py"))
    for path in targets:
        tree = ast.parse(open(path).read())
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            names = [getattr(t, "id", None) for t in node.targets]
            if "ICON" in names:
                icons = [ast.literal_eval(node.value)]
            elif any(n and n.endswith("ICONS") for n in names):
                icons = list(ast.literal_eval(node.value).values())
            else:
                continue
            for icon in icons:
                if not icon_exists(table, icon):
                    problems.append("icon: {} uses missing icon {}".format(os.path.basename(path), icon))


def solve_crates(level):
    rows = level.strip("\n").split("\n")
    walls, goals, boxes, player = set(), set(), set(), None
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char == "#":
                walls.add((x, y))
            if char in ".*+":
                goals.add((x, y))
            if char in "$*":
                boxes.add((x, y))
            if char in "@+":
                player = (x, y)
    if len(goals) != len(boxes) or player is None:
        return None
    floor = {(x, y) for y, row in enumerate(rows) for x, char in enumerate(row) if char != "#"}
    dead = {(x, y) for x, y in floor if (x, y) not in goals
            and ((x - 1, y) in walls or (x + 1, y) in walls) and ((x, y - 1) in walls or (x, y + 1) in walls)}
    start = (player, frozenset(boxes))
    seen = {start}
    queue = deque([(player, frozenset(boxes), 0)])
    while queue:
        position, crates, pushes = queue.popleft()
        if crates == goals:
            return pushes
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            step = (position[0] + dx, position[1] + dy)
            if step in walls:
                continue
            moved = crates
            pushed = 0
            if step in crates:
                beyond = (step[0] + dx, step[1] + dy)
                if beyond in walls or beyond in crates or beyond in dead:
                    continue
                moved = (crates - {step}) | {beyond}
                pushed = 1
            state = (step, moved)
            if state not in seen:
                seen.add(state)
                queue.append((step, moved, pushes + pushed))
    return None


def check_crates(problems):
    tree = ast.parse(open(os.path.join(APPS_DIR, "crates.py")).read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "LEVELS" for t in node.targets):
            for index, level in enumerate(ast.literal_eval(node.value)):
                if solve_crates(level) is None:
                    problems.append("crates: level {} is unsolvable".format(index + 1))


def check_smoke(problems, binary):
    apps = sorted(n[:-3] for n in os.listdir(APPS_DIR) if n.endswith(".py") and not n.startswith("_"))
    with tempfile.TemporaryDirectory() as data:
        for app in apps:
            result = subprocess.run(
                [binary, "--no-watch", "--root=" + os.path.join(ROOT, "os"), "--data=" + data, "--exec=shell.launch({!r}); ui.invalidate()".format(app),
                 "--screenshot=" + os.path.join(data, "shot.bmp"), "--frames=20"],
                capture_output=True, text=True, timeout=60)
            output = result.stdout + result.stderr
            if "Traceback" in output or "stopped" in output or result.returncode != 0:
                problems.append("smoke: {} failed to launch\n{}".format(app, output.strip()))


def main():
    problems = []
    check_syntax(problems)
    check_shadowing(problems)
    check_icons(problems)
    check_crates(problems)
    if "--smoke" in sys.argv:
        check_smoke(problems, os.path.join(ROOT, "pocket"))
    for problem in problems:
        print(problem)
    print("{} problem(s)".format(len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
