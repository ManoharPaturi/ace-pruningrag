from ace_pruningrag.dataset import QueryInput
from ace_pruningrag.price_eligibility import current_symbols, expansion_symbols


def query(text):
    return QueryInput("q", text, "02/28/2024, 07:53:08 PT", ())


def test_current_executor_entity_boundaries_and_multiple_entities():
    assert current_symbols(query("pineapple stock price")) == set()
    assert current_symbols(query("Apple AAPL stock price")) == {"AAPL"}
    assert current_symbols(query("apple versus microsoft stock price")) == {"AAPL", "MSFT"}


def test_expansion_requires_price_hint_and_exact_inventory_word():
    inventory = {"CURO", "MSFT", "ON", "AAPL"}
    assert expansion_symbols(query("latest stock price of curo today"), inventory) == {"CURO"}
    assert expansion_symbols(query("microsoft office languages"), inventory) == set()
    assert expansion_symbols(query("stock price on Tuesday"), inventory) == set()
    assert expansion_symbols(query("stock price of curoextra"), inventory) == set()
    assert expansion_symbols(query("aapl versus msft stock price"), inventory) == {"AAPL", "MSFT"}
