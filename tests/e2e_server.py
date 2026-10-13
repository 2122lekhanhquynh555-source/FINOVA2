import os, sys, tempfile
os.environ.update(DATA_DIR=tempfile.mkdtemp(), GEMINI_API_KEY="UI-TEST-KEY", ALLOW_DEMO_RESET="1", ADMIN_EMAILS="admin@x.com", REGISTER_LIMIT="1000")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests import mock_gemini as MG
srv, url = MG.start(); os.environ["GEMINI_BASE_URL"] = url
import app
app.app.run(port=5057)
