import pytest
import payroll

def test_unknown_attribute_raises_attributeerror():
    with pytest.raises(AttributeError, match="module 'payroll' has no attribute 'foo'"):
        payroll.foo  # Triggers __getattr__ raise

# Covers __init__.py 38% -> 100%

