import os

os.environ.setdefault("AUTO_NGROK", "0")   # tests that start the hub must not open a tunnel
