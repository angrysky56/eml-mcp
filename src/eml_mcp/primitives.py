"""
EML Primitives — core arithmetic functions.

Implementation of the EML (Exp-Minus-Log) Sheffer operator and helper
functions for complex domain safety.
"""

from __future__ import annotations

import numpy as np

# Use complex128 throughout — EML requires complex intermediates
DTYPE = np.complex128

# Safe limits for exp to prevent overflow
EXP_CLAMP_MAX = 700.0  # exp(709) overflows float64
EXP_CLAMP_MIN = -700.0


def _safe_exp(z: complex | np.ndarray) -> complex | np.ndarray:
    """Clamped complex exponential to prevent overflow."""
    if isinstance(z, np.ndarray):
        real_clamped = np.clip(z.real, EXP_CLAMP_MIN, EXP_CLAMP_MAX)
        return np.exp(real_clamped + 1j * z.imag)
    real = max(EXP_CLAMP_MIN, min(EXP_CLAMP_MAX, z.real))
    return np.exp(complex(real, z.imag))


def _safe_log(z: complex | np.ndarray) -> complex | np.ndarray:
    """Complex logarithm (principal branch) with zero handling.

    Uses extended reals convention: ln(0) = -inf, consistent with
    IEEE754 and the EML paper's requirements.
    """
    if isinstance(z, np.ndarray):
        # Handle zero entries
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.log(z.astype(DTYPE))
    if z == 0:
        return complex(float("-inf"), 0.0)
    return np.log(complex(z))


def eml(x: complex, y: complex) -> complex:
    """The EML (Exp-Minus-Log) Sheffer operator.

    eml(x, y) = exp(x) - ln(y)

    This single binary operator, paired with the constant 1,
    generates all standard elementary functions.

    Args:
        x: First argument (feeds into exp).
        y: Second argument (feeds into ln).

    Returns:
        exp(x) - ln(y) as a complex number.
    """
    return _safe_exp(complex(x)) - _safe_log(complex(y))


def eml_array(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Vectorized EML operator for array inputs."""
    return _safe_exp(x.astype(DTYPE)) - _safe_log(y.astype(DTYPE))
