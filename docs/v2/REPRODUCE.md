# Reproducing the v2 follow-up study

> **Superseded for execution (closeout, see [ERRATA C8](../closeout/ERRATA.md)).** Use
> [`docs/closeout/REPRODUCE.md`](../closeout/REPRODUCE.md) and the driver `scripts/closeout.py`. This page is kept as
> the historical command record of the v2 study, but it is not a runnable sequence from one checkout:
> section 1 checks out `experiment-v2`, while `build_report_v2.py`, `build_deck_v2.py`, `package_v2.py` and
> `verify_v2_release.py` (sections 8 and 10) exist only from `v2.0.0` on, and `v2_nondeterminism.py`
> (section 7) only after `v2.0.0`. The corrected workflow separates an experiment checkout (`experiment-v2`,
> simulator commands) from a delivery-tools checkout (analysis, rendering, packaging, verification). Some
> commands below also contain placeholders (`<dev>`, `<final>`, `<all 23 IDs>`) that the driver fills in.

All commands run from a clone of `https://github.com/ywen0511/CSCI645-Project`. Paths in angle brackets
are yours to choose. Every command below was run in this study (cluster jobs used the wrappers described in
§9, which only set environment variables and call these commands).

Legend: **[v1]** script that existed in v1 (unchanged or extended), **[v2]** new in the follow-up.

## 1. Environment

Isaac Lab v3.0.0, Isaac Sim 6.2.0.0, PhysX (`isaacsim_physx`), RSL-RL 5.5.1, PyTorch 2.11 (CUDA 13), Python 3.12,
exactly as in v1: follow [`docs/SETUP_REMOTE.md`](../SETUP_REMOTE.md) and check the lock
`configs/v2/frozen/pip-freeze.txt` (byte-identical to `configs/frozen/pip-freeze.txt`). GPU simulation needs a
Vulkan-capable NVIDIA driver (v1 used 580.x with a user-space ICD; see SETUP_REMOTE). CPU-only steps (analysis,
packaging, verification) need Python 3 with numpy and matplotlib; the report/deck builders also need
`markdown`, `python-pptx`, Chrome and LibreOffice.

```bash
git clone https://github.com/ywen0511/CSCI645-Project.git && cd CSCI645-Project
git checkout experiment-v2          # exact source of every v2 training/evaluation run
export PYTHONPATH=$PWD/src
python -m unittest discover -s tests          # CPU logic tests (32 pass, 1 skipped without Isaac Lab)
```

## 2. Download and verify releases [v2]

```bash
python3 scripts/download_release.py --tag v2.0.0 --output downloads/v2      # anonymous, no credentials
cd downloads/v2 && sha256sum -c SHA256SUMS && cd -
python3 scripts/verify_archives.py --bundle downloads/v2 --extract downloads/v2/x   # re-hash every member
python3 scripts/download_release.py --tag v1.0.0 --output downloads/v1      # v1 assets (for Stage 1/2)
python3 scripts/verify_archives.py --bundle downloads/v1 --extract downloads/v1/extracted
```

## 3. One deterministic episode and one policy replay

```bash
# [v1] one clean nominal episode (v1-equivalent defaults)
python scripts/run_scripted.py --method nominal --num-envs 1 --episodes 1 --output out/nominal_one
# [v2] a matrix with one geometry controller and one downloaded checkpoint on the final suite
cat > /tmp/one.json <<'EOF'
{"name": "one", "suite": "configs/v2/suites/final.jsonl", "num_envs": 900, "protocol": "configs/v2/frozen/protocol.json",
 "entries": [{"id": "geometry_1p5cm", "method": "geometry", "overrides": {"align_max": 0.015}},
             {"id": "combined_seed11__final", "method": "combined", "training_seed": 11,
              "checkpoint": "combined_seed11/checkpoints/final.pt"}]}
EOF
python scripts/eval_matrix.py --matrix /tmp/one.json --output out/one --checkpoint-root downloads/v2/x
```

`eval_matrix.py` checks suite, configuration, controller and checkpoint hashes, refuses to mix protocols,
and resumes by case ID (completed cases are skipped, duplicates rejected).

## 4. Stage 0–1: smoke, negative controls, v1 audit

