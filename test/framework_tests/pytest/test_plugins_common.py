"""Test common plugin behaviors."""


def test_plugins_initialization(testdir):
    """Test plugin can be initialized."""
    result = testdir.runpytest()
    result.assert_outcomes(passed=0)
