"""Project scoring: 6-dimension evaluation model.

Dimensions: token_saving, efficiency_gain, local_first, system_fit, risk_penalty.
Threshold: total >= 3.5 & risk != critical → IntakeCard candidate.
"""
from .scorer import score_project
