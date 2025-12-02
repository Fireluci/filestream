from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

async def auto_restart_cycle():
    while True:
        now = datetime.now(tz=IST)

        # Next restart at 6:00 (AM or PM depending on time)
        next_6 = now.replace(hour=18, minute=0, second=0, microsecond=0)  # default: 6 PM

        if now.hour < 6 or (now.hour == 6 and now.minute == 0):
            # Before 6 AM → schedule 6 AM today
            next_6 = now.replace(hour=6, minute=0, second=0, microsecond=0)
        elif 6 <= now.hour < 18:
            # Between 6 AM & 6 PM → next restart is 6 PM
            next_6 = now.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            # After 6 PM → next restart is 6 AM tomorrow
            next_6 = now.replace(hour=6, minute=0, second=0, microsecond=0) + timedelta(days=1)

        wait_secs = (next_6 - now).total_seconds()

        print(f"[Auto-Restart] Next restart at {next_6.isoformat()} IST ({wait_secs/3600:.2f} hours).")
        await asyncio.sleep(wait_secs)

        # Restart message
        timestamp = datetime.now(tz=IST).isoformat()
        msg = f"♻️ BOT RESTARTED\n⏰ {timestamp}\n🔁 Auto-Restart at 6 AM / 6 PM"

        print("\n" + msg + "\n")
        logging.info(msg)

        # Send to log channel
        try:
            await FileStream.send_message(
                chat_id=Telegram.FLOG_CHANNEL,
                text=msg
            )
        except Exception as e:
            print("[Auto-Restart] Failed sending to FLOG_CHANNEL:", e)

        # Gracefully stop services
        try: await FileStream.stop()
        except: pass

        try: await FileStream._client.disconnect()
        except: pass

        try: await FileStream.session.stop()
        except: pass

        try: await server.cleanup()
        except: pass

        print("[Auto-Restart] Exiting — Koyeb will restart container.")
        sys.exit(0)
