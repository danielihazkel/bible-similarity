"""Incremental `bsim all` (DESIGN.md §16.35): skip a stage whose code, config and inputs match.

A stage's fingerprint has four parts, recorded in `paths.pipeline_state` after it succeeds:
- **code**: the stage function, the module-level helpers it calls and every `bsim` module they
  import, transitively (read from the source files, nothing is imported);
- **config**: the keys the stage actually read, two levels deep (`structure.leitwort_skip_pos`),
  recorded by handing it a `TrackedConfig`;
- **inputs**: the content hash of every project file it opened (an audit hook sees `open`, so
  `pd.read_parquet`, `np.load` and JSON reads) plus every output of the stages it is declared to
  depend on (`pipeline.DEPS`, which also covers model folders, globs and optional files);
- **outputs**: the files that appeared or changed under the data, model and artifact folders while
  it ran.

A stage is up to date when its code and config hashes match, every input still has the recorded
content and every output is still on disk unchanged. Content hashes (cached by size and mtime) give
an early cut-off: a stage that reruns and writes the same bytes leaves its dependents skipped.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import fnmatch
import functools
import hashlib
import inspect
import json
import os
import sys
import textwrap
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from bsim.config import PROJECT_ROOT, resolve_path

STATE_VERSION = 1
WHOLE = "*"  # the whole config was read (iterated or dumped)
MISSING = "<missing>"


# --- config tracking -------------------------------------------------------------------------


class TrackedConfig(dict):
    """A dict that records which keys are read, `depth` levels deep, into a shared set.

    Reading `cfg["structure"]["leitwort_skip_pos"]` records `structure.leitwort_skip_pos`;
    iterating or dumping a level records that level whole (`structure`, or `*` at the top).
    Nested mappings are wrapped copies, so a stage that writes into its config writes into a copy.
    """

    def __init__(
        self, data: dict[str, Any], seen: set[str] | None = None, prefix: str = "", depth: int = 2
    ):
        super().__init__(data)
        self.seen: set[str] = set() if seen is None else seen
        self._prefix = prefix
        self._depth = depth
        self._wrapped: dict[Any, TrackedConfig] = {}

    def _name(self, key: Any) -> str:
        return f"{self._prefix}{key}"

    def _whole(self) -> None:
        self.seen.add(self._prefix[:-1] if self._prefix else WHOLE)

    def __getitem__(self, key: Any) -> Any:
        value = super().__getitem__(key)
        if self._depth > 1 and isinstance(value, dict):
            if key not in self._wrapped:
                self._wrapped[key] = TrackedConfig(
                    value, self.seen, f"{self._name(key)}.", self._depth - 1
                )
            return self._wrapped[key]
        self.seen.add(self._name(key))
        return value

    def get(self, key: Any, default: Any = None) -> Any:
        if dict.__contains__(self, key):
            return self[key]
        self.seen.add(self._name(key))
        return default

    def __contains__(self, key: object) -> bool:
        self.seen.add(self._name(key))
        return super().__contains__(key)

    def __iter__(self) -> Iterator[Any]:
        self._whole()
        return super().__iter__()

    def keys(self) -> Any:  # type: ignore[override]
        self._whole()
        return super().keys()

    def items(self) -> Any:  # type: ignore[override]
        self._whole()
        return super().items()

    def values(self) -> Any:  # type: ignore[override]
        self._whole()
        return super().values()

    def copy(self) -> dict[str, Any]:
        self._whole()
        return dict(super().items())

    def __deepcopy__(self, memo: dict[int, Any]) -> TrackedConfig:
        """A deep copy that keeps recording into the same set (`with_overrides` copies)."""
        data = {k: copy.deepcopy(dict.__getitem__(self, k), memo) for k in dict.keys(self)}
        return TrackedConfig(data, self.seen, self._prefix, self._depth)


def config_value(cfg: dict[str, Any], key: str) -> Any:
    """The value at a dotted key (`*` = the whole config); `MISSING` when absent."""
    if key == WHOLE:
        return cfg
    cur: Any = cfg
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return MISSING
        cur = cur[part]
    return cur


def value_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def minimal_keys(keys: Iterable[str]) -> list[str]:
    """Drop keys covered by a shorter one (`structure` covers `structure.x`; `*` covers all)."""
    keys = set(keys)
    if WHOLE in keys:
        return [WHOLE]
    return sorted(k for k in keys if not any(k.startswith(o + ".") for o in keys if o != k))


# --- code hashing ----------------------------------------------------------------------------

PACKAGE = "bsim"
PACKAGE_ROOT = Path(__file__).resolve().parent


def _module_file(name: str, root: Path, package: str) -> tuple[Path, bool] | None:
    """(file, is_package) of a module of `package` rooted at `root`, without importing it."""
    parts = name.split(".")[1:] if name != package else []
    base = root.joinpath(*parts)
    if (base / "__init__.py").is_file():
        return base / "__init__.py", True
    if base.with_suffix(".py").is_file() and parts:
        return base.with_suffix(".py"), False
    return None


def _imports(tree: ast.AST, module: str, is_pkg: bool, package: str) -> set[str]:
    """Modules of `package` named by the import statements anywhere in `tree` (with parents)."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = module if is_pkg else module.rpartition(".")[0]
                for _ in range(node.level - 1):
                    base = base.rpartition(".")[0]
                mod = f"{base}.{node.module}" if node.module else base
            else:
                mod = node.module or ""
            found.add(mod)
            found.update(f"{mod}.{a.name}" for a in node.names)  # `from bsim.x import y` (module y)
    out: set[str] = set()
    for name in found:
        if name == package or name.startswith(package + "."):
            parts = name.split(".")
            out.update(".".join(parts[:i]) for i in range(1, len(parts) + 1))
    return out


