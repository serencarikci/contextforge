"""API test fixtures.

``tenant_scenario`` and ``TenantScenario`` live in the root ``tests/conftest.py``
so that ``tests/security/`` (which also drives the same authorization/tenancy
scenarios through real HTTP requests) can reuse them.
"""

from __future__ import annotations
