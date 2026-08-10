"""Strict JSON-first command line interface."""
from __future__ import annotations
import argparse,importlib.util,json,shutil,sys
from pathlib import Path
from uuid import uuid4
from . import __version__
from .analysis import compare as compare_rows, response_diagnostics, scale as scale_analysis
from .artifacts import rows, survey
from .diagnostics import branch_graph, burden, inspect
from .envelope import envelope
from .errors import MessickError
from .store import Store, digest, now
from .workflows import evaluate_intent, generate_job, ingest, plan

class StrictParser(argparse.ArgumentParser):
    def error(self,message): raise MessickError("CLI_USAGE_ERROR",message,"Run `messick --help` for the command contract.")

def command(parent,name): return parent.add_parser(name).add_subparsers(dest="action",required=True)
def parser():
    p=StrictParser(prog="messick",description="Pretest and validate structured research instruments."); p.add_argument("--version",action="version",version=f"messick {__version__}"); p.add_argument("--project-dir",type=Path,default=Path.cwd()); p.add_argument("--human",action="store_true"); sub=p.add_subparsers(dest="area",required=True,parser_class=StrictParser)
    x=sub.add_parser("init"); x.add_argument("--title",required=True); x=sub.add_parser("validate"); x.add_argument("--strict",action="store_true"); sub.add_parser("doctor"); sub.add_parser("inspect")
    a=command(sub,"agent"); [a.add_parser(x) for x in ("guide","next","status","history")]; d=command(a,"docs"); d.add_parser("list"); x=d.add_parser("show"); x.add_argument("topic")
    i=command(sub,"instrument"); x=i.add_parser("import"); x.add_argument("--survey",type=Path,required=True); x.add_argument("--message",default=""); x.add_argument("--expected-revision",type=int); x=i.add_parser("show"); x.add_argument("--revision"); i.add_parser("list"); x=i.add_parser("compare"); x.add_argument("--from",dest="from_revision",required=True); x.add_argument("--to",dest="to_revision",required=True); x=i.add_parser("export"); x.add_argument("--revision",required=True); x.add_argument("--output",type=Path,required=True); x=i.add_parser("set-current"); x.add_argument("--revision",required=True)
    for singular in ("intent","issue"):
        q=command(sub,singular); x=q.add_parser("add"); x.add_argument("--input",type=Path,required=True); q.add_parser("list"); x=q.add_parser("show"); x.add_argument("record_id")
        if singular=="issue":
            list_parser=q.choices["list"]; list_parser.add_argument("--question"); list_parser.add_argument("--status")
            x=q.add_parser("adjudicate"); x.add_argument("record_id"); x.add_argument("--decision",choices=("revise","remove","accept","no-action","rescore","reorder"),required=True); x.add_argument("--rationale",required=True)
    sc=command(sub,"scale"); x=sc.add_parser("add"); x.add_argument("--input",type=Path,required=True); sc.add_parser("list"); x=sc.add_parser("show"); x.add_argument("record_id"); x=sc.add_parser("analyze"); x.add_argument("--scale",required=True); x.add_argument("--source",required=True); x=sc.add_parser("compare"); x.add_argument("--scale",required=True); x.add_argument("--sources",nargs="+",required=True)
    b=command(sub,"branching"); b.add_parser("analyze"); b.add_parser("paths")
    b=command(sub,"burden"); b.add_parser("analyze"); x=b.add_parser("show"); x.add_argument("--question",required=True); x=b.add_parser("compare"); x.add_argument("--from",dest="from_revision",required=True); x.add_argument("--to",dest="to_revision",required=True)
    o=command(sub,"options"); o.add_parser("analyze"); s=command(sub,"scoring"); s.add_parser("validate")
    q=command(sub,"pretest"); x=q.add_parser("plan"); x.add_argument("--mode",choices=("cognitive","behavioral"),required=True); x.add_argument("--agents",type=Path); x.add_argument("--models",type=Path); x=q.add_parser("analyze"); x.add_argument("--source",required=True)
    q=command(sub,"job"); x=q.add_parser("generate"); x.add_argument("--plan",required=True); x.add_argument("--output",type=Path,required=True)
    q=command(sub,"results"); x=q.add_parser("ingest"); x.add_argument("--plan",required=True); x.add_argument("--results",type=Path,required=True)
    q=command(sub,"fielding"); x=q.add_parser("plan"); x.add_argument("--revision",required=True)
    q=command(sub,"responses"); x=q.add_parser("ingest"); x.add_argument("--source-type",choices=("human","benchmark"),required=True); x.add_argument("--input",type=Path,required=True); x.add_argument("--instrument-revision",required=True); x.add_argument("--input-format",choices=("humanize","results-ep","csv","json"),required=True); x.add_argument("--sample-description",default=""); x=q.add_parser("show"); x.add_argument("source_id")
    q=command(sub,"source"); x=q.add_parser("compare"); x.add_argument("--left",required=True); x.add_argument("--right",required=True)
    q=command(sub,"validation"); x=q.add_parser("evaluate"); x.add_argument("--intent",required=True)
    q=command(sub,"decision"); q.add_parser("list")
    q=command(sub,"report"); x=q.add_parser("context"); x.add_argument("--output",type=Path,default=Path("analysis/messick_report_context.json")); x=q.add_parser("template"); x.add_argument("--output",type=Path,default=Path("analysis/messick_report_template.md"))
    return p

