import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--all",
        action="store_true",
        help="Run all tests"
    )
