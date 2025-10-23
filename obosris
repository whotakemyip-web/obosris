
from herokutl.client import userbot
from herokutl.modules import Module
import asyncio

class OborsisModule(Module):
    """
    slash-команда /обосрись
    отправляет сообщение с таймером 20 секунд
    """
    def __init__(self):
        super().__init__(
            name="Oborsis",
            description="отправляет предупреждение о том, что пользователь обосрётся",
            commands=["обосрись"],  # это будет slash-команда /обосрись
            hidden=False
        )

    async def обосрись(self, message, *args):
        chat_id = message.chat_id
        
        sent_msg = await userbot.send_message(chat_id, "***пользователь обосрётся через 20 секунд*** ")
        
        await asyncio.sleep(20)
      
        await userbot.edit_message(sent_msg, "***ну он обосрался ***")
