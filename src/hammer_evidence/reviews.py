"""Compare independent source-span annotations without adjudicating truth."""
from .common import digest, present

FIELDS = ('population', 'method', 'result', 'limitation')


def compare_reviews(source, reviews):
    """Require two distinct declared reviewers bound to the exact source bytes.

    source: {text, sha256, url}. reviews: [{reviewer, source_sha256, status,
    fields}]. Status is reviewed or uncertain. Each field is null or an exact
    {start, end, quote} span in the text. No model answers are required.
    """
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
        fields = review.get('fields')
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
    uncertain = any(r['status'] == 'uncertain' for r in reviews)
    agreement = {field: reviews[0]['fields'][field] == reviews[1]['fields'][field] for field in FIELDS}
    return {'schema': 'hammer-review-comparison-v1', 'source_sha256': checksum,
            'status': 'requires_adjudication' if uncertain or not all(agreement.values()) else 'reviewers_agree',
            'field_agreement': agreement, 'uncertain_review': uncertain,
            'automatic_promotion_allowed': False,
            'limitations': ['Distinct names do not prove independent human review.',
                           'Exact span agreement is not verification of scientific truth.',
                           'Different spans may both be valid; preserve originals for adjudication.']}
