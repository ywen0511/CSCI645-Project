"""Synthetic CPU workflow tests; never evidence of simulator performance."""
import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


@pytest.fixture
def ready(tmp_path, monkeypatch):
    f = module('v4_freeze')
    for rel in ['configs/v4/training', 'configs/v4/development/baseline_selection.json',
                'configs/v4/suites', 'src/csci645_handover/v4_protocol.py',
                'results/v4/acceptance/acceptance.json', 'results/v4/acceptance/PROVENANCE.json']:
        src, dst = ROOT / rel, tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copyfile(src, dst)
    ev = tmp_path / 'results/v4/pilot/test-only-evidence.json'
    write(ev, {'synthetic': True})
    report = {'complete': True, 'all_attempts_accounted': True,
              'formal_configuration_decision': 'Synthetic fixture only',
              'other_training_transitions': 1500000,
              'total_training_transitions': 4 * 5505024 + 1500000,
              'runs': [{'profile': p, 'seed': s, 'status': 'completed', 'transitions': 5505024}
                       for p, s in sorted(f.PILOT_RUNS)],
              'evidence': [{'path': str(ev.relative_to(tmp_path)), 'sha256': f.v4.sha256(ev)}]}
    write(tmp_path / 'results/v4/pilot/summary.json', report)
    monkeypatch.setattr(f, 'ROOT', tmp_path)
    monkeypatch.setattr(f, 'git', lambda *a: '' if a[0] == 'status' else 'a' * 40)
    return f, tmp_path


@pytest.mark.parametrize('failure', ['pilot_missing', 'pilot_incomplete', 'duplicate_run', 'over_budget',
                                      'bad_sum', 'failed_acceptance', 'changed_evidence', 'wrong_seeds'])
def test_freeze_refuses_incomplete_evidence_before_writing(ready, failure):
    f, root = ready
    p = root / 'results/v4/pilot/summary.json'
    d = json.loads(p.read_text())
    if failure == 'pilot_missing':
        p.unlink()
    elif failure == 'pilot_incomplete':
        d['complete'] = False
    elif failure == 'duplicate_run':
        d['runs'][1] = d['runs'][0]
    elif failure == 'over_budget':
        d['other_training_transitions'] = 4000000
        d['total_training_transitions'] = 4 * 5505024 + 4000000
    elif failure == 'bad_sum':
        d['total_training_transitions'] -= 1
    elif failure == 'failed_acceptance':
        a = root / 'results/v4/acceptance/acceptance.json'
        data = json.loads(a.read_text()); data['A3_negative_controls']['pass'] = False; write(a, data)
    elif failure == 'changed_evidence':
        (root / d['evidence'][0]['path']).write_text('changed')
    else:
        a = root / 'configs/v4/training/combined_robust_ff.json'
        data = json.loads(a.read_text()); data['training']['seeds'] = [111]; write(a, data)
    if failure != 'pilot_missing':
        write(p, d)
    with pytest.raises((ValueError, FileNotFoundError)):
        f.freeze()
    assert not (root / 'configs/v4/FREEZE.json').exists()
    assert not (root / 'configs/v4/frozen').exists()


def test_freeze_preserves_inputs_and_final_rebuild_is_repeatable(ready):
    f, root = ready
    assert f.prerequisites(root)['formal_runs'] == 25
    f.freeze()
    freeze = root / 'configs/v4/FREEZE.json'
    original = freeze.read_bytes()
    with pytest.raises(SystemExit, match='already exists'):
        f.freeze()
    f.final_suite()
    suite = root / 'configs/v4/suites/final.jsonl'
    data = suite.read_bytes()
    f.final_suite()
    assert data == suite.read_bytes() and freeze.read_bytes() == original
    assert len(data.splitlines()) == 2400
    suite.write_text('corrupt')
    with pytest.raises(ValueError, match='Refusing'):
        f.final_suite()
    assert suite.read_text() == 'corrupt'
    assert freeze.read_bytes() == original


