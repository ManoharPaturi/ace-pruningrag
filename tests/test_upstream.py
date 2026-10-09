import pytest

from ace_pruningrag.upstream import retriever_signature_check


@pytest.mark.parametrize("arguments,status", [("1, 2", "pass"), ("1, 2, 3", "blocked")])
def test_signature_audit_without_importing_heavy_dependencies(tmp_path, arguments, status):
    (tmp_path / "models/retrieve").mkdir(parents=True)
    (tmp_path / "main.py").write_text(f"retriever = Retriever({arguments})\n")
    (tmp_path / "models/retrieve/retriever.py").write_text(
        "import unavailable_heavy_dependency\n"
        "class Retriever:\n"
        "    def __init__(self, top_k, device='cpu'): pass\n"
    )
    result = retriever_signature_check(tmp_path)
    assert result["status"] == status
