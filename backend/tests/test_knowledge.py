"""RAG 知识库索引同步测试。

测试使用系统临时目录，不读写 ``backend/chroma_db``，也不会修改
项目自带的 Markdown 知识文件。
"""

import gc
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import chromadb
from chromadb.api.client import SharedSystemClient

from app.ai import knowledge


class KnowledgeIndexSyncTest(unittest.TestCase):
    def setUp(self):
        # 每个测试拥有独立的 Markdown 目录和 ChromaDB 目录。
        self.temp_directory = tempfile.TemporaryDirectory()
        self.temp_root = Path(self.temp_directory.name)
        self.knowledge_directory = self.temp_root / "knowledge"
        self.chroma_directory = self.temp_root / "chroma_db"
        self.knowledge_directory.mkdir()

        self.knowledge_patch = patch.object(knowledge, "KNOWLEDGE_DIR", self.knowledge_directory)
        self.chroma_patch = patch.object(knowledge, "CHROMA_DIR", self.chroma_directory)
        self.knowledge_patch.start()
        self.chroma_patch.start()

    def tearDown(self):
        self.chroma_patch.stop()
        self.knowledge_patch.stop()

        # ChromaDB 会缓存已打开的 System；清理缓存后再删临时目录，
        # 避免 Windows 下 SQLite 文件句柄导致临时目录无法回收。
        SharedSystemClient.clear_system_cache()
        gc.collect()
        self.temp_directory.cleanup()

    def write_document(self, filename: str, text: str) -> Path:
        path = self.knowledge_directory / filename
        path.write_text(text, encoding="utf-8")
        return path

    def collection_snapshot(self) -> dict[str, dict]:
        """读取临时 collection，转成以文档 ID 为键的快照方便断言。"""
        client = chromadb.PersistentClient(path=str(self.chroma_directory))
        collection = client.get_collection(name="lab_knowledge")
        result = collection.get(include=["documents", "metadatas"])
        return {
            document_id: {"text": text, "metadata": metadata}
            for document_id, text, metadata in zip(
                result["ids"], result["documents"], result["metadatas"]
            )
        }

    def test_markdown_add_update_and_delete_are_synchronized(self):
        """新增、修改、删除 Markdown 后，索引应在下次检索前同步。"""
        safety_path = self.write_document("safety.md", "实验安全：进入实验室前需要登记。")

        _, backend = knowledge.search_documents("实验安全")
        self.assertEqual(backend, "ChromaDB")
        snapshot = self.collection_snapshot()
        # 知识库按段落分块后写入，短文档只有一个 chunk0。
        self.assertEqual(set(snapshot), {"safety_chunk0"})
        old_hash = snapshot["safety_chunk0"]["metadata"]["content_hash"]

        # 修改已有文件：ID 不变，但文本和内容指纹都应被 upsert。
        safety_path.write_text("实验安全：进入前登记，离开时关闭电源。", encoding="utf-8")
        knowledge.search_documents("关闭电源")
        snapshot = self.collection_snapshot()
        self.assertIn("关闭电源", snapshot["safety_chunk0"]["text"])
        self.assertNotEqual(old_hash, snapshot["safety_chunk0"]["metadata"]["content_hash"])

        # 新增文件：无需清空索引，下次检索会增量写入。
        self.write_document("equipment.md", "设备管理：显微镜使用后需要归还。")
        knowledge.search_documents("显微镜")
        self.assertEqual(set(self.collection_snapshot()), {"safety_chunk0", "equipment_chunk0"})

        # 删除本地文件：对应向量不应残留在 ChromaDB 中。
        safety_path.unlink()
        results, backend = knowledge.search_documents("实验安全")
        snapshot = self.collection_snapshot()
        self.assertEqual(backend, "ChromaDB")
        self.assertEqual(set(snapshot), {"equipment_chunk0"})
        self.assertTrue(all(item["source"] != "safety.md" for item in results))

    def test_chromadb_error_falls_back_to_keyword_search(self):
        """ChromaDB 无法创建时，仍应返回本地关键词检索结果。"""
        self.write_document("rules.md", "预约规则：请提前一天申请实验室。")
        invalid_chroma_path = self.temp_root / "not-a-directory"
        invalid_chroma_path.write_text("这是文件，不是目录", encoding="utf-8")

        with patch.object(knowledge, "CHROMA_DIR", invalid_chroma_path):
            results, backend = knowledge.search_documents("预约实验室")

        self.assertEqual(backend, "本地关键词检索")
        self.assertEqual(results[0]["source"], "rules.md")


if __name__ == "__main__":
    unittest.main()
