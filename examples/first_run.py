"""Synthetic smoke test for all three modules; no data downloads or credentials."""
import json
import tempfile
from pathlib import Path
from hammer_evidence import audit_cohort, compare_reviews, run_experiment, verify_run
from hammer_evidence.common import digest


def compute(paths, config):
    return {'sum': sum(json.loads(paths['measurements'].read_text())) * config['scale']}


def main():
    rows = [dict(sample_namespace='fixture', sample_id='s'+str(i), patient_namespace='fixture',
                 patient_id='p'+str(i), identity_source='synthetic only', cohort=role,
                 role=role, endpoint='synthetic', assay='synthetic')
            for i, role in enumerate(('development', 'evaluation'))]
    audit = audit_cohort(rows, expected_endpoint='synthetic', expected_assay='synthetic')
    text = 'Forty adults participated.'
    source = dict(text=text, sha256=digest(text.encode()), url='https://example.org/synthetic')
    fields = dict(population=dict(start=0, end=len(text), quote=text), method=None, result=None, limitation=None)
    reviews = [dict(reviewer=r, source_sha256=source['sha256'], status='reviewed', fields=fields)
               for r in ('Synthetic reviewer A', 'Synthetic reviewer B')]
    compared = compare_reviews(source, reviews)
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        (directory/'input.json').write_text('[1,2,3]')
        run_experiment(directory/'run', inputs={'measurements':directory/'input.json'},
                       code_files={'example':Path(__file__)}, config={'scale':2},
                       splits=[{'train':['synthetic-a'], 'test':['synthetic-b']}], compute=compute)
        verified = verify_run(directory/'run')
        assert json.loads((directory/'run/result.json').read_text()) == {'sum':12}
    assert not audit['findings'] and compared['status'] == 'reviewers_agree'
    print(json.dumps({'cohort':audit['status'], 'review':compared['status'],
                      'run':verified['status'], 'data':'synthetic only'}, indent=2))


if __name__ == '__main__':
    main()
