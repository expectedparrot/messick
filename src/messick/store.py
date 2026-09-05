"""Immutable artifacts and append-only project metadata."""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .errors import MessickError

VISIBLE_DIRS = ("instruments", "edsl_jobs", "data/results", "data/human", "analysis")
PRIVATE_DIRS = ("events", "instruments", "intents", "sources", "runs", "issues", "decisions", "scales", "analyses", "comparisons", "validations", "reports", "cache")

def now(): return datetime.now(timezone.utc).isoformat()
def digest(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.hidden = self.root / ".messick"
        self.project_file = self.hidden / "project.json"

    @property
    def exists(self): return self.project_file.is_file()

    def config_snapshot(self):
        path=self.root/"messick.yaml"
        if not path.exists(): return {"path":None,"sha256":None,"content":{}}
        raw=path.read_bytes()
        try:
            import yaml
            content=yaml.safe_load(raw) or {}
        except Exception as exc: raise MessickError("INVALID_CONFIG","messick.yaml could not be parsed.",detail=str(exc)) from exc
        return {"path":"messick.yaml","sha256":hashlib.sha256(raw).hexdigest(),"content":content}

    def init(self, title: str):
        if self.exists:
            raise MessickError("PROJECT_EXISTS", "A Messick project already exists.", project_root=str(self.root))
        for name in VISIBLE_DIRS: (self.root / name).mkdir(parents=True, exist_ok=True)
        for name in PRIVATE_DIRS: (self.hidden / name).mkdir(parents=True, exist_ok=True)
        state = {"schema_version": 1, "project_id": str(uuid4()), "title": title, "created_at": now(), "revision": 0, "current_instrument_revision": None}
        self._write(state)
        (self.root / "messick.yaml").write_text(f"schema_version: 1\nproject:\n  title: {json.dumps(title)}\nanalysis:\n  burden:\n    words_per_minute: 200\n    uncertainty_fraction: 0.25\n", encoding="utf-8")
        self.event("project.initialized", {"title": title})
        return self.load()

    def require(self):
        if not self.exists:
            raise MessickError("PROJECT_NOT_FOUND", "No Messick project was found.", "Run `messick init --title ...`.", project_root=str(self.root))

    def load(self):
        self.require()
        return json.loads(self.project_file.read_text(encoding="utf-8"))

    def _write(self, state):
        self.hidden.mkdir(parents=True, exist_ok=True)
        temp = self.project_file.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(self.project_file)

    def event(self, kind, data):
        event = {"event_id": str(uuid4()), "type": kind, "timestamp": now(), "data": data}
        path = self.hidden / "events" / f"{event['timestamp'].replace(':','-')}_{event['event_id']}.json"
        path.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return event

    def mutate(self, kind, data, expected_revision=None):
        state = self.load()
        if expected_revision is not None and state["revision"] != expected_revision:
            raise MessickError("REVISION_CONFLICT", "Project revision has changed.", expected=expected_revision, actual=state["revision"])
        state["revision"] += 1
        state.update(data)
        self._write(state); self.event(kind, data)
        return state

    def import_instrument(self, source: Path, message="", expected_revision=None):
        self.require(); source = source.resolve()
        if expected_revision is not None and self.load()["revision"] != expected_revision:
            raise MessickError("REVISION_CONFLICT","Project revision has changed.",expected=expected_revision,actual=self.load()["revision"])
        if not source.is_file(): raise MessickError("ARTIFACT_NOT_FOUND", "Survey artifact does not exist.", path=str(source))
        sha = digest(source)
        existing = self.records("instruments")
        for record in existing:
            if record["sha256"] == sha:
                return record, False
        number = len(existing) + 1; revision_id = f"v{number:03d}"
        target = self.root / "instruments" / f"instrument_{revision_id}.ep"
        # A revision builder may write directly to the package's next canonical
        # path. Register that artifact in place instead of asking shutil to copy
        # a file onto itself (which raises SameFileError).
        if source != target.resolve():
            shutil.copyfile(source, target)
        question_ids=[]; question_hashes={}; branching_graph_hash=None
        try:
            from .artifacts import survey
            normalized=survey(target); question_ids=[q["id"] for q in normalized["questions"]]
            question_hashes={q["id"]:hashlib.sha256(json.dumps({"text":q["text"],"type":q["type"],"options":q["options"]},sort_keys=True).encode()).hexdigest() for q in normalized["questions"] if q["id"]}
            branching_graph_hash=hashlib.sha256(json.dumps(normalized["rules"],sort_keys=True).encode()).hexdigest()
        except MessickError:
            pass
        parent_revision=self.load()["current_instrument_revision"]
        parent_issue_ids={x["issue_id"] for x in self.records("issues") if x.get("instrument_revision")==parent_revision}
        decision_ids=[x["decision_id"] for x in self.records("decisions") if x.get("issue_id") in parent_issue_ids and x.get("action") in ("revise","remove","rescore","reorder")]
        record = {"instrument_id": self.load().get("instrument_id") or str(uuid4()), "revision_id": revision_id, "parent_revision": parent_revision, "decision_ids":decision_ids,"artifact": str(target.relative_to(self.root)), "sha256": sha, "ordered_question_ids":question_ids,"question_hashes":question_hashes,"branching_graph_hash":branching_graph_hash,"message": message, "created_at": now(), "status": "draft"}
        self.put_record("instruments", revision_id, record)
        self.mutate("instrument.imported", {"instrument_id": record["instrument_id"], "current_instrument_revision": revision_id})
        return record, True

    def put_record(self, collection, record_id, value):
        path = self.hidden / collection / f"{record_id}.json"
        if path.exists(): raise MessickError("IMMUTABLE_RECORD", "Record already exists.", record_id=record_id)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def records(self, collection):
        folder = self.hidden / collection
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))] if folder.exists() else []

    def record(self, collection, record_id, id_field=None):
        id_field = id_field or f"{collection.rstrip('s')}_id"
        found = next((r for r in self.records(collection) if r.get(id_field) == record_id), None)
        if found is None:
            raise MessickError("RECORD_NOT_FOUND", "Record was not found.", collection=collection, record_id=record_id)
        return found

    def next_id(self, prefix, collection):
        return f"{prefix}_{len(self.records(collection)) + 1:04d}"

    def copy_artifact(self, source: Path, folder: str, filename: str):
        source = source.resolve()
        if not source.is_file():
            raise MessickError("ARTIFACT_NOT_FOUND", "Artifact does not exist.", path=str(source))
        sha = digest(source)
        target = self.root / folder / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and digest(target) != sha:
            raise MessickError("IMMUTABLE_ARTIFACT", "An artifact already occupies the target path.", path=str(target))
        if not target.exists(): shutil.copyfile(source, target)
        return target, sha

    def add_from_json(self, collection, source: Path, id_field: str):
        try: value = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise MessickError("INVALID_INPUT", f"Cannot read JSON input: {exc}", path=str(source)) from exc
        record_id = value.get(id_field)
        if not record_id: raise MessickError("INVALID_INPUT", f"Required field `{id_field}` is missing.")
        required={"intents":("construct","interpretation","population","use","evidence_tier"),"scales":("items",),"issues":("category","severity","description")}.get(collection,())
        missing=[key for key in required if key not in value]
        if missing: raise MessickError("INVALID_INPUT","Required fields are missing.",fields=missing,collection=collection)
        if collection=="intents" and value.get("evidence_tier") not in ("static","simulation","human"):
            raise MessickError("INVALID_INPUT","Evidence tier must be static, simulation, or human.",evidence_tier=value.get("evidence_tier"))
        if collection=="scales" and (not isinstance(value.get("items"),list) or len(value["items"])<2):
            raise MessickError("INVALID_INPUT","A scale requires at least two item IDs.")
        value.update({"created_at": now()})
        self.put_record(collection, record_id, value); self.mutate(f"{collection}.added", {})
        return value
