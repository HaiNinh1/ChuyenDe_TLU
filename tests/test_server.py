"""Kiểm tra API của giao diện React (server.py) bằng TestClient — không mở trình duyệt, LLM giả lập."""
import json

import pytest
from fastapi.testclient import TestClient

import server
from testgen import agent as agent_module

client = TestClient(server.app)


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    # Không ghi log / file test của lần chạy thử vào thư mục thật của dự án
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setattr(agent_module, "LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(agent_module, "OUTPUT_DIR", tmp_path / "out")
    monkeypatch.setattr(server, "USER_DIR", tmp_path / "user_code")
    return tmp_path


def parse_sse(text: str) -> list:
    """Tách luồng Server-Sent Events thành danh sách (tên sự kiện, dữ liệu)."""
    events = []
    for chunk in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in chunk.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_meta_lists_languages_and_providers():
    data = client.get("/api/meta").json()
    python = next(lang for lang in data["languages"] if lang["name"] == "python")
    assert "grading.py" in python["files"]
    assert python["test_framework"] == "pytest"
    assert "mock" in data["providers"]


def test_source_and_unknown_module():
    assert "def " in client.get("/api/source", params={"language": "python", "file": "grading.py"}).json()["code"]
    assert client.get("/api/source", params={"language": "python", "file": "../server.py"}).status_code == 404


def test_detect_typescript():
    assert client.post("/api/detect", json={"code": "export function f(x: number): number { return x }"}).json() \
        == {"ext": ".ts"}


def test_logs_and_enriched_log():
    logs = client.get("/api/logs").json()
    assert logs, "logs/ cần có ít nhất một log mẫu"
    js = next(item for item in logs if item["name"].startswith("shipping_agent_js"))
    summary = client.get(f"/api/logs/{js['name']}").json()
    # Mỗi vòng có một bản code test; log ghi trên Windows vẫn ra đúng tên file test
    assert len(summary["code_views"]) == len(summary["iterations"])
    assert summary["test_file_name"] == "shipping.test.ts"
    final = summary["code_views"][-1]
    assert final["suspected"] and final["spans"]


@pytest.mark.parametrize("url", ["/api/logs/..%2Fserver.py", "/..%2Fserver.py", "/..%2F..%2Fserver.py",
                                 "/%2E%2E/%2E%2E/server.py"])
def test_cannot_read_files_outside_allowed_dirs(url):
    res = client.get(url)
    assert "TestGenAgent" not in res.text  # nội dung server.py không bao giờ bị trả về


def test_log_endpoint_only_serves_json_in_logs():
    with pytest.raises(server.HTTPException):
        server.log("../server.py")


def test_results_reads_csv():
    data = client.get("/api/results").json()
    assert set(data) == {"summary", "by_module", "runs"}


def test_run_streams_iterations_with_mock_llm(isolated):
    body = {"source_kind": "sample", "language": "python", "file": "calculator.py", "use_mutation": False,
            "max_iterations": 1, "provider": "mock", "model": "mock"}
    with client.stream("POST", "/api/run", json=body) as res:
        assert res.status_code == 200
        events = parse_sse(res.read().decode("utf-8"))
    kinds = [kind for kind, _ in events]
    assert kinds[0] == "start" and "iteration" in kinds and kinds[-1] == "summary"
    summary = events[-1][1]
    assert summary["module"] == "calculator"
    assert len(summary["code_views"]) == len(summary["iterations"])


def test_run_pasted_code_rejects_bad_module_name(isolated):
    body = {"source_kind": "paste", "code": "def f():\n    return 1\n", "ext": ".py", "module_name": "Tên Sai"}
    assert client.post("/api/run", json=body).status_code == 400
