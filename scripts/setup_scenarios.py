#!/usr/bin/env python3
"""
setup_scenarios.py  --  prepare data directories for all scenarios in a YAML file.

Usage:
  cd to user
  python3 ../scripts/setup_scenarios.py bestfit_2030_oct.yaml

Writes:
  user/data/{scenario_name}/hydro_config
  user/data/{scenario_name}/sampler_config
  user/data/{scenario_name}/smash_config
  user/data/{scenario_name}/run_settings   <- stages, loops for run_chain.sh
  user/batch_run_{timestamp}.sh                   <- ready to feed to PBS/SLURM or bash
"""

import os, sys, shutil
from datetime import datetime
from pathlib import Path
import yaml

# ── Locate FRAMEWORK_ROOT ──────────────────────────────────────────────────────
def find_framework_root():
    env_val = os.environ.get("FRAMEWORK_ROOT")
    if env_val:
        return Path(env_val)
    here = Path(__file__).resolve().parent
    for parent in [here] + list(here.parents):
        candidate = parent / "framework.env"
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                if line.startswith("FRAMEWORK_ROOT="):
                    return Path(line.split("=", 1)[1].strip())
    raise RuntimeError("FRAMEWORK_ROOT not set and framework.env not found")

FRAMEWORK_ROOT = find_framework_root()
USER_DIR     = FRAMEWORK_ROOT / "user"
BASE_CONFIGS   = FRAMEWORK_ROOT / "base_configs"
DATA_DIR       = USER_DIR / "data"


def patch_config(template_path: Path, overrides: dict, output_path: Path):
    """
    Read template_path, replace values for matching keys, write to output_path.
    Only the keys listed in `overrides` are changed; all other lines are passed
    through verbatim.  Reports keys that were not found in the template (likely
    a typo in the scenario file).
    """
    lines = template_path.read_text().splitlines(keepends=True)
    matched = set()
    patched = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            key = parts[0].rstrip(":")   # handle both "key value" and "key: value"
            for ovr_key, ovr_val in overrides.items():
                if key == ovr_key.rstrip(":"):
                    line = line.replace(parts[1], str(ovr_val), 1)
                    matched.add(ovr_key)
                    break
        patched.append(line)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(patched))
    unmatched = set(overrides) - matched
    if unmatched:
        print(f"  WARNING: the following keys from the scenario were not found "
              f"in {template_path.name}: {sorted(unmatched)}", file=sys.stderr)


def setup_scenario(name: str, cfg: dict, defaults: dict, timestamp: str):
    scenario_dir = DATA_DIR / name
    scenario_dir.mkdir(parents=True, exist_ok=True)
    (scenario_dir / "logs").mkdir(exist_ok=True)

    hydro_base   = cfg.get("hydro_base",   defaults.get("hydro_base"))
    sampler_base = cfg.get("sampler_base", defaults.get("sampler_base"))
    smash_base   = cfg.get("smash_base",   defaults.get("smash_base"))

    patch_config(BASE_CONFIGS / "hydro"   / hydro_base,
                 cfg.get("hydro",   {}),
                 scenario_dir / "hydro_config")
    patch_config(BASE_CONFIGS / "sampler" / sampler_base,
                 cfg.get("sampler", {}),
                 scenario_dir / "sampler_config")
    patch_config(BASE_CONFIGS / "smash"   / smash_base,
                 cfg.get("smash",   {}),
                 scenario_dir / "smash_config")

    # Write a small settings file consumed by run_chain.sh
    stages = cfg.get("stages", defaults.get("stages", ["hydro", "sampler", "smash"]))
    loops  = cfg.get("loops",  defaults.get("loops",  2))
    settings = (
        f"STAGES=\"{' '.join(stages)}\"\n"
        f"LOOPS={loops}\n"
    )
    (scenario_dir / "run_settings").write_text(settings)

    return f"PREFIX={name} bash {FRAMEWORK_ROOT}/scripts/run_chain.sh\n"


def main(scenario_file: str):
    scenario_file = Path(scenario_file).resolve()
    doc = yaml.safe_load(scenario_file.read_text())
    defaults  = doc.get("defaults",  {})
    scenarios = doc.get("scenarios", [])

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_path = Path(f"batch_run_{timestamp}.sh")

    with batch_path.open("w") as batch:
        batch.write("#!/bin/bash\n")
        for s in scenarios:
            name = s["name"]
            print(f"Setting up scenario: {name}")
            line = setup_scenario(name, s, defaults, timestamp)
            batch.write(line)

    batch_path.chmod(0o755)
    print(f"\nBatch file written to: {batch_path.resolve()}")
    print(f"Run with:  bash {batch_path}  (or submit individual lines to PBS/SLURM)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <scenarios.yaml>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
