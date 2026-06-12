from __future__ import annotations

from pathlib import Path

import streamlit as st

from integrations.day09_bridge import run_day09_agent


ROOT = Path(__file__).resolve().parent

APP_TITLE = "Day 09 - Multi-Agent Demo"
APP_SUBTITLE = "Demo Day 09 supervisor-worker graph cho policy, ticket, HR và access."

SUGGESTED_QUESTIONS = [
    "Khach hang Flash Sale yeu cau hoan tien vi san pham loi - duoc khong?",
    "SLA ticket P1 la bao lau?",
    "Level 4 Admin Access yeu cau phe duyet boi ai?",
    "Toi nghi om thi bao nhieu ngay co luong?",
]


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Oswald:wght@500;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
        }
        
        .stApp {
            background-color: #000000;
            color: #ffffff;
        }
        
        section[data-testid="stSidebar"] {
            background: #111111 !important;
            border-right: 1px solid #333333;
        }
        
        .hero {
            padding: 2rem 2.5rem;
            background: #111111;
            border: 1px solid #333333;
            margin-bottom: 2rem;
            transition: transform 0.3s ease;
            border-radius: 0px !important;
        }
        .hero:hover {
            transform: translateY(-2px);
            border-color: #E3002B;
        }
        .hero h1 {
            margin: 0;
            font-family: 'Oswald', sans-serif;
            font-size: 3rem;
            font-weight: 700;
            line-height: 1.1;
            letter-spacing: -0.02em;
            text-transform: uppercase;
            color: #E3002B;
        }
        .hero p {
            margin: 0.8rem 0 0;
            color: #aaaaaa;
            font-size: 1.1rem;
            font-weight: 400;
            max-width: 70ch;
        }
        
        .metric-card {
            background: #111111;
            border: 1px solid #333333;
            border-radius: 0px !important;
            padding: 1.2rem;
            min-height: 90px;
            transition: border-color 0.2s ease;
        }
        .metric-card:hover {
            border-color: #E3002B;
        }
        .metric-label {
            font-size: 0.75rem;
            font-family: 'Oswald', sans-serif;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #E3002B;
            margin-bottom: 0.4rem;
        }
        .metric-value {
            font-size: 1.25rem;
            font-weight: 700;
            color: #ffffff;
        }
        
        .panel {
            background: #111111;
            border: 1px solid #333333;
            border-radius: 0px !important;
            padding: 1.5rem;
            margin-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _configure_page() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🧠", layout="wide", initial_sidebar_state="expanded")


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## Điều khiển")
        st.caption("App này dùng Day 09 supervisor-worker graph ở phía sau.")
        st.session_state.show_trace = st.toggle("Hiển thị trace", value=st.session_state.get("show_trace", True))
        st.session_state.save_trace = st.toggle("Lưu trace file", value=st.session_state.get("save_trace", True))

        st.markdown("---")
        st.markdown("### Mẫu hỏi nhanh")
        for q in SUGGESTED_QUESTIONS:
            if st.button(q, use_container_width=True):
                st.session_state.prompt = q

        st.markdown("---")
        st.caption("Chạy từ `day10/lab`:")
        st.code("streamlit run app_multi_agent.py", language="bash")


def _render_metric(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main(configure_page: bool = True) -> None:
    if configure_page:
        _configure_page()
    _inject_styles()
    if "prompt" not in st.session_state:
        st.session_state.prompt = ""
    if "show_trace" not in st.session_state:
        st.session_state.show_trace = True
    if "save_trace" not in st.session_state:
        st.session_state.save_trace = True

    _render_sidebar()
    _render_header()

    prompt = st.text_input(
        "Đặt câu hỏi cho multi-agent",
        value=st.session_state.prompt,
        placeholder="Nhập câu hỏi policy, access, ticket hoặc HR...",
    )
    submit = st.button("Chạy agent", type="primary")

    if submit and prompt.strip():
        st.session_state.prompt = prompt.strip()

    query = st.session_state.prompt.strip()
    if not query:
        st.info("Nhập câu hỏi hoặc bấm một mẫu ở sidebar.")
        return

    with st.spinner("Đang chạy supervisor-worker graph..."):
        agent = run_day09_agent(query, save_trace=st.session_state.save_trace)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _render_metric("Route", agent.get("supervisor_route", "n/a"))
    with c2:
        _render_metric("Confidence", f"{agent.get('confidence', 0.0):.2f}")
    with c3:
        _render_metric("Workers", str(len(agent.get("workers_called", []))))
    with c4:
        _render_metric("MCP calls", str(len(agent.get("mcp_tools_used", []))))

    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.subheader("Câu trả lời")
    st.markdown(agent.get("final_answer", "(no answer)") or "(no answer)")

    st.subheader("Routing")
    st.write(f"**Lý do:** {agent.get('route_reason', 'n/a')}")
    st.write(f"**Workers:** {', '.join(agent.get('workers_called', [])) or 'n/a'}")
    st.write(f"**HITL:** {agent.get('hitl_triggered', False)}")

    if agent.get("mcp_tool_called"):
        st.subheader("MCP")
        st.write(f"**Tool gần nhất:** {agent.get('mcp_tool_called')}")
        st.json(agent.get("mcp_result"))

    if st.session_state.show_trace:
        st.subheader("Trace")
        st.json(
            {
                "run_id": agent.get("run_id"),
                "trace_file": agent.get("trace_file"),
                "history": agent.get("history", []),
                "mcp_tools_used": agent.get("mcp_tools_used", []),
            }
        )

    if agent.get("trace_file"):
        st.caption(f"Trace đã lưu: {agent['trace_file']}")

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
