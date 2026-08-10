"""Pretest plans, handoffs, provenance-preserving ingestion and validation."""
from __future__ import annotations
import contextlib,json, shutil,sys,zipfile
from pathlib import Path
from uuid import uuid4
from .artifacts import rows
from .errors import MessickError
from .store import digest, now

def plan(store, mode, agents=None, models=None):
    state=store.load(); revision=state.get("current_instrument_revision")
    if not revision: raise MessickError("NO_INSTRUMENT","A current instrument is required.")
    plan_id=store.next_id("plan","runs")
    agent_record=model_record=None
    if agents:
        target,sha=store.copy_artifact(agents,".messick/runs",f"{plan_id}_agents.ep"); agent_record={"path":str(target),"sha256":sha}
    if models:
        target,sha=store.copy_artifact(models,".messick/runs",f"{plan_id}_models.ep"); model_record={"path":str(target),"sha256":sha}
    value={"plan_id":plan_id,"mode":mode,"instrument_revision":revision,"created_at":now(),"status":"planned","prompts":["paraphrase","answer_process","ambiguity","missing_options"] if mode=="cognitive" else [],"agent_list":agent_record,"model_list":model_record}
    store.put_record("runs",plan_id,value); store.mutate("pretest.planned",{}); return value

def generate_job(store,plan_id,output):
    p=store.record("runs",plan_id,"plan_id"); inst=store.record("instruments",p["instrument_revision"],"revision_id")
    output=output if output.is_absolute() else store.root/output; output.parent.mkdir(parents=True,exist_ok=True)
    if output.suffix != ".ep": raise MessickError("INVALID_OUTPUT","Jobs output must be a durable .ep package.",path=str(output))
    try:
        with contextlib.redirect_stdout(sys.stderr):
            from edsl import AgentList,Jobs,ModelList,Question,QuestionFreeText,Scenario,ScenarioList,Survey
            source_path=store.root/inst["artifact"]
            if zipfile.is_zipfile(source_path): original=Survey.git.load(str(source_path))
            else:
                try: original=Survey.load(str(source_path))
                except Exception:
                    from .artifacts import survey as read_survey
                    original=Survey()
                    for q in read_survey(source_path)["questions"]:
                        kwargs={"question_name":q["id"],"question_text":q["text"]}
                        if q["options"]: kwargs["question_options"]=q["options"]
                        original.add_question(Question(q["type"],**kwargs))
            if p["mode"]=="behavioral": jobs=original.to_jobs()
            else:
                probe=QuestionFreeText(question_name="messick_cognitive_probe",question_text="""Review this survey question as the described respondent.\n\nQuestion ID: {{ question_id }}\nQuestion: {{ question_text }}\nOptions: {{ question_options }}\n\nReturn JSON with keys paraphrase, answer_process, ambiguity, missing_options, assumptions, sensitivity, construct_distinction, and difficulty. Treat this as a diagnostic hypothesis, not an observation of human cognition.""")
                scenarios=ScenarioList([Scenario({"question_id":q.question_name,"question_text":q.question_text,"question_options":getattr(q,"question_options",[])}) for q in original.questions])
                jobs=Survey([probe]).by(scenarios)
            if p.get("agent_list"): jobs=jobs.by(AgentList.git.load(p["agent_list"]["path"]))
            if p.get("model_list"): jobs=jobs.by(ModelList.git.load(p["model_list"]["path"]))
            saved=jobs.git.save(str(output),message=f"Messick {p['mode']} pretest {plan_id}")
            Jobs.git.load(str(output))
    except ImportError as exc: raise MessickError("EDSL_UNAVAILABLE","EDSL is required to generate Jobs.ep.","Install `messick[edsl]`.") from exc
    except MessickError: raise
    except Exception as exc: raise MessickError("JOB_GENERATION_FAILED","Could not generate a loadable EDSL Jobs.ep package.",detail=str(exc)) from exc
    payload={"schema_version":"1.0","owner":"messick","plan_id":plan_id,"mode":p["mode"],"survey":{"path":inst["artifact"],"sha256":inst["sha256"]},"jobs":{"path":str(output),"sha256":digest(output)},"configuration":store.config_snapshot(),"execution":{"owner":"ep","inference_performed":False},"edsl_save":saved}
    return payload,{"jobs":str(output)},handoff(output)

