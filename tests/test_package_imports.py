def test_package_imports_and_version():
    import drrepo

    assert drrepo is not None

    # version attribute
    assert hasattr(drrepo, "__version__"), "drrepo.__version__ missing"
    assert isinstance(drrepo.__version__, str)
    assert drrepo.__version__ == "0.1.0"


def test_cli_and_audit_imports():
    from drrepo.cli import app

    assert app is not None

    from drrepo.audit import build_audit

    assert callable(build_audit)

    from drrepo.reports.markdown_report import render_markdown_report

    assert callable(render_markdown_report)
