"""Entirely synthetic annotations; no human-reviewed reference data."""
import json
from hammer_evidence import adjudicate_reviews
from hammer_evidence.common import digest, encode

text = 'Forty adults participated.'
source = dict(text=text, sha256=digest(text.encode()), url='https://example.org/synthetic')
span = dict(start=0, end=len(text), quote=text)
fields = dict(population=span, method=None, result=None, limitation=None)
reviews = [dict(reviewer=name, source_sha256=source['sha256'], status='reviewed', fields=dict(fields))
           for name in ('Synthetic A', 'Synthetic B')]
reviews[1]['fields']['population'] = None
decision = dict(adjudicator='Synthetic C', reviewed_at='2026-10-04T00:00:00+00:00',
                source_sha256=source['sha256'], reviews_sha256=digest(encode(reviews)),
                decisions={field:dict(status='resolved', span=value,
                                     reason='Synthetic example: explicit population sentence; other fields absent.')
                           for field,value in fields.items()})
result = adjudicate_reviews(source, reviews, decision)
assert result['status'] == 'adjudication_recorded'
assert result['reference_fields']['population'] == span
assert not result['automatic_promotion_allowed']
print(json.dumps({'status':result['status'], 'data':'synthetic only'}, indent=2))