@functools.cache
def _module_deps(name: str, root: Path, package: str) -> frozenset[str]:
    found = _module_file(name, root, package)
    if found is None:
        return frozenset()
    path, is_pkg = found
    return frozenset(_imports(ast.parse(path.read_bytes()), name, is_pkg, package))


def module_closure(
    start: Iterable[str], root: Path = PACKAGE_ROOT, package: str = PACKAGE
) -> list[str]:
    """Every module of `package` reachable from `start` through import statements, sorted."""
    seen: set[str] = set()
    todo = [m for m in start if _module_file(m, root, package)]
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        todo.extend(m for m in _module_deps(name, root, package) if _module_file(m, root, package))
    return sorted(seen)


def _source(fn: Callable[..., Any]) -> str:
    try:
        return textwrap.dedent(inspect.getsource(fn))
    except (OSError, TypeError):
        return getattr(fn, "__qualname__", repr(fn))


def code_hash(fn: Callable[..., Any], root: Path = PACKAGE_ROOT, package: str = PACKAGE) -> str:
    """Hash of a stage function, the same-module helpers it calls and the modules they import."""
    module = getattr(fn, "__module__", "") or ""
    fns = [fn]
    glob = getattr(fn, "__globals__", {})
    for name in getattr(getattr(fn, "__code__", None), "co_names", ()):
        obj = glob.get(name)
        if inspect.isfunction(obj) and obj.__module__ == module and obj is not fn:
            fns.append(obj)
    start: set[str] = set()
    h = hashlib.sha256()
    for f in fns:
        src = _source(f)
        h.update(src.encode("utf-8"))
        with contextlib.suppress(SyntaxError):  # a lambda cut out of a longer line
            start |= _imports(ast.parse(src), module, False, package)
    for name in module_closure(start, root, package):
        found = _module_file(name, root, package)
        if found:
            h.update(name.encode("utf-8"))
            h.update(found[0].read_bytes())
    return h.hexdigest()[:16]


def config_literals(fn: Callable[..., Any], cfg: dict[str, Any]) -> list[str]:
    """Top-level config sections named by a string literal in the stage's code (an over-estimate
    of what it reads, for stages adopted without running)."""
    module = getattr(fn, "__module__", "") or ""
    src = _source(fn)
    try:
        start = _imports(ast.parse(src), module, False, PACKAGE)
    except SyntaxError:
        start = set()
    texts = [src]
    for name in module_closure(start):
        found = _module_file(name, PACKAGE_ROOT, PACKAGE)
        if found:
            texts.append(found[0].read_text("utf-8"))
    literals: set[str] = set()
    for text in texts:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        literals.update(
            n.value
            for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        )
    return sorted(k for k in cfg if k in literals)


