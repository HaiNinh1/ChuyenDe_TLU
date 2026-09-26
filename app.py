"""Giao diện demo (Streamlit).

Chạy:  streamlit run app.py

Chức năng:
- Chọn module mẫu trong targets/ hoặc dán code Python của bạn
- Chạy agent, xem tiến trình TỪNG VÒNG ngay khi đang chạy
- Biểu đồ coverage / mutation score qua các vòng
- Xem code test ở mỗi vòng, test SUSPECTED_BUG được tô đỏ
- Tab kết quả thực nghiệm (results/)
- Chế độ REPLAY: phát lại từ log JSON đã lưu (phòng mất mạng / API lỗi khi demo)
"""
import difflib
import html
import json
import re
import time
from pathlib import Path

import matplotlib
import pandas as pd
import streamlit as st

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from adapters import get_adapter  # noqa: E402
from testgen.agent import AgentConfig, TestGenAgent  # noqa: E402
from testgen.config import DEFAULT_MODELS, ROOT_DIR, load_settings  # noqa: E402
from testgen.llm_client import LLMClient  # noqa: E402

TARGETS_DIR = ROOT_DIR / "targets" / "python"
LOGS_DIR = ROOT_DIR / "logs"
RESULTS_DIR = ROOT_DIR / "results"
USER_DIR = ROOT_DIR / "workspace" / "user_code"

ACTION_LABELS = {
    "fix_collection": "🔧 Sửa file test hỏng",
    "fix_tests": "🧪 Phân loại & sửa test fail",
    "improve_coverage": "📈 Bổ sung test tăng coverage",
    "kill_mutants": "🧬 Bổ sung test giết mutant",
    "stop": "⏹️ Dừng",
}

st.set_page_config(page_title="LLM Test Agent", page_icon="🧪", layout="wide")


# ============================================================ HIỂN THỊ DÙNG CHUNG
def iteration_card(it: dict):
    """Hiển thị một vòng lặp (dùng cho cả chạy thật lẫn replay)."""
    label = ACTION_LABELS.get(it["action"], it["action"])
    cols = st.columns([1, 1, 1, 1, 1])
    cols[0].metric("Vòng", it["iteration"])
    cols[1].metric("Pass / Fail", f"{it['passed']} / {it['failed'] + it['errors']}")
    cols[2].metric("Line cov.", f"{it['line_coverage']}%")
    cols[3].metric("Branch cov.", f"{it['branch_coverage']}%")
    ms = it.get("mutation_score")
    cols[4].metric("Mutation", f"{ms}%" if ms is not None else "—")
    st.markdown(f"**{label}** — {it['reason']}")
    if it.get("xfailed"):
        st.warning(f"{it['xfailed']} test được gắn nhãn SUSPECTED_BUG (nghi code có bug)")
    for c in it.get("classifications", []):
        icon = "🐞" if c["verdict"] == "SUSPECTED_BUG" else "✏️"
        st.caption(f"{icon} `{c['test']}` → **{c['verdict']}**: {c['reason']}")
    if it.get("survived_mutants"):
        with st.expander(f"{len(it['survived_mutants'])} mutant còn sống"):
            for m in it["survived_mutants"]:
                st.code(m, language="text")
    if it.get("lesson"):
        st.caption(f"📝 LESSON: {it['lesson']}")
    st.divider()


def history_frame(iterations: list) -> pd.DataFrame:
    return pd.DataFrame([{
        "Vòng": it["iteration"],
        "Line coverage": it["line_coverage"],
        "Branch coverage": it["branch_coverage"],
        "Mutation score": it.get("mutation_score"),
        "Số test pass": it["passed"],
        "Gọi LLM (cộng dồn)": it.get("llm_calls_so_far", 0),
    } for it in iterations])


