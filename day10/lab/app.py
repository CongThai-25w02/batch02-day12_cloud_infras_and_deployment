from __future__ import annotations

import csv
import html
import json
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import streamlit as st

from integrations.day09_bridge import run_day09_agent
from transform.local_embedding import build_embedding_function


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
MANIFESTS = ARTIFACTS / "manifests"
EVALS = ARTIFACTS / "eval"
REPORTS = ROOT / "reports"
DOCS = ROOT / "docs"

APP_TITLE = "Day 08 - RAG Chatbot"
APP_SUBTITLE = "Chatbot RAG cho refund policy, HR leave, access control và IT SLA trong bộ dữ liệu đã làm sạch."

EXAMPLE_QUESTIONS = [
    "Khách hàng có tối đa bao nhiêu ngày làm việc để gửi yêu cầu hoàn tiền?",
    "Nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?",
    "Level 4 Admin Access yêu cầu phê duyệt bởi ai?",
]

STOPWORDS = {
    "và",
    "hoặc",
    "của",
    "là",
    "theo",
    "cho",
    "một",
    "những",
    "nào",
    "bao",
    "nhiêu",
    "trong",
    "được",
    "có",
    "không",
    "the",
    "toi",
    "gi",
    "ve",
    "về",
    "đâu",
    "để",
    "sau",
    "khi",
    "bao_lâu",
    "ai",
}


def _load_text(path: Path, limit: int | None = None) -> str:
    if not path.is_file():
        return f"(missing) {path.name}"
    text = path.read_text(encoding="utf-8")
    return text if limit is None else text[:limit]


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _latest_file(folder: Path, pattern: str) -> Path | None:
    if not folder.is_dir():
        return None
    files = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _normalize_text(text: str) -> str:
    """Return a lower-cased, accent-stripped version for matching and ranking."""
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


NORMALIZED_STOPWORDS = {_normalize_text(word) for word in STOPWORDS}


@st.cache_data(show_spinner=False)
def _load_cleaned_corpus() -> list[dict]:
    manifest = _load_json(_latest_file(MANIFESTS, "manifest_*.json") or Path(""))
    cleaned_csv = manifest.get("cleaned_csv", "")
    cleaned_path = ROOT / cleaned_csv if cleaned_csv else None
    if not cleaned_path or not cleaned_path.is_file():
        cleaned_path = _latest_file(ARTIFACTS / "cleaned", "cleaned_*.csv")
    if not cleaned_path or not cleaned_path.is_file():
        return []
    return _load_csv(cleaned_path)


def _query_terms(query: str) -> list[str]:
    raw_terms = re.findall(r"[a-z0-9]+", _normalize_text(query))
    terms = [t for t in raw_terms if len(t) > 2 and t not in NORMALIZED_STOPWORDS]
    uniq: list[str] = []
    for term in terms:
        if term not in uniq:
            uniq.append(term)
    return uniq[:12]


def _detect_leave_intent(query: str) -> str | None:
    q = _normalize_text(query)
    if not q:
        return None
    if any(phrase in q for phrase in ("nghi om", "om", "sick leave")):
        return "sick"
    if any(phrase in q for phrase in ("phep nam", "nghi phep", "ngay phep", "annual leave")):
        return "annual"
    if any(phrase in q for phrase in ("khong luong", "unpaid leave", "nghi khong luong")):
        return "unpaid"
    if "nghi" in q and "luong" in q:
        return "ambiguous"
    return None


def _hr_leave_focus_terms(intent: str | None) -> list[str]:
    if intent == "sick":
        return ["nghi om", "10 ngay", "tra luong", "benh vien", "9:00"]
    if intent == "annual":
        return ["phep nam", "12 ngay", "15 ngay", "18 ngay", "chuyen nam"]
    if intent == "unpaid":
        return ["khong luong", "nghi khong luong"]
    return []


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    norm_chars: list[str] = []
    index_map: list[int] = []
    for idx, ch in enumerate(text or ""):
        expanded = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode("ascii")
        for out_ch in expanded:
            norm_chars.append(out_ch.lower())
            index_map.append(idx)
    return "".join(norm_chars), index_map


