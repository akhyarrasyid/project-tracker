import sys

import pytest

print("Starting pytest programmatically...", flush=True)
ret = pytest.main(["-vv", "-s", "tests/"])
print(f"pytest exited with code: {ret}", flush=True)
sys.exit(ret)
