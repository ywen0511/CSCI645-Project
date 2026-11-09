# CPU workflow review before the V4 freeze

Reviewed base: `f68136211e6b0debac01e5a856f88249d0a7738c` on
`study/v4-grasp-uncertainty`. The preparation agent performed no GPU or simulator work.
No development/acceptance result, simulator code, numerical condition, training setting,
checkpoint or published release was changed. This is workflow maintenance before freeze.

## Findings addressed

1. Status still said acceptance had not started although the uploaded acceptance record
   has passed A1–A9 and smoke resume. The status now points to that record and its
   mixed-commit provenance. It does not claim a new acceptance run at the maintenance SHA.
2. The preregistration text claimed a completed freeze and referenced absent generated
   files. It now distinguishes the protocol specification from actual freeze evidence.
   README now directs readers to V4 and accurately reports 34 byte-identical tables plus
   one numerically equal table in V3 maintenance verification.
3. `v4_freeze.py freeze` did not require completed pilots or acceptance and could overwrite
   an existing freeze. It now checks the detailed acceptance flags, provenance, all four
   declared completed pilots, the 24M all-attempt budget, configuration decision, hashed
   pilot evidence and five-by-five formal seeds/budgets before writing. Pilot evidence and
   acceptance/protocol documentation are included in frozen hashes. The read-only `check`
   command exposes this gate; it is expected to fail on the current public snapshot because
   the pilot completion report is absent. This is an honest pending requirement.
4. Final-suite generation previously overwrote its outputs. It now reproduces identical
   bytes on repeat runs and refuses to overwrite different suite/manifest bytes. It keeps
   the pre-final freeze separate and unmodified.
5. An absent frozen matrix directory could produce an empty successful selection. Selection
   now requires all 25 declared runs and six entries per run (step 0 plus five candidates),
   validates case metadata and outcome flags, binds every record to the actual checkpoint
   file SHA256 and experiment source, and writes results only after every run passes.
   The CLI therefore requires `--checkpoint-root <runs>/train`. Config/controller hashes
   must be present and consistent within each candidate's records; this is not an independent
   recomputation of the simulator configuration hash. Step 0 remains ineligible.
6. Formal manifest generation refuses missing/partial five-profile/five-seed inputs;
   empty manifests cannot masquerade as completed stages.

## Evidence and remaining limits

`tests/test_v4_workflow.py` exercises these failures and a synthetic complete 25-run
selection, without loading a model or simulator. Synthetic fixtures are not research data.
`results/v4/cpu_workflow_review.json` records the executed CPU checks. The remote agent
must rerun the CPU suite in its environment and exercise these commands against real
pilot/checkpoint artifacts before claiming operational verification.

The pilot report is deliberately not fabricated locally. No final suite or formal freeze
has been generated in the real repository by this preparation task. Temporary synthetic
fixtures test generation and overwrite behavior. The simulator acceptance remains the
original uploaded evidence, with the table-support control fix explicitly documented.

Scientific caution: baseline selection used development data. The main mixed-ID condition
is already at 24/24 for calibrated geometry; a future ceiling is possible and must be
reported. EMA's 23/24 versus calibrated geometry's 22/24 on mixed OOD is only one case
in a small development set. Do not redesign the final protocol to obtain an RL win.
