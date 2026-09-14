from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_lab_is_container_scoped_and_has_cleanup_guard():
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    script = (ROOT / "lab" / "run_demo.sh").read_text(encoding="utf-8")

    assert "NET_ADMIN" in compose
    assert "network_mode: host" not in compose
    assert "docker compose exec -T recorder ip route del default" in script
    assert "trap restore_lab EXIT INT TERM" in script
    assert "docker compose restart recorder" in script
