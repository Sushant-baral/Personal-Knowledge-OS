"""
This project doesn't have authentication yet, so every request currently
operates as a single local user. All routes call get_or_create_default_user()
instead of trusting a user_id from the client. Replace this once real auth
is added — nothing else in the codebase should need to change, since
everything else already takes a user_id.
"""

from sqlalchemy.orm import Session

from app.database.models import User

_DEFAULT_USER_NAME = "default"


def get_or_create_default_user(db: Session) -> User:
    user = db.query(User).filter(User.name == _DEFAULT_USER_NAME).first()
    if user:
        return user

    user = User(name=_DEFAULT_USER_NAME)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