def absout(store,path): return path if path.is_absolute() else store.root/path
def instrument(store,revision=None):
    revision=revision or store.load().get("current_instrument_revision")
    if not revision: raise MessickError("NO_INSTRUMENT","No instrument revision is current.")
    return store.record("instruments",revision,"revision_id")
def survey_for(store,revision=None): return survey(store.root/instrument(store,revision)["artifact"])
def source_rows(store,source_id):
    src=store.record("sources",source_id,"source_id"); return src,rows(store.root/src["artifact"],"csv" if src["input_format"]=="csv" else "json")
def declared_bounds(store,revision):
    result={}
    for q in survey_for(store,revision)["questions"]:
        values=[]
        for raw in q["options"]:
            try: values.append(float(raw))
            except (TypeError,ValueError): values=[]; break
        if values: result[q["id"]]=(min(values),max(values))
    return result
def artifact(store,kind,value):
    value={**value,"configuration":store.config_snapshot()}; analysis_id=store.next_id(kind,"analyses"); path=store.root/"analysis"/f"{analysis_id}.json"; path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8"); rec={"analysis_id":analysis_id,"analysis_type":kind,"artifact":str(path.relative_to(store.root)),"sha256":digest(path),"configuration_sha256":value["configuration"]["sha256"],"created_at":now(),"warnings":value.get("warnings",[])}
    for key in ("instrument_revision","source_id","source_type","scale_id"):
        if key in value: rec[key]=value[key]
    store.put_record("analyses",analysis_id,rec); return rec,path

