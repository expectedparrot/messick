"""Deterministic instrument, path, textual-complexity, and burden checks."""
from __future__ import annotations
import math, re
from collections import Counter

ASSUMPTIONS={"version":"1.0","words_per_minute":200,"base_comprehension_seconds":2.0,"option_seconds":0.6,"open_text_seconds":20.0,"branch_overhead_seconds":0.5,"uncertainty_fraction":0.25}
VAGUE={"often","sometimes","regularly","usually","generally","recently","frequently","rarely"}
TECHNICAL={"synergy","utilize","paradigm","construct","operationalize"}

def inspect(s):
    qs=s["questions"]; issues=[]; seen=set()
    for q in qs:
        qid=q["id"]
        if not qid: issues.append(issue(None,"schema","error","Question has no stable ID."))
        elif qid in seen: issues.append(issue(qid,"schema","error","Question ID is duplicated."))
        seen.add(qid)
        if not q["text"].strip(): issues.append(issue(qid,"comprehension","error","Question text is empty."))
        opts=[str(x).strip() for x in q["options"]]
        dup=[x for x,n in Counter(x.lower() for x in opts).items() if n>1]
        if dup: issues.append(issue(qid,"response-mapping","warning",f"Duplicate response options: {', '.join(dup)}"))
        normalized=[re.sub(r"[^a-z0-9]+","",x.lower()) for x in opts]
        overlaps=sorted({opts[i] for i,x in enumerate(normalized) for j,y in enumerate(normalized) if i<j and x and y and (x in y or y in x)})
        if overlaps: issues.append(issue(qid,"response-mapping","warning",f"Potentially overlapping response options: {', '.join(overlaps)}"))
        issues.extend(complexity(q))
    ids={q["id"] for q in qs}; graph=branch_graph(s)
    for q in qs:
        references=re.findall(r"{{\s*([A-Za-z_][\w.]*)\s*}}",q["text"]+" "+str(q["instructions"]))
        for ref in references:
            if ref.split(".")[0] not in ids and ref.split(".")[0] not in ("agent","scenario"):
                issues.append(issue(q["id"],"schema","error",f"Template references unknown value `{ref}`."))
    for edge in graph["edges"]:
        if edge["from"] not in ids or edge["to"] not in ids: issues.append(issue(edge["from"],"branching","error",f"Branch references unknown question `{edge['to']}`."))
    if graph["cycles"]: issues.append(issue(None,"branching","error","Branch graph contains a cycle."))
    for qid in graph["unreachable"]: issues.append(issue(qid,"branching","warning","Question is unreachable."))
    return {"question_count":len(qs),"issues":issues,"issue_counts":dict(Counter(x["severity"] for x in issues)),"branching":graph}

def issue(qid,category,severity,message,feature=None):
    return {"question_id":qid,"category":category,"severity":severity,"message":message,"feature":feature}

def complexity(q):
    text=q["text"]; words=re.findall(r"[A-Za-z][A-Za-z'-]*",text); low=[w.lower() for w in words]; out=[]
    sentences=max(1,len(re.findall(r"[.!?]+",text))); syllables=sum(max(1,len(re.findall(r"[aeiouy]+",w.lower()))) for w in words)
    grade=0.39*(len(words)/sentences)+11.8*(syllables/max(1,len(words)))-15.59
    if len(words)>30: out.append(issue(q["id"],"burden/fatigue","warning","Prompt exceeds 30 words.","length"))
    if re.search(r"\bnot\b.*\b(not|never|except)\b",text,re.I): out.append(issue(q["id"],"comprehension","warning","Possible double negation.","negation"))
    if " and " in text.lower() and "?" in text: out.append(issue(q["id"],"ambiguity","warning","Possible multi-part or double-barreled question.","conjunction"))
    vague=sorted(set(low)&VAGUE)
    if vague: out.append(issue(q["id"],"ambiguity","warning",f"Vague quantifier or reference: {', '.join(vague)}.","vague-term"))
    technical=sorted(set(low)&TECHNICAL)
    if technical: out.append(issue(q["id"],"comprehension","warning",f"Potentially technical term: {', '.join(technical)}.","technical-term"))
    q["metrics"]={"word_count":len(words),"sentence_count":sentences,"reading_grade":round(max(0,grade),2),"option_count":len(q["options"]),"longest_option_words":max([len(str(x).split()) for x in q["options"]] or [0])}
    return out