def candidate_fixture(s, tmp_path):
    cases = s.v4.make_cases('validation', s.v4.CONDITIONS, list(s.v4.VALIDATION))
    cp = tmp_path / 'weights.pt'; cp.write_bytes(b'synthetic checkpoint, not Torch')
    entry = {'id': 'fixture', 'training_seed': 111, 'checkpoint': 'step_002031616.pt'}
    rows = [{'case_id': c['case_id'], 'condition': c['condition'], 'observation_error': c['observation_error'],
             'grasp_offset_requested_xyz_m': c['grasp_offset_xyz_m'], 'reset_valid': True, 'success': True,
             'terminal_reason': 'success', 'collision': False, 'residual_abs_mean_m': 0.001,
             'entry_id': entry['id'], 'training_seed': 111, 'checkpoint_transitions': 2031616,
             'checkpoint_sha256': s.v4.sha256(cp), 'suite_hash': 'b'*64, 'config_hash': 'c'*64,
             'controller_hash': 'd'*64, 'source_commit': 'a'*40, 'source_dirty': False} for c in cases]
    return cases, cp, entry, rows


@pytest.mark.parametrize('failure', ['checkpoint', 'source', 'seed', 'suite', 'sensor', 'grasp', 'duplicate', 'transitions'])
def test_selection_rejects_stale_or_mismatched_records(tmp_path, failure):
    s = module('v4_select_checkpoints')
    cases, cp, entry, rows = candidate_fixture(s, tmp_path)
    assert s.candidate(rows, cases, entry, cp, 'b'*64, 'a'*40)['success_rate'] == 1
    if failure == 'checkpoint':
        cp.write_bytes(b'changed')
    elif failure == 'source':
        rows[0]['source_commit'] = 'e'*40
    elif failure == 'seed':
        rows[0]['training_seed'] = 222
    elif failure == 'suite':
        rows[0]['suite_hash'] = 'e'*64
    elif failure == 'sensor':
        rows[0]['observation_error'] = {}
    elif failure == 'grasp':
        rows[0]['grasp_offset_requested_xyz_m'] = [1., 0., 0.]
    elif failure == 'duplicate':
        rows.append(copy.deepcopy(rows[0]))
    else:
        rows[0]['checkpoint_transitions'] = 0
    with pytest.raises(ValueError):
        s.candidate(rows, cases, entry, cp, 'b'*64, 'a'*40)


def test_empty_inputs_cannot_produce_successful_manifests_or_selection(tmp_path, monkeypatch):
    m = module('v4_manifests')
    monkeypatch.setattr(m, 'FROZEN', tmp_path / 'missing')
    monkeypatch.setattr(m, 'OUT', tmp_path / 'jobs')
    with pytest.raises(ValueError, match='five frozen profiles'):
        m.train()
    with pytest.raises(ValueError, match='empty'):
        m.write('fixture', [])
    s = module('v4_select_checkpoints')
    monkeypatch.setattr(s, 'ROOT', tmp_path)
    p = tmp_path / 'configs/v4/suites/validation.jsonl'
    p.parent.mkdir(parents=True); p.write_text('{}\n')
    with pytest.raises(ValueError, match='25 declared'):
        s.select(tmp_path, tmp_path / 'output', tmp_path, 'a'*40)
    assert not (tmp_path / 'output').exists()


def test_selection_full_matrix_and_no_partial_publication(ready, tmp_path, monkeypatch):
    f, root = ready
    f.freeze()
    s = module('v4_select_checkpoints'); monkeypatch.setattr(s, 'ROOT', root)
    cases, _, _, template = candidate_fixture(s, tmp_path)
    suite_hash = s.v4.sha256(root / 'configs/v4/suites/validation.jsonl')
    first_file = None
    for mp in sorted((root / 'configs/v4/frozen/matrices/validation').glob('*.json')):
        for e in json.loads(mp.read_text())['entries']:
            cp = root / 'train' / e['checkpoint']; cp.parent.mkdir(parents=True, exist_ok=True)
            cp.write_bytes(e['id'].encode())
            rows = [dict(r, entry_id=e['id'], training_seed=e['training_seed'], suite_hash=suite_hash,
                         checkpoint_sha256=s.v4.sha256(cp), checkpoint_transitions=int(cp.stem.split('_')[1]))
                    for r in template]
            target = root / 'validation' / mp.stem / (e['id'] + '.jsonl')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(''.join(json.dumps(r) + '\n' for r in rows))
            first_file = first_file or target
    out = s.select(root / 'validation', root / 'selected', root / 'train', 'a'*40)
    assert len(out) == 25
    assert all(v['selected'] == s.CANDIDATES[-1] for v in out.values())
    first_file.write_text(first_file.read_text().replace('"source_dirty": false', '"source_dirty": true'))
    with pytest.raises(ValueError):
        s.select(root / 'validation', root / 'rejected-output', root / 'train', 'a'*40)
    assert not (root / 'rejected-output').exists()