def next_action(store):
    state=store.load(); root=str(store.root); revision=state.get("current_instrument_revision")
    analyses=store.records("analyses")
    def has(kind,**fields): return any(x.get("analysis_type")==kind and all(x.get(k)==v for k,v in fields.items()) for x in analyses)
    def cmd(name,args,mutation,reason,inputs=None,artifacts=None,transition=None,approval=False,spending=False):
        return action(store,name,args,mutation,reason,inputs,artifacts,transition,approval,spending)
    if not revision:
        return cmd("instrument import",["instrument","import","--survey","<survey_path>"],True,"Register the first immutable Survey revision.",{"survey_path":field("string","A readable Survey.ep path.","--survey",fmt="path")},transition="current_instrument_revision is set")
    if not store.records("intents"):
        return cmd(
            "intent add",
            ["intent", "add", "--input", "<intent_path>"],
            True,
            "Define the interpretation and use before evaluating evidence.",
            {
                "intent_path": field(
                    "string",
                    "A readable JSON intent file matching content_schema.",
                    "--input",
                    fmt="path",
                    content_schema={
                        "type": "object",
                        "required": [
                            "intent_id",
                            "construct",
                            "interpretation",
                            "population",
                            "use",
                            "evidence_tier",
                        ],
                        "properties": {
                            "intent_id": {"type": "string"},
                            "construct": {"type": "string"},
                            "interpretation": {"type": "string"},
                            "population": {"type": "string"},
                            "use": {"type": "string"},
                            "evidence_tier": {
                                "type": "string",
                                "enum": ["static", "simulation", "human"],
                            },
                        },
                        "additionalProperties": True,
                    },
                )
            },
            transition="an intent is registered",
        )
    if not has("instrument_inspection",instrument_revision=revision): return cmd("inspect",["inspect"],True,"Run deterministic instrument checks.",transition="instrument inspection is recorded")
    severe=[x for x in store.records("issues") if x.get("instrument_revision")==revision and x.get("severity") in ("error","severe")]; decided={x.get("issue_id") for x in store.records("decisions")}
    pending=next((x for x in severe if x["issue_id"] not in decided),None)
    if pending:
        return cmd("issue adjudicate",["issue","adjudicate",pending["issue_id"],"--decision","<decision>","--rationale","<rationale>"],True,"Adjudicate the remaining severe issue.",{"decision":field("string","Disposition for the issue.","--decision",["revise","remove","accept","no-action","rescore","reorder"]),"rationale":field("string","Auditable rationale.","--rationale")},{"issue_id":pending["issue_id"]},"the severe issue has a decision")
    normalized=survey_for(store,revision)
    if not has("burden",instrument_revision=revision): return cmd("burden analyze",["burden","analyze"],True,"Measure respondent burden for the current revision.",transition="burden analysis is recorded")
    if normalized.get("rules") and not has("branching",instrument_revision=revision): return cmd("branching analyze",["branching","analyze"],True,"Analyze reachable paths for the branched instrument.",transition="branching analysis is recorded")
    if any(q.get("options") for q in normalized["questions"]) and not has("options",instrument_revision=revision): return cmd("options analyze",["options","analyze"],True,"Check response-option mappings where options exist.",transition="option analysis is recorded")
    scales=store.records("scales")
    if scales and not has("scoring",instrument_revision=revision): return cmd("scoring validate",["scoring","validate"],True,"Validate scoring declarations for registered scales.",transition="scoring validation is recorded")
    needs_simulation=any(x.get("evidence_tier")!="static" for x in store.records("intents"))
    runs=[x for x in store.records("runs") if x.get("instrument_revision")==revision]
    if needs_simulation and not runs:
        return cmd("pretest plan",["pretest","plan","--mode","cognitive","--models","<models_path>"],True,"Create a cognitive execution design using the model selected by ep-agent. Add --agents only to override the documented three-profile respondent pilot.",{"models_path":field("string","ModelList.ep produced from the current ep-agent model selection.","--models",fmt="path"),"agents_path":field("string","Optional AgentList.ep overriding the bounded respondent pilot.","--agents",fmt="path",required=False,conditional=True)},transition="a pretest plan with a non-empty execution matrix is recorded")
    if needs_simulation:
        run=runs[-1]; jobs=next((x for x in store.records("reports") if x.get("plan_id")==run["plan_id"] and x.get("job_id")),None)
        if not jobs:
            return cmd("job generate",["job","generate","--plan",run["plan_id"],"--output","edsl_jobs/cognitive_pretest.ep"],True,"Generate the exact portable job and ep handoff.",artifacts={"plan_id":run["plan_id"],"output":str(store.root/"edsl_jobs/cognitive_pretest.ep")},transition="a Jobs.ep artifact and handoff are recorded")
        sources=[x for x in store.records("sources") if x.get("plan_id")==run["plan_id"]]
        if not sources:
            return cmd("results ingest",["results","ingest","--plan",run["plan_id"],"--results","<results_path>"],True,"Ingest the Results.ep produced by the separately approved ep run.",{"results_path":field("string","Results.ep from this plan's ep handoff.","--results",fmt="path")},{"plan_id":run["plan_id"],"jobs_path":str(store.root/jobs["artifact"])},"the exact Results source is registered")
        source=sources[-1]
        if not has("pretest",source_id=source["source_id"]): return cmd("pretest analyze",["pretest","analyze","--source",source["source_id"]],True,"Analyze the newly ingested cognitive evidence before validation.",artifacts={"source_id":source["source_id"]},transition="pretest analysis is recorded and findings become issues")
        for scale in scales:
            if not has("scale",source_id=source["source_id"],scale_id=scale["scale_id"]): return cmd("scale analyze",["scale","analyze","--scale",scale["scale_id"],"--source",source["source_id"]],True,"Analyze the declared scale against the collected source.",artifacts={"scale_id":scale["scale_id"],"source_id":source["source_id"]},transition="scale analysis is recorded")
    evaluated={x["intent_id"] for x in store.records("validations")}
    intent=next((x for x in store.records("intents") if x["intent_id"] not in evaluated),None)
    if intent: return cmd("validation evaluate",["validation","evaluate","--intent",intent["intent_id"]],True,"Evaluate the declared intent against completed relevant analyses.",artifacts={"intent_id":intent["intent_id"]},transition="intent validation is recorded")
    context=store.root/"analysis/messick_report_context.json"; template=store.root/"analysis/messick_report_template.md"
    if not context.exists(): return cmd("report context",["report","context","--output","analysis/messick_report_context.json"],True,"Produce the bounded analytic handoff.",artifacts={"output":str(context)},transition="report context exists")
    if not template.exists(): return cmd("report template",["report","template","--output","analysis/messick_report_template.md"],True,"Produce the report-writing handoff.",artifacts={"output":str(template)},transition="report template exists")
    strict=next((x for x in store.records("reports") if x.get("report_id")=="strict_validation" and x.get("project_revision")==state["revision"]),None)
    if not strict: return cmd("validate strict",["validate","--strict"],True,"Perform the final strict project validation.",transition="strict validation succeeds for the current project revision")
    return {"contract_version":"1.0","terminal":True,"name":"complete","cwd":root,"argv":[],"mutation":False,"spending":False,"approval_required":False,"prerequisites":[],"expected_transition":"none","known_artifacts":{"report_context":str(context),"report_template":str(template)},"reason":"All relevant analyses, handoffs, adjudications, and strict validation are complete."}