def handoff(path):
    p=str(path)
    return [{"cwd":str(path.parent),"argv":["ep","inspect",p],"approval_required":False},{"cwd":str(path.parent),"argv":["ep","jobs","cost",p],"approval_required":False},{"cwd":str(path.parent),"argv":["ep","run",p,"--output","<Results.ep>"],"approval_required":True}]

def ingest(store,source_path,source_type,instrument_revision,input_format=None,plan_id=None,sample_description=""):
    if source_type not in ("simulated-cognitive","simulated-behavioral","human","benchmark"): raise MessickError("INVALID_SOURCE_TYPE","Unsupported evidence source type.",source_type=source_type)
    store.record("instruments",instrument_revision,"revision_id")
    parsed=rows(source_path,input_format); sha=digest(source_path)
    for existing in store.records("sources"):
        if existing["sha256"]==sha and existing["source_type"]==source_type: return existing,False
    source_id=store.next_id("source","sources"); folder="data/human" if source_type=="human" else "data/results"
    suffix="".join(source_path.suffixes) or ".ep"; target,_=store.copy_artifact(source_path,folder,f"{source_id}{suffix}")
    record={"source_id":source_id,"source_type":source_type,"instrument_revision":instrument_revision,"artifact":str(target.relative_to(store.root)),"sha256":sha,"row_count":len(parsed),"sample_description":sample_description,"plan_id":plan_id,"input_format":input_format or source_path.suffix.lstrip("."),"created_at":now(),"comparability_notes":[],"transmitted_to_model":False,"pooled":False}
    store.put_record("sources",source_id,record); store.mutate("responses.ingested",{}); return record,True

def evaluate_intent(store,intent_id):
    intent=store.record("intents",intent_id,"intent_id"); tier=intent.get("evidence_tier") or intent.get("selected_evidence_tier") or "simulation"; sources=store.records("sources")
    relevant=[s for s in sources if s.get("instrument_revision")==store.load().get("current_instrument_revision")]
    human=[s for s in relevant if s["source_type"]=="human"]; simulated=[s for s in relevant if s["source_type"].startswith("simulated")]
    consequential=bool(intent.get("consequential")) or any(x in str(intent.get("use","")).lower() for x in ("diagnos","eligib","trigger","decision"))
    reasons=[]
    if (tier=="human" or consequential) and not human: status="requires_human_evidence"; reasons.append("The claim requires suitable human evidence.")
    elif tier=="simulation" and not simulated: status="not_evaluated"; reasons.append("No simulated evidence exists for the current revision.")
    elif tier=="static" and not store.records("analyses"): status="not_evaluated"; reasons.append("No deterministic analysis exists for the current revision.")
    else:
        decisions={x["issue_id"] for x in store.records("decisions")}; severe=[x for x in store.records("issues") if x.get("instrument_revision")==store.load().get("current_instrument_revision") and x.get("severity") in ("error","severe") and x["issue_id"] not in decisions]
        criteria=intent.get("acceptance_criteria",{}); failures=[]
        if severe: failures.append(f"{len(severe)} severe issue(s) remain unadjudicated")
        minimum=criteria.get("minimum_sample_size") or criteria.get("min_n")
        eligible=human if tier=="human" else simulated if tier=="simulation" else relevant
        if minimum is not None and (not eligible or max(x["row_count"] for x in eligible)<minimum): failures.append(f"minimum sample size {minimum} was not met")
        minimum_alpha=criteria.get("minimum_alpha") or criteria.get("min_alpha")
        if minimum_alpha is not None:
            alphas=[]
            for rec in store.records("analyses"):
                if rec.get("analysis_type")=="scale":
                    try: alphas.append(json.loads((store.root/rec["artifact"]).read_text()).get("cronbach_alpha"))
                    except (OSError,json.JSONDecodeError): pass
            alphas=[x for x in alphas if x is not None]
            if not alphas: status="inconclusive"; reasons.append("The declared alpha criterion has not been evaluated.")
            elif max(alphas)<minimum_alpha: failures.append(f"minimum alpha {minimum_alpha} was not met")
        if failures: status="challenged"; reasons.extend(failures)
        elif not reasons: status="supported"; reasons.append("Required evidence exists at the declared tier and no blocking challenge remains.")
    result={"validation_id":store.next_id("validation","validations"),"intent_id":intent_id,"status":status,"evidence_source_ids":[x["source_id"] for x in relevant],"reasons":reasons,"limitations":["Status is bounded to the declared evidence tier; it is not global instrument validity."],"created_at":now()}
    store.put_record("validations",result["validation_id"],result); store.mutate("validation.evaluated",{}); return result
