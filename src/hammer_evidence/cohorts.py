"""Detect declared identity and design problems; do not infer patient aliases."""
from collections import Counter, defaultdict
from .common import present


def audit_cohort(samples, *, expected_endpoint, expected_assay):
    """Inspect flat specimen records. Return aggregate findings, never identities.

    Required fields: sample_namespace, sample_id, cohort, role (development or
    evaluation), patient_namespace, patient_id, identity_source, endpoint, assay.
    Aliases across namespaces require an externally reviewed crosswalk first.
    """
    if not isinstance(samples, list) or not samples or any(not isinstance(r, dict) for r in samples):
        raise ValueError('Nonempty list of specimen records required')
    if not present(expected_endpoint) or not present(expected_assay):
        raise ValueError('Explicit endpoint and assay required')
    issues = Counter()
    specimens = Counter()
    patients = defaultdict(list)
    cohort_roles = defaultdict(set)
    namespaces = set()
    fields = ('sample_namespace', 'sample_id', 'cohort', 'role', 'patient_namespace',
              'patient_id', 'identity_source', 'endpoint', 'assay')
    for row in samples:
        for field in fields:
            if not present(row.get(field)):
                issues['missing_' + field] += 1
        if row.get('role') not in ('development', 'evaluation'):
            issues['invalid_role'] += 1
        if all(present(row.get(k)) for k in ('sample_namespace', 'sample_id')):
            specimens[(row['sample_namespace'].strip(), row['sample_id'].strip())] += 1
        if all(present(row.get(k)) for k in ('patient_namespace', 'patient_id', 'identity_source')):
            namespace = row['patient_namespace'].strip()
            namespaces.add(namespace)
            patients[(namespace, row['patient_id'].strip())].append(row)
        if present(row.get('cohort')):
            cohort_roles[row['cohort'].strip()].add(row.get('role') if isinstance(row.get('role'), str) else None)
        if present(row.get('endpoint')) and row['endpoint'] != expected_endpoint:
            issues['endpoint_mismatch'] += 1
        if present(row.get('assay')) and row['assay'] != expected_assay:
            issues['assay_mismatch'] += 1
    issues['duplicate_specimen_records'] = sum(n - 1 for n in specimens.values())
    issues['patients_across_roles'] = sum(
        {'development', 'evaluation'} <= {r.get('role') for r in rows if isinstance(r.get('role'), str)}
        for rows in patients.values())
    issues['cohorts_across_roles'] = sum({'development', 'evaluation'} <= roles for roles in cohort_roles.values())
    if len(namespaces) > 1:
        issues['cross_namespace_identity_unresolved'] = 1
    findings = [{'code': code, 'count': count} for code, count in sorted(issues.items()) if count]
    return {'schema': 'hammer-cohort-audit-v1', 'specimens': len(samples),
            'reported_patient_groups': len(patients),
            'patients_with_repeated_specimens': sum(len(rows) > 1 for rows in patients.values()),
            'findings': findings, 'status': 'issues_found' if findings else 'no_detected_structural_conflicts',
            'independence_certified': False, 'evaluation_allowed': False,
            'limitations': ['Only supplied identities and metadata are checked.',
                           'Identity-source text is not verified evidence.',
                           'Different aliases, unrecorded data access and clinical eligibility require review.']}