```bash
# [v1] negative controls (20 clean cases each)
python scripts/run_scripted.py --method nominal --num-envs 20 --episodes 20 --set 'negative_control="no_receiver"' --output out/neg_no_receiver
python scripts/run_scripted.py --method nominal --num-envs 20 --episodes 20 --set 'negative_control="giver_holds"' --output out/neg_giver_holds
python scripts/run_scripted.py --method nominal --num-envs 20 --episodes 20 --set 'negative_control="table_support"' \
    --set 'table_size_override=[0.06,0.30,0.20]' --trace 2 --output out/neg_table_support
# [v1] regenerate v1 tables from downloaded raw records (run in a clean clone at tag v1.0.0)
python3 scripts/build_run_index.py --runs downloads/v1/extracted/results --output out/v1/run_index.json
python3 scripts/analyze.py --run-index out/v1/run_index.json --output out/v1/primary
python3 scripts/build_run_index.py --runs downloads/v1/extracted/results --output out/v1/run_index_secondary.json \
    --eval-dir eval_final_checkpoint --scripted-eval-dir eval
python3 scripts/analyze.py --run-index out/v1/run_index_secondary.json --output out/v1/secondary
# [v2] reconciliation of v1 records, checkpoints and selection
python3 scripts/v2_audit_v1.py --bundle downloads/v1 --extracted downloads/v1/extracted --output results/v2/audit/v1_reconciliation.json
# [v1] separate-process replay with the experiment-v1 source (clean clone), predeclared sample, two batch sizes
python scripts/evaluate.py --method combined --training-seed 11 --protocol configs/frozen/protocol.json \
    --checkpoint downloads/v1/extracted/combined_seed11/checkpoints/step_000000000.pt downloads/v1/extracted/combined_seed11/checkpoints/final.pt \
    --suite configs/v2/suites/v1_replay_sample.jsonl --run-id combined_seed11 --output out/replay_b23 --num-envs 23 --trace-cases <all 23 IDs>
#   (repeat for nominal/geometry and all nine runs, and with --num-envs 1 into out/replay_b1)
python3 scripts/v2_compare_replay.py --archived downloads/v1/extracted/results/eval --archived downloads/v1/extracted/results/eval_final_checkpoint \
    --replay out/replay_b23 --replay out/replay_b1 --output results/v2/audit/v1_replay_comparison.json
```

## 5. Stage 2–3: development diagnostics, constants, ablations [v2]

```bash
python3 scripts/make_v2_suites.py development && python3 scripts/make_v2_suites.py feasibility && python3 scripts/make_v2_suites.py valproxy
python3 scripts/make_v2_matrices.py dev            # dev_controls, dev_learned, dev_geometry
for m in dev_controls dev_learned dev_geometry dev_feasibility dev_feas_constants dev_valproxy \
         dev_constants_ext dev_feas_constants_ext dev_failure_traces; do
  python scripts/eval_matrix.py --matrix configs/v2/matrices/$m.json --output <dev>/${m#dev_} --checkpoint-root downloads/v1/extracted
done
# output folder names used by the analysis: controls, learned, geometry, feasibility, feas_constants, valproxy,
# constants_ext, feas_constants_ext, failure_traces
python3 scripts/v2_analyze_dev.py --dev <dev> --output results/v2/diagnostics --n-boot 4000   # committed tables used 4,000 replicates
python3 scripts/v2_select_constants.py --dev <dev> --output results/v2/diagnostics/constants_v2.json
python3 scripts/v2_plot_traces.py --case v2dev-joint_early_stress-0017 --trace <dev>/failure_traces/traces/geometry_zero.json \
    --trace <dev>/failure_traces/traces/combined_final_s11.json --output fig.png
```

## 6. Stage 4: pilots and freeze [v2]

```bash
python scripts/train.py --method combined --seed 101 --protocol configs/v2/pilot/P2_zero_mean_init.json --run-type pilot \
    --transitions 5000000 --checkpoint-every 1000000 --output <pilot>/train/combined_P2_s101
#   (also combined P1 s101 5M, residual P2 s101 4.5M, smoke combined P2 s102 98,304 + resume to 196,608)
python3 scripts/make_ckpt_matrix.py --run-dir <pilot>/train/combined_P2_s101 --method combined --seed 101 \
    --suite configs/v2/suites/development.jsonl --protocol configs/v2/pilot/P2_zero_mean_init.json --tags all \
    --name p --output <pilot>/eval/combined_P2_s101/matrix_development.json
python scripts/eval_matrix.py --matrix <pilot>/eval/combined_P2_s101/matrix_development.json --output <pilot>/eval/combined_P2_s101/development
python3 scripts/v2_analyze_pilots.py --pilot <pilot> --output results/v2/pilot
python3 scripts/make_v2_protocol.py --actor-init zero_mean_output --const-geometry-1p5cm 0.010 --const-geometry-1cm 0.007 --const-nominal 0.009
python3 scripts/make_v2_suites.py heldout --protocol configs/v2/protocol.json
python3 scripts/check_v2_suites.py
python  scripts/freeze_v2.py --protocol configs/v2/protocol.json --output configs/v2/frozen --freeze-utc <UTC>   # needs Isaac Lab Python
python3 scripts/make_v2_final_matrices.py --protocol configs/v2/protocol.json --det-only
```