def live_chart(slot, iterations: list):
    """Biểu đồ cập nhật trực tiếp trong lúc chạy (cần ít nhất 2 vòng mới vẽ được đường)."""
    if len(iterations) >= 2:
        df = history_frame(iterations).set_index("Vòng")
        slot.line_chart(df[["Line coverage", "Branch coverage", "Mutation score"]], y_label="%", x_label="Vòng")


def progress_chart(iterations: list):
    """Biểu đồ matplotlib: coverage và mutation score qua các vòng."""
    df = history_frame(iterations)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(df["Vòng"], df["Line coverage"], "o-", label="Line coverage")
    ax.plot(df["Vòng"], df["Branch coverage"], "s-", label="Branch coverage")
    if df["Mutation score"].notna().any():
        ax.plot(df["Vòng"], df["Mutation score"], "^-", label="Mutation score")
    ax.set_xlabel("Vòng lặp")
    ax.set_ylabel("%")
    ax.set_ylim(0, 105)
    ax.set_xticks(df["Vòng"])
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    return fig


def highlight_code(code: str, suspected: list) -> str:
    """HTML của code test, tô đỏ các hàm test SUSPECTED_BUG."""
    spans = []
    try:
        import ast
        for node in ast.parse(code).body:
            if isinstance(node, ast.FunctionDef) and node.name in suspected:
                start = min([node.lineno] + [d.lineno for d in node.decorator_list])
                spans.append((start, node.end_lineno))
    except SyntaxError:
        pass
    rows = []
    for i, line in enumerate(code.splitlines(), start=1):
        bad = any(a <= i <= b for a, b in spans)
        background = "#ffd9d9" if bad else "transparent"
        rows.append(f'<div style="background:{background};white-space:pre">'
                    f'<span style="color:#999">{i:4d}  </span>{html.escape(line)}</div>')
    return ('<div style="font-family:Consolas,Menlo,monospace;font-size:13px;line-height:1.45;'
            'background:#f7f7f9;color:#222;padding:10px;border-radius:6px;overflow-x:auto">'
            + "".join(rows) + "</div>")


def summary_box(summary: dict):
    final = summary["final"]
    stats = summary["stats"]
    st.success(f"**Kết thúc:** {summary['stop_reason']}")
    cols = st.columns(6)
    cols[0].metric("Line coverage", f"{final['line_coverage']}%")
    cols[1].metric("Branch coverage", f"{final['branch_coverage']}%")
    cols[2].metric("Mutation score", f"{final['mutation_score']}%" if final["mutation_score"] is not None else "—")
    cols[3].metric("Số vòng", final["num_iterations"])
    cols[4].metric("Gọi LLM", stats["llm_calls"])
    cols[5].metric("Thời gian", f"{stats['total_seconds']} s")
    if summary["suspected_bugs"]:
        st.error("🐞 **Nghi phát hiện bug trong code** (cần người kiểm tra):")
        for name, reason in summary["suspected_bugs"].items():
            st.markdown(f"- `{name}`: {reason}")
    st.caption(f"LLM: {summary['llm']['provider']} / {summary['llm']['model']}"
               + (f" · Log: `{Path(summary['log_path']).name}`" if summary.get("log_path") else ""))


# ============================================================ THANH BÊN
st.sidebar.title("🧪 LLM Test Agent")
mode = st.sidebar.radio("Chế độ", ["Chạy mới", "REPLAY từ log"])

