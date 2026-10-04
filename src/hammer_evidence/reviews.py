"""Compare independent source-span annotations without adjudicating truth."""
import json
from datetime import datetime
from .common import digest, encode, present

FIELDS = ('population', 'method', 'result', 'limitation')


def compare_reviews(source, reviews):
    """Require two distinct declared reviewers bound to the exact source bytes.

    source: {text, sha256, url}. reviews: [{reviewer, source_sha256, status,
    fields}]. Status is reviewed or uncertain. Each field is null or an exact
    {start, end, quote} span in the text. No model answers are required.
    """
    if not isinstance(source, dict):
        raise ValueError('Source object required')
    text = source.get('text')
    if not isinstance(text, str) or not text.strip() or not present(source.get('url')):
        raise ValueError('Source text and citation URL required')
    checksum = digest(text.encode())
    if source.get('sha256') != checksum:
        raise ValueError('Source checksum mismatch')
    if not isinstance(reviews, list) or len(reviews) != 2 or any(not isinstance(r, dict) for r in reviews):
        raise ValueError('Exactly two reviewer records required')
    identities = set()
    for review in reviews:
        reviewer = review.get('reviewer')
        if not present(reviewer) or reviewer.strip().casefold() in identities:
            raise ValueError('Two distinct named reviewers required')
        identities.add(reviewer.strip().casefold())
        if review.get('source_sha256') != checksum:
            raise ValueError('Review belongs to another source version')
        if review.get('status') not in ('reviewed', 'uncertain'):
            raise ValueError('Explicit review status required')
        _validate_fields(text, review.get('fields'))
    uncertain = any(r['status'] == 'uncertain' for r in reviews)
    agreement = {field: reviews[0]['fields'][field] == reviews[1]['fields'][field] for field in FIELDS}
    return {'schema': 'hammer-review-comparison-v1', 'source_sha256': checksum,
            'status': 'requires_adjudication' if uncertain or not all(agreement.values()) else 'reviewers_agree',
            'field_agreement': agreement, 'uncertain_review': uncertain,
            'automatic_promotion_allowed': False,
            'limitations': ['Distinct names do not prove independent human review.',
                           'Exact span agreement is not verification of scientific truth.',
                           'Different spans may both be valid; preserve originals for adjudication.']}


def _validate_fields(text, fields):
    if not isinstance(fields, dict) or set(fields) != set(FIELDS):
        raise ValueError('Exactly four evidence fields required')
    for span in fields.values():
        if span is None:
            continue
        if not isinstance(span, dict) or set(span) != {'start', 'end', 'quote'}:
            raise ValueError('Exact source span or null required')
        start, end = span['start'], span['end']
        if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text)
                or text[start:end] != span['quote']):
            raise ValueError('Invalid source offsets or quote')


def adjudicate_reviews(source, reviews, decision):
    """Record a third person's explicit resolution, bound to both original reviews.

    A decision contains adjudicator, reviewed_at (timezone-aware ISO date-time),
    source_sha256, reviews_sha256 and decisions. Each of the four field decisions
    contains status (resolved or unresolved), span (exact source span or null),
    and reason. An unresolved field cannot supply a reference span.
    """
    comparison = compare_reviews(source, reviews)
    if not isinstance(decision, dict):
        raise ValueError('Adjudication object required')
    person = decision.get('adjudicator')
    if (not present(person) or person.strip().casefold() in
            {review['reviewer'].strip().casefold() for review in reviews}):
        raise ValueError('A distinct named adjudicator is required')
    if decision.get('source_sha256') != comparison['source_sha256']:
        raise ValueError('Adjudication belongs to another source')
    reviews_hash = digest(encode(reviews))
    if decision.get('reviews_sha256') != reviews_hash:
        raise ValueError('Adjudication does not match the original reviews')
    try:
        reviewed_at = datetime.fromisoformat(decision['reviewed_at'].replace('Z', '+00:00'))
        if reviewed_at.utcoffset() is None:
            raise ValueError('Timezone required')
    except (KeyError, AttributeError, TypeError, ValueError):
        raise ValueError('Timezone-aware ISO review timestamp required') from None
    decisions = decision.get('decisions')
    if not isinstance(decisions, dict) or set(decisions) != set(FIELDS):
        raise ValueError('A decision for every evidence field is required')
    fields = {}
    unresolved = []
    for field in FIELDS:
        item = decisions[field]
        if (not isinstance(item, dict) or set(item) != {'status', 'span', 'reason'}
                or item['status'] not in ('resolved', 'unresolved') or not present(item['reason'])):
            raise ValueError('Each field requires explicit status, span and rationale')
        if item['status'] == 'unresolved':
            if item['span'] is not None:
                raise ValueError('Unresolved fields cannot supply reference spans')
            unresolved.append(field)
        fields[field] = item['span']
    _validate_fields(source['text'], fields)
    return {'schema': 'hammer-adjudication-v1',
            'status': 'requires_adjudication' if unresolved else 'adjudication_recorded',
            'source_sha256': comparison['source_sha256'], 'reviews_sha256': reviews_hash,
            'decision_sha256': digest(encode(decision)), 'adjudicator': person.strip(),
            'reviewed_at': reviewed_at.isoformat(), 'decisions': json.loads(encode(decisions)),
            'unresolved_fields': unresolved, 'reference_fields': None if unresolved else json.loads(encode(fields)),
            'automatic_promotion_allowed': False,
            'limitations': ['Attribution and independence are self-reported, not authenticated.',
                           'A recorded decision is not independent benchmark validation or scientific certification.']}
