import gzip,json
from pathlib import Path
from messick.artifacts import survey
from messick.diagnostics import branch_graph,burden,inspect
from messick.analysis import response_diagnostics,scale

def test_compressed_ep_and_branch_paths(tmp_path):
    value={"questions":[{"question_name":"q1","question_text":"Continue?","question_options":["yes","no"],"question_type":"multiple_choice"},{"question_name":"q2","question_text":"Why?","question_type":"free_text"}],"rule_collection":{"rules":[{"current_q":0,"next_q":1,"expression":"q1 == 'yes'"}]}}
    path=tmp_path/"survey.ep"
    with gzip.open(path,"wt") as f: json.dump(value,f)
    parsed=survey(path); graph=branch_graph(parsed)
    assert [q["id"] for q in parsed["questions"]]==["q1","q2"]
    assert graph["paths"]==[["q1","q2"]]

def test_complexity_and_burden_are_reproducible():
    s={"questions":[{"id":"q","text":"I do not never feel supported and respected usually?","type":"multiple_choice","options":[1,2,3],"instructions":"","raw":{},"index":0}],"rules":[]}
    findings=inspect(s)["issues"]
    assert {x["feature"] for x in findings if x.get("feature")} >= {"negation","conjunction","vague-term"}
    assert burden(s)==burden(s)

def test_declared_bounds_and_reverse_scoring():
    rows=[{"a":1,"b":5},{"a":2,"b":4},{"a":3,"b":3},{"a":4,"b":2},{"a":5,"b":1}]
    diagnostics=response_diagnostics(rows,{"a":(1,5)})
    a=next(x for x in diagnostics["items"] if x["question_id"]=="a")
    assert a["floor_rate"]==.2 and a["ceiling_rate"]==.2
    result=scale(rows,{"scale_id":"s","items":["a","b"],"reverse_scored":["b"],"range":[1,5]})
    assert result["cronbach_alpha"]==1.0

def test_git_backed_edsl_survey(tmp_path):
    from edsl import QuestionMultipleChoice,Survey
    path=tmp_path/"survey.ep"; Survey([QuestionMultipleChoice(question_name="q",question_text="Q?",question_options=["a","b"])]).git.save(str(path),message="fixture")
    assert survey(path)["questions"][0]["id"]=="q"
