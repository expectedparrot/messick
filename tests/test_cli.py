import json
from pathlib import Path
from messick.cli import main

def call(capsys, *args):
    code=main(list(args)); return code,json.loads(capsys.readouterr().out)

def test_project_flow(tmp_path, capsys):
    code,out=call(capsys,"--project-dir",str(tmp_path),"init","--title","Test")
    assert code==0 and out["schema_version"]=="1.0" and out["revision"]==0
    assert out["argv"][-1]=="Test"
    survey=tmp_path/"source.ep"; survey.write_bytes(b"survey artifact")
    code,out=call(capsys,"--project-dir",str(tmp_path),"instrument","import","--survey",str(survey))
    assert code==0 and out["data"]["created"] is True and out["revision"]==1
    code,out=call(capsys,"--project-dir",str(tmp_path),"instrument","import","--survey",str(survey))
    assert out["data"]["created"] is False and out["revision"]==1
    code,out=call(capsys,"--project-dir",str(tmp_path),"agent","next")
    assert out["data"]["recommended_action"]["name"]=="intent add"

def test_import_registers_artifact_already_at_canonical_target(tmp_path, capsys):
    call(capsys,"--project-dir",str(tmp_path),"init","--title","Same path")
    first=tmp_path/"first.ep"; first.write_text("first")
    call(capsys,"--project-dir",str(tmp_path),"instrument","import","--survey",str(first))
    second=tmp_path/"instruments/instrument_v002.ep"; second.write_text("second")
    code,out=call(capsys,"--project-dir",str(tmp_path),"instrument","import","--survey",str(second),"--message","adjudicated revision")
    assert code==0 and out["data"]["instrument"]["revision_id"]=="v002"
    assert second.read_text()=="second"
    intent=tmp_path/"intent.json"; intent.write_text(json.dumps({"intent_id":"meaning","construct":"x","interpretation":"score means x","population":"adults","use":"research","evidence_tier":"static"}))
    call(capsys,"--project-dir",str(tmp_path),"intent","add","--input",str(intent))
    action=call(capsys,"--project-dir",str(tmp_path),"agent","next")[1]["data"]["recommended_action"]
    assert action["name"]=="instrument compare"

def test_errors_are_enveloped(tmp_path, capsys):
    code,out=call(capsys,"--project-dir",str(tmp_path),"validate")
    assert code==1 and out["status"]=="error" and out["errors"][0]["code"]=="PROJECT_NOT_FOUND"

def test_strict_validation_and_report(tmp_path, capsys):
    call(capsys,"--project-dir",str(tmp_path),"init","--title","Test")
    survey=tmp_path/"source.ep"; survey.write_text("survey")
    call(capsys,"--project-dir",str(tmp_path),"instrument","import","--survey",str(survey))
    intent=tmp_path/"intent.json"; intent.write_text(json.dumps({"intent_id":"meaning","construct":"x","interpretation":"score means x","population":"adults","use":"research","evidence_tier":"static"}))
    code,_=call(capsys,"--project-dir",str(tmp_path),"intent","add","--input",str(intent)); assert code==0
    code,_=call(capsys,"--project-dir",str(tmp_path),"validation","evaluate","--intent","meaning"); assert code==0
    code,out=call(capsys,"--project-dir",str(tmp_path),"validate","--strict"); assert code==0 and out["data"]["valid"]
    code,out=call(capsys,"--project-dir",str(tmp_path),"report","context"); assert code==0
    assert (tmp_path/"analysis/messick_report_context.json").is_file()
