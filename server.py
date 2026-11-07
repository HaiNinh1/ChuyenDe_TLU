"""API cho giao diện demo React (thư mục web/) — thay cho app.py (Streamlit).

Chạy:   python server.py            -> mở http://127.0.0.1:8000
(Giao diện đã build nằm ở web/dist; muốn sửa giao diện: cd web && npm run dev)

Server CHỈ gọi lại các hàm có sẵn (adapters, TestGenAgent, LLMClient) — không chứa logic sinh test.
Các endpoint:
  GET  /api/meta            ngôn ngữ, module mẫu, công cụ + tình trạng cài đặt, nhà cung cấp LLM
  GET  /api/source          mã nguồn một module mẫu
  POST /api/detect          tự nhận diện ngôn ngữ của đoạn code dán vào
  POST /api/run             chạy agent; trả về luồng sự kiện (Server-Sent Events) để xem TỪNG VÒNG khi đang chạy
  GET  /api/logs            danh sách log đã lưu (chế độ REPLAY)
  GET  /api/logs/{tên}      nội dung một log
  GET  /api/results         kết quả thực nghiệm (results/*.csv)
"""
import csv
import json
import queue
import re
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from adapters import adapter_for_file, all_adapters, detect_language, get_adapter
from testgen.agent import AgentConfig, TestGenAgent
from testgen.config import DEFAULT_MODELS, ROOT_DIR, load_settings
from testgen.llm_client import LLMClient

TARGETS_DIR = ROOT_DIR / "targets"
LOGS_DIR = ROOT_DIR / "logs"
RESULTS_DIR = ROOT_DIR / "results"
USER_DIR = ROOT_DIR / "workspace" / "user_code"
WEB_DIST = ROOT_DIR / "web" / "dist"

app = FastAPI(title="LLM Test Agent")
run_lock = threading.Lock()  # mỗi lúc chỉ chạy MỘT agent (thư mục tạm và quota LLM dùng chung)


# ============================================================ HÀM PHỤ
def target_files(adapter) -> list:
    folder = TARGETS_DIR / adapter.name
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix in adapter.file_extensions)


def summary_adapter(summary: dict):
    """Log trước khi refactor đa ngôn ngữ không có trường "language" -> Python."""
    return get_adapter(summary.get("language", "python"))


def code_view(adapter, code: str) -> dict:
    """Thông tin để hiển thị một bản code test: số test, test SUSPECTED_BUG và vị trí dòng của chúng."""
    valid = adapter.is_valid(code)
    suspected = adapter.suspected_tests(code) if valid else []
    spans = [list(span) for name, span in adapter.test_line_spans(code).items() if name in suspected] if valid else []
    return {
        "code": code,
        "valid": valid,
        "num_tests": len(adapter.test_names(code)) if valid else 0,
        "suspected": suspected,
        "spans": spans,
    }


def enrich(summary: dict) -> dict:
    """Thêm dữ liệu cho giao diện: code test của từng vòng (vòng cuối = final_test_code, giống app.py cũ)."""
    adapter = summary_adapter(summary)
    its = summary.get("iterations", [])
    views = []
    for i, it in enumerate(its):
        code = it["test_code"] if i < len(its) - 1 else summary.get("final_test_code", it["test_code"])
        views.append(code_view(adapter, code))
    # Log ghi trên Windows dùng dấu "\" -> đổi sang "/" để Path đọc đúng trên mọi hệ điều hành
    module_path = (summary.get("module_path") or f"{summary['module']}.py").replace("\\", "/")
    summary["code_views"] = views
    summary["tools"] = adapter.describe_tools()
    summary["fence"] = adapter.prompt_hints(module_path)["fence"]
    summary["test_file_name"] = adapter.test_file_path(module_path).name
    return summary


