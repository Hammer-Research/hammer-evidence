"""Research accounting primitives. No clinical or independence certification."""
from .cohorts import audit_cohort
from .reviews import compare_reviews
from .runs import run_experiment, verify_run

__version__ = '0.1.0'
__all__ = ['audit_cohort', 'compare_reviews', 'run_experiment', 'verify_run']
