# Shop API — static analysis fixture
This intentionally vulnerable Python source is only read by AST and Bandit. It is never imported, installed or served by this platform.
SQL injection: GET /api/user?id=... → user_controller → get_user → find_user.
Command injection: GET /api/diagnostic?host=... → diagnostic_controller → run_diagnostic.
Negative control: GET /api/health has no reachable vulnerable sink.
