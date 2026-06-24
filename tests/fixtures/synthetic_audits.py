from typing import Dict, Any


def healthy_audit() -> Dict[str, Any]:
    return {
        "metadata": {"total_files": 10, "total_directories": 3, "python_files": 8, "test_files": 3, "has_readme": True},
        "static_analysis": [
            {"tool": "ruff", "status": "completed", "findings": []},
            {"tool": "bandit", "status": "completed", "findings": []},
            {"tool": "radon", "status": "completed", "summary": {"average_complexity": 2.0}, "findings": []},
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "completed", "summary": {"passed": 10, "failed": 0, "errors": 0}, "findings": []},
            {"tool": "coverage", "status": "completed", "summary": {"coverage_percent": 95.0}, "findings": []},
        ],
        "repository_analysis": [
            {"tool": "readme", "status": "completed", "findings": []},
            {"tool": "structure", "status": "completed", "findings": []},
        ],
        "scoring": {"overall_score": 95, "repository_health_score": 95, "portfolio_readiness_score": 92, "categories": {}},
        "diagnosis": {"hard_flags": [], "limitations": []},
        "remediation_suggestions": [],
    }


def weak_audit() -> Dict[str, Any]:
    return {
        "metadata": {"total_files": 5, "total_directories": 2, "python_files": 3, "test_files": 0, "has_readme": False},
        "static_analysis": [
            {"tool": "ruff", "status": "completed", "findings": [{"severity": "low"}]},
            {"tool": "bandit", "status": "completed", "findings": [{"severity": "low"}]},
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "completed", "summary": {"passed": 0, "failed": 0, "errors": 0}, "findings": []},
        ],
        "repository_analysis": [
            {"tool": "readme", "status": "completed", "findings": []},
            {"tool": "structure", "status": "completed", "findings": []},
        ],
        "scoring": {"overall_score": 70, "repository_health_score": 70, "portfolio_readiness_score": 65, "categories": {}},
        "diagnosis": {"hard_flags": [], "limitations": []},
        "remediation_suggestions": [],
    }


def failing_tests_audit() -> Dict[str, Any]:
    return {
        "metadata": {"total_files": 8, "total_directories": 2, "python_files": 6, "test_files": 2, "has_readme": True},
        "static_analysis": [
            {"tool": "ruff", "status": "completed", "findings": []},
            {"tool": "bandit", "status": "completed", "findings": []},
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "completed", "summary": {"passed": 5, "failed": 2, "errors": 1}, "findings": []},
            {"tool": "coverage", "status": "completed", "summary": {"coverage_percent": 60.0}, "findings": []},
        ],
        "repository_analysis": [
            {"tool": "readme", "status": "completed", "findings": []},
            {"tool": "structure", "status": "completed", "findings": []},
        ],
        "scoring": {"overall_score": 75, "repository_health_score": 70, "portfolio_readiness_score": 68, "categories": {}},
        "diagnosis": {"hard_flags": [], "limitations": []},
        "remediation_suggestions": [],
    }


def security_risk_audit() -> Dict[str, Any]:
    return {
        "metadata": {"total_files": 12, "total_directories": 4, "python_files": 10, "test_files": 3, "has_readme": True},
        "static_analysis": [
            {"tool": "ruff", "status": "completed", "findings": []},
            {"tool": "bandit", "status": "completed", "findings": [{"severity": "critical"}]},
        ],
        "test_analysis": [
            {"tool": "pytest", "status": "completed", "summary": {"passed": 8, "failed": 0, "errors": 0}, "findings": []},
        ],
        "repository_analysis": [
            {"tool": "readme", "status": "completed", "findings": []},
            {"tool": "structure", "status": "completed", "findings": []},
        ],
        "scoring": {"overall_score": 60, "repository_health_score": 65, "portfolio_readiness_score": 55, "categories": {}},
        "diagnosis": {"hard_flags": ["SECURITY_ISSUE"], "limitations": []},
        "remediation_suggestions": ["fix_security_issue"],
    }
