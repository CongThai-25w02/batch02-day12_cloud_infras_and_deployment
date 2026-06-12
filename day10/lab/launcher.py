from __future__ import annotations

import streamlit as st

import app as rag_app
import app_multi_agent as multi_agent_app


APP_TITLE = "Day 10 Home"
APP_SUBTITLE = "Choose the experience you want to demo: RAG chatbot or multi-agent orchestration."


def _configure_page() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")


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
        
        /* Sidebar styling for Dark Theme */
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
        .hero-rail {
            display: flex;
            gap: 0.8rem;
            flex-wrap: wrap;
            margin-top: 1.5rem;
        }
        .hero-pill {
            padding: 0.4rem 1rem;
            background: #E3002B;
            color: #ffffff;
            font-family: 'Oswald', sans-serif;
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .entry-card {
            height: 100%;
            padding: 1.8rem;
            background: #111111;
            border: 1px solid #333333;
            transition: all 0.2s ease-in-out;
            position: relative;
            overflow: hidden;
            cursor: pointer;
        }
        .entry-card:hover {
            transform: translateY(-4px);
            border-color: #E3002B;
            background: #1a1a1a;
        }
        .entry-card::before {
            content: "";
            position: absolute;
            inset: 0 auto auto 0;
            width: 100%;
            height: 4px;
            background: #E3002B;
            opacity: 0.8;
            transition: opacity 0.3s ease;
        }
        .entry-card:hover::before {
            opacity: 1;
        }
        .entry-kicker {
            display: inline-block;
            font-size: 0.75rem;
            font-family: 'Oswald', sans-serif;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: #E3002B;
            margin-bottom: 0.8rem;
        }
        .entry-title {
            font-size: 1.6rem;
            font-family: 'Oswald', sans-serif;
            text-transform: uppercase;
            color: #ffffff;
            margin: 0 0 0.5rem;
        }
        .entry-desc {
            color: #cccccc;
            line-height: 1.6;
            min-height: 4.5rem;
            font-weight: 300;
        }
        .entry-meta {
            margin-top: 1.2rem;
            color: #888888;
            font-size: 0.9rem;
            font-style: italic;
        }
        .entry-badge {
            display: inline-block;
            margin-top: 1.2rem;
            padding: 0.4rem 1rem;
            background: #E3002B;
            color: #ffffff;
            font-family: 'Oswald', sans-serif;
            text-transform: uppercase;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }
        .entry-card:hover .entry-badge {
            background: #ff1a43;
            color: #fff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _card_html(kicker: str, title: str, desc: str, meta: str, badge: str) -> str:
    return f"""
    <div class="entry-card">
        <div class="entry-kicker">{kicker}</div>
        <div class="entry-title">{title}</div>
        <div class="entry-desc">{desc}</div>
        <div class="entry-meta">{meta}</div>
        <div class="entry-badge">{badge}</div>
    </div>
    """


def _render_home() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>{APP_TITLE}</h1>
            <p>{APP_SUBTITLE}</p>
            <div class="hero-rail">
                <span class="hero-pill">3 entrypoints</span>
                <span class="hero-pill">RAG + Multi-agent</span>
                <span class="hero-pill">Launcher first</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            _card_html(
                "Day 08",
                "RAG Chatbot",
                "Chat-first experience over the cleaned Day 10 knowledge base. Use this for normal Q&A, evidence lookup, and deploy demos.",
                "Best for: refund policy, HR leave, access control, and data observability evidence.",
                "Open Day 08 RAG",
            ),
            unsafe_allow_html=True,
        )
        if st.button("Open Day 08 RAG", use_container_width=True, type="primary"):
            st.session_state.view = "rag"
            st.rerun()

    with right:
        st.markdown(
            _card_html(
                "Day 09",
                "Multi-Agent Demo",
                "Supervisor-worker orchestration powered by the Day 09 graph. It shows routing, policy reasoning, MCP calls, and trace details.",
                "Best for: policy/access/ticket/HR questions where you want to see the agent flow.",
                "Open Day 09 Multi-agent",
            ),
            unsafe_allow_html=True,
        )
        if st.button("Open Day 09 Multi-agent", use_container_width=True):
            st.session_state.view = "multi"
            st.rerun()

    st.markdown("---")
    st.caption("Launcher runs both experiences from one screen, so you can demo the single-agent and multi-agent versions side by side.")


def _render_back_button() -> None:
    if st.button("← Back to home", use_container_width=True):
        st.session_state.view = "home"
        st.rerun()


def _render_current_view(view: str) -> None:
    if view == "rag":
        _render_back_button()
        rag_app.main(configure_page=False)
    elif view == "multi":
        _render_back_button()
        multi_agent_app.main(configure_page=False)
    else:
        _render_home()


def main() -> None:
    _configure_page()
    _inject_styles()
    if "view" not in st.session_state:
        st.session_state.view = "home"
    _render_current_view(st.session_state.view)


if __name__ == "__main__":
    main()
