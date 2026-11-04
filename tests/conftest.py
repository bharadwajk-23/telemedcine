import os
import sys

os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest")
os.environ.setdefault("TWILIO_API_KEY", "SKtest")
os.environ.setdefault("TWILIO_API_SECRET", "secret")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "authtoken")
os.environ.setdefault("TWILIO_TWIML_APP_SID", "APtest")
os.environ.setdefault("TWILIO_CALLER_ID", "+15550000000")
os.environ.setdefault("BASE_URL", "http://testserver")
os.environ.setdefault("DATA_FILE", "data/test_data.json")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
