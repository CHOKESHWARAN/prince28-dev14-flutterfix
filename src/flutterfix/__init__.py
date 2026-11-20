"""FlutterFix package."""

import os

# Ensure pure-Python mode for SQLAlchemy across all environments
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")
