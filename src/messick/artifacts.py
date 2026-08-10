"""Portable artifact readers using JSON first and optional public EDSL APIs."""
from __future__ import annotations
import contextlib,csv, gzip, json,sys,zipfile
from pathlib import Path
from .errors import MessickError

def read_json(path: Path):
    try:
        with path.open("rb") as probe: compressed = probe.read(2) == b"\x1f\x8b"
        opener = gzip.open if compressed or path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as handle: return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MessickError("UNSUPPORTED_ARTIFACT", "Artifact is not readable JSON.", "Use a portable JSON/CSV artifact or install the matching EDSL version.", path=str(path), detail=str(exc)) from exc

def survey(path: Path):
    if zipfile.is_zipfile(path):
        try:
            with contextlib.redirect_stdout(sys.stderr):
                from edsl import Survey
                raw=Survey.git.load(str(path)).to_dict()
        except ImportError as exc: raise MessickError("EDSL_UNAVAILABLE","EDSL is required to load Survey.ep.","Install `messick[edsl]`.") from exc
        except Exception as exc: raise MessickError("INVALID_SURVEY","Could not load the EDSL Survey.ep package.",path=str(path),detail=str(exc)) from exc
    else: raw = read_json(path)
    if isinstance(raw, dict) and "survey" in raw: raw = raw["survey"]
    questions = raw.get("questions", raw.get("data", {}).get("questions", [])) if isinstance(raw, dict) else []
    if not isinstance(questions, list): raise MessickError("INVALID_SURVEY", "Survey questions must be a list.")
    normalized=[]
    for index, q in enumerate(questions):
        if not isinstance(q, dict): continue
        name=q.get("question_name") or q.get("name") or q.get("id")
        text=q.get("question_text") or q.get("text") or q.get("prompt") or ""
        opts=q.get("question_options") or q.get("options") or q.get("choices") or []
        if isinstance(opts, dict): opts=list(opts.values())
        normalized.append({"id":name,"text":str(text),"type":q.get("question_type") or q.get("type") or "unknown","options":list(opts or []),"required":q.get("required",False),"instructions":q.get("instructions", ""),"raw":q,"index":index})
    rules = raw.get("rules", raw.get("branching", raw.get("rule_collection",{}).get("rules",[]))) if isinstance(raw, dict) else []
    # EDSL's public dictionary representation expresses branch endpoints as indexes.
    if isinstance(raw,dict) and isinstance(raw.get("rule_collection"),dict):
        names=[q["id"] for q in normalized]
        converted=[]
        for rule in rules:
            if not isinstance(rule,dict): continue
            source=rule.get("current_q"); target=rule.get("next_q")
            if isinstance(source,int) and 0<=source<len(names) and isinstance(target,int) and 0<=target<len(names):
                converted.append({"from":names[source],"to":names[target],"condition":rule.get("expression")})
        rules=converted
    return {"questions":normalized,"rules":rules if isinstance(rules,list) else [],"raw":raw}

def rows(path: Path, fmt=None):
    fmt=fmt or ("csv" if path.suffix.lower()==".csv" else "json")
    if fmt=="csv":
        try:
            with path.open(newline="",encoding="utf-8-sig") as f: return list(csv.DictReader(f))
        except OSError as exc: raise MessickError("INVALID_INPUT",str(exc),path=str(path)) from exc
    if zipfile.is_zipfile(path):
        try:
            with contextlib.redirect_stdout(sys.stderr):
                from edsl import Results
                result=Results.git.load(str(path)); raw=result.to_dict(full_dict=True)
            normalized=[]
            for row in raw.get("data",[]):
                value=dict(row.get("answer",{}))
                value.update({f"agent.{k}":v for k,v in row.get("agent",{}).items() if k not in ("edsl_version","edsl_class_name")})
                value.update({f"scenario.{k}":v for k,v in row.get("scenario",{}).items() if k not in ("edsl_version","edsl_class_name")})
                iteration=row.get("iteration")
                value["iteration"]=iteration.get("iteration") if isinstance(iteration,dict) else iteration
                normalized.append(value)
            return normalized
        except ImportError as exc: raise MessickError("EDSL_UNAVAILABLE","EDSL is required to load Results.ep.","Install `messick[edsl]`.") from exc
        except Exception as exc: raise MessickError("INVALID_RESPONSES","Could not load the EDSL Results.ep package.",path=str(path),detail=str(exc)) from exc
    raw=read_json(path)
    if isinstance(raw,list): return raw
    for key in ("rows","responses","data","results"):
        if isinstance(raw,dict) and isinstance(raw.get(key),list): return raw[key]
    raise MessickError("INVALID_RESPONSES","Response artifact must contain a list of row objects.",path=str(path))
