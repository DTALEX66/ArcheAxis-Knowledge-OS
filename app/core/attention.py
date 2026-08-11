"""Attention scoring — DEFERRED placeholder.

The attention_score concept is live (see app.schemas.CoreObject.attention_score,
app.memory.database attention_score column, app.core.router). The standalone
attention-scoring implementation is deferred: routing currently derives scores
inside app.core.router. This module is reserved for a dedicated attention
scorer; an empty module here is NOT a working implementation.
"""
