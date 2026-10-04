import copy
import json
from pathlib import Path
import pytest

from hammer_evidence import audit_cohort, compare_reviews, run_experiment, verify_run
from hammer_evidence.common import digest


def samples():
    return [dict(sample_namespace='synthetic', sample_id='s'+str(i), cohort=role,
                 role=role, patient_namespace='reviewed-crosswalk', patient_id='p'+str(i),
                 identity_source='synthetic fixture only', endpoint='tissue', assay='test')
            for i, role in enumerate(('development', 'evaluation'))]


def audit(rows):
    return audit_cohort(rows, expected_endpoint='tissue', expected_assay='test')


def test_complete_metadata_is_not_independence_certification():
    result = audit(samples())
    assert not result['findings']
    assert not result['independence_certified'] and not result['evaluation_allowed']
    assert 'p0' not in json.dumps(result)


@pytest.mark.parametrize('field,value,code', [
    ('patient_id','p0','patients_across_roles'),
    ('sample_id','s0','duplicate_specimen_records'),
    ('cohort','development','cohorts_across_roles'),
    ('patient_namespace','different','cross_namespace_identity_unresolved'),
    ('identity_source','unknown','missing_identity_source'),
    ('endpoint','progression','endpoint_mismatch'),
    ('assay','other','assay_mismatch'),
    ('role',[],'invalid_role'),
])
def test_cohort_problems(field,value,code):
    rows=samples();rows[1][field]=value
    assert code in {v['code'] for v in audit(rows)['findings']}


def test_repeated_specimens_are_reported_without_inventing_aliases():
    rows=samples(); rows.append(dict(rows[0],sample_id='s2'))
    assert audit(rows)['patients_with_repeated_specimens']==1
    rows[2]['patient_id']='different-alias'
    assert audit(rows)['patients_with_repeated_specimens']==0


def review_fixture():
    text='We studied 40 adults. No independent cohort was tested.'
    source=dict(text=text,sha256=digest(text.encode()),url='https://example.org/synthetic')
    fields=dict(population=dict(start=0,end=21,quote=text[:21]),method=None,result=None,limitation=None)
    reviews=[dict(reviewer=name,source_sha256=source['sha256'],status='reviewed',fields=copy.deepcopy(fields))
             for name in ('Synthetic A','Synthetic B')]
    return source,reviews


def test_agreement_is_not_promotion():
    result=compare_reviews(*review_fixture())
    assert result['status']=='reviewers_agree'
    assert not result['automatic_promotion_allowed']


@pytest.mark.parametrize('change',['reviewer','source','quote','offset','boolean','fields','pending'])
def test_bad_annotations(change):
    source,reviews=review_fixture()
    if change=='reviewer': reviews[1]['reviewer']=' synthetic a '
    elif change=='source': source['text']+='altered'
    elif change=='quote': reviews[1]['fields']['population']['quote']='fabricated'
    elif change=='offset': reviews[1]['fields']['population']['end']=999
    elif change=='boolean': reviews[1]['fields']['population']['start']=False
    elif change=='fields': reviews[1]['fields'].pop('method')
    else: reviews[1]['status']='pending'
    with pytest.raises(ValueError):compare_reviews(source,reviews)


def test_disagreement_and_uncertainty_remain_unresolved():
    source,reviews=review_fixture();reviews[1]['fields']['population']=None
    result=compare_reviews(source,reviews)
    assert result['status']=='requires_adjudication' and not result['field_agreement']['population']
    source,reviews=review_fixture();reviews[1]['status']='uncertain'
    assert compare_reviews(source,reviews)['status']=='requires_adjudication'


def compute(paths,config):
    return {'sum':sum(json.loads(paths['values'].read_text()))*config['scale']}


def fail(paths,config):
    raise RuntimeError('Synthetic failure')


def tamper(paths,config):
    paths['values'].write_text('[999]')
    return {'sum':999}


def bad_result(paths,config):
    return {'value':float('nan')}


def arguments(tmp_path):
    source=tmp_path/'values.json';source.write_text('[1,2,3]')
    return dict(inputs={'values':source},code_files={'analysis':Path(__file__)},config={'scale':2},
                splits=[{'train':['synthetic-a'],'test':['synthetic-b']}],compute=compute)


def test_run_snapshots_results_and_refuses_reuse(tmp_path):
    args=arguments(tmp_path);out=tmp_path/'run'
    assert run_experiment(out,**args)['status']=='completed'
    assert json.loads((out/'result.json').read_text())=={'sum':12}
    assert verify_run(out)['status']=='checksums_verified'
    args['inputs']['values'].write_text('[999]')
    assert verify_run(out)['status']=='checksums_verified'
    with pytest.raises(FileExistsError):run_experiment(out,**args)
    (out/'result.json').write_text('{"sum":1}')
    with pytest.raises(ValueError):verify_run(out)


def test_metadata_runs_do_not_fabricate_splits(tmp_path):
    args=arguments(tmp_path);args['splits']=[]
    assert run_experiment(tmp_path/'metadata',kind='metadata',**args)['status']=='completed'
    assert json.loads((tmp_path/'metadata/manifest.json').read_text())['kind']=='metadata'
    with pytest.raises(ValueError):run_experiment(tmp_path/'model',**args)


@pytest.mark.parametrize('callback',[fail,tamper,bad_result])
def test_failed_runs_remain_reserved_against_retry(tmp_path,callback):
    args=arguments(tmp_path);args['compute']=callback;out=tmp_path/'run'
    with pytest.raises((RuntimeError,ValueError)):run_experiment(out,**args)
    assert json.loads((out/'receipt.json').read_text())['status']=='failed'
    with pytest.raises(ValueError):verify_run(out)
    with pytest.raises(FileExistsError):run_experiment(out,**args)


@pytest.mark.parametrize('change',['overlap','duplicate','alias','code'])
def test_invalid_plan_fails_before_reservation(tmp_path,change):
    args=arguments(tmp_path);out=tmp_path/'run'
    if change=='overlap':args['splits'][0]['test']=[' synthetic-a ']
    elif change=='duplicate':args['splits'][0]['train']=['a',' a ']
    elif change=='alias':args['inputs']={'../outside':next(iter(args['inputs'].values()))}
    else:args['code_files']={'wrong':next(iter(args['inputs'].values()))}
    with pytest.raises(ValueError):run_experiment(out,**args)
    assert not out.exists()
