import logging
import re
import asyncio
from .. import loader, utils

logger = logging.getLogger(__name__)
__version__ = (1, 0, 0)

@loader.tds
class SourceTriggerMod(loader.Module):
    """отправляет медиа или текст из канала в ответ на текстовые триггеры"""

    strings = {
        "name": "sourcetrigger",
        "parsing_started": "<emoji document_id=5204189706237004154>➡️</emoji> <b>parsing started.</b> это очистит все старые триггеры и сканирует канал заново, подождите...",
        "parsing_complete": "<emoji document_id=5260726538302660868>✅</emoji> <b>parsing complete</b>\nобработано: <b>{}</b> точных, <b>{}</b> по вхождению, <b>{}</b> точных+удалить, <b>{}</b> regex, <b>{}</b> regex+удалить",
        "channel_error": "<emoji document_id=5260342697075416641>❌</emoji> <b>ошибка доступа к каналу</b>",
        "add_trigger_error": "<emoji document_id=5258474669769497337>❗️</emoji> <b>не удалось добавить триггер</b>",
        "must_be_reply": "<emoji document_id=5260450573768990626>➡️</emoji> <b>нужно ответить на сообщение</b>",
        "no_trigger_specified": "<emoji document_id=5257965174979042426>📝</emoji> <b>нужно указать триггер</b>",
        "invalid_trigger_format": "<emoji document_id=5260342697075416641>❌</emoji> <b>неверный формат триггера</b>",
        "processing_add": "<emoji document_id=5427181942934088912>💬</emoji> <b>обработка</b>",
    }

    strings_ru = strings

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "source_channel_id",
                -1002911008271,
                lambda: self.strings("config_source_channel"),
                validator=loader.validators.Integer(),
            )
        )
        self.triggers = {}

    async def on_dlmod(self):
        self.triggers.update(self.db.get("SourceTrigger", "triggers", {}))

    def _get_source_channel(self):
        return [self.config["source_channel_id"]]

    async def _process_message_for_triggers(self, msg):
        if not msg or not getattr(msg, 'text', None): 
            return None
        text = msg.text.strip()
        first_line = text.split('\n', 1)[0].strip()
        ttype, trigger = None, None
        if first_line.startswith("~~~"):
            content_after = first_line[3:].lstrip()
            if content_after.startswith("|"):
                pattern = content_after[1:].strip()
                try:
                    re.compile(pattern, re.IGNORECASE)
                    ttype, trigger = "regex_delete", pattern
                except:
                    return None
            else:
                ttype, trigger = "exact_delete", content_after.strip().lower()
        elif first_line.startswith("~~"):
            ttype, trigger = "contains", first_line[2:].strip().lower()
        elif first_line.startswith("~"):
            content_after = first_line[1:].lstrip()
            if content_after.startswith("|"):
                pattern = content_after[1:].strip()
                try:
                    re.compile(pattern, re.IGNORECASE)
                    ttype, trigger = "regex", pattern
                except:
                    return None
            else:
                ttype, trigger = "exact", content_after.strip().lower()
        return (ttype, trigger, msg.id) if ttype and trigger else None

    @loader.command(ru_doc="обновить базу триггеров из канала")
    async def parsetriggers(self, message):
        status_msg = await utils.answer(message, self.strings("parsing_started"))
        self.triggers.clear()
        counts = {"exact":0,"contains":0,"exact_delete":0,"regex":0,"regex_delete":0}
        source_id = self.config["source_channel_id"]
        if not source_id:
            await utils.answer(status_msg, self.strings("channel_error"))
            return
        try:
            channel_entity = await self.client.get_entity(source_id)
            async for msg in self.client.iter_messages(channel_entity, limit=None):
                result = await self._process_message_for_triggers(msg)
                if not result:
                    continue
                ttype, trigger, msg_id = result
                key = f"{ttype}::{trigger}"
                if key not in self.triggers:
                    self.triggers[key] = []
                if msg_id not in self.triggers[key]:
                    self.triggers[key].append(msg_id)
                counts[ttype] += 1
            self.db.set("SourceTrigger", "triggers", self.triggers)
            await utils.answer(status_msg, self.strings("parsing_complete").format(
                counts["exact"], counts["contains"], counts["exact_delete"], counts["regex"], counts["regex_delete"]
            ))
        except Exception as e:
            logger.exception("failed to parse triggers")
            await utils.answer(status_msg, self.strings("channel_error") + f"\n<code>{utils.escape_html(str(e))}</code>")

    def _parse_trigger_string(self, text):
        text = text.strip()
        ttype, trigger = None, None
        if text.startswith("~~~"):
            content_after = text[3:].lstrip()
            if content_after.startswith("|"):
                pattern = content_after[1:].strip()
                try:
                    re.compile(pattern, re.IGNORECASE)
                    ttype, trigger = "regex_delete", pattern
                except:
                    return None, None
            else:
                ttype, trigger = "exact_delete", content_after.strip().lower()
        elif text.startswith("~~"):
            ttype, trigger = "contains", text[2:].strip().lower()
        elif text.startswith("~"):
            content_after = text[1:].lstrip()
            if content_after.startswith("|"):
                pattern = content_after[1:].strip()
                try:
                    re.compile(pattern, re.IGNORECASE)
                    ttype, trigger = "regex", pattern
                except:
                    return None, None
            else:
                ttype, trigger = "exact", content_after.strip().lower()
        return ttype, trigger

    @loader.command(ru_doc="<ответ на сообщение> <триггер> - добавить новый триггер")
    async def addtrigger(self, message):
        reply = await message.get_reply_message()
        if not reply:
            await utils.answer(message, self.strings("must_be_reply"))
            return
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_trigger_specified"))
            return
        ttype, trigger = self._parse_trigger_string(args)
        if not ttype or not trigger:
            await utils.answer(message, self.strings("invalid_trigger_format"))
            return
        status_msg = await utils.answer(message, self.strings("processing_add"))
        source_id = self.config["source_channel_id"]
        try:
            content_msg = await self.client.send_file(source_id, reply)
            trigger_msg = await self.client.send_message(source_id, args, reply_to=content_msg.id)
            key = f"{ttype}::{trigger}"
            if key not in self.triggers:
                self.triggers[key] = []
            if content_msg.id not in self.triggers[key]:
                self.triggers[key].append(content_msg.id)
            self.db.set("SourceTrigger", "triggers", self.triggers)
        except:
            await utils.answer(status_msg, self.strings("add_trigger_error"))

    @loader.watcher(no_commands=True)
    async def watcher(self, message):
        if not getattr(message, "out", False) or not getattr(message, "text", None):
            return
        text = message.raw_text.strip().lower()
        matched_key = None
        for key in self.triggers:
            if key.startswith("regex_delete::"):
                pattern = key.split("::",1)[1]
                try:
                    if re.fullmatch(pattern, text, re.IGNORECASE):
                        matched_key = key
                        break
                except: continue
        if not matched_key:
            exact_delete_key = f"exact_delete::{text}"
            if exact_delete_key in self.triggers:
                matched_key = exact_delete_key
        if not matched_key:
            for key in self.triggers:
                if key.startswith("regex::"):
                    pattern = key.split("::",1)[1]
                    try:
                        if re.fullmatch(pattern, text, re.IGNORECASE):
                            matched_key = key
                            break
                    except: continue
        if not matched_key:
            exact_key = f"exact::{text}"
            if exact_key in self.triggers:
                matched_key = exact_key
        if not matched_key:
            for key in self.triggers:
                if key.startswith("contains::"):
                    trigger = key.split("::",1)[1]
                    if trigger in text:
                        matched_key = key
                        break
        if matched_key:
            msg_ids = self.triggers[matched_key]
            if not msg_ids: return
            should_delete = "delete" in matched_key.split("::",1)[0]
            tasks = [self._process_and_send(message, msg_id) for msg_id in msg_ids]
            await asyncio.gather(*tasks)
            if should_delete and getattr(message,"out",False):
                await message.delete()

    async def _process_and_send(self, trigger_message, msg_id):
        source_id = self.config["source_channel_id"]
        try:
            source_msg = await self.client.get_messages(source_id, ids=msg_id)
            if not source_msg: return
            caption = source_msg.text or ""
            if source_msg.media:
                await self.client.send_file(
                    trigger_message.peer_id,
                    source_msg,
                    caption=caption or None,
                    reply_to=trigger_message.reply_to_msg_id if getattr(trigger_message,"is_reply",False) else None
                )
            elif caption:
                await utils.answer(trigger_message, caption, reply_to=trigger_message.reply_to_msg_id if getattr(trigger_message,"is_reply",False) else None)
        except:
            pass
