"""核心业务接口回归测试，使用独立 SQLite 数据库，不会改动开发 MySQL 数据。"""

import base64
import gc
import json
import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
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
from app.ai.agent import execute_tools_node, has_explicit_reservation_intent, local_tool_node
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


class _ScriptedChatClient:
    """按脚本吐流的假模型客户端：每次 create 调用依次消费一段预置分片。

    如果脚本被多调用一次，会直接抛断言错误——这正是回归“模型被重复调用”问题：
    修复前一次问答会同时命中图内 agent 和图外 run_model_tools 两条路径。
    """

    def __init__(self, rounds):
        self.rounds = list(rounds)
        self.create_calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.create_calls += 1
        if not self.rounds:
            raise AssertionError("模型调用次数超出脚本预期：说明存在重复调用路径")
        return iter(self.rounds.pop(0))


def _content_round(text, chunk_size=4):
    """构造一轮纯文本流式返回。"""
    return [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content=text[index : index + chunk_size], tool_calls=None)
                )
            ]
        )
        for index in range(0, len(text), chunk_size)
    ]


def _tool_call_round(name, arguments, call_id="call_1"):
    """构造一轮工具调用返回：首片带 id 和名称，后续片增量下发参数。"""
    return [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                index=0,
                                id=call_id,
                                function=SimpleNamespace(name=name, arguments=""),
                            )
                        ],
                    )
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(
                        content=None,
                        tool_calls=[
                            SimpleNamespace(
                                index=0,
                                id=None,
                                function=SimpleNamespace(name=None, arguments=arguments),
                            )
                        ],
                    )
                )
            ]
        ),
    ]


