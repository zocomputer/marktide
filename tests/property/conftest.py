"""Bounded Hypothesis profiles for AA#2 property/metamorphic tests."""

from __future__ import annotations

import os

from hypothesis import HealthCheck, settings

settings.register_profile(
    "fast",
    max_examples=100,
    deadline=200,
    suppress_health_check=(HealthCheck.too_slow, HealthCheck.filter_too_much),
)
settings.register_profile(
    "nightly",
    max_examples=500,
    deadline=500,
    suppress_health_check=(HealthCheck.too_slow, HealthCheck.filter_too_much),
)
settings.register_profile(
    "campaign",
    max_examples=2000,
    deadline=None,
    suppress_health_check=(HealthCheck.too_slow, HealthCheck.filter_too_much),
)

# Fast is the default to prevent local/agent runs from hanging. CI/nightly can
# opt into heavier profiles via HYPOTHESIS_PROFILE=nightly or pytest's native
# --hypothesis-profile flag.
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "fast"))
