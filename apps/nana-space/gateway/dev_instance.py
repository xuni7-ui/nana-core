"""Explicitly create/run a fresh owned development instance. Never opens a production home."""

import argparse, json, os, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
MARKER = "nana-space-development.json"


def initialize(home, project=REPO):
    from nana_core.life.config import LifeConfig, write_config
    from nana_core.life.surfaces import SurfaceBinding
    from nana_core.life.application import LifeApplication
    from nana_core.continuity.project_work.service import material_for

    home = Path(home).absolute()
    if home.exists() or home.is_symlink():
        raise ValueError("NEW_DEVELOPMENT_HOME_REQUIRED")
    config = LifeConfig(
        project_root=str(project),
        materials=(material_for(project, "src/nana_core/continuity/recurrence.py"),),
        practice=material_for(project, "src/nana_core/continuity/identity.py"),
        heldout=material_for(project, "src/nana_core/continuity/autonomy/requests.py"),
        transfer=material_for(project, "src/nana_core/continuity/subject/social.py"),
        max_autonomous_materials=0,
        provider_calls_per_day=0,
        provider_calls_per_hour=0,
        provider_total_calls_limit=0,
        provider_total_reserved_cost_micro=0,
        surface_bindings=(
            SurfaceBinding(
                binding_id="nana.space",
                platform="nana.space",
                surface="chat.direct",
                adapter="nana-space.gateway",
            ),
        ),
    )
    write_config(home, config)
    with LifeApplication(home, bootstrap_grant=False) as app:
        identity = app.runtime.identity_id
    marker = home / MARKER
    marker.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "realm": "OWNED_DEVELOPMENT_ONLY",
                "identity_id": identity,
                "binding_id": "nana.space",
                "paid_provider": False,
                "production": False,
            }
        )
    )
    marker.chmod(0o600)
    return {
        "identity_id": identity,
        "realm": "OWNED_DEVELOPMENT_ONLY",
        "production": False,
    }


def check_home(home, identity):
    home = Path(home).absolute()
    marker = home / MARKER
    if (
        home != home.resolve()
        or not home.is_dir()
        or home.stat().st_uid != os.getuid()
        or home.stat().st_mode & 0o077
    ):
        raise ValueError("PRIVATE_DEVELOPMENT_HOME_REQUIRED")
    if (
        marker.is_symlink()
        or not marker.is_file()
        or marker.stat().st_uid != os.getuid()
        or marker.stat().st_mode & 0o077
        or marker.stat().st_size > 2048
    ):
        raise ValueError("DEVELOPMENT_MARKER_REQUIRED")
    value = json.loads(marker.read_text())
    if (
        value.get("realm") != "OWNED_DEVELOPMENT_ONLY"
        or value.get("identity_id") != identity
        or value.get("production") is not False
    ):
        raise ValueError("DEVELOPMENT_IDENTITY_MISMATCH")
    return home


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=["init", "run"])
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--subject-id")
    p.add_argument("--seconds", type=float, default=3600)
    a = p.parse_args()
    if a.operation == "init":
        print(json.dumps(initialize(a.home)))
        return
    check_home(a.home, a.subject_id)
    from nana_core.life.config import load_config

    config = load_config(a.home)
    if (
        config.max_autonomous_materials
        or config.provider_calls_per_day
        or config.provider_hosts
        or config.allow_local_skills
        or config.owned_application_profile
    ):
        raise ValueError("QUALIFICATION_PROFILE_CHANGED")
    from nana_core.life.__main__ import run

    run(a.home, a.seconds, headless=True, router=None, control_enabled=True)


if __name__ == "__main__":
    main()
