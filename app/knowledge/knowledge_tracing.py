"""Bayesian Knowledge Tracing (BKT) engine — absorbed from OATutor / pyBKT / pyKT.

Pure-Python + numpy implementation of the classic two-state HMM:

    latent:  L (learned)  /  ~L (not yet learned)
    observed: correct (1) / incorrect (0)

Parameters per skill:
    p_l0  — P(L at t=0)               prior mastery
    p_t   — P(learn | ~L)             transition (learning rate)
    p_g   — P(correct | ~L)           guess
    p_s   — P(incorrect | L)          slip

Supports:
    * online posterior updates (one response at a time)
    * batch prediction on a response sequence
    * EM fitting (Baum-Welch) from observation sequences, as in pyBKT

Design rules (project governance):
    * pure calculation — no persistence, no I/O, no provider calls
    * mastery output is a probability, never asserted as verified truth
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

__all__ = ["BKTModel", "BKTParameterError", "fit_bkt", "estimate_mastery"]


class BKTParameterError(ValueError):
    """Raised when BKT parameters leave the open probability interval."""


@dataclass(frozen=True)
class BKTModel:
    """One skill's BKT parameters (immutable; use \"replace\" to update)."""

    skill_id: str
    p_l0: float = 0.2
    p_t: float = 0.1
    p_g: float = 0.2
    p_s: float = 0.1

    def __post_init__(self) -> None:
        for name in ("p_l0", "p_t", "p_g", "p_s"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise BKTParameterError(f"{name} must be in [0,1], got {value}")
        # guess + slip must be distinguishable from chance in both states
        if self.p_g >= 1.0 - self.p_s:
            raise BKTParameterError("guess + slip must be < 1 to keep states identifiable")

    # ── online update ─────────────────────────────────────────

    def update(self, mastery: float, correct: bool) -> float:
        """Return P(L | response) after one observed response.

        Args:
            mastery: prior P(L) before the response (0..1).
            correct: whether the learner answered correctly.

        Returns:
            posterior P(L | response) in [0, 1].
        """
        p_l = float(np.clip(mastery, 0.0, 1.0))
        if correct:
            likelihood_learned = 1.0 - self.p_s
            likelihood_unlearned = self.p_g
        else:
            likelihood_learned = self.p_s
            likelihood_unlearned = 1.0 - self.p_g
        evidence = p_l * likelihood_learned + (1.0 - p_l) * likelihood_unlearned
        if evidence <= 0.0:
            return 0.0
        posterior = p_l * likelihood_learned / evidence
        # transition: even an unlearned state can learn after the response
        return float(np.clip(posterior + (1.0 - posterior) * self.p_t, 0.0, 1.0))

    def predict_sequence(self, responses: list[bool], initial: float | None = None) -> list[float]:
        """Return the mastery trajectory for a response sequence."""
        mastery = float(initial if initial is not None else self.p_l0)
        out: list[float] = []
        for correct in responses:
            mastery = self.update(mastery, bool(correct))
            out.append(mastery)
        return out

    def probability_correct(self, mastery: float) -> float:
        """P(correct | current mastery) — used for prediction of next response."""
        p_l = float(np.clip(mastery, 0.0, 1.0))
        return float(np.clip(p_l * (1.0 - self.p_s) + (1.0 - p_l) * self.p_g, 0.0, 1.0))

    def replace(self, **kwargs: float) -> "BKTModel":
        """Return a new model with the given parameters replaced (immutability)."""
        data = {"skill_id": self.skill_id, "p_l0": self.p_l0, "p_t": self.p_t,
                "p_g": self.p_g, "p_s": self.p_s}
        data.update(kwargs)
        return BKTModel(**data)


# ── EM fitting (Baum-Welch), pyBKT-style ─────────────────────────

def _forward_backward(model: BKTModel, responses: list[bool]) -> tuple[np.ndarray, np.ndarray, float]:
    """Forward-backward over the two latent states.

    State 0 = not learned, state 1 = learned.
    Returns (alpha, beta, log_likelihood).
    """
    n = len(responses)
    if n == 0:
        raise ValueError("cannot fit BKT on an empty response sequence")
    # transition matrix: rows from-state, cols to-state
    trans = np.array([[1.0 - model.p_t, model.p_t], [0.0, 1.0]])
    # emission: P(obs | state)
    emit = np.array([
        [1.0 - model.p_g, model.p_g],   # state ~L: incorrect, correct
        [model.p_s, 1.0 - model.p_s],   # state L:  incorrect, correct
    ])
    obs = np.array([1.0 if r else 0.0 for r in responses])

    alpha = np.zeros((n, 2))
    alpha[0] = np.array([1.0 - model.p_l0, model.p_l0]) * emit[:, int(obs[0])]
    scale = alpha[0].sum()
    if scale <= 0.0:
        alpha[0] = np.array([1.0, 0.0]) * 1e-12
        scale = alpha[0].sum()
    alpha[0] /= scale
    log_lik = float(np.log(scale))
    for t in range(1, n):
        alpha[t] = (alpha[t - 1] @ trans) * emit[:, int(obs[t])]
        s = alpha[t].sum()
        if s <= 0.0:
            alpha[t] = np.array([1.0, 1.0]) * 1e-12
            s = alpha[t].sum()
        alpha[t] /= s
        log_lik += float(np.log(s))

    beta = np.zeros((n, 2))
    beta[-1] = 1.0
    for t in range(n - 2, -1, -1):
        beta[t] = (trans @ (emit[:, int(obs[t + 1])] * beta[t + 1]))
        s = beta[t].sum()
        if s > 0.0:
            beta[t] /= s

    return alpha, beta, log_lik


def _expected_sufficient_statistics(
    model: BKTModel, responses: list[bool],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Expected counts over states, transitions and emissions (Baum-Welch E-step)."""
    alpha, beta, _ = _forward_backward(model, responses)
    gamma = alpha * beta
    gamma /= gamma.sum(axis=1, keepdims=True) + 1e-12

    n = len(responses)
    trans = np.array([[1.0 - model.p_t, model.p_t], [0.0, 1.0]])
    emit = np.array([
        [1.0 - model.p_g, model.p_g],
        [model.p_s, 1.0 - model.p_s],
    ])
    obs = np.array([1.0 if r else 0.0 for r in responses])

    xi = np.zeros((n - 1, 2, 2))
    for t in range(n - 1):
        joint = (alpha[t][:, None] * trans) * (emit[:, int(obs[t + 1])] * beta[t + 1])[None, :]
        denom = joint.sum()
        if denom > 0.0:
            xi[t] = joint / denom

    p0 = float(gamma[0, 1])
    t_from_unlearned = float(xi[:, 0, 1].sum())
    stay_unlearned = float(xi[:, 0, 0].sum())
    learned_total = float(gamma[:, 1].sum()) + 1e-12
    unlearned_total = float(gamma[:, 0].sum()) + 1e-12
    learned_and_wrong = float((gamma[:, 1] * (1.0 - obs)).sum())
    unlearned_and_right = float((gamma[:, 0] * obs).sum())
    return p0, t_from_unlearned, stay_unlearned, learned_total, unlearned_total, learned_and_wrong, unlearned_and_right


def fit_bkt(
    skill_id: str,
    sequences: list[list[bool]],
    *,
    max_iterations: int = 200,
    tolerance: float = 1e-6,
) -> BKTModel:
    """Fit a BKT model from one or more response sequences via EM.

    Args:
        skill_id: stable skill/concept identifier.
        sequences: list of response sequences (True = correct).
        max_iterations: EM rounds cap.
        tolerance: log-likelihood convergence threshold.

    Returns:
        A fitted BKTModel.
    """
    if not sequences or any(len(seq) == 0 for seq in sequences):
        raise ValueError("fit_bkt requires at least one non-empty response sequence")
    model = BKTModel(skill_id=skill_id)
    prev_log_lik = float("-inf")
    for _ in range(max_iterations):
        acc = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        log_lik = 0.0
        for seq in sequences:
            p0, t_un, stay_un, learned_tot, unlearned_tot, l_wrong, u_right = (
                _expected_sufficient_statistics(model, seq)
            )
            acc[0] += p0
            acc[1] += t_un
            acc[2] += stay_un
            acc[3] += learned_tot
            acc[4] += unlearned_tot
            acc[5] += l_wrong
            acc[6] += u_right
            _, _, ll = _forward_backward(model, seq)
            log_lik += ll
        total_trans_unlearned = acc[1] + acc[2]
        new_t = acc[1] / total_trans_unlearned if total_trans_unlearned > 0 else model.p_t
        new_s = acc[5] / acc[3]
        new_g = acc[6] / acc[4]
        new_l0 = acc[0] / len(sequences)
        new_t = float(np.clip(new_t, 1e-6, 1.0 - 1e-6))
        new_s = float(np.clip(new_s, 1e-6, 0.999))
        new_g = float(np.clip(new_g, 1e-6, 0.999))
        # identifiability: guess + slip must stay strictly below 1 (degenerate
        # fits on noisy data would otherwise be unidentifiable)
        if new_g + new_s >= 0.99:
            excess = (new_g + new_s - 0.98) / 2.0
            new_g = max(1e-6, new_g - excess)
            new_s = max(1e-6, new_s - excess)
        new_l0 = float(np.clip(new_l0, 1e-6, 1.0 - 1e-6))
        model = BKTModel(skill_id=skill_id, p_l0=new_l0, p_t=new_t, p_g=new_g, p_s=new_s)
        if abs(log_lik - prev_log_lik) < tolerance:
            break
        prev_log_lik = log_lik
    return model


def estimate_mastery(model: BKTModel, responses: list[bool] | None = None) -> float:
    """Convenience: posterior P(L) after a response sequence (or prior if none)."""
    if not responses:
        return float(model.p_l0)
    trajectory = model.predict_sequence(list(responses))
    return float(trajectory[-1])
