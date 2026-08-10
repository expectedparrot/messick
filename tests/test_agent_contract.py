import json
from pathlib import Path

from messick.cli import main


ROOT = Path(__file__).parents[1]


def call(capsys, root, *args, ok=True):
    code = main(["--project-dir", str(root), *args])
    result = json.loads(capsys.readouterr().out)
    if ok:
        assert code == 0, result
    return code, result


def test_agent_next_is_a_portable_complete_static_loop(tmp_path, capsys):
    ex = ROOT / "examples/simulation_only"
    call(capsys, tmp_path, "init", "--title", "Portable")
    first = call(capsys, tmp_path, "agent", "next")[1]["data"]["recommended_action"]
    assert first["cwd"] == str(tmp_path.resolve())
    assert first["argv"][:3] == ["messick", "--project-dir", str(tmp_path.resolve())]
    assert first["input_schema"]["properties"]["survey_path"]["placement"] == {"kind": "flag", "flag": "--survey"}

    call(capsys, tmp_path, "instrument", "import", "--survey", str(ex / "survey.ep"))
    intent = tmp_path / "static-intent.json"
    intent.write_text(json.dumps({"intent_id": "static", "construct": "trust", "interpretation": "score represents trust", "population": "adults", "use": "research", "evidence_tier": "static"}))
    call(capsys, tmp_path, "intent", "add", "--input", str(intent))

    names = []
    for _ in range(12):
        action = call(capsys, tmp_path, "agent", "next")[1]["data"]["recommended_action"]
        names.append(action["name"])
        if action.get("terminal"):
            break
        assert action["cwd"] == str(tmp_path.resolve())
        assert action["argv"][:3] == ["messick", "--project-dir", str(tmp_path.resolve())]
        call(capsys, tmp_path, *action["argv"][3:])
    assert names == ["inspect", "burden analyze", "options analyze", "validation evaluate", "report context", "report template", "validate strict", "complete"]


def test_execution_design_is_explicit_and_empty_design_fails(tmp_path, capsys):
    from edsl import Agent, AgentList, Model, ModelList

    ex = ROOT / "examples/simulation_only"
    call(capsys, tmp_path, "init", "--title", "Matrix")
    call(capsys, tmp_path, "instrument", "import", "--survey", str(ex / "survey.ep"))
    agents = tmp_path / "agents.ep"
    models = tmp_path / "models.ep"
    AgentList([Agent(traits={"profile": "a"}), Agent(traits={"profile": "b"})]).git.save(str(agents), message="test agents")
    ModelList([Model("test")]).git.save(str(models), message="test model")
    plan = call(capsys, tmp_path, "pretest", "plan", "--mode", "cognitive", "--agents", str(agents), "--models", str(models))[1]["data"]["plan"]
    assert plan["execution_design"] == {"instrument_question_count": 3, "question_count": 1, "scenario_count": 3, "agent_count": 2, "model_count": 1, "expected_calls": 6}
    assert plan["agent_list"]["sha256"] and plan["model_list"]["sha256"]
    generated = call(capsys, tmp_path, "job", "generate", "--plan", plan["plan_id"], "--output", "edsl_jobs/test.ep")[1]["data"]
    assert generated["job"]["execution"]["expected_calls"] == 6
    assert generated["job"]["agent_list"]["sha256"] == plan["agent_list"]["sha256"]
    assert generated["job"]["model_list"]["sha256"] == plan["model_list"]["sha256"]
    assert generated["handoff"][0]["argv"] == ["ep", "inspect", str(tmp_path / "edsl_jobs/test.ep")]

    empty = tmp_path / "empty-agents.ep"
    AgentList([]).git.save(str(empty), message="empty")
    code, result = call(capsys, tmp_path, "pretest", "plan", "--mode", "cognitive", "--agents", str(empty), "--models", str(models), ok=False)
    assert code == 1
    assert result["errors"][0]["code"] == "EMPTY_EXECUTION_DESIGN"


def test_bounded_default_agents_require_an_explicit_model(tmp_path, capsys):
    from edsl import Model, ModelList

    ex = ROOT / "examples/simulation_only"
    call(capsys, tmp_path, "init", "--title", "Default matrix")
    call(capsys, tmp_path, "instrument", "import", "--survey", str(ex / "survey.ep"))
    code, result = call(capsys, tmp_path, "pretest", "plan", "--mode", "cognitive", ok=False)
    assert code == 1 and result["errors"][0]["code"] == "MODEL_SELECTION_REQUIRED"
    models = tmp_path / "selected-model.ep"
    ModelList([Model("test")]).git.save(str(models), message="ep-agent selected model")
    plan = call(capsys, tmp_path, "pretest", "plan", "--mode", "cognitive", "--models", str(models))[1]["data"]["plan"]
    assert plan["agent_list"]["origin"] == "bounded-default"
    assert plan["model_list"]["origin"] == "explicit"
    assert plan["execution_design"]["expected_calls"] == 9


def test_agent_next_completes_simulated_results_analysis_loop(tmp_path, capsys):
    from edsl import Model, ModelList

    ex = ROOT / "examples/simulation_only"
    call(capsys, tmp_path, "init", "--title", "Complete simulation")
    call(capsys, tmp_path, "instrument", "import", "--survey", str(ex / "survey.ep"))
    call(capsys, tmp_path, "intent", "add", "--input", str(ex / "intent.json"))
    call(capsys, tmp_path, "scale", "add", "--input", str(ex / "scale.json"))
    models = tmp_path / "current-model.ep"
    ModelList([Model("test")]).git.save(str(models), message="ep-agent current model")

    names = []
    for _ in range(20):
        action = call(capsys, tmp_path, "agent", "next")[1]["data"]["recommended_action"]
        names.append(action["name"])
        if action.get("terminal"):
            break
        argv = action["argv"][3:]
        if action["name"] == "pretest plan":
            assert "<agents_path>" not in argv
            assert action["input_schema"]["properties"]["agents_path"]["placement"]["kind"] == "conditional_flag"
            argv = [str(models) if value == "<models_path>" else value for value in argv]
        elif action["name"] == "results ingest":
            argv = [str(ex / "results.ep") if value == "<results_path>" else value for value in argv]
        call(capsys, tmp_path, *argv)

    assert names == [
        "inspect", "burden analyze", "options analyze", "scoring validate",
        "pretest plan", "job generate", "results ingest", "pretest analyze",
        "scale analyze", "validation evaluate", "report context", "report template",
        "validate strict", "complete",
    ]
