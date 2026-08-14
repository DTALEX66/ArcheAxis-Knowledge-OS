"""First-run setup wizard (backend) — AXW-DATA-402.

Readiness checks reuse the shared workspace-manifest / path-policy /
capability-store facilities instead of building a second copy of the
layout logic. The HTTP surface lives in ``app/setup/router.py``.
"""
