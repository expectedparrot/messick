import json
from pathlib import Path
from messick.cli import main

ROOT=Path(__file__).parents[1]
def run(capsys,root,*args):
    code=main(["--project-dir",str(root),*args]); output=json.loads(capsys.readouterr().out); assert code==0,output; return output

def test_simulation_workflow(tmp_path,capsys):
    ex=ROOT/"examples/simulation_only"
    run(capsys,tmp_path,"init","--title","Trust")
    run(capsys,tmp_path,"instrument","import","--survey",str(ex/"survey.ep"))
    run(capsys,tmp_path,"intent","add","--input",str(ex/"intent.json"))
    run(capsys,tmp_path,"scale","add","--input",str(ex/"scale.json"))
    inspected=run(capsys,tmp_path,"inspect"); assert inspected["data"]["summary"]["question_count"]==3
    burden=run(capsys,tmp_path,"burden","analyze"); assert burden["data"]["paths"]["longest"]["seconds"]>0
    planned=run(capsys,tmp_path,"pretest","plan","--mode","behavioral"); pid=planned["data"]["plan"]["plan_id"]
    job=run(capsys,tmp_path,"job","generate","--plan",pid,"--output","edsl_jobs/pilot.ep"); assert job["data"]["handoff"][2]["approval_required"]
    ingested=run(capsys,tmp_path,"results","ingest","--plan",pid,"--results",str(ex/"results.ep")); sid=ingested["data"]["source"]["source_id"]
    analysis=run(capsys,tmp_path,"scale","analyze","--scale","workplace_trust","--source",sid); assert analysis["data"]["cronbach_alpha"] is not None
    validation=run(capsys,tmp_path,"validation","evaluate","--intent","trust_mean"); assert validation["data"]["validation"]["status"]=="supported"
    report=run(capsys,tmp_path,"report","context"); assert Path(report["artifacts"]["report_context"]).is_file()

def test_human_sources_are_not_pooled(tmp_path,capsys):
    ex=ROOT/"examples/simulation_only"; run(capsys,tmp_path,"init","--title","Trust"); run(capsys,tmp_path,"instrument","import","--survey",str(ex/"survey.ep"))
    sim=run(capsys,tmp_path,"responses","ingest","--source-type","benchmark","--input",str(ex/"results.ep"),"--instrument-revision","v001","--input-format","json")["data"]["source"]["source_id"]
    human=run(capsys,tmp_path,"responses","ingest","--source-type","human","--input",str(ex/"results.ep"),"--instrument-revision","v001","--input-format","json")["data"]["source"]["source_id"]
    result=run(capsys,tmp_path,"source","compare","--left",sim,"--right",human); assert result["data"]["pooled"] is False

def test_real_edsl_results_package_is_ingested(tmp_path,capsys):
    from edsl import Agent,Model,QuestionMultipleChoice,Results,Scenario,Survey
    from edsl.results import Result
    survey=Survey([QuestionMultipleChoice(question_name="q",question_text="Q?",question_options=[1,2])])
    result=Result(agent=Agent(traits={"group":"a"}),scenario=Scenario(),model=Model("test"),iteration=0,answer={"q":1},prompt={})
    package=tmp_path/"real.results.ep"; Results(survey=survey,data=[result]).git.save(str(package),message="fixture")
    ex=ROOT/"examples/simulation_only"; run(capsys,tmp_path,"init","--title","Real EDSL"); run(capsys,tmp_path,"instrument","import","--survey",str(ex/"survey.ep"))
    source=run(capsys,tmp_path,"responses","ingest","--source-type","human","--input",str(package),"--instrument-revision","v001","--input-format","results-ep")
    assert source["data"]["source"]["row_count"]==1
