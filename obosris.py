from herokutl.client import client
from herokutl.modules import Module
import asyncio

class OborsisModule(Module):
    name = "oborsis"
    commands = ["обосрись"]

    async def on_command(self, message):
        if message.text.lower().startswith("/обосрись"):
            target = message.reply_to_user.first_name if message.reply_to_user else "пользователь"
            await client.send_message(
                message.chat.id,
                f"***{target} обосрётся через 20 секунд***"
            )
            await asyncio.sleep(20)
            await client.send_message(
                message.chat.id,
                f"{target} обосрался"
            )
