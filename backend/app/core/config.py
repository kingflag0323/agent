from pathlib import Path
import os

ROOT = Path(os.environ.get('SXF_ROOT', Path(__file__).resolve().parents[3])).resolve()
DATA = Path(os.environ.get('SXF_DATA_DIR', ROOT / 'data')).resolve()
DATA.mkdir(parents=True, exist_ok=True)
os.chmod(DATA, 0o700)
DB = DATA / 'sentinel.db'
REPOS = DATA / 'repositories'
REPOS.mkdir(exist_ok=True)
ALLOWED_ROOTS = [Path(p).expanduser().resolve() for p in os.environ.get('SXF_REPO_ROOTS', str(ROOT / 'demo') + os.pathsep + str(REPOS)).split(os.pathsep)]
DEFAULTS = {
    'xdr': {'mode': 'demo', 'base_url': 'https://172.20.0.140', 'auth_type': 'token', 'access_key': '', 'secret_key': '', 'auth_code': '', 'auth_header': 'Authorization', 'auth_scheme': 'Bearer', 'token': '', 'timeout': 20, 'verify_tls': True, 'ca_bundle': ''},
    'llm': {'mode': 'mock', 'base_url': '', 'api_key': '', 'model': '', 'temperature': 0.1, 'timeout': 30, 'max_tokens': 1500, 'thinking_mode': 'auto'},
    'agent': {'max_steps': 20, 'timeout': 120, 'reviewer': True, 'debug': False},
    'workspace': {'working_directory': str(REPOS), 'report_directory': str(DATA/'reports')},
    'ti': {'enabled': False, 'provider': 'cisa', 'api_key': '', 'interval_hours': 6, 'lookback_days': 7},
    'audit': {'max_files': 1000, 'max_file_kb': 512, 'timeout': 45},
}
