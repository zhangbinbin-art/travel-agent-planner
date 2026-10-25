import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models import User
from core.hash import get_password_hash

db = SessionLocal()

# 确保存在管理员测试账号 admin / admin123
admin = db.query(User).filter(User.username == "admin").first()
if not admin:
    admin = User(username="admin", password_hash=get_password_hash("admin123"), role="admin")
    db.add(admin)
else:
    admin.role = "admin"
db.commit()

for u in db.query(User).all():
    print(u.id, u.username, u.role)
db.close()
