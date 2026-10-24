from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GEOMETRY_PATH = REPO_ROOT / "shared" / "config" / "sand_table_rev_c.json"
FIXTURE_ROOT = REPO_ROOT / "fixtures" / "replay"
SAMPLE_FIXTURE = FIXTURE_ROOT / "sample_trial"
