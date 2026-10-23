"""Test defaults.

The full test suite exercises the admin catalog. Edition-specific tests spawn a
subprocess with ``MCP_EDITION`` set so import-time resolution is exercised.
"""

import os

os.environ.setdefault("MCP_EDITION", "admin")
