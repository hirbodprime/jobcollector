from typing import Optional, Sequence
from asgiref.sync import sync_to_async
from django.db.models import Q
from core.models import Post
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

def format_post(p: Post) -> str:
    header = {
        "JOB": "💼 New Remote Job",
        "PROJECT": "🚀 New Project",
        "COMPETITION": "🏆 New Competition",
    }.get(p.category, "📢 New Opportunity")

    lines = [
        f"{header}",
        "─────────────────",
        f"Title: {p.title}",
        f"Link: {p.link}",
        "#remote",
    ]
    return "\n".join(lines)

@sync_to_async
def fetch_unposted(limit: int = 10) -> Sequence[Post]:
    return list(Post.objects.filter(posted_to_channel=False).order_by("created_at")[:limit])

@sync_to_async
def mark_posted(ids: list[int]):
    Post.objects.filter(id__in=ids).update(posted_to_channel=True)

async def post_new_items_job(context: ContextTypes.DEFAULT_TYPE):
    channel = context.bot_data.get("target_channel")
    if not channel:
        return
    posts = await fetch_unposted(limit=20)
    if not posts:
        return
    sent_ids = []
    for p in posts:
        try:
            await context.bot.send_message(chat_id=channel, text=format_post(p), disable_web_page_preview=True)
            sent_ids.append(p.id)
        except Exception:
            pass
    if sent_ids:
        await mark_posted(sent_ids)

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

def build_application(bot_token: str, target_channel: str):
    app = Application.builder().token(bot_token).build()
    app.add_handler(CommandHandler("ping", ping))
    app.job_queue.run_repeating(post_new_items_job, interval=int(app.bot_data.get("post_interval", 60)), first=5)
    app.bot_data["target_channel"] = target_channel
    return app
