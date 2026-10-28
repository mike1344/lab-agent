"""为新数据库创建第一个管理员账号。"""

import argparse
from getpass import getpass

from app.database import Base, SessionLocal, engine
from app.models import Equipment, Lab, Reservation, User  # noqa: F401
from app.utils.password import hash_password


def main():
    parser = argparse.ArgumentParser(description="创建智能实验室系统管理员")
    parser.add_argument("--username", required=True, help="管理员用户名")
    parser.add_argument("--email", required=True, help="管理员邮箱")
    parser.add_argument("--full-name", default="系统管理员", help="管理员姓名")
    args = parser.parse_args()

    # 使用 getpass 读取密码，不让密码明文显示在终端或命令历史中。
    password = getpass("请输入管理员密码（至少 8 位）：")
    if len(password) < 8:
        raise SystemExit("密码长度不能少于 8 位")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        exists = (
            db.query(User).filter((User.username == args.username.strip()) | (User.email == args.email.lower())).first()
        )
        if exists:
            raise SystemExit("用户名或邮箱已存在")

        user = User(
            username=args.username.strip(),
            password=hash_password(password),
            email=args.email.lower(),
            full_name=args.full_name.strip() or None,
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        print(f"管理员 {user.username} 创建成功")


if __name__ == "__main__":
    main()
