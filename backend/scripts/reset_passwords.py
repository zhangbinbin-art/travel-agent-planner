"""一次性迁移：为用户表补 phone 列，并把所有账号密码重置为 123456。

用法：
    python scripts/reset_passwords.py            # 预览
    python scripts/reset_passwords.py --apply    # 执行

说明：
    - 若 users 表缺少 phone 列，自动 ALTER TABLE 添加（唯一索引由模型声明，MySQL 下为普通列 + 唯一约束）；
    - 所有账号（含 admin / 商家 / 普通用户）密码统一重置为 123456；
    - 只改 users.password_hash 与表结构，不动任何业务数据。
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from core.database import engine
from core.hash import get_password_hash
from core.database import SessionLocal
from models import User

DEFAULT_PASSWORD = "123456"


def ensure_phone_column(apply: bool) -> bool:
    columns = {col["name"] for col in inspect(engine).get_columns("users")}
    if "phone" in columns:
        print("[SKIP] users.phone 已存在")
        return False
    print("[FIX ] users 表缺少 phone 列，将执行 ALTER TABLE")
    if apply:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20) NULL"))
            try:
                conn.execute(text("ALTER TABLE users ADD UNIQUE INDEX uq_users_phone (phone)"))
            except Exception as exc:  # 索引已存在时忽略
                print("       唯一索引创建跳过：", exc)
        print("[DONE] phone 列已添加")
    return True


def reset_passwords(apply: bool) -> None:
    db = SessionLocal()
    users = db.query(User).order_by(User.id).all()
    print("=== 待重置账号 %d 个 ===" % len(users))
    for user in users:
        print("  id=%-3s %-12s role=%-8s -> %s" % (user.id, user.username, user.role, DEFAULT_PASSWORD))
    if not apply:
        return
    hashed = get_password_hash(DEFAULT_PASSWORD)
    for user in users:
        user.password_hash = hashed
    db.commit()
    print("[DONE] 已重置 %d 个账号密码为 %s" % (len(users), DEFAULT_PASSWORD))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    ensure_phone_column(args.apply)
    reset_passwords(args.apply)
    if not args.apply:
        print("DRY-RUN 结束，加 --apply 才会写库。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
