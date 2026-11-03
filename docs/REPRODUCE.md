# Reproduction guide

Everything below uses only this repository, the official Isaac Lab/Isaac Sim distributions and the
assets of the GitHub Release. Commands run from the repository root with the environment of
`docs/SETUP_REMOTE.md` active. Isaac Lab 3.0 runs headless by default.

## 0. Get the exact source

```bash
git clone https://github.com/ywen0511/CSCI645-Project.git && cd CSCI645-Project
git checkout experiment-v1        # experiment source used for every final run
export PYTHONPATH=$PWD/src:$PYTHONPATH
python3 scripts/check_handoff.py && python3 -B -m unittest discover -s tests -v
```

`experiment-v1` contains the frozen protocol `configs/frozen/protocol.json`
(SHA-256 `9727eae67fdab5ce2c908e7b467f510707a668d89531cad22acd6286d83f97fc`) and the three case suites.
Later commits only add analysis, report and release material.

## 1. Download and verify the release

```bash
mkdir downloads && cd downloads
gh release download v1.0.0 --repo ywen0511/CSCI645-Project      # or download the assets in a browser
sha256sum -c SHA256SUMS
python3 ../scripts/verify_release.py --bundle . --protocol ../configs/frozen/protocol.json
for f in *.tar.gz; do tar xzf "$f"; done
cd ..
```

`checkpoints.json` lists, for every method and seed, the selected/final/resume checkpoint members, their
SHA-256 hashes, transitions, validation score, observation schema and replay command.

## 2. Single episodes of the training-free controllers

```bash
python scripts/run_scripted.py --method nominal --num-envs 1 --episodes 1 --output outputs/nominal_one
python scripts/run_scripted.py --method geometry --suite configs/frozen/suites/development.jsonl \
    --case-ids development-position_stress-0000 --num-envs 1 --output outputs/geometry_one
```

## 3. Replay a downloaded policy (separate process)

```bash
python scripts/evaluate.py --method combined --training-seed 11 \
    --checkpoint downloads/combined_seed11/checkpoints/<selected>.pt \
    --suite configs/frozen/suites/final.jsonl --limit 10 --run-id combined_seed11 --output outputs/replay
```

Replace `<selected>` with `selected_checkpoint` from `checkpoints.json`. Evaluation is deterministic
(no exploration, frozen normalization). Batched GPU physics is not bitwise reproducible across batch
compositions; the release verification record states the observed agreement with the archived records.

## 4. Regenerate tables and figures from the raw records

```bash
python3 scripts/build_run_index.py --runs downloads/results --output downloads/results/run_index.json
python3 scripts/analyze.py --run-index downloads/results/run_index.json --output outputs/summary
```

`analyze.py` needs only NumPy and Matplotlib and rebuilds `counts.csv`, `metrics_per_run.csv`,
`metrics_per_method.csv`, `comparisons.csv`, `selection.json`, `tables.md` and `figures/`.

## 5. Resume training from a checkpoint

```bash
python scripts/train.py --method combined --seed 11 --protocol configs/frozen/protocol.json \
    --output runs/combined_seed11 --resume downloads/combined_seed11/checkpoints/latest.pt
```

Resume restores model, optimizer, iteration, transition counter, curriculum position and RNG states and
restarts the episodes at a boundary (an approximate continuation, not a bitwise replay of simulator state).

## 6. Full experiment

```bash
python3 scripts/run_experiments.py --protocol configs/frozen/protocol.json --output runs/final --resume
```

This trains the nine runs (3 learned methods x seeds 11/22/33, 10,027,008 transitions each, ~15 min per
run on one A100 with 1024 environments), validates the candidate checkpoints on the validation suite,
selects one per run (highest validation success, then lowest drop rate, then earliest step), evaluates the
selected checkpoints plus `nominal` and `geometry` on all 1,800 final cases, and regenerates the summary.
The reported runs executed these same commands as independent one-GPU batch jobs in parallel.

## 7. Videos

```bash
python scripts/record_video.py --method geometry --suite configs/frozen/suites/final.jsonl \
    --case-id final-joint_early_stress-0000 --run-id geometry --output outputs/geometry.mp4
```

Videos re-run a case in one environment with a Newton Warp camera (rendering only); the sidecar JSON
stores provenance and compares the replay outcome with the archived evaluation record.