# --- files -----------------------------------------------------------------------------------


def file_key(path: str | Path) -> str:
    """A project-relative POSIX path (absolute outside the project; lower case on Windows)."""
    p = Path(os.path.abspath(path))
    try:
        key = p.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        key = p.as_posix()
    return key.lower() if os.name == "nt" else key  # one key per file on a case-blind disk


def key_path(key: str) -> Path:
    p = Path(key)
    return p if p.is_absolute() else PROJECT_ROOT / p


class Files:
    """Content hashes of files, cached by (size, mtime_ns)."""

    def __init__(self, cache: dict[str, list[Any]] | None = None):
        self.cache: dict[str, list[Any]] = cache or {}

    def sha(self, key: str) -> str | None:
        try:
            st = key_path(key).stat()
        except OSError:
            return None
        hit = self.cache.get(key)
        if hit and hit[0] == st.st_size and hit[1] == st.st_mtime_ns:
            return hit[2]
        with key_path(key).open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()[:20]
        self.cache[key] = [st.st_size, st.st_mtime_ns, digest]
        return digest


class Scope:
    """The folders a stage may read from and write to, and the files never tracked."""

    def __init__(self, roots: Iterable[Path], ignore: Iterable[str]):
        self.roots = sorted({os.path.abspath(r) for r in roots})
        self._norm = [os.path.normcase(r) for r in self.roots]
        self.ignore = list(ignore)

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> Scope:
        roots = [resolve_path(cfg, k) for k in cfg["pipeline"]["roots"]]
        ignore = [*cfg["pipeline"]["ignore"]]
        ignore += [file_key(resolve_path(cfg, k)) for k in ("pipeline_state", "labels")]
        return cls(roots, ignore)

    def inside(self, abspath: str) -> bool:
        p = os.path.normcase(abspath)
        return any(p == r or p.startswith(r + os.sep) for r in self._norm)

    def ignored(self, key: str) -> bool:
        return any(fnmatch.fnmatch(key, pat) for pat in self.ignore)

    def snapshot(self) -> dict[str, tuple[int, int]]:
        """(size, mtime_ns) of every tracked file under the roots."""
        out: dict[str, tuple[int, int]] = {}
        seen_roots: list[str] = []
        for root, norm in zip(self.roots, self._norm, strict=True):
            if any(norm.startswith(s + os.sep) for s in seen_roots) or not os.path.isdir(root):
                continue
            seen_roots.append(norm)
            for dirpath, _, names in os.walk(root):
                for n in names:
                    full = os.path.join(dirpath, n)
                    key = file_key(full)
                    if self.ignored(key):
                        continue
                    try:
                        st = os.stat(full)
                    except OSError:
                        continue
                    out[key] = (st.st_size, st.st_mtime_ns)
        return out


_reading: list[set[str]] = []  # the read set of the running stage (a stack of one)
_hooked: list[Scope] = []


def _audit(event: str, args: tuple[Any, ...]) -> None:
    if not _reading or event not in ("open", "sqlite3.connect"):
        return
    target = args[0] if args else None
    if isinstance(target, int) or target is None:
        return
    if event == "open":
        mode, flags = (args[1], args[2]) if len(args) > 2 else (None, 0)
        if isinstance(mode, str):
            if any(c in mode for c in "wax"):
                return
        elif isinstance(flags, int) and flags & (os.O_WRONLY | os.O_CREAT):
            return
    try:
        path = os.path.abspath(os.fsdecode(target))
    except (TypeError, ValueError):
        return
    if _hooked and _hooked[0].inside(path):
        _reading[-1].add(path)


@contextmanager
def tracking_reads(scope: Scope) -> Iterator[set[str]]:
    """Collect the files under the scope's roots opened for reading inside the block."""
    if not _hooked:
        sys.addaudithook(_audit)
        _hooked.append(scope)
    _hooked[0] = scope
    reads: set[str] = set()
    _reading.append(reads)
    try:
        yield reads
    finally:
        _reading.pop()


# --- state -----------------------------------------------------------------------------------


