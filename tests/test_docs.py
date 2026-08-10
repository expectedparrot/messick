from pathlib import Path

ROOT=Path(__file__).parents[1]

def test_readme_has_agent_bootstrap_and_artwork():
    text=(ROOT/"README.md").read_text()
    assert "## Copy and paste into Codex or Claude Code" in text
    assert "messick agent next" in text
    assert "ep jobs cost" in text
    assert "explicit approval" in text
    assert "docs/assets/messick-artwork.png" in text
    assert (ROOT/"docs/assets/messick-artwork.png").is_file()

def test_static_docs_link_agent_guidance_and_artwork():
    index=(ROOT/"docs/index.html").read_text()
    assert 'src="assets/messick-artwork.png"' in index
    assert 'href="agent.html"' in index
    assert "messick agent next" in (ROOT/"docs/agent.html").read_text()