def _highlight_text(text: str, query: str) -> str:
    terms = _query_terms(query)
    if not terms:
        return html.escape(text)

    pattern = re.compile("(" + "|".join(re.escape(term) for term in sorted(terms, key=len, reverse=True)) + ")", re.IGNORECASE)
    normalized_text, index_map = _normalize_with_map(text)
    if normalized_text and index_map:
        hits: list[tuple[int, int]] = []
        for match in pattern.finditer(normalized_text):
            hits.append((match.start(), match.end()))
        if hits:
            pieces: list[str] = []
            last = 0
            for start, end in hits:
                src_start = index_map[min(start, len(index_map) - 1)]
                src_end = index_map[min(end - 1, len(index_map) - 1)] + 1
                if src_start < last:
                    continue
                pieces.append(html.escape(text[last:src_start]))
                pieces.append(f"<mark class='rag-hit'>{html.escape(text[src_start:src_end])}</mark>")
                last = src_end
            pieces.append(html.escape(text[last:]))
            return "".join(pieces)


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


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## Điều khiển")
        if st.session_state.get("active_mode") not in {"Chat mode", "Evidence"}:
            st.session_state.active_mode = "Chat mode"

        if st.session_state.active_mode == "Evidence":
            if st.button("Quay lại chat", use_container_width=True):
                st.session_state.active_mode = "Chat mode"
                st.rerun()
            st.caption("Mục evidence được giữ tối giản để dễ demo và chấm bài.")
        else:
            if st.button("Mở evidence", use_container_width=True):
                st.session_state.active_mode = "Evidence"
                st.rerun()

            with st.expander("Thiết lập truy xuất", expanded=False):
                st.session_state.top_k = st.slider("Top-k retrieval", 3, 8, st.session_state.get("top_k", 5))
                st.session_state.use_reranking = st.toggle("Dùng reranking", value=st.session_state.get("use_reranking", True))
                st.session_state.use_day09_agent = st.toggle(
                    "Dùng Day 09 agent bridge",
                    value=st.session_state.get("use_day09_agent", True),
                )

            st.markdown("### Mẫu hỏi nhanh")
            for example in EXAMPLE_QUESTIONS:
                if st.button(example, use_container_width=True):
                    st.session_state.chat_draft = example
                    st.session_state.active_mode = "Chat mode"
                    st.rerun()

        with st.expander("Chạy app", expanded=False):
            st.caption("App gốc: `day10/lab/app.py`")
            st.code("streamlit run app.py", language="bash")


def _format_retrieval_label(retrieval_source: str | None) -> str:
    if retrieval_source is None:
        return "Chưa truy xuất"
    if retrieval_source == "":
        return "Không có kết quả"
    return retrieval_source


def _should_use_day09_agent(query: str) -> bool:
    q = _normalize_text(query)
    if not q:
        return False
    keywords = (
        "refund",
        "hoan tien",
        "flash sale",
        "license",
        "subscription",
        "access",
        "admin",
        "level",
        "ticket",
        "p1",
        "sla",
        "escalation",
        "hr",
        "nghi",
        "phep",
        "luong",
    )
    return any(keyword in q for keyword in keywords)


def _render_stats(mode: str, retrieval_source: str | None = None) -> None:
    cols = st.columns(4)
    stats = [
        ("Mode", mode),
        ("Top-k", str(st.session_state.top_k)),
        ("Rerank", "On" if st.session_state.use_reranking else "Off"),
        ("Retrieval", _format_retrieval_label(retrieval_source)),
    ]
    for col, (label, value) in zip(cols, stats, strict=False):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


@st.cache_resource(show_spinner=False)
def _load_collection():
    try:
        import chromadb
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("chromadb is required for retrieval") from exc

    db_path = os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db"))
    collection_name = os.environ.get("CHROMA_COLLECTION", "day10_kb")
    client = chromadb.PersistentClient(path=db_path)
    emb = build_embedding_function(model_name=os.environ.get("EMBEDDING_MODEL", "local-hash"))
    return client.get_collection(name=collection_name, embedding_function=emb)


