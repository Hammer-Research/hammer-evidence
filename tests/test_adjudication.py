import copy
import json
import pytest
from hammer_evidence import adjudicate_reviews, run_experiment, verify_run
from hammer_evidence.common import digest, encode
from test_contracts import review_fixture, arguments


def fixture():
    source, reviews = review_fixture()
    reviews[1]['fields']['population'] = None
    decision = {'adjudicator':'Synthetic C', 'reviewed_at':'2026-10-04T00:00:00+00:00',
                'source_sha256':source['sha256'], 'reviews_sha256':digest(encode(reviews)),
                'decisions':{f:dict(status='resolved',span=span,reason='Synthetic fixture rationale')
                             for f,span in reviews[0]['fields'].items()}}
    return source,reviews,decision


def test_explicit_resolution_preserves_originals():
    source,reviews,decision=fixture();original=copy.deepcopy(reviews)
    report=adjudicate_reviews(source,reviews,decision)
    assert report['status']=='adjudication_recorded'
    assert report['reference_fields']['population']==reviews[0]['fields']['population']
    assert not report['automatic_promotion_allowed']
    assert reviews==original


def test_unresolved_fields_never_become_reference_labels():
    source,reviews,decision=fixture()
    decision['decisions']['population'].update(status='unresolved',span=None)
    result=adjudicate_reviews(source,reviews,decision)
    assert result['status']=='requires_adjudication'
    assert result['reference_fields'] is None


@pytest.mark.parametrize('change',['reviewer','source','reviews','timestamp','timezone','reason','span','unresolved','missing'])
def test_invalid_or_stale_decision_rejected(change):
    source,reviews,decision=fixture()
    if change=='reviewer':decision['adjudicator']=' synthetic a '
    elif change=='source':decision['source_sha256']='wrong'
    elif change=='reviews':reviews[0]['status']='uncertain'
    elif change=='timestamp':decision['reviewed_at']='yesterday'
    elif change=='timezone':decision['reviewed_at']='2026-10-04'
    elif change=='reason':decision['decisions']['method']['reason']=''
    elif change=='span':decision['decisions']['population']['span']['quote']='fabricated'
    elif change=='unresolved':decision['decisions']['population']['status']='unresolved'
    else:decision['decisions'].pop('method')
    with pytest.raises(ValueError):adjudicate_reviews(source,reviews,decision)


@pytest.mark.parametrize('name',['receipt.json','manifest.json','result.json','inputs/values'])
def test_verification_rejects_symlinks_outside_run(tmp_path,name):
    output=tmp_path/'run';run_experiment(output,**arguments(tmp_path))
    path=output/name;outside=tmp_path/'outside';outside.write_bytes(path.read_bytes())
    path.unlink();path.symlink_to(outside)
    with pytest.raises(ValueError,match='outside'):verify_run(output)


def test_manifest_cannot_name_parent_paths(tmp_path):
    output=tmp_path/'run';run_experiment(output,**arguments(tmp_path))
    manifest=json.loads((output/'manifest.json').read_text())
    manifest['files']['../outside']='0'*64
    raw=encode(manifest);(output/'manifest.json').write_bytes(raw)
    receipt=json.loads((output/'receipt.json').read_text());receipt['manifest_sha256']=digest(raw)
    (output/'receipt.json').write_bytes(encode(receipt))
    with pytest.raises(ValueError):verify_run(output)
