"""用户种子数据脚本（v0.9+）。

新增/确保测试账号：
- admin / admin123（role=admin）
- favtest1 / abc123（role=user）
- shop01 / 123456（role=merchant, shop_name=默认店铺）

不再生成 guest 账号。脚本幂等，可重复执行。
必须传入 --yes 才会执行写入操作。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, engine
from core.hash import get_password_hash
from models import User


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="初始化测试用户（admin/user/merchant），不生成 guest")
    parser.add_argument("--yes", action="store_true", help="确认执行种子初始化")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    print("=== seed_users start ===")
    print("target:", str(engine.url).replace("://", "://***:***@") if "@" in str(engine.url) else engine.url)

    if not args.yes:
        print("WARNING: 将创建/更新测试账号（admin/favtest1/shop01），不生成 guest。")
        print("WARNING: 未传入 --yes，已退出。")
        print("hint: python scripts/seed_users.py --yes")
        return 2

    db = SessionLocal()
    try:
        seeds = [
            {"username": "admin", "password": "admin123", "role": "admin", "email": None, "shop_name": None, "audit_status": "approved"},
            {"username": "favtest1", "password": "abc123", "role": "user", "email": None, "shop_name": None, "audit_status": "approved"},
            {"username": "shop01", "password": "123456", "role": "merchant", "email": None, "shop_name": "默认店铺", "audit_status": "approved"},
            {"username": "shop02", "password": "123456", "role": "merchant", "email": None, "shop_name": "待审核客栈", "audit_status": "pending"},
        ]
        for s in seeds:
            user = db.query(User).filter(User.username == s["username"]).first()
            if user:
                user.role = s["role"]
                user.shop_name = s.get("shop_name")
                user.audit_status = s.get("audit_status", "approved")
                user.password_hash = get_password_hash(s["password"])
                print(f"updated: {s['username']} role={s['role']} audit={user.audit_status}")
            else:
                user = User(
                    username=s["username"],
                    password_hash=get_password_hash(s["password"]),
                    role=s["role"],
                    email=s.get("email"),
                    shop_name=s.get("shop_name"),
                    audit_status=s.get("audit_status", "approved"),
                )
                db.add(user)
                print(f"created: {s['username']} role={s['role']} audit={user.audit_status}")

        # 清理 guest 账号（如存在）
        guest = db.query(User).filter(User.role == "guest").all()
        for g in guest:
            print(f"removing guest user: {g.username} (id={g.id})")
            db.delete(g)

        db.commit()
        print("=== seed_users done ===")
        print("accounts: admin/admin123, favtest1/abc123, shop01/123456(approved), shop02/123456(pending)")
        return 0
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