def _retrieve(query: str, top_k: int) -> list[dict]:
    terms = _query_terms(query)
    normalized_query = _normalize_text(query)
    leave_intent = _detect_leave_intent(query)
    corpus = _load_cleaned_corpus()
    if not corpus:
        return []

    scored: list[dict] = []
    for row in corpus:
        text = row.get("chunk_text", "")
        doc_id = row.get("doc_id", "")
        text_low = _normalize_text(text)
        doc_low = _normalize_text(doc_id)
        score = 0.0
        for term in terms:
            if term in text_low:
                score += 2.0
            if term in doc_low:
                score += 1.0
        if any(ch.isdigit() for ch in query) and any(ch.isdigit() for ch in text):
            score += 0.5
        # Small boost for exact phrases appearing in the chunk.
        if normalized_query.split():
            for phrase in ("hoan tien", "phep nam", "nghi om", "khong luong", "phe duyet", "sla", "vpn", "mat khau", "escalation"):
                if phrase in normalized_query and phrase in text_low:
                    score += 1.5
        if doc_low == "hr_leave_policy" and leave_intent:
            for focus_term in _hr_leave_focus_terms(leave_intent):
                if focus_term in text_low:
                    score += 2.5
        if score <= 0:
            continue
        scored.append(
            {
                "content": text,
                "score": score,
                "metadata": {
                    "doc_id": doc_id,
                    "effective_date": row.get("effective_date", ""),
                    "run_id": row.get("exported_at", ""),
                    "chunk_id": row.get("chunk_id", ""),
                },
            }
        )

    if not scored:
        return []

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _pick_best_sentence(
    sentences: list[str],
    terms: list[str],
    required_phrases: list[str] | None = None,
) -> str | None:
    if not sentences:
        return None

    required_phrases = required_phrases or []
    preferred = [sentence for sentence in sentences if all(phrase in _normalize_text(sentence) for phrase in required_phrases)]
    pool = preferred or sentences

    best_sentence = pool[0]
    best_score = -1
    for sentence in pool:
        score = 0
        low = _normalize_text(sentence)
        for term in terms:
            if term in low:
                score += 3
        if any(ch.isdigit() for ch in sentence):
            score += 1
        if "tra luong" in low or "phep nam" in low or "nghi om" in low:
            score += 1
        if score > best_score:
            best_score = score
            best_sentence = sentence
    return best_sentence


def _synthesize_answer(query: str, contexts: list[dict]) -> str:
    if not contexts:
        return "Mình chưa tìm thấy nguồn đủ liên quan trong knowledge base hiện tại."

    leave_intent = _detect_leave_intent(query)
    if leave_intent == "ambiguous":
        return (
            "Bạn đang hỏi về nghỉ ốm, phép năm hay nghỉ không lương? "
            "Mình cần bạn nói rõ loại nghỉ để trả lời chính xác."
        )

    if leave_intent == "unpaid":
        for ctx in contexts:
            if _normalize_text(ctx.get("metadata", {}).get("doc_id", "")) != "hr_leave_policy":
                continue
            text = ctx.get("content", "")
            sentences = _split_sentences(text)
            for sentence in sentences:
                low = _normalize_text(sentence)
                if "khong luong" in low or "unpaid" in low:
                    return f"Dựa trên các nguồn truy xuất được, {sentence} [1]"
        return "Mình chưa thấy chính sách nghỉ không lương trong tài liệu HR hiện tại."

    if leave_intent in {"sick", "annual"}:
        focus_terms = _hr_leave_focus_terms(leave_intent)
        required_phrases = ["nghi om"] if leave_intent == "sick" else ["phep nam"]
        hr_contexts = [ctx for ctx in contexts if _normalize_text(ctx.get("metadata", {}).get("doc_id", "")) == "hr_leave_policy"]
        search_pool = hr_contexts or contexts
        for ctx in search_pool:
            sentences = _split_sentences(ctx.get("content", ""))
            best_sentence = _pick_best_sentence(sentences, focus_terms, required_phrases=required_phrases)
            if best_sentence:
                return f"Dựa trên các nguồn truy xuất được, {best_sentence} [1]"

    top_score = contexts[0].get("score", 0.0)
    if top_score < 2.0:
        return (
            "Mình chưa tìm thấy nguồn đủ liên quan để trả lời chắc chắn. "
            "Bạn có thể hỏi lại bằng từ khóa cụ thể hơn?"
        )

    terms = _query_terms(query)
    lines: list[str] = []
    for source_idx, ctx in enumerate(contexts[:2], start=1):
        sentences = _split_sentences(ctx.get("content", ""))
        if not sentences:
            continue
        best_sentence = _pick_best_sentence(sentences, terms) or sentences[0]
        lines.append(f"{best_sentence} [{source_idx}]")

    if not lines:
        return "Mình chưa tìm thấy nguồn đủ liên quan trong knowledge base hiện tại."

    intro = "Dựa trên các nguồn truy xuất được, "
    return intro + " ".join(lines)