def field(typ,description,flag,allowed=None,fmt=None,required=True,conditional=False,content_schema=None):
    value={"type":typ,"description":description,"placement":{"kind":"conditional_flag" if conditional else "flag","flag":flag},"required":required}
    if allowed:value["allowed_values"]=allowed
    if fmt:value["format"]=fmt
    if content_schema:value["content_schema"]=content_schema
    return value

def action(store,name,args,mutation,reason,inputs=None,artifacts=None,transition=None,approval=False,spending=False):
    argv=["messick","--project-dir",str(store.root),*args]
    required=[k for k,v in (inputs or {}).items() if v.get("required",True)]
    return {"contract_version":"1.0","name":name,"cwd":str(store.root),"argv":argv,"mutation":mutation,"spending":spending,"approval_required":approval,"reason":reason,"input_schema":{"type":"object","required":required,"properties":inputs or {}},"prerequisites":[],"expected_transition":transition or "command completes","known_artifacts":artifacts or {}}

def execute(a,s):
    if a.area=="init": return s.init(a.title),{},[]
    if a.area=="doctor":
        edsl_available=importlib.util.find_spec("edsl") is not None; checks={"python":{"ok":sys.version_info>=(3,11)},"edsl":{"ok":edsl_available,"optional_for_static_review":True},"ep":{"ok":shutil.which("ep") is not None},"project":{"ok":s.exists},"schema":{"ok":not s.exists or s.load().get("schema_version")==1},"humanize":{"ok":shutil.which("humanize") is not None,"optional":True}}; warnings=[] if checks["ep"]["ok"] else [{"code":"EP_NOT_FOUND","message":"`ep` is unavailable."}]; return {"checks":checks},{},warnings
    s.require(); state=s.load()
    if a.area=="validate":
        problems=[]
        if not state.get("current_instrument_revision"):problems.append({"code":"NO_INSTRUMENT","message":"No current instrument."})
        if a.strict and not s.records("intents"):problems.append({"code":"NO_INTENTS","message":"Strict validation requires an intent."})
        decided={x.get("issue_id") for x in s.records("decisions")}
        if a.strict:
            problems += [{"code":"UNADJUDICATED_SEVERE_ISSUE","issue_id":x["issue_id"]} for x in s.records("issues") if x.get("severity") in ("error","severe") and x["issue_id"] not in decided]
            evaluated={x["intent_id"] for x in s.records("validations")}
            problems += [{"code":"INTENT_NOT_EVALUATED","intent_id":x["intent_id"]} for x in s.records("intents") if x.get("status","active") in ("active","proposed") and x["intent_id"] not in evaluated]
        if problems:raise MessickError("PROJECT_INVALID","Project validation failed.",problems=problems)
        if a.strict:
            report_id=f"strict_validation_r{state['revision']}"
            if not any(x.get("report_id")=="strict_validation" and x.get("project_revision")==state["revision"] for x in s.records("reports")):
                s.put_record("reports",report_id,{"report_id":"strict_validation","record_id":report_id,"project_revision":state["revision"],"created_at":now()})
        return {"valid":True,"strict":a.strict},{},[]
    if a.area=="instrument":
        if a.action=="import": rec,created=s.import_instrument(a.survey,a.message,a.expected_revision); return {"instrument":rec,"created":created},{"survey":rec["artifact"]},[]
        if a.action=="list":return {"instruments":s.records("instruments")},{},[]
        if a.action=="show":return {"instrument":instrument(s,a.revision)},{},[]
        if a.action=="set-current": rec=instrument(s,a.revision); s.mutate("instrument.current_changed",{"current_instrument_revision":rec["revision_id"]}); return {"instrument":rec},{},[]
        if a.action=="export": rec=instrument(s,a.revision); out=absout(s,a.output); out.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(s.root/rec["artifact"],out); return {"instrument":rec},{"survey":str(out)},[]
        left,right=survey_for(s,a.from_revision),survey_for(s,a.to_revision); li={q["id"]:q for q in left["questions"]}; ri={q["id"]:q for q in right["questions"]}; return {"from":a.from_revision,"to":a.to_revision,"added":sorted(ri.keys()-li.keys()),"removed":sorted(li.keys()-ri.keys()),"changed":sorted(k for k in li.keys()&ri.keys() if li[k]["text"]!=ri[k]["text"] or li[k]["options"]!=ri[k]["options"])},{},[]
    if a.area in ("intent","issue"):
        collection=a.area+"s"; id_field=a.area+"_id"
        if a.action=="add":return {a.area:s.add_from_json(collection,a.input,id_field)},{},[]
        if a.action=="list":
            records=s.records(collection)
            if a.area=="issue":
                if a.question: records=[x for x in records if x.get("question_id")==a.question]
                if a.status:
                    decided={x["issue_id"]:x["action"] for x in s.records("decisions")}; records=[x for x in records if (decided.get(x["issue_id"],x.get("disposition","open"))==a.status)]
            return {collection:records},{},[]
        if a.action=="show":return {a.area:s.record(collection,a.record_id,id_field)},{},[]
        issue=s.record("issues",a.record_id,"issue_id"); decision={"decision_id":s.next_id("decision","decisions"),"issue_id":issue["issue_id"],"action":a.decision,"rationale":a.rationale,"evidence_ids":issue.get("evidence_source_ids",[]),"actor":"cli-user","created_at":now()}; s.put_record("decisions",decision["decision_id"],decision); s.mutate("issue.adjudicated",{}); return {"decision":decision},{},[]
    if a.area=="decision":return {"decisions":s.records("decisions")},{},[]
    if a.area=="inspect":
        result=inspect(survey_for(s)); result.update({"instrument_revision":state["current_instrument_revision"],"analysis_version":"1.0"}); rec,path=artifact(s,"instrument_inspection",result)
        for finding in result["issues"]:
            iid=s.next_id("issue","issues"); value={"issue_id":iid,"instrument_revision":state["current_instrument_revision"],**finding,"evidence_source_ids":[],"disposition":"open","created_at":now()}; s.put_record("issues",iid,value)
        s.mutate("instrument.inspected",{}); return {"summary":{"question_count":result["question_count"],"issue_counts":result["issue_counts"]}},{"analysis":str(path)},[]
    if a.area=="branching":
        graph=branch_graph(survey_for(s))
        if a.action=="paths": return {"paths":graph["paths"],"path_count":graph["path_count"]},{},[]
        result={**graph,"instrument_revision":state["current_instrument_revision"]}; rec,path=artifact(s,"branching",result); s.mutate("branching.analyzed",{}); return graph,{"analysis":str(path)},[]
    if a.area=="burden":
        if a.action=="analyze": result=burden(survey_for(s),s.config_snapshot()["content"].get("analysis",{}).get("burden",{})); result["instrument_revision"]=state["current_instrument_revision"]; rec,path=artifact(s,"burden",result); s.mutate("burden.analyzed",{}); return {"paths":result["paths"],"warning":result["warning"]},{"analysis":str(path)},[]
        if a.action=="show": result=burden(survey_for(s)); found=next((x for x in result["questions"] if x["question_id"]==a.question),None); return {"question":found},{},[]
        l,r=burden(survey_for(s,a.from_revision)),burden(survey_for(s,a.to_revision)); return {"from":a.from_revision,"to":a.to_revision,"typical_seconds_change":r["paths"]["typical"]["seconds"]-l["paths"]["typical"]["seconds"],"from_paths":l["paths"],"to_paths":r["paths"]},{},[]
    if a.area=="options":
        result=inspect(survey_for(s)); findings=[x for x in result["issues"] if x["category"]=="response-mapping"]; payload={"findings":findings,"count":len(findings),"instrument_revision":state["current_instrument_revision"]}; rec,path=artifact(s,"options",payload); s.mutate("options.analyzed",{}); return {"findings":findings,"count":len(findings)},{"analysis":str(path)},[]
    if a.area=="scoring":
        errors=[]; ids={q["id"] for q in survey_for(s)["questions"]}
        for scale in s.records("scales"):
            errors += [{"scale_id":scale["scale_id"],"code":"UNKNOWN_ITEM","item":x} for x in scale.get("items",[]) if x not in ids]
            errors += [{"scale_id":scale["scale_id"],"code":"REVERSE_RANGE_REQUIRED"}] if scale.get("reverse_scored") and not scale.get("range") else []
        payload={"valid":not errors,"findings":errors,"instrument_revision":state["current_instrument_revision"]}; rec,path=artifact(s,"scoring",payload); s.mutate("scoring.validated",{}); return {"valid":not errors,"findings":errors},{"analysis":str(path)},[]
    if a.area=="scale":
        if a.action=="add":return {"scale":s.add_from_json("scales",a.input,"scale_id")},{},[]
        if a.action=="list":return {"scales":s.records("scales")},{},[]
        if a.action=="show":return {"scale":s.record("scales",a.record_id,"scale_id")},{},[]
        definition=s.record("scales",a.scale,"scale_id")
        if a.action=="analyze": src,rs=source_rows(s,a.source); result=scale_analysis(rs,definition); result.update({"scale_id":a.scale,"source_id":a.source,"source_type":src["source_type"]}); rec,path=artifact(s,"scale",result); s.mutate("scale.analyzed",{}); return {"scale_id":a.scale,"source_id":a.source,"source_type":src["source_type"],"n":result["n"],"item_count":len(result["items"]),"cronbach_alpha":result["cronbach_alpha"],"mcdonald_omega":result["mcdonald_omega"]},{"analysis":str(path)},result["warnings"]
        values=[]
        for sid in a.sources: src,rs=source_rows(s,sid); values.append({"source_id":sid,"source_type":src["source_type"],"analysis":scale_analysis(rs,definition)})
        comparison={"scale_id":a.scale,"sources":values,"pooled":False}; rec,path=artifact(s,"scale_comparison",comparison); s.mutate("scales.compared",{}); return {"scale_id":a.scale,"source_count":len(values),"pooled":False},{"analysis":str(path)},[]
    if a.area=="pretest":
        if a.action=="plan":return {"plan":plan(s,a.mode,a.agents,a.models)},{},[]
        src,rs=source_rows(s,a.source); result=response_diagnostics(rs,declared_bounds(s,src["instrument_revision"])); normalized=[]
        if src["source_type"]=="simulated-cognitive":
            for row in rs:
                raw=row.get("messick_cognitive_probe"); finding=raw
                if isinstance(raw,str):
                    try:finding=json.loads(raw)
                    except json.JSONDecodeError:finding={"unstructured_response":raw}
                if not isinstance(finding,dict):finding={"unstructured_response":str(finding)}
                qid=row.get("scenario.question_id"); normalized.append({"question_id":qid,"finding":finding})
                for key,category in (("ambiguity","ambiguity"),("missing_options","missing-option"),("sensitivity","sensitivity/social-desirability"),("difficulty","comprehension")):
                    value=finding.get(key)
                    if value and str(value).lower() not in ("none","no","false","n/a"):
                        iid=s.next_id("issue","issues"); issue={"issue_id":iid,"instrument_revision":src["instrument_revision"],"question_id":qid,"category":category,"severity":"warning","evidence_source_ids":[a.source],"description":str(value),"evidence_excerpt":str(value)[:500],"disposition":"open","created_at":now()}; s.put_record("issues",iid,issue)
        boundary="Simulated findings are diagnostic hypotheses, not human validation." if src["source_type"].startswith("simulated") else "Human findings are bounded to the recorded sample and fielding conditions."
        result.update({"source_id":a.source,"source_type":src["source_type"],"normalized_cognitive_findings":normalized,"claims_boundary":boundary}); rec,path=artifact(s,"pretest",result); s.mutate("pretest.analyzed",{}); return {"source_id":a.source,"row_count":len(rs),"item_count":len(result["items"]),"cognitive_finding_count":len(normalized)},{"analysis":str(path)},[]
    if a.area=="job": data,arts,steps=generate_job(s,a.plan,a.output); s.mutate("job.generated",{}); return {"job":data,"handoff":steps},arts,[]
    if a.area=="results":
        p=s.record("runs",a.plan,"plan_id"); typ="simulated-cognitive" if p["mode"]=="cognitive" else "simulated-behavioral"; rec,created=ingest(s,a.results,typ,p["instrument_revision"],plan_id=a.plan); return {"source":rec,"created":created},{"source_artifact":rec["artifact"]},[]
    if a.area=="fielding":
        inst=instrument(s,a.revision); fid=s.next_id("fielding","runs"); out=s.root/"analysis"/f"{fid}.json"; value={"fielding_plan_id":fid,"instrument_revision":a.revision,"survey_artifact":inst["artifact"],"survey_sha256":inst["sha256"],"owner":"Humanize/external","deployment_authorized":False,"created_at":now()}; out.write_text(json.dumps(value,indent=2)+"\n"); return {"plan":value},{"fielding_plan":str(out)},[]
    if a.area=="responses":
        if a.action=="show":return {"source":s.record("sources",a.source_id,"source_id")},{},[]
        fmt="csv" if a.input_format=="csv" else "json"; rec,created=ingest(s,a.input,a.source_type,a.instrument_revision,fmt,sample_description=a.sample_description); return {"source":rec,"created":created},{"source_artifact":rec["artifact"]},[]
    if a.area=="source":
        ls,lr=source_rows(s,a.left); rs,rr=source_rows(s,a.right); result=compare_rows(lr,rr); result.update({"left":{"source_id":a.left,"source_type":ls["source_type"],"sample_description":ls["sample_description"]},"right":{"source_id":a.right,"source_type":rs["source_type"],"sample_description":rs["sample_description"]},"comparability_notes":ls.get("comparability_notes",[])+rs.get("comparability_notes",[])}); rec,path=artifact(s,"source_comparison",result); s.mutate("sources.compared",{}); return {"left":result["left"],"right":result["right"],"left_n":result["left_n"],"right_n":result["right_n"],"item_count":len(result["items"]),"pooled":False,"equivalence_claimed":False},{"analysis":str(path)},[]
    if a.area=="validation":return {"validation":evaluate_intent(s,a.intent)},{},[]
    if a.area=="agent":
        if a.action=="guide":return {"principles":["Validate interpretations and uses, never instruments globally.","Keep simulated and human evidence distinct.","Execute inference only through ep."],"control_surface":"messick agent next"},{},[]
        if a.action=="next":return {"recommended_action":next_action(s)},{},[]
        if a.action=="status":return {"project":state,"counts":{k:len(s.records(k)) for k in ("instruments","intents","scales","sources","issues","decisions","analyses","validations")}},{},[]
        if a.action=="history":return {"events":s.records("events")},{},[]
        topics={"concepts":"Immutable revisions, declared intents, sourced evidence, issues, decisions, and reproducible analyses.","evidence":"Static, simulated-cognitive, simulated-behavioral, human, and benchmark evidence remain separate.","handoff":"Messick generates Jobs; ep inspects, costs, and executes them.","errors":"Errors use stable codes in the versioned JSON envelope."}
        if a.docs_action=="list":return {"topics":sorted(topics)},{},[]
        if a.topic not in topics:raise MessickError("DOC_TOPIC_NOT_FOUND","Documentation topic was not found.",topic=a.topic)
        return {"topic":a.topic,"content":topics[a.topic]},{},[]
    if a.area=="report":
        out=absout(s,a.output); out.parent.mkdir(parents=True,exist_ok=True)
        if a.action=="template": out.write_text("# Instrument pretest\n\n<!-- Populate from messick_report_context.json; preserve evidence-source labels. -->\n\n## Purpose and intended uses\n\n## Evidence\n\n## Findings\n\n## Revisions and decisions\n\n## Limitations and next evidence\n",encoding="utf-8"); return {},{"report_template":str(out)},[]
        sources=s.records("sources"); instruments=s.records("instruments"); analyses=s.records("analyses"); plans=s.records("runs"); canonical=[{"kind":"instrument","path":x["artifact"],"sha256":x["sha256"]} for x in instruments]+[{"kind":"evidence","path":x["artifact"],"sha256":x["sha256"]} for x in sources]+[{"kind":"analysis","path":x["artifact"],"sha256":x["sha256"]} for x in analyses]; context={"schema_version":"1.0","project":state,"instrument":instrument(s),"intents":s.records("intents"),"scales":s.records("scales"),"pretest_plans":plans,"execution_designs":[{"plan_id":x["plan_id"],"agent_list":x.get("agent_list"),"model_list":x.get("model_list"),"execution_design":x.get("execution_design")} for x in plans],"evidence_sources":sources,"evidence_inventory":{"simulated":[x["source_id"] for x in sources if x["source_type"].startswith("simulated")],"human":[x["source_id"] for x in sources if x["source_type"]=="human"]},"issues":s.records("issues"),"decisions":s.records("decisions"),"analyses":analyses,"validations":s.records("validations"),"revision_history":instruments,"limitations":["Simulated evidence does not establish human reliability, dimensionality, prevalence, subgroup differences, or decision accuracy."],"canonical_artifacts":canonical}; out.write_text(json.dumps(context,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return {"summary":{"source_count":len(sources),"issue_count":len(context["issues"])}},{"report_context":str(out)},[]
    raise MessickError("NOT_IMPLEMENTED","Command is not implemented.")

def main(argv=None):
    raw=list(sys.argv[1:] if argv is None else argv); label="messick "+" ".join(raw); root=Path.cwd(); human="--human" in raw
    if "--project-dir" in raw:
        try: root=Path(raw[raw.index("--project-dir")+1])
        except IndexError: pass
    s=Store(root)
    try:
        a=parser().parse_args(raw); s=Store(a.project_dir); human=a.human; data,arts,warnings=execute(a,s); result=envelope(label,s.root,s.load()["revision"] if s.exists else 0,argv=["messick",*raw],data=data,artifacts=arts,warnings=warnings); code=0
    except MessickError as exc:result=envelope(label,s.root,s.load()["revision"] if s.exists else 0,argv=["messick",*raw],status="error",errors=[exc.as_dict()]); code=1
    print(json.dumps(result.get("data",{}),indent=2,sort_keys=True) if human else json.dumps(result,sort_keys=True)); return code
if __name__=="__main__":raise SystemExit(main())
