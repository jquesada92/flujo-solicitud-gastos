"""Compatibility entrypoint.

The application factory lives in app.application. Keeping this module as a thin
alias preserves local commands such as `uvicorn app.main:app` without putting
migrations, seeds or business configuration in FastAPI startup.
"""

from app.application import app, create_app

__all__ = ['app', 'create_app']
