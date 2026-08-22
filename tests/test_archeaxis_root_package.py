"""Root package alias test (G7: archeaxis namespace available per plan)."""
from __future__ import annotations


def test_root_package_aliases():
    import archeaxis
    assert archeaxis.__version__ == "0.6.8"
    assert archeaxis.__product__ == "ArcheAxis Knowledge / 星环知识平台"

    import archeaxis.federation
    import archeaxis.ingestion
    assert archeaxis.federation is not None

    from archeaxis.app.main import app
    assert app is not None
