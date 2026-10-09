import ast
import hashlib

import pytest

from ace_pruningrag.compatibility import patch_constructor


def fixture_source():
    return (
        "if __name__ == '__main__':\n"
        "    noise = test_noise\n"
        "    retriever = Retriever(1, 2, 'embedding', 'reranker', False, "
        "200, 0, 0, False, 'cpu', noise)\n"
    )


def test_patch_preserves_supported_arguments_and_refuses_noise():
    source = fixture_source()
    digest = hashlib.sha256(source.encode()).hexdigest()
    patched = patch_constructor(source, digest)
    observed = []

    class Retriever:
        def __init__(self, a, b, c, d, e, f, g, h, i, j):
            observed.append((a, b, c, d, e, f, g, h, i, j))

    exec(patched, {"__name__": "__main__", "Retriever": Retriever, "test_noise": 0})
    assert observed == [(1, 2, "embedding", "reranker", False, 200, 0, 0, False, "cpu")]
    with pytest.raises(ValueError, match="noise=0"):
        exec(patched, {"__name__": "__main__", "Retriever": Retriever, "test_noise": 1})
    assert len(observed) == 1
    ast.parse(patched)


def test_patch_rejects_changed_source_and_unknown_call_shape():
    source = fixture_source()
    with pytest.raises(ValueError, match="reviewed source"):
        patch_constructor(source + "# changed", hashlib.sha256(source.encode()).hexdigest())
    source = source.replace(", noise)", ", unknown)")
    with pytest.raises(ValueError, match="extra argument"):
        patch_constructor(source, hashlib.sha256(source.encode()).hexdigest())
