from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from drrepo.architecture.hotspots import build_hotspots, group_findings_by_path
from drrepo.architecture.imports import PythonModuleInfo, collect_python_import_graph, read_json_file
from drrepo.architecture.models import (
    ArchitectureAssessment,
    ArchitectureCycle,
    ArchitectureEdge,
    ArchitectureEvidence,
    ArchitectureLayer,
    ArchitectureNode,
    to_plain_dict,
)


MAX_NODES = 80
MAX_EDGES = 160
MAX_CYCLES = 8
MAX_EXTERNALS = 12
MAX_ENTRY_POINTS = 12
STDLIB_MODULES = set(getattr(sys, "stdlib_module_names", set()))


def build_architecture_assessment(audit: dict[str, Any]) -> dict[str, Any]:
    root = Path(str(audit.get("path") or ".")).resolve()
    modules, parse_errors = collect_python_import_graph(root)
    module_by_name = {module.module: module for module in modules if module.module}

    nodes = [_node_from_module(module, root) for module in modules]
    nodes.extend(_frontend_nodes(root))
    node_by_module = {module.module: node for module, node in zip(modules, nodes) if module.module}

    edges = _build_import_edges(modules, module_by_name, node_by_module)
    edges.extend(_frontend_api_edges(nodes, root))
    _apply_dependency_metrics(nodes, edges)

    cycles = _detect_cycles(nodes, edges)
    test_status_by_path = _map_test_relationships(modules, module_by_name)
    findings_by_path = group_findings_by_path(audit)
    _apply_finding_context(nodes, findings_by_path)
    _apply_radon_metrics(nodes, findings_by_path)
    cycle_node_ids = {node_id for cycle in cycles for node_id in cycle.node_ids}
    hotspots = build_hotspots(nodes, findings_by_path, cycle_node_ids, test_status_by_path)
    _attach_hotspot_risk(nodes, hotspots)

    layers = _build_layers(nodes)
    entry_points = _entry_points(nodes)
    external_integrations = _external_integrations(modules, root)
    evidence_gaps = _evidence_gaps(parse_errors, audit, modules)
    limitations = [
        "Static architecture analysis uses imports, filenames, framework signals, analyzer findings, and test evidence. It does not execute repository code.",
        "Call relationships are reported only when directly evidenced by static imports or conservative frontend API-client patterns.",
    ]
    if len(modules) >= 350:
        limitations.append("Python module analysis was truncated at 350 files.")
    summary = _summary(entry_points, layers, external_integrations, cycles, hotspots, evidence_gaps)
    confidence = _confidence(parse_errors, nodes, edges)

    assessment = ArchitectureAssessment(
        status="partial" if parse_errors else "completed",
        confidence=confidence,
        summary=summary,
        nodes=nodes[:MAX_NODES],
        edges=edges[:MAX_EDGES],
        layers=layers,
        entry_points=entry_points[:MAX_ENTRY_POINTS],
        external_integrations=external_integrations[:MAX_EXTERNALS],
        cycles=cycles[:MAX_CYCLES],
        hotspots=hotspots,
        evidence_gaps=evidence_gaps,
        limitations=limitations,
    )
    return to_plain_dict(assessment)


def _node_from_module(module: PythonModuleInfo, root: Path) -> ArchitectureNode:
    kind, layer, confidence, reasons = _classify_python_module(module)
    metrics = {"line_count": _line_count(root / module.path)}
    if module.route_count:
        metrics["route_count"] = module.route_count
    if module.syntax_error:
        metrics["parse_error"] = module.syntax_error
    evidence = [ArchitectureEvidence(module.path, reason) for reason in reasons]
    return ArchitectureNode(
        id=f"node:{module.module or module.path}",
        label=Path(module.path).name,
        kind=kind,
        path=module.path,
        language="python",
        layer=layer,
        symbols=module.symbols,
        confidence=confidence,
        evidence=evidence,
        metrics=metrics,
    )


def _classify_python_module(module: PythonModuleInfo) -> tuple[str, str, str, list[str]]:
    path = module.path.lower()
    name = Path(path).stem
    reasons: list[str] = []
    if _is_test_path(module.path):
        return "test", "tests", "high", ["pytest-style path"]
    if module.route_count or "fastapi" in [s.lower() for s in module.framework_signals] or "flask" in [s.lower() for s in module.framework_signals]:
        reasons.append("framework route or app signal")
        return "api_route", "API/interface", "high", reasons
    if name in {"cli", "__main__"} or module.has_main_guard:
        reasons.append("CLI/main guard signal")
        return "CLI", "API/interface", "high", reasons
    if any(part in path for part in ("service", "usecase", "orchestrator")):
        reasons.append("service naming signal")
        return "service", "application/service", "medium", reasons
    if any(part in path for part in ("repository", "repositories", "dao", "database", "db", "store")):
        reasons.append("data-access naming signal")
        return "repository/data-access", "data/infrastructure", "medium", reasons
    if any(part in path for part in ("schema", "schemas", "model", "models", "domain")):
        reasons.append("model/schema naming signal")
        return "model/schema", "domain/core", "medium", reasons
    if any(part in path for part in ("config", "settings", "pyproject")):
        reasons.append("configuration naming signal")
        return "configuration", "configuration", "medium", reasons
    return "module", "domain/core", "medium", ["python module"]


