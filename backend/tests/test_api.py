"""核心业务接口回归测试，使用独立 SQLite 数据库，不会改动开发 MySQL 数据。"""

import base64
import gc
import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

# 测试库只在系统临时目录中创建，不删除或覆盖项目内的同名文件。
TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="lab_agent_api_test_")
TEST_DB = Path(TEST_DIRECTORY.name) / "test_lab_agent.db"

# 必须在导入 app 之前覆盖数据库配置，因为 engine 会在导入阶段创建。
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DB.as_posix()}"
os.environ["OPENAI_API_KEY"] = ""

from fastapi.testclient import TestClient
from chromadb.api.client import SharedSystemClient

from app.ai.knowledge import build_local_embedding
from app.database import SessionLocal, engine
from app.ai.agent import has_explicit_reservation_intent, local_tool_node
from app.main import app
from app.models.user import User
from app.utils.password import hash_password


def extract_streamed_tokens(raw_text: str) -> str:
    """把 SSE 响应里的 token 事件拼接成完整回答，避免断言依赖分段边界。"""
    content = []
    for line in raw_text.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[len("data: "):])
            if "content" in payload:
                content.append(payload["content"])
    return "".join(content)


class ApiFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # AI SSE 会调用真实 RAG；索引也放在临时目录，避免测试改动开发知识库。
        cls.chroma_directory = tempfile.TemporaryDirectory(prefix="lab_agent_chroma_test_")
        cls.chroma_patch = patch("app.ai.knowledge.CHROMA_DIR", Path(cls.chroma_directory.name))
        cls.chroma_patch.start()
        with SessionLocal() as db:
            db.add(
                User(
                    username="admin",
                    password=hash_password("Admin123456"),
                    email="admin@example.com",
                    full_name="系统管理员",
                    is_active=True,
                    is_superuser=True,
                )
            )
            db.commit()

    @classmethod
    def tearDownClass(cls):
        engine.dispose()
        cls.chroma_patch.stop()
        SharedSystemClient.clear_system_cache()
        gc.collect()
        cls.chroma_directory.cleanup()
        TEST_DIRECTORY.cleanup()

    def login(self, username: str, password: str) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        self.assertEqual(response.json()["code"], 200)
        return {"Authorization": f"Bearer {response.json()['data']['token']}"}

    def test_health_endpoint(self):
        """部署探活：/health 必须返回 200 和 status=ok，供监控系统探测。"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_local_embedding_is_stable(self):
        """本地向量必须固定且归一化，否则同一问题每次检索结果会漂移。"""
        first_vector = build_local_embedding("实验室设备故障")
        second_vector = build_local_embedding("实验室设备故障")

        self.assertEqual(first_vector, second_vector)
        self.assertEqual(len(first_vector), 128)
        vector_length = sum(value * value for value in first_vector) ** 0.5
        self.assertAlmostEqual(vector_length, 1.0)

    def test_password_change_invalidates_old_token(self):
        """修改密码后旧 JWT 必须失效，新密码可以重新登录。"""
        register_data = {
            "username": "password_user",
            "password": "OldPassword123",
            "email": "password-user@example.com",
            "full_name": "改密测试用户",
        }
        self.assertEqual(
            self.client.post("/api/auth/register", json=register_data).status_code,
            200,
        )
        old_headers = self.login("password_user", "OldPassword123")

        changed = self.client.put(
            "/api/user/password",
            headers=old_headers,
            json={"old_password": "OldPassword123", "new_password": "NewPassword456"},
        )
        self.assertEqual(changed.status_code, 200)

        old_token_result = self.client.get("/api/user/info", headers=old_headers)
        self.assertEqual(old_token_result.status_code, 401)
        self.assertEqual(old_token_result.json()["code"], 401)

        new_headers = self.login("password_user", "NewPassword456")
        self.assertEqual(
            self.client.get("/api/user/info", headers=new_headers).status_code,
            200,
        )

    def test_ai_confirmation_uses_latest_request_and_respects_cancellation(self):
        """多轮确认应选最新参数；否定或撤回消息绝不能调用写工具。"""
        old_request = "预约实验室ID 1 2026-10-01 09:00-10:00 用途：旧需求"
        new_request = "预约实验室ID 2 2026-10-02 11:00-12:00 用途：新需求"
        history = [
            {"role": "user", "content": old_request},
            {"role": "user", "content": new_request},
        ]
        self.assertFalse(has_explicit_reservation_intent("不要帮我预约"))
        self.assertFalse(has_explicit_reservation_intent("我不想创建预约"))

        with patch("app.ai.agent.create_lab_reservation", return_value="预约已创建") as create_tool:
            local_tool_node({"message": "确认预约", "history": history, "user_id": 1, "db": object()})
            self.assertEqual(create_tool.call_args.args[2]["lab_id"], 2)
            self.assertEqual(create_tool.call_args.args[2]["purpose"], "新需求")

            create_tool.reset_mock()
            local_tool_node({"message": "不要帮我预约", "history": history, "user_id": 1, "db": object()})
            create_tool.assert_not_called()

            cancelled_history = [*history, {"role": "user", "content": "取消预约"}]
            local_tool_node({"message": "确认预约", "history": cancelled_history, "user_id": 1, "db": object()})
            create_tool.assert_not_called()

            stale_history = [history[0], {"role": "user", "content": "查询设备故障说明"}]
            local_tool_node({"message": "确认预约", "history": stale_history, "user_id": 1, "db": object()})
            create_tool.assert_not_called()

    def test_full_business_flow(self):
        # 1. 注册、重复注册与登录。
        register_data = {
            "username": "student01",
            "password": "Student123",
            "email": "student01@example.com",
            "full_name": "测试学生",
        }
        self.assertEqual(self.client.post("/api/auth/register", json=register_data).json()["code"], 200)
        self.assertEqual(self.client.post("/api/auth/register", json=register_data).json()["code"], 400)

        # 错误密码必须返回真实 HTTP 401，同时仍保留统一响应体。
        invalid_login = self.client.post(
            "/api/auth/login",
            json={"username": "student01", "password": "WrongPassword123"},
        )
        self.assertEqual(invalid_login.status_code, 401)
        self.assertEqual(invalid_login.json()["code"], 401)

        student_headers = self.login("student01", "Student123")
        admin_headers = self.login("admin", "Admin123456")

        invalid_user = self.client.post(
            "/api/user",
            headers=admin_headers,
            json={"username": "   ", "password": "Password123", "email": "invalid-name@example.com"},
        )
        self.assertEqual(invalid_user.status_code, 400)

        info = self.client.get("/api/user/info", headers=student_headers).json()
        self.assertEqual(info["data"]["full_name"], "测试学生")

        # 普通用户不能调用管理员接口；依赖层应返回真实 HTTP 403。
        forbidden = self.client.post(
            "/api/labs",
            headers=student_headers,
            json={"name": "越权实验室", "location": "未知位置", "capacity": 1},
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["code"], 403)

        # 2. 管理员创建实验室和设备。
        lab_response = self.client.post(
            "/api/labs",
            headers=admin_headers,
            json={"name": "  人工智能实验室  ", "location": "实训楼 301", "capacity": 40, "description": "AI 实验教学", "status": 1},
        ).json()
        self.assertEqual(lab_response["code"], 200)
        self.assertEqual(lab_response["data"]["name"], "人工智能实验室")
        lab_id = lab_response["data"]["id"]

        # 显式 null 和全空格不能绕过更新/新增校验写坏数据库必填列。
        self.assertEqual(
            self.client.put(f"/api/labs/{lab_id}", headers=admin_headers, json={"status": None}).status_code,
            400,
        )
        self.assertEqual(
            self.client.post("/api/labs", headers=admin_headers, json={"name": "  ", "location": "三楼"}).status_code,
            400,
        )

        equipment_response = self.client.post(
            "/api/equipment",
            headers=admin_headers,
            json={"lab_id": lab_id, "name": " GPU 工作站 ", "code": " GPU-001 ", "quantity": 10, "description": "模型训练", "status": 1},
        ).json()
        self.assertEqual(equipment_response["code"], 200)
        self.assertEqual(equipment_response["data"]["code"], "GPU-001")
        self.assertEqual(
            self.client.put(
                f"/api/equipment/{equipment_response['data']['id']}",
                headers=admin_headers,
                json={"quantity": None},
            ).status_code,
            400,
        )

        # 3. 学生提交预约；同一时间段的第二条申请会被拦截。
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        reservation_data = {
            "lab_id": lab_id,
            "reservation_date": tomorrow,
            "start_time": "09:00:00",
            "end_time": "11:00:00",
            "purpose": "人工智能实验教学",
        }
        reservation_response = self.client.post(
            "/api/reservations", headers=student_headers, json=reservation_data
        ).json()
        self.assertEqual(reservation_response["code"], 200)
        # 创建接口支持每周重复，返回创建成功的预约列表；此处未开启重复，只有一条。
        self.assertEqual(len(reservation_response["data"]), 1)
        reservation_id = reservation_response["data"][0]["id"]
        conflict = self.client.post(
            "/api/reservations", headers=student_headers, json=reservation_data
        ).json()
        self.assertEqual(conflict["code"], 400)

        past_time_today = {
            **reservation_data,
            "reservation_date": date.today().isoformat(),
            "start_time": "00:00:00",
            "end_time": "00:01:00",
        }
        self.assertEqual(
            self.client.post(
                "/api/reservations", headers=student_headers, json=past_time_today
            ).status_code,
            400,
        )

        # 4. 实验室暂停后不能批准；恢复开放后，管理员可以正常审核。
        self.assertEqual(
            self.client.put(f"/api/labs/{lab_id}", headers=admin_headers, json={"status": 0}).status_code,
            200,
        )
        self.assertEqual(
            self.client.put(
                f"/api/reservations/{reservation_id}/review",
                headers=admin_headers,
                json={"status": "approved", "review_comment": "暂停期间不应通过"},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.put(f"/api/labs/{lab_id}", headers=admin_headers, json={"status": 1}).status_code,
            200,
        )

        # 5. 管理员审核后，学生可以在“我的预约”看到结果并取消。
        review = self.client.put(
            f"/api/reservations/{reservation_id}/review",
            headers=admin_headers,
            json={"status": "approved", "review_comment": "请按时到场"},
        ).json()
        self.assertEqual(review["code"], 200)
        mine = self.client.get("/api/reservations/mine", headers=student_headers).json()
        self.assertEqual(mine["data"][0]["status"], "approved")
        cancel = self.client.put(
            f"/api/reservations/{reservation_id}/cancel", headers=student_headers
        ).json()
        self.assertEqual(cancel["code"], 200)

        # 5. 上传接口与本地 AI SSE 链路都能独立运行。
        invalid_upload = self.client.post(
            "/api/upload/image",
            headers=student_headers,
            files={"file": ("demo.png", b"fake-png-content", "image/png")},
        )
        self.assertEqual(invalid_upload.status_code, 400)

        # 使用真实的 1×1 PNG，验证合法图片仍能保存并返回静态路径。
        valid_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        with tempfile.TemporaryDirectory(prefix="lab_agent_upload_test_") as upload_dir:
            with patch("app.api.upload.UPLOAD_DIR", Path(upload_dir)):
                upload = self.client.post(
                    "/api/upload/image",
                    headers=student_headers,
                    files={"file": ("demo.png", valid_png, "image/png")},
                ).json()
                self.assertEqual(upload["code"], 200)
                self.assertTrue((Path(upload_dir) / upload["data"]["filename"]).exists())

        ai_response = self.client.post(
            "/api/ai/chat/stream",
            headers=student_headers,
            json={"message": "当前有哪些开放的实验室和设备？", "history": []},
        )
        self.assertEqual(ai_response.status_code, 200)
        self.assertIn("event: token", ai_response.text)
        # SSE 会把回答拆成多个 token 事件，拼接完整回答后再校验内容。
        streamed_answer = extract_streamed_tokens(ai_response.text)
        self.assertIn("GPU", streamed_answer)

        # 6. 多轮 AI 预约：上一轮提供参数，本轮明确确认；重复确认不能生成第二条记录。
        reservation_instruction = (
            f"预约实验室ID {lab_id} {tomorrow} 13:00-14:00 用途：多轮对话预约测试"
        )
        multi_turn_payload = {
            "message": "确认预约",
            "history": [{"role": "user", "content": reservation_instruction}],
        }
        ai_reservation = self.client.post(
            "/api/ai/chat/stream",
            headers=student_headers,
            json=multi_turn_payload,
        )
        self.assertEqual(ai_reservation.status_code, 200)
        self.assertIn("create_lab_reservation", ai_reservation.text)

        # 再发一次相同确认会命中时间冲突，数据库中仍然只有一条该用途的预约。
        self.client.post(
            "/api/ai/chat/stream",
            headers=student_headers,
            json=multi_turn_payload,
        )
        mine_after_ai = self.client.get(
            "/api/reservations/mine",
            headers=student_headers,
        ).json()["data"]
        ai_reservations = [
            item for item in mine_after_ai if item["purpose"] == "多轮对话预约测试"
        ]
        self.assertEqual(len(ai_reservations), 1)
        self.assertEqual(ai_reservations[0]["status"], "pending")

    def test_avatar_persists_and_plain_profile_save_keeps_it(self):
        """头像上传后必须落库；之后再保存普通资料不能把头像清空。"""
        register_data = {
            "username": "avatar_user",
            "password": "Avatar12345",
            "email": "avatar-user@example.com",
            "full_name": "头像用户",
        }
        self.assertEqual(self.client.post("/api/auth/register", json=register_data).json()["code"], 200)
        headers = self.login("avatar_user", "Avatar12345")

        valid_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        with tempfile.TemporaryDirectory(prefix="lab_agent_avatar_test_") as upload_dir:
            with patch("app.api.upload.UPLOAD_DIR", Path(upload_dir)):
                upload = self.client.post(
                    "/api/upload/image",
                    headers=headers,
                    files={"file": ("avatar.png", valid_png, "image/png")},
                ).json()
                self.assertEqual(upload["code"], 200)
        avatar_url = f"http://127.0.0.1:8000{upload['data']['url']}"

        saved = self.client.put(
            "/api/user/profile",
            headers=headers,
            json={"email": "avatar-user@example.com", "full_name": "头像用户", "avatar_url": avatar_url},
        ).json()
        self.assertEqual(saved["code"], 200)
        self.assertEqual(saved["data"]["avatar_url"], avatar_url)

        plain_save = self.client.put(
            "/api/user/profile",
            headers=headers,
            json={"email": "avatar-user@example.com", "full_name": "改个名字"},
        ).json()
        self.assertEqual(plain_save["code"], 200)
        # 没有显式携带 avatar_url 时，已有头像不能被清空。
        self.assertEqual(plain_save["data"]["avatar_url"], avatar_url)

    def test_reservation_update_cannot_bypass_slot_rules(self):
        """修改待审核预约时，冲突/当天过期/超时长/黑名单规则必须生效。"""
        admin_headers = self.login("admin", "Admin123456")
        register_data = {
            "username": "editor_user",
            "password": "Editor12345",
            "email": "editor-user@example.com",
            "full_name": "修改预约用户",
        }
        self.assertEqual(self.client.post("/api/auth/register", json=register_data).json()["code"], 200)
        headers = self.login("editor_user", "Editor12345")

        lab_id = self.client.post(
            "/api/labs",
            headers=admin_headers,
            json={"name": "修改校验实验室", "location": "实训楼 501", "capacity": 10, "status": 1},
        ).json()["data"]["id"]

        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        first = self.client.post(
            "/api/reservations",
            headers=headers,
            json={
                "lab_id": lab_id,
                "reservation_date": tomorrow,
                "start_time": "09:00:00",
                "end_time": "11:00:00",
                "purpose": "修改校验-第一条",
            },
        ).json()
        self.assertEqual(first["code"], 200)
        second_id = self.client.post(
            "/api/reservations",
            headers=headers,
            json={
                "lab_id": lab_id,
                "reservation_date": tomorrow,
                "start_time": "11:00:00",
                "end_time": "12:00:00",
                "purpose": "修改校验-第二条",
            },
        ).json()["data"][0]["id"]

        # 1) 改成与已有预约冲突的时间
        conflict = self.client.put(
            f"/api/reservations/{second_id}",
            headers=headers,
            json={"start_time": "10:00:00", "end_time": "11:30:00"},
        )
        self.assertEqual(conflict.status_code, 400)

        # 2) 改成今天已经过去的开始时间
        past = self.client.put(
            f"/api/reservations/{second_id}",
            headers=headers,
            json={"reservation_date": date.today().isoformat(), "start_time": "00:00:00", "end_time": "00:30:00"},
        )
        self.assertEqual(past.status_code, 400)

        # 3) 单次超过 4 小时
        too_long = self.client.put(
            f"/api/reservations/{second_id}",
            headers=headers,
            json={"start_time": "12:00:00", "end_time": "17:00:00"},
        )
        self.assertEqual(too_long.status_code, 400)

        # 4) 改成管理员设置的不可约时段
        blackout = self.client.post(
            "/api/blackouts",
            headers=admin_headers,
            json={"lab_id": lab_id, "blackout_date": tomorrow, "start_time": "13:00:00", "end_time": "14:00:00", "reason": "维护测试"},
        ).json()
        self.assertEqual(blackout["code"], 200)
        blocked = self.client.put(
            f"/api/reservations/{second_id}",
            headers=headers,
            json={"start_time": "13:00:00", "end_time": "13:30:00"},
        )
        self.assertEqual(blocked.status_code, 400)

        # 所有非法修改都被拦截后，原记录保持 11:00-12:00 不变
        mine = self.client.get("/api/reservations/mine", headers=headers).json()["data"]
        current = next(item for item in mine if item["id"] == second_id)
        self.assertEqual(str(current["start_time"]), "11:00:00")
        self.assertEqual(str(current["end_time"]), "12:00:00")

    def test_repair_handling_creates_notification(self):
        """管理员处理报修后，报修人应收到站内通知。"""
        admin_headers = self.login("admin", "Admin123456")
        register_data = {
            "username": "repair_user",
            "password": "Repair12345",
            "email": "repair-user@example.com",
            "full_name": "报修用户",
        }
        self.assertEqual(self.client.post("/api/auth/register", json=register_data).json()["code"], 200)
        headers = self.login("repair_user", "Repair12345")

        created = self.client.post(
            "/api/repairs",
            headers=headers,
            json={"title": "投影仪无法开机", "description": "按电源键没有反应，指示灯不亮。"},
        ).json()
        self.assertEqual(created["code"], 200)
        repair_id = created["data"]["id"]

        handled = self.client.put(
            f"/api/repairs/{repair_id}/handle",
            headers=admin_headers,
            json={"status": "processing", "handle_comment": "已联系维修师傅，明天上门。"},
        ).json()
        self.assertEqual(handled["code"], 200)

        notifications = self.client.get("/api/notifications/mine", headers=headers).json()["data"]
        repair_notifications = [item for item in notifications if item["type"] == "repair_result"]
        self.assertEqual(len(repair_notifications), 1)
        self.assertIn("处理中", repair_notifications[0]["title"])
        self.assertEqual(repair_notifications[0]["related_id"], repair_id)

    def test_ai_recommendation_respects_blackout_and_past_dates(self):
        """推荐工具应跳过不可约时段和已经过去的日期。"""
        from app.ai.tools import check_lab_availability, recommend_lab

        admin_headers = self.login("admin", "Admin123456")
        lab_id = self.client.post(
            "/api/labs",
            headers=admin_headers,
            json={"name": "黑名单推荐实验室", "location": "实训楼 601", "capacity": 8, "status": 1},
        ).json()["data"]["id"]
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.client.post(
            "/api/blackouts",
            headers=admin_headers,
            json={"lab_id": lab_id, "blackout_date": tomorrow, "start_time": "13:00:00", "end_time": "18:00:00", "reason": "全天维护"},
        )

        with SessionLocal() as db:
            availability = check_lab_availability(db, lab_id, tomorrow)
            self.assertIn("不可约", availability)
            self.assertIn("全天维护", availability)

            # 该实验室整个下午都不可约，不能被推荐
            recommendation = recommend_lab(db, tomorrow, "afternoon", 2)
            self.assertNotIn("黑名单推荐实验室", recommendation)

            # 已经过去的日期不再给出推荐
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            past = recommend_lab(db, yesterday, "afternoon", 2)
            self.assertIn("已经过去", past)


if __name__ == "__main__":
    unittest.main()