def _render_source(source: dict, index: int, query: str | None = None) -> None:
    metadata = source.get("metadata", {})
    doc_id = metadata.get("doc_id", "unknown")
    effective_date = metadata.get("effective_date", "")
    score = source.get("score", 0.0)
    content = source.get("content", "").strip().replace("\n", " ")
    excerpt = content[:500]
    rendered_excerpt = _highlight_text(excerpt, query or "") if query else html.escape(excerpt)

    st.markdown(
        f"""
        <div class="source-card">
            <div class="source-head">
                <div class="source-title">{index}. {html.escape(str(doc_id))}</div>
                <div class="source-meta">score {score:.3f} · {html.escape(str(effective_date))}</div>
            </div>
            <div class="source-preview">{rendered_excerpt}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _show_chat_mode() -> None:
    st.subheader("Chat mode")
    st.caption("Chat RAG có citation và lưu lịch sử ngắn để hỏi tiếp mạch lạc hơn.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for turn in st.session_state.chat_history:
        with st.chat_message("user"):
            st.markdown(turn["question"])
        with st.chat_message("assistant"):
            st.markdown(turn["answer"])
            if turn.get("retrieval_source"):
                st.caption(f"Retrieval source: {turn['retrieval_source']}")
            if turn.get("day09_agent"):
                agent = turn["day09_agent"]
                st.caption(
                    f"Day 09 route: {agent.get('supervisor_route', 'n/a')} | "
                    f"{agent.get('route_reason', 'n/a')}"
                )

    prompt = st.chat_input("Nhập câu hỏi của bạn")
    if not prompt and st.session_state.get("chat_draft"):
        prompt = st.session_state.chat_draft
        st.session_state.chat_draft = ""

    if prompt:
        query = prompt.strip()
        if query:
            with st.chat_message("user"):
                st.markdown(query)
            result = answer_query(
                query,
                top_k=st.session_state.top_k,
                use_day09_agent=st.session_state.get("use_day09_agent", True),
                save_trace=True,
            )
            with st.chat_message("assistant"):
                with st.spinner("Đang truy vấn và tổng hợp câu trả lời..."):
                    answer = result["answer"]
                    sources = result["sources"]
                    retrieval_source = result["retrieval_source"]
                    day09_agent = result["day09_agent"]

                st.markdown(answer)
                if sources and sources[0].get("score", 0.0) >= 2.0:
                    st.caption(f"Nguồn truy xuất: {retrieval_source}")
                else:
                    st.caption("Nguồn truy xuất: Không có kết quả")

                if sources and sources[0].get("score", 0.0) >= 2.0:
                    with st.expander("Nguồn đã dùng", expanded=True):
                        for i, source in enumerate(sources, start=1):
                            _render_source(source, i, query=query)

                if day09_agent:
                    with st.expander("Day 09 agent bridge", expanded=False):
                        st.write(f"Route: `{day09_agent.get('supervisor_route', 'n/a')}`")
                        st.write(f"Lý do: {day09_agent.get('route_reason', 'n/a')}")
                        st.write(f"Workers: {', '.join(day09_agent.get('workers_called', [])) or 'n/a'}")
                        st.write(f"Confidence: {day09_agent.get('confidence', 0.0)}")
                        if day09_agent.get("trace_file"):
                            st.write(f"Trace: {day09_agent['trace_file']}")
                        if day09_agent.get("final_answer"):
                            st.markdown("**Câu trả lời Day 09**")
                            st.markdown(day09_agent["final_answer"])

            st.session_state.chat_history.append(
                {
                    "question": query,
                    "answer": answer,
                    "sources": sources,
                    "retrieval_source": retrieval_source or "",
                    "day09_agent": day09_agent,
                }
            )

    if st.button("Xóa lịch sử chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.chat_draft = ""
        st.rerun()


def answer_query(
    query: str,
    *,
    top_k: int = 5,
    use_day09_agent: bool = True,
    save_trace: bool = True,
) -> dict:
    day09_agent = None
    if use_day09_agent and _should_use_day09_agent(query):
        try:
            day09_agent = run_day09_agent(query, save_trace=save_trace)
        except Exception as exc:
            day09_agent = {
                "supervisor_route": "error",
                "route_reason": f"Day 09 bridge error: {exc}",
                "workers_called": [],
                "confidence": 0.0,
                "final_answer": "",
                "trace_file": None,
            }

    try:
        sources = _retrieve(query, top_k)
        answer = _synthesize_answer(query, sources)
        retrieval_source = sources[0].get("metadata", {}).get("doc_id", "") if sources else ""
    except Exception as exc:
        answer = (
            "Tạm thời chưa thể truy vấn Chroma. "
            f"Lỗi: {exc}"
        )
        sources = []
        retrieval_source = ""

    if day09_agent and day09_agent.get("final_answer"):
        if not sources or sources[0].get("score", 0.0) < 2.0 or "Mình chưa tìm thấy" in answer:
            answer = day09_agent["final_answer"]

    return {
        "answer": answer,
        "sources": sources,
        "retrieval_source": retrieval_source,
        "day09_agent": day09_agent,
    }


def _show_evidence() -> None:
    st.subheader("Evidence")

    manifest = _load_json(_latest_file(MANIFESTS, "manifest_*.json") or Path(""))
    grading_rows = _load_jsonl(EVALS / "grading_run.jsonl")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Run", str(manifest.get("run_id", "n/a")))
    with c2:
        st.metric("Cleaned", str(manifest.get("cleaned_records", "n/a")))
    with c3:
        st.metric("Quarantine", str(manifest.get("quarantine_records", "n/a")))
    with c4:
        st.metric("Grading", f"{len(grading_rows)}/10")

    left, right = st.columns([1.1, 0.9])
    with left:
        st.subheader("Manifest snapshot")
        st.json(manifest if manifest else {"status": "No manifest found"})
        st.subheader("Grading summary")
        if grading_rows:
            contains_ok = sum(bool(r.get("contains_expected")) for r in grading_rows)
            forb_ok = sum(not bool(r.get("hits_forbidden")) for r in grading_rows)
            top1_ok = sum(bool(r.get("top1_doc_matches")) for r in grading_rows)
            gcols = st.columns(3)
            with gcols[0]:
                st.metric("contains_expected", f"{contains_ok}/10")
            with gcols[1]:
                st.metric("hits_forbidden clear", f"{forb_ok}/10")
            with gcols[2]:
                st.metric("top1_doc_matches", f"{top1_ok}/10")
        else:
            st.info("Chưa tìm thấy `grading_run.jsonl`.")

    with right:
        st.subheader("Liên kết nhanh")
        st.write(f"- [Group report]({(REPORTS / 'group_report.md').as_posix()})")
        st.write(f"- [Runbook]({(DOCS / 'runbook.md').as_posix()})")
        st.write(f"- [Pipeline architecture]({(DOCS / 'pipeline_architecture.md').as_posix()})")
        st.write(f"- [Data contract]({(DOCS / 'data_contract.md').as_posix()})")
        st.write(f"- [Latest manifest]({(MANIFESTS / 'manifest_after-fix-eval.json').as_posix()})")

    st.caption("Evidence được giữ tối giản: một manifest snapshot, một grading summary và vài liên kết quan trọng.")


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
        
        .source-card {
            background: #111111;
            border: 1px solid #333333;
            border-radius: 0px !important;
            padding: 1.2rem;
            margin-bottom: 1rem;
            transition: border-color 0.2s ease;
        }
        .source-card:hover {
            border-color: #E3002B;
        }
        .source-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #222222;
            padding-bottom: 0.5rem;
            margin-bottom: 0.8rem;
        }
        .source-title {
            font-family: 'Oswald', sans-serif;
            text-transform: uppercase;
            font-size: 1.1rem;
            color: #E3002B;
        }
        .source-meta {
            font-size: 0.85rem;
            color: #888888;
        }
        .source-preview {
            color: #cccccc;
            font-size: 0.95rem;
            line-height: 1.5;
        }
        .rag-hit {
            background-color: rgba(227, 0, 43, 0.25) !important;
            color: #ffffff !important;
            border-bottom: 2px solid #E3002B;
            padding: 0 2px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _configure_page() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="🤖", layout="wide", initial_sidebar_state="expanded")


def main(configure_page: bool = True) -> None:
    if configure_page:
        _configure_page()
    _inject_styles()
    if "top_k" not in st.session_state:
        st.session_state.top_k = 5
    if "use_reranking" not in st.session_state:
        st.session_state.use_reranking = True
    if "use_day09_agent" not in st.session_state:
        st.session_state.use_day09_agent = True
    if "active_mode" not in st.session_state:
        st.session_state.active_mode = "Chat mode"
    if "chat_draft" not in st.session_state:
        st.session_state.chat_draft = ""

    _render_sidebar()
    _render_header()

    mode = st.session_state.active_mode
    retrieval_source = ""
    if st.session_state.get("chat_history"):
        retrieval_source = st.session_state.chat_history[-1].get("retrieval_source", "")
    _render_stats(mode, retrieval_source)

    st.markdown("<div class='chat-wrap'>", unsafe_allow_html=True)
    if mode == "Chat mode":
        _show_chat_mode()
    else:
        _show_evidence()
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
