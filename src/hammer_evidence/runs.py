"""Local experiment snapshots and terminal receipts; not an execution sandbox."""
import importlib.metadata
import inspect
import json
import platform
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .common import digest, encode, file_digest


def _time():
    return datetime.now(timezone.utc).isoformat()


def _split_check(splits):
    if not isinstance(splits, list) or not splits:
        raise ValueError('Explicit split records required')
    for split in splits:
        if not isinstance(split, dict) or set(split) != {'train', 'test'}:
            raise ValueError('Each split requires train and test group IDs')
        for group in split.values():
            if (not isinstance(group, list) or not group
                    or any(not isinstance(v, str) or not v.strip() for v in group)
                    or len(set(v.strip() for v in group)) != len(group)):
                raise ValueError('Unique nonempty group IDs required within each split side')
        if {v.strip() for v in split['train']} & {v.strip() for v in split['test']}:
            raise ValueError('Train/test group overlap')


def run_experiment(output, *, inputs, code_files, config, splits, compute, dependencies=(), kind='model'):
    """Run compute(snapshot_paths, config) once in a new local run directory.

    The callback must use the supplied snapshots; hidden dependencies cannot be
    detected. Code, config and splits are recorded before invocation. Split IDs
    are declared grouping units, not inferred patient identities. Outputs stay
    local: a run directory may contain confidential inputs and split identities.
    """
    if kind == 'model':
        _split_check(splits)
    elif kind != 'metadata' or splits != []:
        raise ValueError('Metadata runs require empty splits; kind must be model or metadata')
    if not isinstance(config, dict):
        raise ValueError('Explicit configuration object required')
    config_raw = encode(config)
    if not inputs or not code_files:
        raise ValueError('Named inputs and source code files required')
    for mapping in (inputs, code_files):
        if any(not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', name) for name in mapping):
            raise ValueError('File aliases must contain only letters, digits, underscore or hyphen')
        if any(not Path(path).is_file() for path in mapping.values()):
            raise ValueError('All declared inputs and code must be files')
    source = inspect.getsourcefile(compute)
    if not source or Path(source).resolve() not in {Path(p).resolve() for p in code_files.values()}:
        raise ValueError('Callback source must be included in code_files')
    versions = {name: importlib.metadata.version(name) for name in dependencies}
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    receipt = {'schema': 'hammer-run-receipt-v1', 'status': 'reserved', 'created_at': _time(),
               'clinical_validity': 'not_established', 'independence_certified': False}
    (folder/'receipt.json').write_bytes(encode(receipt))
    try:
        snapshots = {}
        files = {}
        for category, mapping in (('inputs', inputs), ('code', code_files)):
            (folder/category).mkdir()
            for name, path in mapping.items():
                target = folder/category/name
                before = file_digest(path)
                shutil.copyfile(path, target)
                if file_digest(target) != before or file_digest(path) != before:
                    raise ValueError('Input changed while snapshotting')
                files[f'{category}/{name}'] = before
                if category == 'inputs':
                    snapshots[name] = target
        (folder/'config.json').write_bytes(config_raw)
        (folder/'splits.json').write_bytes(encode(splits))
        for name in ('config.json', 'splits.json'):
            files[name] = file_digest(folder/name)
        manifest = {'schema': 'hammer-run-manifest-v1', 'kind': kind, 'files': files, 'python': platform.python_version(),
                    'dependencies': versions, 'callback': compute.__module__ + '.' + compute.__qualname__,
                    'scope': 'Declared files and parameters only; not a sandbox or independent-evaluation approval.'}
        manifest_raw = encode(manifest)
        (folder/'manifest.json').write_bytes(manifest_raw)
        receipt['manifest_sha256'] = digest(manifest_raw)
        (folder/'receipt.json').write_bytes(encode(receipt))
        result = compute(snapshots, json.loads(config_raw))
        if not isinstance(result, dict):
            raise ValueError('Experiment must return a JSON object')
        result_raw = encode(result)
        if any(file_digest(folder/name) != checksum for name, checksum in files.items()):
            raise ValueError('Snapshot modified during computation')
        if (folder/'manifest.json').read_bytes() != manifest_raw:
            raise ValueError('Manifest modified during computation')
        (folder/'result.json').write_bytes(result_raw)
        receipt.update(status='completed', finished_at=_time(), result_sha256=digest(result_raw))
        (folder/'receipt.json').write_bytes(encode(receipt))
        return receipt
    except BaseException as exc:
        receipt.update(status='failed', finished_at=_time(), error_type=type(exc).__name__)
        (folder/'receipt.json').write_bytes(encode(receipt))
        raise


def verify_run(folder):
    """Check a completed local receipt. Hashes are integrity checks, not signatures."""
    folder = Path(folder).resolve()
    receipt = json.loads(_contained_file(folder, 'receipt.json').read_text())
    if receipt.get('schema') != 'hammer-run-receipt-v1' or receipt.get('status') != 'completed':
        raise ValueError('Completed run receipt required')
    raw = _contained_file(folder, 'manifest.json').read_bytes()
    if digest(raw) != receipt['manifest_sha256']:
        raise ValueError('Manifest checksum mismatch')
    manifest = json.loads(raw)
    if manifest.get('schema') != 'hammer-run-manifest-v1' or not manifest.get('files'):
        raise ValueError('Invalid run manifest')
    for name, checksum in manifest['files'].items():
        path = _contained_file(folder, name)
        if file_digest(path) != checksum:
            raise ValueError('Run file checksum or path mismatch')
    if file_digest(_contained_file(folder, 'result.json')) != receipt['result_sha256']:
        raise ValueError('Result checksum mismatch')
    return {'status': 'checksums_verified', 'files': len(manifest['files']) + 1,
            'independence_certified': False, 'clinical_validity': 'not_established'}


def _contained_file(folder, name):
    if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('Run files must remain within the run directory')
    path = (folder/name).resolve()
    if folder not in path.parents or not path.is_file():
        raise ValueError('Run file missing or outside the run directory')
    return path
