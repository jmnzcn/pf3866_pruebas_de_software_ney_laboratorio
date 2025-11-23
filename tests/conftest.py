import pytest, os, random
random.seed(42)

def pytest_addoption(parser):
    parser.addoption("--retries", action="store", default="1")

@pytest.fixture(autouse=True)
def _stable_env(monkeypatch):
    monkeypatch.setenv("TZ","UTC")
