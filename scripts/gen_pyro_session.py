# scripts/gen_pyro_session.py
from pyrogram import Client

api_id = int(input("API_ID: ").strip())
api_hash = input("API_HASH: ").strip()

with Client("gen", api_id=api_id, api_hash=api_hash) as app:
    s = app.export_session_string()
    print("\nPYRO STRING SESSION:\n")
    print(s)