class State:
    """`paths.pipeline_state`: per stage its code, config, inputs and outputs; the hash cache."""

    def __init__(self, path: Path):
        self.path = path
        data: dict[str, Any] = {}
        if path.exists():
            try:
                data = json.loads(path.read_text("utf-8"))
            except (OSError, ValueError):
                data = {}
        if data.get("version") != STATE_VERSION:
            data = {}
        self.stages: dict[str, dict[str, Any]] = data.get("stages", {})
        self.files = Files(data.get("files", {}))

    def save(self) -> None:
        live = {k for e in self.stages.values() for part in ("inputs", "outputs") for k in e[part]}
        files = {k: v for k, v in self.files.cache.items() if k in live}
        payload = {"version": STATE_VERSION, "stages": self.stages, "files": files}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=1, sort_keys=True), "utf-8")
        os.replace(tmp, self.path)

    def outputs_of(self, stages: Iterable[str]) -> set[str]:
        return {k for s in stages for k in self.stages.get(s, {}).get("outputs", {})}

    def owner(self, key: str) -> str | None:
        for name, entry in self.stages.items():
            if key in entry.get("outputs", {}):
                return name
        return None


def stale_reason(
    name: str, fn: Callable[..., Any], cfg: dict[str, Any], state: State, deps: Iterable[str]
) -> str | None:
    """Why the stage must run, or None when it is up to date."""
    entry = state.stages.get(name)
    if entry is None:
        return "never run"
    if entry["code"] != code_hash(fn):
        return "code changed"
    for key, h in sorted(entry["config"].items()):
        if value_hash(config_value(cfg, key)) != h:
            return f"config {key} changed"
    for key, h in sorted(entry["inputs"].items()):
        if state.files.sha(key) != h:
            return f"input {key} changed" if key_path(key).exists() else f"input {key} missing"
    new = sorted(state.outputs_of(deps) - set(entry["inputs"]) - set(entry["outputs"]))
    if new:
        return f"new input {new[0]}" + (f" (+{len(new) - 1})" if len(new) > 1 else "")
    for key, h in sorted(entry["outputs"].items()):
        if state.files.sha(key) != h:
            return f"output {key} changed" if key_path(key).exists() else f"output {key} missing"
    return None


def record(
    name: str,
    fn: Callable[..., Any],
    cfg: dict[str, Any],
    state: State,
    *,
    order: list[str],
    deps: Iterable[str],
    seen: set[str],
    reads: set[str],
    before: dict[str, tuple[int, int]],
    after: dict[str, tuple[int, int]],
    seconds: float,
    log: Callable[[str], None],
) -> None:
    """Store a finished stage's fingerprint; warn about inputs from undeclared stages."""
    deps = list(deps)
    old = state.stages.get(name, {}).get("outputs", {})
    changed = {k for k, v in after.items() if before.get(k) != v}
    outputs = changed | {k for k in old if k in after}
    for other, entry in state.stages.items():  # a file belongs to the stage that wrote it last
        if other != name:
            for k in outputs & set(entry.get("outputs", {})):
                del entry["outputs"][k]
    later = state.outputs_of(order[order.index(name) + 1 :]) if name in order else set()
    read_keys = {file_key(p) for p in reads} - outputs
    for k in sorted(read_keys):
        owner = state.owner(k)
        if owner and owner != name and owner not in deps and owner not in later:
            log(f"note: {name} read {k}, written by {owner}, which DEPS does not list")
    inputs = (read_keys | state.outputs_of(deps)) - outputs - later
    state.stages[name] = {
        "code": code_hash(fn),
        "config": {k: value_hash(config_value(cfg, k)) for k in minimal_keys(seen)},
        "inputs": {k: h for k in sorted(inputs) if (h := state.files.sha(k)) is not None},
        "outputs": {k: h for k in sorted(outputs) if (h := state.files.sha(k)) is not None},
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seconds": round(seconds, 2),
    }


def adopt(name: str, fn: Callable[..., Any], cfg: dict[str, Any], state: State) -> None:
    """Mark a stage up to date without running it: its outputs are trusted as they are.

    Its config is every section its code names (it has not run, so the keys it reads are not
    known); inputs and outputs are empty, so the first rerun of a stage it depends on reruns it.
    """
    state.stages[name] = {
        "code": code_hash(fn),
        "config": {k: value_hash(cfg[k]) for k in config_literals(fn, cfg)},
        "inputs": {},
        "outputs": {},
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "seconds": 0.0,
        "adopted": True,
    }
