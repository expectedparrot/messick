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
    state=store.load()
    if not state.get("current_instrument_revision"): return action("instrument import",["messick","instrument","import","--survey","<Survey.ep>"],True,"Register the first immutable Survey revision.")
    if not store.records("intents"): return action("intent add",["messick","intent","add","--input","intent.json"],True,"Define the interpretation and use before evaluating evidence.",{"intent_id":"stable ID","construct":"target construct","interpretation":"score interpretation","population":"intended population","use":"intended use","evidence_tier":"static|simulation|human"})
    if not any(x["analysis_type"]=="instrument_inspection" for x in store.records("analyses")): return action("inspect",["messick","inspect"],False,"Run deterministic instrument checks.")
    severe=[x for x in store.records("issues") if x.get("severity") in ("error","severe")]; decided={x.get("issue_id") for x in store.records("decisions")}
    if any(x["issue_id"] not in decided for x in severe): return action("issue adjudicate",["messick","issue","adjudicate","<issue-id>","--decision","<decision>","--rationale","<rationale>"],True,"Adjudicate the remaining severe issue.")
    if not store.records("runs"): return action("pretest plan",["messick","pretest","plan","--mode","cognitive"],True,"Create a simulation-first cognitive pretest.")
    if not store.records("sources"): return action("job generate",["messick","job","generate","--plan",store.records("runs")[-1]["plan_id"],"--output","edsl_jobs/cognitive_pretest.ep"],True,"Generate the exact portable job for the ep handoff.")
    if not store.records("validations"): return action("validation evaluate",["messick","validation","evaluate","--intent",store.records("intents")[0]["intent_id"]],True,"Evaluate the declared intent against its evidence tier.")
    if not (store.root/"analysis/messick_report_context.json").exists(): return action("report context",["messick","report","context","--output","analysis/messick_report_context.json"],True,"Produce the bounded analytic handoff.")
    return {"terminal":True,"name":"complete","cwd":str(store.root),"argv":[],"mutation":False,"approval_required":False,"reason":"The declared simulation-first pretest workflow is complete."}
def action(name,argv,mutation,reason,schema=None):
    x={"name":name,"cwd":"<project_root>","argv":argv,"mutation":mutation,"approval_required":False,"reason":reason}
    if schema:x["input_schema"]={"type":"object","required":list(schema),"properties":{k:{"type":"string","description":v} for k,v in schema.items()}}
    return x

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
        graph=branch_graph(survey_for(s)); return ({"paths":graph["paths"],"path_count":graph["path_count"]} if a.action=="paths" else graph),{},[]
    if a.area=="burden":
        if a.action=="analyze": result=burden(survey_for(s),s.config_snapshot()["content"].get("analysis",{}).get("burden",{})); rec,path=artifact(s,"burden",result); s.mutate("burden.analyzed",{}); return {"paths":result["paths"],"warning":result["warning"]},{"analysis":str(path)},[]
        if a.action=="show": result=burden(survey_for(s)); found=next((x for x in result["questions"] if x["question_id"]==a.question),None); return {"question":found},{},[]
        l,r=burden(survey_for(s,a.from_revision)),burden(survey_for(s,a.to_revision)); return {"from":a.from_revision,"to":a.to_revision,"typical_seconds_change":r["paths"]["typical"]["seconds"]-l["paths"]["typical"]["seconds"],"from_paths":l["paths"],"to_paths":r["paths"]},{},[]
    if a.area=="options":
        result=inspect(survey_for(s)); findings=[x for x in result["issues"] if x["category"]=="response-mapping"]; return {"findings":findings,"count":len(findings)},{},[]
    if a.area=="scoring":
        errors=[]; ids={q["id"] for q in survey_for(s)["questions"]}
        for scale in s.records("scales"):
            errors += [{"scale_id":scale["scale_id"],"code":"UNKNOWN_ITEM","item":x} for x in scale.get("items",[]) if x not in ids]
            errors += [{"scale_id":scale["scale_id"],"code":"REVERSE_RANGE_REQUIRED"}] if scale.get("reverse_scored") and not scale.get("range") else []
        return {"valid":not errors,"findings":errors},{},[]
    if a.area=="scale":
        if a.action=="add":return {"scale":s.add_from_json("scales",a.input,"scale_id")},{},[]
        if a.action=="list":return {"scales":s.records("scales")},{},[]
        if a.action=="show":return {"scale":s.record("scales",a.record_id,"scale_id")},{},[]
        definition=s.record("scales",a.scale,"scale_id")
        if a.action=="analyze": src,rs=source_rows(s,a.source); result=scale_analysis(rs,definition); result.update({"source_id":a.source,"source_type":src["source_type"]}); rec,path=artifact(s,"scale",result); s.mutate("scale.analyzed",{}); return {"scale_id":a.scale,"source_id":a.source,"source_type":src["source_type"],"n":result["n"],"item_count":len(result["items"]),"cronbach_alpha":result["cronbach_alpha"],"mcdonald_omega":result["mcdonald_omega"]},{"analysis":str(path)},result["warnings"]
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
        sources=s.records("sources"); instruments=s.records("instruments"); analyses=s.records("analyses"); canonical=[{"kind":"instrument","path":x["artifact"],"sha256":x["sha256"]} for x in instruments]+[{"kind":"evidence","path":x["artifact"],"sha256":x["sha256"]} for x in sources]+[{"kind":"analysis","path":x["artifact"],"sha256":x["sha256"]} for x in analyses]; context={"schema_version":"1.0","project":state,"instrument":instrument(s),"intents":s.records("intents"),"scales":s.records("scales"),"evidence_sources":sources,"evidence_inventory":{"simulated":[x["source_id"] for x in sources if x["source_type"].startswith("simulated")],"human":[x["source_id"] for x in sources if x["source_type"]=="human"]},"issues":s.records("issues"),"decisions":s.records("decisions"),"analyses":analyses,"validations":s.records("validations"),"revision_history":instruments,"limitations":["Simulated evidence does not establish human reliability, dimensionality, prevalence, subgroup differences, or decision accuracy."],"canonical_artifacts":canonical}; out.write_text(json.dumps(context,indent=2,sort_keys=True)+"\n",encoding="utf-8"); return {"summary":{"source_count":len(sources),"issue_count":len(context["issues"])}},{"report_context":str(out)},[]
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