def _frontend_nodes(root: Path) -> list[ArchitectureNode]:
    nodes: list[ArchitectureNode] = []
    package_paths = [path for path in (root / "package.json", root / "frontend" / "package.json") if path.exists()]
    for package_path in package_paths:
        rel = str(package_path.relative_to(root)).replace("\\", "/")
        package = read_json_file(package_path)
        deps = sorted(set((package.get("dependencies") or {}).keys()) | set((package.get("devDependencies") or {}).keys()))[:24]
        base = package_path.parent
        frontend_id = f"node:{rel}"
        nodes.append(ArchitectureNode(
            id=frontend_id,
            label=base.name if base != root else "frontend",
            kind="frontend",
            path=rel,
            language="javascript",
            layer="presentation/frontend",
            symbols=deps,
            confidence="high",
            evidence=[ArchitectureEvidence(rel, "package.json frontend/package evidence")],
            metrics={"dependency_count": len(deps)},
        ))
        for candidate in ("src/main.tsx", "src/main.ts", "src/App.tsx", "src/index.tsx", "src/app.tsx"):
            entry = base / candidate
            if entry.exists():
                entry_rel = str(entry.relative_to(root)).replace("\\", "/")
                nodes.append(ArchitectureNode(
                    id=f"node:{entry_rel}",
                    label=Path(entry_rel).name,
                    kind="entry_point",
                    path=entry_rel,
                    language="typescript",
                    layer="presentation/frontend",
                    confidence="high",
                    evidence=[ArchitectureEvidence(entry_rel, "common frontend entry file")],
                    metrics={"line_count": _line_count(entry)},
                ))
                break
    return nodes


