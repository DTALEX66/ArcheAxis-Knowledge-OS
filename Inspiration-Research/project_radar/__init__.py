"""Project Radar — daily GitHub AI project screening and intake pipeline.

Modules:
- collectors/: news/GitHub/RSS data collectors
- scoring/: project evaluation (token_saving, efficiency, local_first, system_fit, risk)
- outputs/: daily brief + screening table generators
- filters/: dedup, noise filter, license check
"""
from .scoring import score_project
