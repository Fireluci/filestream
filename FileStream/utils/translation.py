from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from FileStream.config import Telegram

class LANG(object):

    START_TEXT = """
    <B>🔆 [ DOWNLOAD / STREAM ] 🔆
⌬──━━━━━━━━━━━━━━──⌬
♻ With This Bot You Can Get Fast Download / Stream Links To Any Telegram Files!</b>"""
    HELP_TEXT = """
<b>- ᴀᴅᴅ ᴍᴇ ᴀs ᴀɴ ᴀᴅᴍɪɴ ᴏɴ ᴛʜᴇ ᴄʜᴀɴɴᴇʟ</b>
<b>- sᴇɴᴅ ᴍᴇ ᴀɴʏ ᴅᴏᴄᴜᴍᴇɴᴛ ᴏʀ ᴍᴇᴅɪᴀ</b>
<b>- ɪ'ʟʟ ᴘʀᴏᴠɪᴅᴇ sᴛʀᴇᴀᴍᴀʙʟᴇ ʟɪɴᴋ</b>\n
<b>🔞 ᴀᴅᴜʟᴛ ᴄᴏɴᴛᴇɴᴛ sᴛʀɪᴄᴛʟʏ ᴘʀᴏʜɪʙɪᴛᴇᴅ.</b>\n
<i><b> ʀᴇᴘᴏʀᴛ ʙᴜɢs ᴛᴏ <a href='https://telegram.me/AvishkarPatil'>ᴅᴇᴠᴇʟᴏᴘᴇʀ</a></b></i>"""

    ABOUT_TEXT = """
<b>⚜ ᴍʏ ɴᴀᴍᴇ : {}</b>\n
<b>✦ ᴠᴇʀsɪᴏɴ : {}</b>
<b>✦ ᴜᴘᴅᴀᴛᴇᴅ ᴏɴ : 06-January-2024</b>
<b>✦ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href='https://telegram.me/AvishkarPatil'>Avishkar Patil</a></b>\n
"""

    STREAM_TEXT = """
<b>[ DOWNLOAD / STREAM ]
⌬──━━━━━━━━━━──⌬
📗 Fɪʟᴇ Nᴀᴍᴇ ➜ {}\n
📒 Fɪʟᴇ Sɪᴢᴇ ➜ {}\n
♻️ Dᴏᴡɴʟᴏᴀᴅ ➜ {}\n
🌟 Sᴛʀᴇᴀᴍ ➜ {}</b>"""

    STREAM_TEXT_X = """
<b>[ DOWNLOAD / STREAM ]
⌬──━━━━━━━━━━──⌬
📗 Fɪʟᴇ Nᴀᴍᴇ ➜ {}\n
📒 Fɪʟᴇ Sɪᴢᴇ ➜ {}\n
♻️ Dᴏᴡɴʟᴏᴀᴅ ➜ {}\n
🌟 Sᴛʀᴇᴀᴍ ➜ {}</b>"""

    BAN_TEXT = "__Sᴏʀʀʏ Sɪʀ, Yᴏᴜ ᴀʀᴇ Bᴀɴɴᴇᴅ ᴛᴏ ᴜsᴇ ᴍᴇ.__\n\n**[Cᴏɴᴛᴀᴄᴛ Dᴇᴠᴇʟᴏᴘᴇʀ](tg://user?id={}) Tʜᴇʏ Wɪʟʟ Hᴇʟᴘ Yᴏᴜ**"


class BUTTON(object):
    START_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('ᴀʙᴏᴜᴛ', callback_data='about'),
            InlineKeyboardButton('ᴄʟᴏsᴇ', callback_data='close')
        ],
            [InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url=f'https://telegram/{Telegram.UPDATES_CHANNEL}')]
        ]
    )
    HELP_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='home'),
            InlineKeyboardButton('ᴀʙᴏᴜᴛ', callback_data='about'),
            InlineKeyboardButton('ᴄʟᴏsᴇ', callback_data='close'),
        ],
            [InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url=f'https://telegram/{Telegram.UPDATES_CHANNEL}')]
        ]
    )
    ABOUT_BUTTONS = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton('ʜᴏᴍᴇ', callback_data='home'),
            InlineKeyboardButton('ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('ᴄʟᴏsᴇ', callback_data='close'),
        ],
            [InlineKeyboardButton("📢 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url=f'https://telegram/{Telegram.UPDATES_CHANNEL}')]
        ]
    )