def _build_import_edges(
    modules: list[PythonModuleInfo],
    module_by_name: dict[str, PythonModuleInfo],
    node_by_module: dict[str, ArchitectureNode],
) -> list[ArchitectureEdge]:
    edges: list[ArchitectureEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for module in modules:
        source = node_by_module.get(module.module)
        if not source:
            continue
        for imported in module.internal_imports:
            target_module = _resolve_internal_module(imported, module_by_name)
            target = node_by_module.get(target_module or "")
            if not target or target.id == source.id:
                continue
            key = (source.id, target.id, "imports")
            if key in seen:
                continue
            seen.add(key)
            edges.append(ArchitectureEdge(
                source=source.id,
                target=target.id,
                kind="imports",
                confidence="high",
                evidence=[ArchitectureEvidence(source.path, f"imports {imported}")],
            ))
    return edges


def _resolve_internal_module(imported: str, module_by_name: dict[str, PythonModuleInfo]) -> str | None:
    if imported in module_by_name:
        return imported
    parts = imported.split(".")
    while len(parts) > 1:
        parts.pop()
        candidate = ".".join(parts)
        if candidate in module_by_name:
            return candidate
    return None


def _frontend_api_edges(nodes: list[ArchitectureNode], root: Path) -> list[ArchitectureEdge]:
    api_nodes = [node for node in nodes if node.kind == "api_route"]
    if not api_nodes:
        return []
    edges: list[ArchitectureEdge] = []
    for node in nodes:
        if node.layer != "presentation/frontend":
            continue
        if node.path.endswith("package.json"):
            continue
        path = root / node.path
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if re.search(r"['\"]\/api\/|\bfetch\s*\(|\baxios\.(get|post|put|delete|patch|request)\s*\(", text):
            edges.append(ArchitectureEdge(
                source=node.id,
                target=api_nodes[0].id,
                kind="frontend_calls_api",
                confidence="medium",
                evidence=[ArchitectureEvidence(node.path, "frontend API call pattern")],
            ))
    return edges


def _apply_dependency_metrics(nodes: list[ArchitectureNode], edges: list[ArchitectureEdge]) -> None:
    incoming = Counter(edge.target for edge in edges if edge.kind in {"imports", "frontend_calls_api"})
    outgoing = Counter(edge.source for edge in edges if edge.kind in {"imports", "frontend_calls_api"})
    for node in nodes:
        node.metrics["incoming_internal_dependencies"] = incoming.get(node.id, 0)
        node.metrics["outgoing_internal_dependencies"] = outgoing.get(node.id, 0)
        node.metrics["dependency_centrality"] = incoming.get(node.id, 0) + outgoing.get(node.id, 0)


def _detect_cycles(nodes: list[ArchitectureNode], edges: list[ArchitectureEdge]) -> list[ArchitectureCycle]:
    node_ids = {node.id for node in nodes}
    path_by_id = {node.id: node.path for node in nodes}
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.kind == "imports" and edge.source in node_ids and edge.target in node_ids:
            adjacency[edge.source].append(edge.target)

    index = 0
    stack: list[str] = []
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def strongconnect(node_id: str) -> None:
        nonlocal index
        indices[node_id] = index
        lowlinks[node_id] = index
        index += 1
        stack.append(node_id)
        on_stack.add(node_id)
        for target in adjacency.get(node_id, []):
            if target not in indices:
                strongconnect(target)
                lowlinks[node_id] = min(lowlinks[node_id], lowlinks[target])
            elif target in on_stack:
                lowlinks[node_id] = min(lowlinks[node_id], indices[target])
        if lowlinks[node_id] == indices[node_id]:
            component: list[str] = []
            while stack:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node_id:
                    break
            if len(component) > 1:
                components.append(sorted(component))

    for node_id in sorted(node_ids):
        if node_id not in indices:
            strongconnect(node_id)

    cycles: list[ArchitectureCycle] = []
    for idx, component in enumerate(sorted(components), start=1):
        paths = [path_by_id[item] for item in component]
        classification = "benign/package-initialization cycle requiring review" if all(path.endswith("__init__.py") for path in paths) else "likely architectural cycle"
        cycles.append(ArchitectureCycle(
            id=f"cycle:{idx}",
            node_ids=component,
            paths=paths,
            classification=classification,
            confidence="medium",
            evidence=[ArchitectureEvidence(paths[0], "strongly connected import component")],
        ))
    return cycles


def _map_test_relationships(modules: list[PythonModuleInfo], module_by_name: dict[str, PythonModuleInfo]) -> dict[str, str]:
    production = {module.module: module for module in modules if not _is_test_path(module.path)}
    status = {module.path: "no_associated_test_evidence" for module in production.values()}
    if not any(_is_test_path(module.path) for module in modules):
        return {path: "unavailable" for path in status}

    for test_module in [module for module in modules if _is_test_path(module.path)]:
        for imported in test_module.internal_imports:
            target_name = _resolve_internal_module(imported, module_by_name)
            target = production.get(target_name or "")
            if target:
                status[target.path] = "directly_tested"
        test_name = Path(test_module.path).stem
        candidate = test_name.removeprefix("test_").removesuffix("_test")
        for prod in production.values():
            if Path(prod.path).stem == candidate and status[prod.path] == "no_associated_test_evidence":
                status[prod.path] = "possibly_tested"
    return status


def _apply_finding_context(nodes: list[ArchitectureNode], findings_by_path: dict[str, list[dict[str, Any]]]) -> None:
    by_path = {node.path: node for node in nodes}
    for path, findings in findings_by_path.items():
        node = by_path.get(path)
        if not node:
            continue
        node.metrics["finding_count"] = len(findings)
        if any(str(item.get("code")) == "B101" and _is_test_path(path) for item in findings):
            node.risk["b101_context"] = "expected_test_assert"


def _apply_radon_metrics(nodes: list[ArchitectureNode], findings_by_path: dict[str, list[dict[str, Any]]]) -> None:
    by_path = {node.path: node for node in nodes}
    for path, findings in findings_by_path.items():
        node = by_path.get(path)
        if not node:
            continue
        max_complexity = 0
        for finding in findings:
            if str(finding.get("tool")).lower() != "radon":
                continue
            message = str(finding.get("message") or "")
            match = re.search(r"complexity\s+(\d+)", message)
            if match:
                max_complexity = max(max_complexity, int(match.group(1)))
            sev = str(finding.get("severity") or "")
            max_complexity = max(max_complexity, {"B": 6, "C": 11, "D": 21, "E": 31, "F": 41}.get(sev, 0))
        if max_complexity:
            node.metrics["max_complexity"] = max_complexity


def _attach_hotspot_risk(nodes: list[ArchitectureNode], hotspots: list[Any]) -> None:
    by_id = {node.id: node for node in nodes}
    for hotspot in hotspots:
        node = by_id.get(hotspot.node_id)
        if node:
            node.risk = {
                "hotspot_id": hotspot.id,
                "rank": hotspot.rank,
                "risk_score": hotspot.risk_score,
                "risk_level": hotspot.risk_level,
            }


def _build_layers(nodes: list[ArchitectureNode]) -> list[ArchitectureLayer]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        grouped[node.layer].append(node.id)
    labels = {
        "presentation/frontend": "Presentation / Frontend",
        "API/interface": "API / Interface",
        "application/service": "Application / Service",
        "domain/core": "Domain / Core",
        "data/infrastructure": "Data / Infrastructure",
        "configuration": "Configuration",
        "tests": "Tests",
    }
    return [
        ArchitectureLayer(
            id=layer_id,
            label=labels.get(layer_id, layer_id),
            node_ids=sorted(node_ids)[:20],
            confidence="medium",
            evidence=[ArchitectureEvidence("", "path, naming, import, or framework signal")],
        )
        for layer_id, node_ids in sorted(grouped.items())
    ]


def _entry_points(nodes: list[ArchitectureNode]) -> list[dict[str, Any]]:
    entries = []
    for node in nodes:
        if node.kind in {"entry_point", "api_route", "CLI"}:
            entries.append({"node_id": node.id, "path": node.path, "kind": node.kind, "confidence": node.confidence})
    return sorted(entries, key=_entry_point_rank)


def _entry_point_rank(entry: dict[str, Any]) -> tuple[int, str]:
    path = str(entry.get("path") or "")
    kind = str(entry.get("kind") or "")
    if kind == "api_route":
        return (0, path)
    if path.endswith("/cli.py") or path == "cli.py":
        return (1, path)
    if kind == "entry_point":
        return (2, path)
    if kind == "CLI":
        return (3, path)
    return (4, path)


def _external_integrations(modules: list[PythonModuleInfo], root: Path) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    evidence: dict[str, str] = {}
    for module in modules:
        for imported in module.external_imports:
            name = imported.split(".")[0]
            if not name or name in STDLIB_MODULES:
                continue
            counts[name] += 1
            evidence.setdefault(name, module.path)
    package = read_json_file(root / "package.json")
    package_deps = set((package.get("dependencies") or {}).keys())
    for name in package_deps:
        counts[name] += 1
        evidence.setdefault(name, "package.json")
    return [
        {"name": name, "kind": "external_package", "confidence": "medium", "evidence": [{"path": evidence[name], "reason": "static import or package dependency"}]}
        for name, _ in counts.most_common(MAX_EXTERNALS)
    ]


def _evidence_gaps(parse_errors: list[str], audit: dict[str, Any], modules: list[PythonModuleInfo]) -> list[str]:
    gaps: list[str] = []
    if parse_errors:
        gaps.append(f"{len(parse_errors)} Python file(s) could not be parsed, so architecture evidence is partial.")
    if not any(_is_test_path(module.path) for module in modules):
        gaps.append("No pytest-style test files were detected for source-to-test mapping.")
    coverage_entries = [entry for entry in audit.get("test_analysis", []) or [] if isinstance(entry, dict) and str(entry.get("tool")).lower() == "coverage"]
    if not coverage_entries:
        gaps.append("Coverage file mapping was unavailable.")
    return gaps[:6]


def _summary(
    entry_points: list[dict[str, Any]],
    layers: list[ArchitectureLayer],
    external_integrations: list[dict[str, Any]],
    cycles: list[ArchitectureCycle],
    hotspots: list[Any],
    evidence_gaps: list[str],
) -> str:
    entry = entry_points[0]["path"] if entry_points else "the detected source modules"
    layer_names = ", ".join(layer.label for layer in layers[:4]) or "a compact module layout"
    external = external_integrations[0]["name"] if external_integrations else "no dominant external integration"
    cycle_text = f"{len(cycles)} import cycle(s) need review" if cycles else "no circular import components were detected"
    hotspot_text = f"the top hotspot is {hotspots[0].path}" if hotspots else "no production hotspot exceeded the v1 threshold"
    gap_text = f" Biggest evidence gap: {evidence_gaps[0]}" if evidence_gaps else ""
    return f"Static evidence suggests requests or execution enter through {entry}; the repository appears organized around {layer_names}. The most visible external dependency signal is {external}; {cycle_text}, and {hotspot_text}.{gap_text}"


def _confidence(parse_errors: list[str], nodes: list[ArchitectureNode], edges: list[ArchitectureEdge]) -> str:
    if parse_errors:
        return "medium"
    if nodes and edges:
        return "high"
    if nodes:
        return "medium"
    return "low"


def _is_test_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    name = parts[-1] if parts else path
    return "tests" in parts or name.startswith("test_") or name.endswith("_test.py")


def _line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    except OSError:
        return 0
