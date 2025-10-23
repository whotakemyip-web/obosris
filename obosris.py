from heroku.modules import Module
import asyncio

class OborsisModule(Module):
    name = "oborsis"
    commands = ["обосрись"]

    async def on_command(self, message):
        target = message.reply_to_user.first_name if message.reply_to_user else "пользователь"
        await message.respond(f"{target} обосрётся через 20 секунд")
        await asyncio.sleep(20)
        await message.respond(f"{target} обосрался")