run_clicked = replay_clicked = False
module_path = None
if mode == "Chạy mới":
    source_kind = st.sidebar.radio("Mã nguồn", ["Module mẫu", "Dán code Python"])
    if source_kind == "Module mẫu":
        names = sorted(p.stem for p in TARGETS_DIR.glob("*.py"))
        chosen = st.sidebar.selectbox("Module", names, index=names.index("grading") if "grading" in names else 0)
        module_path = TARGETS_DIR / f"{chosen}.py"
    else:
        module_name = st.sidebar.text_input("Tên module (chữ thường, không dấu)", "user_module")
        pasted = st.sidebar.text_area("Dán code Python (nên có docstring mô tả hành vi đúng)", height=220)
        if pasted.strip() and re.fullmatch(r"[a-z_][a-z0-9_]*", module_name or ""):
            USER_DIR.mkdir(parents=True, exist_ok=True)
            module_path = USER_DIR / f"{module_name}.py"
            module_path.write_text(pasted, encoding="utf-8")
        elif pasted.strip():
            st.sidebar.error("Tên module không hợp lệ")

    st.sidebar.subheader("Cấu hình agent")
    use_mutation = st.sidebar.checkbox("Mutation testing", value=True)
    use_memory = st.sidebar.checkbox("Bộ nhớ tự học", value=False)
    max_iters = st.sidebar.slider("Số vòng tối đa", 1, 10, 6)
    line_th = st.sidebar.slider("Ngưỡng line coverage (%)", 50, 100, 95)
    branch_th = st.sidebar.slider("Ngưỡng branch coverage (%)", 50, 100, 90)
    mut_th = st.sidebar.slider("Ngưỡng mutation score (%)", 50, 100, 80, disabled=not use_mutation)
    max_mutants = st.sidebar.slider("Số mutant tối đa", 5, 40, 20, disabled=not use_mutation)

    st.sidebar.subheader("LLM")
    env_settings = load_settings()
    providers = list(DEFAULT_MODELS)
    provider = st.sidebar.selectbox("Nhà cung cấp", providers, index=providers.index(env_settings.provider))
    model = st.sidebar.text_input("Model", env_settings.model if provider == env_settings.provider
                                  else DEFAULT_MODELS[provider])
    run_clicked = st.sidebar.button("▶️ Chạy agent", type="primary", disabled=module_path is None)
