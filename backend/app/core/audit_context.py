"""Attach an auditable actor to the SQLAlchemy connection doing a mutation."""

from sqlalchemy.orm import Session


def set_audit_actor(
    db: Session,
    *,
    user_id: int | None,
    identifier: str,
    identity_document: str | None = None,
    label: str | None = None,
) -> None:
    actor = {
        'user_id': user_id,
        'identifier': identifier,
        'identity_document': identity_document,
        'label': label,
    }
    db.info['audit_actor'] = actor
    connection = db.connection()
    connection.info['audit_actor'] = actor


def set_system_audit_actor(db: Session, identifier: str) -> None:
    set_audit_actor(db, user_id=None, identifier=identifier, label='Sistema')