## 7. Stage 5: final training, selection, evaluation, analysis [v1 train.py extended; rest v2]

```bash
P=configs/v2/frozen/protocol.json
for M in residual combined combined_no_phase; do for S in 11 22 33; do
  python scripts/train.py --method $M --seed $S --protocol $P --run-type final --output <final>/train/${M}_seed$S
  #   resume after interruption: add --resume <final>/train/${M}_seed$S/checkpoints/latest.pt
  python3 scripts/make_ckpt_matrix.py --run-dir <final>/train/${M}_seed$S --method $M --seed $S \
      --suite configs/v2/suites/validation.jsonl --protocol $P --tags v2_candidates --name val --num-envs 400 \
      --output <final>/validation/${M}_seed$S/matrix.json
  python scripts/eval_matrix.py --matrix <final>/validation/${M}_seed$S/matrix.json --output <final>/validation/${M}_seed$S
done; done
python3 scripts/v2_select.py --train-root <final>/train --validation <final>/validation --output results/v2/final/selection
python3 scripts/make_v2_final_matrices.py --protocol configs/v2/protocol.json --train-root <final>/train \
    --selection results/v2/final/selection/selection.json
for f in configs/v2/matrices/final/final_*.json; do case $f in *manifest*) continue;; esac
  n=$(basename $f .json); python scripts/eval_matrix.py --matrix $f --output <final>/eval/${n#final_}; done
python3 scripts/v2_analyze_final.py --final <final>/eval --train <final>/train --output results/v2/summary
python3 scripts/v2_nondeterminism.py --final <final>/eval > results/v2/summary/nondeterminism_untrained_vs_zero.json
```

With the release assets, `<final>` is the extracted `raw-final-eval.tar.gz` (`final/eval`) and the
`train_log.jsonl` files from the checkpoint archives; `results/v2/summary/*.csv`, `tables.md` and
`summary.json` are regenerated byte for byte (figures are regenerated but PNG bytes may differ by library
version).

## 8. Stage 6: videos, report, deck, packaging [v2; record_video.py v1, extended]

```bash
python3 scripts/v2_select_videos.py --final <final>/eval --output-dir <videos> --plan video_plan.json
python scripts/record_video.py --plan video_plan.json --suite configs/v2/suites/final.jsonl --protocol configs/v2/frozen/protocol.json
python3 scripts/build_report_v2.py && python3 scripts/build_deck_v2.py && python3 scripts/build_report.py
python3 scripts/package_v2.py --v2-root <v2 run root> --videos <videos> --tag v2.0.0 \
    --experiment-commit $(git rev-parse experiment-v2^{commit}) --analysis-commit $(git rev-parse HEAD) \
    --output <release_dir> --redact <private work prefix>=<WORK>
```

## 9. Cluster wrappers and resume rules

The LSF wrappers used on the cluster (one GPU per job, self-terminating, wall-clock limited) only export the
Isaac Sim environment (Vulkan ICD, node-local caches) and call the commands above. Resume rules: training
resumes from `latest.pt` and refuses nothing silently (resumed runs write `run_resume.json`); `eval_matrix.py`
skips only case IDs whose existing records carry the same suite/config/controller/checkpoint hashes and
aborts on any mismatch; `freeze_v2.py` never overwrites a frozen protocol with different content; final runs
must come from a clean checkout at `experiment-v2` (the job wrappers check `git describe --exact-match` and
a clean tree). No command depends on a personal desktop path.

## 10. Verify the published release

```bash
git clone https://github.com/ywen0511/CSCI645-Project.git clone && git -C clone checkout v2.0.0
python3 -I clone/scripts/download_release.py --tag v2.0.0 --output dl && (cd dl && sha256sum -c SHA256SUMS)
python3 -I clone/scripts/verify_archives.py --bundle dl --extract x
python3 -I clone/scripts/verify_v2_release.py --bundle dl
python3 clone/scripts/v2_select.py --train-root x --validation x/final/validation --suite clone/configs/v2/suites/validation.jsonl --output regen/selection
python3 clone/scripts/v2_analyze_final.py --final x/final/eval --manifest clone/configs/v2/matrices/final/final_manifest.json \
    --selection regen/selection --train x --output regen/summary      # compare with clone/results/v2/summary (cmp)
# GPU replay of downloaded checkpoints: scripts/cluster_v2/verify_job.sh (matrix rule in docs/v2/RELEASE_VERIFICATION.md)
python3 clone/scripts/v2_compare_replay.py --archived x/final/eval --replay <replay out> --output replay_comparison.json
```

Byte-identical regeneration was observed with NumPy 2.4.4; other NumPy builds can change the last digit of
`np.polyfit` slopes in `residual_behaviour.csv` / `summary.json`.
