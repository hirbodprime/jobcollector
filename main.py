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

    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")
    string_sess = os.getenv("TELETHON_STRING_SESSION") or None
    telethon_client = None
    if api_id and api_hash:
        telethon_client = await build_telethon_client(api_id, api_hash, string_sess)

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
    if telethon_client:
        tasks.append(asyncio.create_task(telegram_channels_loop(crawl_interval, telethon_client)))

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
