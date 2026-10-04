"""JSON-in/JSON-out interfaces for reviewable local checks."""
import argparse
import json
from pathlib import Path

from .cohorts import audit_cohort
from .reviews import compare_reviews, adjudicate_reviews
from .runs import verify_run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('cohort', 'reviews', 'adjudicate'):
        command = commands.add_parser(name)
        command.add_argument('input', type=Path)
    command = commands.add_parser('verify-run')
    command.add_argument('directory', type=Path)
    args = parser.parse_args()
    if args.command == 'verify-run':
        result = verify_run(args.directory)
    else:
        data = json.loads(args.input.read_text())
        functions = {'cohort': audit_cohort, 'reviews': compare_reviews, 'adjudicate': adjudicate_reviews}
        result = functions[args.command](**data)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