def _edge(rule):
    if not isinstance(rule,dict): return None
    source=rule.get("source") or rule.get("question") or rule.get("from") or rule.get("current_question")
    target=rule.get("target") or rule.get("next_question") or rule.get("to")
    return {"from":source,"to":target,"condition":rule.get("condition") or rule.get("expression")} if source and target else None

def branch_graph(s):
    ids=[q["id"] for q in s["questions"] if q["id"]]; explicit=[x for x in (_edge(r) for r in s["rules"]) if x]
    edges=list(explicit); explicit_sources={e["from"] for e in explicit}
    for a,b in zip(ids,ids[1:]):
        if a not in explicit_sources: edges.append({"from":a,"to":b,"condition":"default"})
    adjacency={x:[] for x in ids}
    for e in edges:
        if e["from"] in adjacency and e["to"] in adjacency: adjacency[e["from"]].append(e["to"])
    reachable=set(); cycles=[]
    def walk(n,stack):
        if n in stack: cycles.append(stack[stack.index(n):]+[n]); return
        if n in reachable: return
        reachable.add(n)
        for nxt in adjacency.get(n,[]): walk(nxt,stack+[n])
    if ids: walk(ids[0],[])
    paths=[]
    def enumerate_paths(n,path):
        if n in path: return
        nxt=adjacency.get(n,[])
        if not nxt: paths.append(path+[n]); return
        for x in nxt:
            if len(paths)<1000: enumerate_paths(x,path+[n])
    if ids and not cycles: enumerate_paths(ids[0],[])
    return {"edges":edges,"cycles":cycles,"unreachable":[x for x in ids if x not in reachable],"paths":paths,"path_count":len(paths),"truncated":len(paths)>=1000}

def burden(s, assumptions=None):
    cfg={**ASSUMPTIONS,**(assumptions or {})}; estimates=[]
    for q in s["questions"]:
        complexity(q); m=q["metrics"]; reading=60*m["word_count"]/cfg["words_per_minute"]
        comprehension=cfg["base_comprehension_seconds"]+max(0,m["reading_grade"]-8)*.15
        recall=3.0 if re.search(r"past|last|remember|recall|how many",q["text"],re.I) else 1.0
        judgment=1.5+cfg["option_seconds"]*m["option_count"]
        response=cfg["open_text_seconds"] if (not q["options"] or "free" in q["type"] or "text" in q["type"]) else 1.0
        overhead=cfg["branch_overhead_seconds"] if any(e for e in branch_graph(s)["edges"] if e["from"]==q["id"] and e["condition"]!="default") else 0
        center=sum((reading,comprehension,recall,judgment,response,overhead)); u=cfg["uncertainty_fraction"]
        estimates.append({"question_id":q["id"],"seconds":{"low":round(center*(1-u),2),"central":round(center,2),"high":round(center*(1+u),2)},"components":{"reading":round(reading,2),"comprehension":round(comprehension,2),"recall":recall,"judgment":round(judgment,2),"response_entry":response,"conditional_overhead":overhead},"confidence":"low" if response>=cfg["open_text_seconds"] else "medium","basis":"versioned heuristic, not observed human timing"})
    by_id={x["question_id"]:x for x in estimates}; paths=branch_graph(s)["paths"] or [[q["id"] for q in s["questions"]]]
    totals=[{"questions":p,"seconds":round(sum(by_id[x]["seconds"]["central"] for x in p if x in by_id),2)} for p in paths]
    totals.sort(key=lambda x:x["seconds"]); typical=totals[len(totals)//2] if totals else {"questions":[],"seconds":0}
    return {"assumptions":cfg,"questions":estimates,"paths":{"shortest":totals[0] if totals else typical,"typical":typical,"longest":totals[-1] if totals else typical,"count":len(totals)},"warning":"Pre-fielding duration is estimated, not observed human completion time."}
