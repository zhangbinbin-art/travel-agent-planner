"""手机号登录准备：去掉 phone 唯一约束 + 建立演示双身份账号。

用法：
    python scripts/init_phone_login.py            # 预览
    python scripts/init_phone_login.py --apply    # 执行

说明：
    - 同一手机号允许同时存在「普通用户」与「商户」两条记录，因此 phone 不能唯一；
    - 演示账号：同一手机号 13800000000 下分别有普通用户 demouser 与商户 demoshop，密码均为 123456；
    - 顺带清理测试期间创建的 phonetest* 账号。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from core.database import SessionLocal, engine
from core.hash import get_password_hash
from models import User

DEMO_PHONE = "13800000000"
DEMO_PASSWORD = "123456"

DEMO_ACCOUNTS = [
    {"username": "demouser", "role": "user", "shop_name": None, "audit_status": "approved"},
    {"username": "demoshop", "role": "merchant", "shop_name": "示例民宿", "audit_status": "approved"},
]

CLEANUP_PREFIX = "phonetest"


def adjust_indexes(apply: bool) -> None:
    inspector = inspect(engine)
    indexes = inspector.get_indexes("users")
    names = {idx.get("name") for idx in indexes}
    unique_phone = [
        idx for idx in indexes if idx.get("unique") and idx.get("column_names") == ["phone"]
    ]
    print("当前 phone 相关索引：", [i.get("name") for i in unique_phone] or "无唯一索引")
    if not apply:
        return
    with engine.begin() as conn:
        for idx in unique_phone:
            conn.execute(text("ALTER TABLE users DROP INDEX `%s`" % idx["name"]))
            print("[DONE] 已删除唯一索引", idx["name"])
        if "ix_users_phone" not in names:
            conn.execute(text("ALTER TABLE users ADD INDEX ix_users_phone (phone)"))
            print("[DONE] 已创建普通索引 ix_users_phone")


def ensure_demo_accounts(apply: bool) -> None:
    db = SessionLocal()
    hashed = get_password_hash(DEMO_PASSWORD)
    for account in DEMO_ACCOUNTS:
        existing = db.query(User).filter(User.username == account["username"]).first()
        action = "更新" if existing else "创建"
        print("[%s] %-10s role=%-8s phone=%s" % (action, account["username"], account["role"], DEMO_PHONE))
        if not apply:
            continue
        if existing:
            existing.phone = DEMO_PHONE
            existing.role = account["role"]
            existing.password_hash = hashed
            existing.audit_status = account["audit_status"]
            if account["role"] == "merchant":
                existing.shop_name = account["shop_name"]
        else:
            db.add(
                User(
                    username=account["username"],
                    password_hash=hashed,
                    role=account["role"],
                    phone=DEMO_PHONE,
                    audit_status=account["audit_status"],
                    shop_name=account["shop_name"],
                )
            )
    if apply:
        db.commit()

    leftovers = db.query(User).filter(User.username.like(CLEANUP_PREFIX + "%")).all()
    if leftovers:
        print("清理测试账号：", [u.username for u in leftovers])
        if apply:
            for user in leftovers:
                db.delete(user)
            db.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    adjust_indexes(args.apply)
    ensure_demo_accounts(args.apply)
    if not args.apply:
        print("DRY-RUN 结束，加 --apply 才会执行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