class AiStreamConvergenceTest(unittest.TestCase):
    """回归：工具事件与回答 token 必须只来自图内一条路径。

    背景：修复前模型工具调用在图内 agent 和图外 run_model_tools 各执行一遍，
    模型被调用三次、写工具可能被重复执行。现在统一为图内单一路径。
    本类字母序先于 ApiFlowTest 执行且共享同一临时数据库：收尾时只清理自己的
    Chroma 索引目录，共享数据库文件留给 ApiFlowTest 统一删除。
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.chroma_directory = tempfile.TemporaryDirectory(prefix="lab_agent_chroma_sse_test_")
        cls.chroma_patch = patch("app.ai.knowledge.CHROMA_DIR", Path(cls.chroma_directory.name))
        cls.chroma_patch.start()
        registered = cls.client.post(
            "/api/auth/register",
            json={
                "username": "sse_user",
                "password": "Sse123456",
                "email": "sse-user@example.com",
                "full_name": "流式回归用户",
            },
        )
        if registered.json()["code"] != 200:
            raise RuntimeError(f"测试用户注册失败：{registered.text}")

    @classmethod
    def tearDownClass(cls):
        cls.chroma_patch.stop()
        SharedSystemClient.clear_system_cache()
        gc.collect()
        cls.chroma_directory.cleanup()

    def login_sse_user(self) -> dict[str, str]:
        response = self.client.post(
            "/api/auth/login",
            json={"username": "sse_user", "password": "Sse123456"},
        )
        self.assertEqual(response.json()["code"], 200)
        return {"Authorization": f"Bearer {response.json()['data']['token']}"}

    def test_keyed_graph_is_the_only_tool_path(self):
        """有 Key 且需要一次工具调用：模型最多调 2 次、工具只执行 1 次、事件完整。"""
        headers = self.login_sse_user()
        chat_client = _ScriptedChatClient(
            [
                _tool_call_round("get_today", "{}"),
                _content_round("今天是 2026 年 10 月 17 日。"),
            ]
        )
        with (
            patch("app.ai.agent.settings.OPENAI_API_KEY", "test-key"),
            patch("app.ai.agent.OpenAI", return_value=chat_client),
            patch("app.ai.agent.get_today", return_value="2026-10-17") as today_tool,
            patch("app.api.ai.stream_answer") as fallback_answer,
        ):
            response = self.client.post(
                "/api/ai/chat/stream",
                headers=headers,
                json={"message": "今天几号？", "history": []},
            )

        self.assertEqual(response.status_code, 200)
        text = response.text
        # 修复前这里会变成 3 次模型调用、工具执行 2 次。
        self.assertEqual(chat_client.create_calls, 2)
        today_tool.assert_called_once()
        # 工具事件来自图内透传：每个工具一对 start/end，标签可读。
        self.assertEqual(text.count("event: tool_start"), 1)
        self.assertEqual(text.count("event: tool_end"), 1)
        self.assertIn("换算今天/明天日期", text)
        # 回答 token 由图内流式产出，不再走第二段生成路径。
        self.assertEqual(extract_streamed_tokens(text), "今天是 2026 年 10 月 17 日。")
        fallback_answer.assert_not_called()
        self.assertIn("event: done", text)
        # “已调用”汇总出现在回答 token 之前，保持旧版展示顺序。
        self.assertLess(text.index("已调用："), text.index("event: token"))

    def test_keyed_graph_answers_without_tools_in_one_call(self):
        """有 Key 但不需要工具：一次模型调用完成回答，不出现任何工具事件。"""
        headers = self.login_sse_user()
        chat_client = _ScriptedChatClient([_content_round("实验室周一至周五开放。")])
        with (
            patch("app.ai.agent.settings.OPENAI_API_KEY", "test-key"),
            patch("app.ai.agent.OpenAI", return_value=chat_client),
            patch("app.api.ai.stream_answer") as fallback_answer,
        ):
            response = self.client.post(
                "/api/ai/chat/stream",
                headers=headers,
                json={"message": "实验室什么时候开放？", "history": []},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(chat_client.create_calls, 1)
        self.assertEqual(extract_streamed_tokens(response.text), "实验室周一至周五开放。")
        fallback_answer.assert_not_called()
        self.assertNotIn("event: tool_start", response.text)

    def test_write_tool_runs_at_most_once_per_turn(self):
        """同一轮对话里创建预约最多真正执行一次，重复调用只回提示。"""
        events = []
        arguments = json.dumps(
            {
                "lab_id": 1,
                "reservation_date": "2099-01-01",
                "start_time": "09:00",
                "end_time": "10:00",
                "purpose": "设备调试",
            },
            ensure_ascii=False,
        )
        state = {
            "message": "确认预约",
            "user_id": 1,
            "db": None,
            "event_sink": events.append,
            "messages": [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "create_lab_reservation", "arguments": arguments},
                        }
                    ],
                }
            ],
        }
        with patch("app.ai.agent.create_lab_reservation", return_value="预约创建成功") as create_tool:
            first = execute_tools_node(state)
            self.assertEqual(create_tool.call_count, 1)
            self.assertTrue(first["write_tool_handled"])

            second_state = {
                **state,
                **first,
                "messages": [
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": "call_2",
                                "type": "function",
                                "function": {"name": "create_lab_reservation", "arguments": arguments},
                            }
                        ],
                    }
                ],
            }
            second = execute_tools_node(second_state)
            self.assertEqual(create_tool.call_count, 1)
            self.assertIn("已经处理过一次预约请求", second["messages"][-1]["content"])

        self.assertEqual(
            [event["type"] for event in events],
            ["tool_start", "tool_end", "tool_start", "tool_end"],
        )

    def test_model_tool_path_stays_single_source(self):
        """结构回归：重复的图外模型工具入口不得回流，端点也不再自建数据库会话。"""
        import inspect

        import app.ai.agent as agent_module
        import app.api.ai as ai_api_module

        self.assertFalse(hasattr(agent_module, "run_model_tools"))
        api_source = inspect.getsource(ai_api_module)
        self.assertNotIn("run_model_tools", api_source)
        self.assertNotIn("SessionLocal", api_source)


if __name__ == "__main__":
    unittest.main()