else:
    logs = sorted(LOGS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if logs:
        log_file = st.sidebar.selectbox("Chọn log", logs, format_func=lambda p: p.name)
        speed = st.sidebar.slider("Tốc độ phát lại (giây/vòng)", 0.0, 3.0, 1.0, 0.5)
        replay_clicked = st.sidebar.button("▶️ Phát lại", type="primary")
    else:
        st.sidebar.info("Chưa có log nào trong logs/")

# ============================================================ CÁC TAB
tab_run, tab_chart, tab_code, tab_exp, tab_src = st.tabs(
    ["🔄 Tiến trình", "📊 Biểu đồ", "🧾 Code test", "🔬 Kết quả thực nghiệm", "📄 Mã nguồn module"])

with tab_run:
    if run_clicked and module_path is not None:
        st.subheader(f"Đang chạy agent cho `{module_path.name}`")
        status = st.status("Agent đang làm việc...", expanded=True)
        chart_slot = st.empty()
        live = []

        def on_progress(kind, payload):
            # Hàm callback: agent gọi mỗi khi có thông báo / xong một vòng
            if kind == "message":
                status.write(payload)
            elif kind == "iteration":
                live.append(payload)
                with status:
                    iteration_card(payload)
                live_chart(chart_slot, live)

        config = AgentConfig(max_iterations=max_iters, line_threshold=line_th, branch_threshold=branch_th,
                             use_mutation=use_mutation, mutation_threshold=mut_th, max_mutants=max_mutants,
                             use_memory=use_memory, label="app")
        try:
            client = LLMClient(settings=load_settings(provider=provider, model=model))
            summary = TestGenAgent(module_path, client=client, config=config, progress=on_progress).run()
            st.session_state["summary"] = summary
            status.update(label="Hoàn tất", state="complete")
        except Exception as exc:  # hiển thị lỗi thay vì làm sập giao diện
            status.update(label="Lỗi", state="error")
            st.error(f"Lỗi: {exc}")

    elif replay_clicked:
        summary = json.loads(log_file.read_text(encoding="utf-8"))
        summary["log_path"] = str(log_file)
        st.subheader(f"REPLAY: `{log_file.name}`")
        st.info("Đang phát lại từ log đã lưu — không gọi LLM, không cần mạng.")
        chart_slot = st.empty()
        shown = []
        for it in summary["iterations"]:
            shown.append(it)
            iteration_card(it)
            live_chart(chart_slot, shown)
            time.sleep(speed)
        st.session_state["summary"] = summary

    summary = st.session_state.get("summary")
    if summary:
        summary_box(summary)
    elif not (run_clicked or replay_clicked):
        st.info("Chọn module ở thanh bên rồi bấm **Chạy agent**, hoặc chọn **REPLAY từ log** để phát lại một lần "
                "chạy đã lưu.")

summary = st.session_state.get("summary")

with tab_chart:
    if summary and summary["iterations"]:
        st.pyplot(progress_chart(summary["iterations"]))
        st.dataframe(history_frame(summary["iterations"]), hide_index=True)
    else:
        st.info("Chưa có dữ liệu. Hãy chạy agent hoặc replay một log.")

with tab_code:
    if summary and summary["iterations"]:
        its = summary["iterations"]
        idx = st.select_slider("Xem code test tại vòng", options=list(range(len(its))), value=len(its) - 1)
        code = its[idx]["test_code"] if idx < len(its) - 1 else summary["final_test_code"]
        adapter = get_adapter(summary.get("language", "python"))  # log cũ (trước refactor) không có "language"
        suspected = adapter.suspected_tests(code)
        c1, c2, c3 = st.columns(3)
        c1.metric("Số test", len(adapter.test_names(code)) if adapter.is_valid(code) else "lỗi cú pháp")
        c2.metric("SUSPECTED_BUG", len(suspected))
        c3.metric("Số dòng", len(code.splitlines()))
        if suspected:
            st.error("Các test tô đỏ bên dưới được agent GIỮ LẠI và gắn nhãn SUSPECTED_BUG "
                     f"(không sửa cho khớp code): {', '.join(suspected)}")
        if idx > 0 and st.checkbox("Chỉ xem thay đổi so với vòng trước (diff)"):
            before = its[idx - 1]["test_code"]
            diff = "\n".join(difflib.unified_diff(before.splitlines(), code.splitlines(),
                                                  f"vòng {idx - 1}", f"vòng {idx}", lineterm=""))
            st.code(diff or "(không đổi)", language="diff")
        else:
            st.html(highlight_code(code, suspected))
        st.download_button("⬇️ Tải file test", code, file_name=f"test_{summary['module']}.py")
    else:
        st.info("Chưa có dữ liệu.")

with tab_exp:
    results_csv = RESULTS_DIR / "results.csv"
    if results_csv.exists():
        st.subheader("Trung bình theo cấu hình")
        st.dataframe(pd.read_csv(results_csv), hide_index=True)
        for image in ("summary.png", "mutation_by_module.png"):
            if (RESULTS_DIR / image).exists():
                st.image(str(RESULTS_DIR / image))
        by_module = RESULTS_DIR / "results_by_module.csv"
        if by_module.exists():
            with st.expander("Chi tiết theo module"):
                st.dataframe(pd.read_csv(by_module), hide_index=True)
        runs = RESULTS_DIR / "runs.csv"
        if runs.exists():
            with st.expander("Dữ liệu thô (từng lần chạy)"):
                st.dataframe(pd.read_csv(runs), hide_index=True)
        st.caption("Nguồn: `python evaluate.py`. Xem phần hạn chế trong HOC_TAP.md (GĐ7).")
    else:
        st.info("Chưa có kết quả. Chạy `python evaluate.py --quick` hoặc `python evaluate.py --runs 3`.")

with tab_src:
    src_path = module_path if mode == "Chạy mới" and module_path else (
        Path(summary["module_path"]) if summary else None)
    if summary and mode != "Chạy mới":
        st.code(summary.get("source_code", ""), language="python", line_numbers=True)
    elif src_path and src_path.exists():
        st.code(src_path.read_text(encoding="utf-8"), language="python", line_numbers=True)
    else:
        st.info("Chưa chọn module.")
