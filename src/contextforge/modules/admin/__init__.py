"""Administration and governance module (Phase 4).

Owns platform/organization administration concerns that sit *on top of* the
existing tenant modules: organization settings and quotas, feature flags,
versioned prompt templates, per-organization LLM provider configuration,
token/cost analytics, and data retention policies.

Services in this module orchestrate the repositories that already exist in
other modules wherever possible instead of duplicating their read models.
"""
