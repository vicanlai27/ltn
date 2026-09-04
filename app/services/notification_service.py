from app.extensions import db
from app.models.notifications import Notification
from app.models.user import User

def notify_user(user_id, kind, title, message=None, link_url=None):
    item = Notification(user_id=user_id, kind=kind, title=title, message=message, link_url=link_url)
    db.session.add(item)
    db.session.commit()
    return item

def notify_roles(roles, kind, title, message=None, link_url=None, exclude_user_id=None):
    users = User.query.filter(User.role.in_(tuple(roles)), User.account_status == User.STATUS_ACTIVE).all()
    created=[]
    for user in users:
        if exclude_user_id and user.id == exclude_user_id:
            continue
        created.append(Notification(user_id=user.id, kind=kind, title=title, message=message, link_url=link_url))
    if created:
        db.session.add_all(created)
        db.session.commit()
    return created
