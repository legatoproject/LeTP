"""Stubs for pytest option integration tests."""
import pytest
import swilog


def test_failing_case(request):
    """Test force assert."""
    swilog.info("Test %s" % request.node.name)
    assert False


def test_passing_case(request):
    """Test passing case."""
    swilog.info("Test %s" % request.node.name)


@pytest.fixture
def error_fixture():
    """Force assert as an error."""
    assert 0


def test_error_case(error_fixture):
    """Test pytest errors."""
    assert error_fixture
