"""Which database the tests run against.

SQLite in memory by default (fast, nothing to install). Set TEST_DATABASE_URL to a
PostgreSQL URL, as the CI does, to run the same tests against the production engine
and the Alembic migrations instead.
"""

import os

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