def read_csv(path: Path) -> list:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sse(event: str, data) -> str:
    """Một sự kiện theo định dạng Server-Sent Events."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ============================================================ ENDPOINT
@app.get("/api/meta")
def meta():
    languages = []
    for adapter in all_adapters():
        files = target_files(adapter)
        if not files:
            continue
        env = adapter.check_environment()
        languages.append({
            "name": adapter.name,
            "display_name": adapter.display_name,
            "extensions": list(adapter.file_extensions),
            "test_framework": adapter.test_framework,
            "coverage_tool": adapter.coverage_tool,
            "mutation_tool": adapter.mutation_tool,
            "tools": adapter.describe_tools(),
            "files": [p.name for p in files],
            "env": {"ok": env.ok, "mutation_available": env.mutation_available, "message": env.message(),
                    "install_hint": env.install_hint, "tools": env.tools},
        })
    settings = load_settings()
    return {"languages": languages, "providers": DEFAULT_MODELS,
            "default_provider": settings.provider, "default_model": settings.model}


@app.get("/api/source")
def source(language: str, file: str):
    adapter = get_adapter(language)
    path = next((p for p in target_files(adapter) if p.name == file), None)
    if path is None:
        raise HTTPException(404, "Không tìm thấy module")
    return {"code": path.read_text(encoding="utf-8"), "fence": adapter.prompt_hints(path)["fence"]}


class DetectRequest(BaseModel):
    code: str


@app.post("/api/detect")
def detect(req: DetectRequest):
    return {"ext": detect_language(req.code) if req.code.strip() else ".py"}


class RunRequest(BaseModel):
    source_kind: str = "sample"        # sample | paste
    language: str = "python"
    file: str = ""
    code: str = ""                     # khi dán code
    ext: str = ".py"
    module_name: str = "user_module"
    use_mutation: bool = True
    use_memory: bool = False
    max_iterations: int = 6
    line_threshold: float = 95
    branch_threshold: float = 90
    mutation_threshold: float = 80
    max_mutants: int = 20
    provider: str = "mock"
    model: str = "mock"


def resolve_module(req: RunRequest) -> Path:
    if req.source_kind == "paste":
        if not req.code.strip():
            raise HTTPException(400, "Chưa dán code")
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", req.module_name or "") or req.ext not in (".py", ".js", ".ts"):
            raise HTTPException(400, "Tên module không hợp lệ (chữ thường, không dấu, không khoảng trắng)")
        USER_DIR.mkdir(parents=True, exist_ok=True)
        path = USER_DIR / f"{req.module_name}{req.ext}"
        path.write_text(req.code, encoding="utf-8")
        return path
    adapter = get_adapter(req.language)
    path = next((p for p in target_files(adapter) if p.name == req.file), None)
    if path is None:
        raise HTTPException(404, "Không tìm thấy module")
    return path


@app.post("/api/run")
def run(req: RunRequest):
    module_path = resolve_module(req)
    adapter = adapter_for_file(module_path)
    env = adapter.check_environment()
    if not env.ok:
        raise HTTPException(400, env.message())
    if not run_lock.acquire(blocking=False):
        raise HTTPException(409, "Đang có một lần chạy khác, hãy đợi nó xong")

    events = queue.Queue()  # agent (luồng phụ) bỏ sự kiện vào, luồng trả về trình duyệt lấy ra

    def worker():
        try:
            config = AgentConfig(max_iterations=req.max_iterations, line_threshold=req.line_threshold,
                                 branch_threshold=req.branch_threshold,
                                 use_mutation=req.use_mutation and env.mutation_available,
                                 mutation_threshold=req.mutation_threshold, max_mutants=req.max_mutants,
                                 use_memory=req.use_memory, label="app")
            client = LLMClient(settings=load_settings(provider=req.provider, model=req.model or None))
            agent = TestGenAgent(module_path, client=client, config=config,
                                 progress=lambda kind, payload: events.put((kind, payload)))
            events.put(("summary", enrich(agent.run())))
        except Exception as exc:  # gửi lỗi về giao diện thay vì làm sập server
            events.put(("error", str(exc)))
        finally:
            run_lock.release()
            events.put(("end", None))

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        yield sse("start", {"module": module_path.name, "tools": adapter.describe_tools()})
        while True:
            kind, payload = events.get()
            if kind == "end":
                break
            yield sse(kind, payload)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/logs")
def logs():
    items = []
    for path in sorted(LOGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        final = data.get("final", {})
        items.append({
            "name": path.name,
            "language": data.get("language", "python"),
            "module": data.get("module", ""),
            "label": data.get("label", ""),
            "iterations": len(data.get("iterations", [])),
            "line_coverage": final.get("line_coverage"),
            "mutation_score": final.get("mutation_score"),
            "suspected_bugs": len(data.get("suspected_bugs") or {}),
            "model": (data.get("llm") or {}).get("model", ""),
            "mtime": path.stat().st_mtime,
        })
    return items


@app.get("/api/logs/{name}")
def log(name: str):
    path = LOGS_DIR / Path(name).name  # chỉ lấy tên file, không cho đọc ra ngoài logs/
    if path.suffix != ".json" or not path.is_file():
        raise HTTPException(404, "Không tìm thấy log")
    summary = json.loads(path.read_text(encoding="utf-8"))
    summary["log_path"] = str(path)
    return enrich(summary)


@app.get("/api/results")
def results():
    return {
        "summary": read_csv(RESULTS_DIR / "results.csv"),
        "by_module": read_csv(RESULTS_DIR / "results_by_module.csv"),
        "runs": read_csv(RESULTS_DIR / "runs.csv"),
    }


# ============================================================ GIAO DIỆN ĐÃ BUILD
if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        file = (WEB_DIST / path).resolve()
        # Chỉ trả file nằm TRONG web/dist (chặn "../" đọc file khác của dự án); còn lại trả trang chính
        inside = file.is_relative_to(WEB_DIST.resolve())
        return FileResponse(file if path and inside and file.is_file() else WEB_DIST / "index.html")


if __name__ == "__main__":
    import uvicorn

    if not WEB_DIST.exists():
        print("Chưa build giao diện: cd web && npm install && npm run build")
    print("Mở trình duyệt tại http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
