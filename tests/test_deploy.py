"""The public read-only server (DESIGN.md §10.3, docs/DEPLOY.md): config profiles, the bundle of
`bsim deploy-bundle`, and the server over it with nothing personal and no query encoder."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bsim.api.app import create_app
from bsim.config import PROJECT_ROOT, load_config, merge
from bsim.deploy import noncommercial, run_deploy_bundle


def test_config_extends(tmp_path):
    (tmp_path / "base.yaml").write_text("a: {x: 1, y: 2}\nb: [1, 2]\nc: keep\n", encoding="utf-8")
    (tmp_path / "over.yaml").write_text("extends: base.yaml\na: {y: 3}\nb: [9]\n", "utf-8")
    assert load_config(tmp_path / "over.yaml") == {"a": {"x": 1, "y": 3}, "b": [9], "c": "keep"}


def test_public_profile():
    cfg, default = load_config(PROJECT_ROOT / "configs" / "public.yaml"), load_config()
    s = cfg["serve"]
    assert (s["personal"], s["encoder"], s["labels_writable"], s["cors_origins"]) == (
        False, False, False, [],
    )  # fmt: skip
    assert s["max_page"] == default["serve"]["max_page"]  # the rest as in default.yaml
    assert cfg["paths"]["db"].startswith(default["deploy"]["out"] + "/")
    assert cfg["labels"]["queue"]["preload"] is False
    docker = load_config(PROJECT_ROOT / "configs" / "docker.yaml")  # the image's: public + a cache
    assert docker["serve"]["personal"] is False and docker["serve"]["cache_dir"] == "/app/cache"


def public(cfg, bundle: Path, **serve):
    """The fixture's config served as configs/public.yaml serves a bundle."""
    prof = load_config(PROJECT_ROOT / "configs" / "public.yaml")
    out = merge(cfg, {"serve": {**prof["serve"], **serve}, "labels": prof["labels"]})
    art = bundle / "artifacts"
    out["paths"] = {**cfg["paths"], "artifacts": str(art), "db": str(art / "results.sqlite"),
                    "labels": str(bundle / "labels.sqlite")}  # fmt: skip
    return out


@pytest.fixture
def bundle(built, tmp_path):
    cfg, _ = built
    labels = Path(cfg["paths"]["labels"])
    labels.write_bytes(b"private")  # never copied
    out = tmp_path / "bundle"
    manifest = run_deploy_bundle(cfg, out, no_nc=True, log=lambda _: None)
    return cfg, out, manifest


def test_bundle(bundle):
    cfg, out, manifest = bundle
    on_disk = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    assert on_disk == {*manifest["files"], "bundle.json"}
    assert "artifacts/results.sqlite" in on_disk and not (out / "labels.sqlite").exists()
    assert not any(p.startswith("artifacts/llm") for p in on_disk)
    stages, tables, files = noncommercial(cfg)
    assert manifest["stages_removed"] == stages
    assert set(manifest["emptied_tables"]) <= set(tables)
    assert {"witnesses_verses", "clauses"} <= set(manifest["emptied_tables"])
    assert not set(files) & {Path(p).name for p in on_disk}
    assert json.loads((out / "bundle.json").read_text("utf-8"))["noncommercial_removed"] is True
    with pytest.raises(RuntimeError, match="not empty"):
        run_deploy_bundle(cfg, out, log=lambda _: None)


def test_public_server(bundle):
    cfg, out, _ = bundle
    client = TestClient(create_app(public(cfg, out), log=lambda _: None))
    for path in ["/api/labels", "/api/notebook", "/api/labels/queue"]:
        r = client.get(path)
        assert r.status_code == 404 and r.json()["detail"]["code"] == "personal_off", path
    assert client.put("/api/labels", json={}).status_code in (404, 422)
    rt = client.get("/api/meta").json()["runtime"]
    assert (rt["personal"], rt["encoder_on"], rt["encoder_ready"]) == (False, False, False)
    assert rt["encoder_error"] == "semantic search is off on this server"
    assert client.get("/api/search?q=דגן&mode=lexical").status_code == 200
    for mode in ("semantic", "fused"):
        r = client.get(f"/api/search?q=דגן&mode={mode}")
        assert r.status_code == 503 and "off on this server" in r.json()["detail"], mode
    assert client.get("/api/align?a=0&b=5").status_code == 503
    # the non-commercial analyses, as stages that did not run
    r = client.get("/api/witnesses")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "stage_missing"
    # the rest answers: the pages that read many tables, and the verse vectors
    for path in ["/api/findings", "/api/dossier/v:0", "/api/compare?a=c:0:1&b=c:1:1",
                 "/api/structure/c:0:1", "/api/eval", "/api/books"]:  # fmt: skip
        assert client.get(path).status_code == 200, path
    assert client.get("/api/eval").json()["etcbc"] is None


def test_public_server_without_vectors(built, tmp_path):
    cfg, _ = built
    out = tmp_path / "bundle"
    manifest = run_deploy_bundle(cfg, out, embeddings=False, log=lambda _: None)
    assert not any(p.endswith(".npy") for p in manifest["files"])
    client = TestClient(create_app(public(cfg, out, embeddings=False), log=lambda _: None))
    assert client.get("/api/compare?a=c:0:1&b=c:1:1").status_code == 503
    s = client.get("/api/structure/c:0:1").json()
    assert s["semantic"] is None and s["lexical"]["matrix"]
    rows = client.get("/api/sequences/1").json()["rows"]
    assert rows and all(r["cosine"] is None for r in rows)
    with pytest.raises(RuntimeError, match="needs serve.embeddings"):
        create_app(public(cfg, out, embeddings=False, encoder=True), log=lambda _: None)


def test_public_server_never_imports_torch(bundle):
    """The premise of the public image (DEPLOY.md): no ML libraries installed."""
    cfg, out, _ = bundle
    cfg_file = out.parent / "public.json"
    cfg_file.write_text(json.dumps(public(cfg, out)), encoding="utf-8")
    code = f"""
import json, sys
from pathlib import Path
from fastapi.testclient import TestClient
from bsim.api.app import create_app
cfg = json.loads(Path({str(cfg_file)!r}).read_text(encoding="utf-8"))
client = TestClient(create_app(cfg, log=lambda _: None))
assert client.get("/api/search?q=דגן&mode=lexical").status_code == 200
assert client.get("/api/compare?a=c:0:1&b=c:1:1").status_code == 200
assert client.get("/api/findings").status_code == 200
heavy = sorted(m for m in ("torch", "transformers", "sentence_transformers") if m in sys.modules)
print(json.dumps(heavy))
"""
    run = [sys.executable, "-c", code]
    r = subprocess.run(run, capture_output=True, encoding="utf-8", cwd=PROJECT_ROOT)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout.strip().splitlines()[-1]) == []
