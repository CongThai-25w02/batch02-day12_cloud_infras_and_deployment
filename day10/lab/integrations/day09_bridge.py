from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DAY09_ROOT = REPO_ROOT / "day09" / "lab"
DAY10_ARTIFACTS = REPO_ROOT / "day10" / "lab" / "artifacts" / "day09_agent"


def _load_day09_graph_module():
    graph_path = DAY09_ROOT / "graph.py"
    spec = spec_from_file_location("day09_lab_graph_bridge", graph_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Day 09 graph from {graph_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_day09_agent(task: str, save_trace: bool = True) -> dict[str, Any]:
    module = _load_day09_graph_module()
    state = module.run_graph(task)

    trace_file = None
    if save_trace:
        DAY10_ARTIFACTS.mkdir(parents=True, exist_ok=True)
        trace_file = module.save_trace(state, output_dir=str(DAY10_ARTIFACTS))

    return {
        "run_id": state.get("run_id"),
        "supervisor_route": state.get("supervisor_route"),
        "route_reason": state.get("route_reason"),
        "workers_called": state.get("workers_called", []),
        "confidence": state.get("confidence", 0.0),
        "final_answer": state.get("final_answer", ""),
        "sources": state.get("sources", []),
        "mcp_tools_used": state.get("mcp_tools_used", []),
        "mcp_tool_called": state.get("mcp_tool_called"),
        "mcp_result": state.get("mcp_result"),
        "hitl_triggered": state.get("hitl_triggered", False),
        "history": state.get("history", []),
        "trace_file": trace_file,
    }
