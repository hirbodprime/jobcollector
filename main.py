# main.py
import os
import asyncio
import threading
from dotenv import load_dotenv

def init_django():
    load_dotenv()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobcollector.settings")

    import django
    django.setup()

def runserver_thread():
    from django.core.management import call_command
    port = os.getenv("DJANGO_PORT", "8000")
    call_command("runserver", f"127.0.0.1:{port}")

def migrate_and_seed():
    from django.core.management import call_command
    call_command("migrate", interactive=False)
    call_command("seed_sources")

async def async_main():
    # ✅ All imports that touch Django models happen AFTER init_django()
    from crawlers.telegram_channels import build_telethon_client
    from crawlers.scheduler import websites_loop, telegram_channels_loop
    from bots.telegram_bot import build_application

    # Run migrations in a separate thread
    await asyncio.to_thread(migrate_and_seed)

    # if os.getenv("START_DJANGO_SERVER", "1") == "1":
    #     threading.Thread(target=runserver_thread, daemon=True).start()

    from crawlers.pyro_channels import build_pyro_client as build_pyro_client, telegram_channels_loop as pyro_channels_loop

    api_id_env = os.getenv("API_ID", "").strip()
    api_hash = os.getenv("API_HASH", "").strip()
    pyro_string = os.getenv("PYRO_STRING_SESSION") or None  # generate this once locally (see below)
    pyro_client = None
    if api_id_env and api_hash:
        try:
            api_id = int(api_id_env)
        except ValueError:
            api_id = 0
        if api_id > 0:
            # Optional: SOCKS5/HTTP proxy dict if needed { "scheme":"socks5", "hostname":"127.0.0.1", "port":9050 }
            proxy = None
            pyro_client = await build_pyro_client(api_id, api_hash, pyro_string, proxy=proxy)
    else:
        print("Skipping Telegram user client (no API_ID/API_HASH).")

    bot_token = os.getenv("BOT_TOKEN", "")
    target_channel = os.getenv("TARGET_CHANNEL", "")
    post_interval = int(os.getenv("POST_INTERVAL_SECONDS", "60"))
    crawl_interval = int(os.getenv("CRAWL_INTERVAL_SECONDS", "60"))

    if not bot_token or not target_channel:
        print("!! BOT_TOKEN or TARGET_CHANNEL missing in .env — bot will not post.")
        return

    app = build_application(bot_token, target_channel)
    app.bot_data["post_interval"] = post_interval

    await app.initialize()
    await app.start()

    tasks = [asyncio.create_task(websites_loop(crawl_interval))]
    if pyro_client:
        tasks.append(asyncio.create_task(pyro_channels_loop(crawl_interval, pyro_client)))


    print("Remotebridge running. Ctrl+C to exit.")
    try:
        await app.updater.start_polling()
        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        for t in tasks:
            t.cancel()
        if telethon_client:
            await telethon_client.disconnect()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    init_django()              # ✅ make Django apps (including `core`) ready
    asyncio.run(async_main())  # then run everything
