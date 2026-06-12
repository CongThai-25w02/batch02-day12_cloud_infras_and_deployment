from __future__ import annotations

import sys
import types
from dataclasses import dataclass


@dataclass
class _Ctx:
    label: str = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _SessionState(dict):
    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        self[name] = value


class _FakeStreamlit(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("streamlit")
        self.session_state = _SessionState()
        self.sidebar = _Ctx("sidebar")

    def cache_data(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def cache_resource(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator

    def set_page_config(self, *args, **kwargs):
        return None

    def markdown(self, *args, **kwargs):
        return None

    def caption(self, *args, **kwargs):
        return None

    def code(self, *args, **kwargs):
        return None

    def metric(self, *args, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None

    def write(self, *args, **kwargs):
        return None

    def json(self, *args, **kwargs):
        return None

    def subheader(self, *args, **kwargs):
        return None

    def title(self, *args, **kwargs):
        return None

    def toggle(self, label, *args, **kwargs):
        return kwargs.get("value", False)

    def button(self, label, *args, **kwargs):
        return False

    def text_input(self, label, *args, **kwargs):
        return kwargs.get("value", "") or ""

    def chat_input(self, label, *args, **kwargs):
        return ""

    def slider(self, label, *args, **kwargs):
        return kwargs.get("value", kwargs.get("min_value", 0))

    def columns(self, spec, *args, **kwargs):
        count = spec if isinstance(spec, int) else len(spec)
        return [_Ctx(f"col{i}") for i in range(count)]

    def spinner(self, *args, **kwargs):
        return _Ctx("spinner")

    def expander(self, *args, **kwargs):
        return _Ctx("expander")

    def container(self, *args, **kwargs):
        return _Ctx("container")

    def chat_message(self, *args, **kwargs):
        return _Ctx("chat_message")

    def rerun(self):
        return None


def _install_fake_streamlit() -> None:
    fake = _FakeStreamlit()
    sys.modules["streamlit"] = fake


def _short(text: str, limit: int = 220) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "..."


def main() -> int:
    _install_fake_streamlit()

    import launcher
    import app
    import app_multi_agent

    print("ENTRYPOINT_IMPORT_OK")

    launcher.main()
    print("LAUNCHER_MAIN_OK")

    app.main(configure_page=False)
    print("RAG_MAIN_OK")

    app_multi_agent.main(configure_page=False)
    print("MULTI_MAIN_OK")

    rag_query = "Nhân viên dưới 3 năm kinh nghiệm được bao nhiêu ngày phép năm?"
    rag_result = app.answer_query(rag_query, top_k=5, use_day09_agent=True, save_trace=False)
    print("RAG_SAMPLE")
    print(f"query={rag_query}")
    print(f"answer={_short(rag_result['answer'])}")
    print(f"source={rag_result['retrieval_source'] or 'n/a'}")
    if rag_result.get("day09_agent"):
        print(f"day09_route={rag_result['day09_agent'].get('supervisor_route', 'n/a')}")

    multi_query = "Khach hang Flash Sale yeu cau hoan tien vi san pham loi - duoc khong?"
    multi_result = app_multi_agent.run_day09_agent(multi_query, save_trace=False)
    print("MULTI_SAMPLE")
    print(f"query={multi_query}")
    print(f"answer={_short(multi_result.get('final_answer', ''))}")
    print(f"route={multi_result.get('supervisor_route', 'n/a')}")
    print(f"reason={_short(multi_result.get('route_reason', 'n/a'))}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
