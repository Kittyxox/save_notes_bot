import json
import os
import logging
import re
import shutil
import traceback
import sys
from datetime import datetime
from telegram import BotCommand, CallbackQuery
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.error import BadRequest
from telegram import ParseMode
from telegram import InputFile

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs_bot.txt'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Error handler function
def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb = ''.join(tb_list)
    update.message.reply_text(f"An error occurred: ```{tb}```", parse_mode=ParseMode.MARKDOWN)
AUTHORIZED_USER_IDS = [,]
def bot_logs(update: Update, context: CallbackContext) -> None:
    if not is_user_authorized(update.effective_user.id):
        update.message.reply_text("You don't have access to this bot. Please contact @TheCodingWizard.")
        return

    if not os.path.exists('logs_bot.txt'):
        update.message.reply_text("No logs found.")
        return

    with open('logs_bot.txt', 'rb') as f:
        update.message.reply_document(document=InputFile(f), filename='logs_bot.txt')
def is_user_authorized(user_id: int) -> bool:
    return user_id in AUTHORIZED_USER_IDS

def start(update: Update, context: CallbackContext) -> None:
    if not is_user_authorized(update.effective_user.id):
        update.message.reply_text("You don't have access to this bot. Please contact @TheCodingWizard.")
        return

    user = update.effective_user
    update.message.reply_text(f'Hi, {user.first_name}! Please send me any notes, I will save them.')

def sanitize_command(command: str) -> str:
    command = command.lower()
    command = re.sub(r"[^a-z0-9_]", "", command)
    return command
def send_available_commands_message(update: Update, context: CallbackContext) -> None:
    bot_commands = context.bot.get_my_commands()

    available_commands_text = "Available commands:\n\n"
    for command in bot_commands:
        available_commands_text += f"/{command.command} - {command.description}\n"

    update.message.reply_text(available_commands_text)
def send_available_commands_callback(callback_query: CallbackQuery, context: CallbackContext) -> None:
    bot_commands = context.bot.get_my_commands()

    available_commands_text = "Available commands:\n\n"
    for command in bot_commands:
        available_commands_text += f"/{command.command} - {command.description}\n"

    callback_query.message.reply_text(available_commands_text)

def backup_notes() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"notes_backup_{timestamp}.json"
    shutil.copy("notes.json", backup_file)
def save_note(update: Update, context: CallbackContext) -> None:
    if not is_user_authorized(update.effective_user.id):
        update.message.reply_text("You don't have access to this bot. Please contact @TheCodingWizard.")
        return
    text = update.message.text

    # Check if we are editing an existing note
    if "edit_note" in context.user_data and "note_command" in context.user_data:
        note_number = context.user_data["edit_note"]
        note_command = context.user_data["note_command"]

        with open("notes.json", "r") as f:
            notes = json.load(f)
        backup_notes()

        # Update the note text
        for idx, note in enumerate(notes):
            if idx == note_number and note["command"] == note_command:
                note["note"] = text
                break

        with open("notes.json", "w") as f:
            json.dump(notes, f)

        # Get the display number for the updated note
        display_number = sum(1 for note in notes[:note_number + 1] if note["command"] == note_command)

        update.message.reply_text(f"{note_command} Note {display_number} has been updated.")

        # Clear the edit_note and note_command from user_data
        del context.user_data["edit_note"]
        del context.user_data["note_command"]
        context.user_data["is_editing"] = False
        return

    # If it's not an edit and the is_editing flag is not set, continue with the original save_note code
    if not context.user_data.get("is_editing"):
        command = text.split()[0]
        if command == "/clearall":
            return
        # Extract first word from the message
        user_id = update.message.from_user.id
        username = update.message.from_user.username

        sanitized_command = sanitize_command(command)

        if not sanitized_command:
            update.message.reply_text(
                "Invalid command format. Commands should contain only lowercase English letters, digits, and underscores.")
            return

        note_data = {
            "user_id": user_id,
            "username": username,
            "command": f"/{sanitized_command}",
            "note": text
        }

        if not os.path.exists("notes.json"):
            with open("notes.json", "w") as f:
                json.dump([], f)

        with open("notes.json", "r") as f:
            notes = json.load(f)

        notes.append(note_data)

        with open("notes.json", "w") as f:
            json.dump(notes, f)

        update.message.reply_text(f"Note has been saved under {note_data['command']} command.")

        # Update the bot commands
        bot_commands = [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="logs", description="Upload logs"),
            BotCommand(command="clearall", description="Clear all notes"),
            BotCommand(command="bot_logs", description="Upload bot logs"),
        ]

        unique_commands = set()

        for note in notes:
            sanitized_command = sanitize_command(note["command"][1:])
            if sanitized_command not in unique_commands:
                bot_commands.append(
                    BotCommand(command=sanitized_command, description=f"{sanitized_command.capitalize()} Notes"))
                unique_commands.add(sanitized_command)

        context.bot.set_my_commands(bot_commands)
        send_available_commands_message(update, context)



def display_notes(update: Update, context: CallbackContext) -> None:
    if not is_user_authorized(update.effective_user.id):
        update.message.reply_text("You don't have access to this bot. Please contact @TheCodingWizard.")
        return
    command = update.message.text
    if command == "/clearall":
        return
    if command == "/bot_logs":
        bot_logs(update, context)  # Call the bot_logs function to upload the logs_bot.txt file
        return
    if not os.path.exists("notes.json"):
        update.message.reply_text("There are no notes in this chat.")
        return

    with open("notes.json", "r") as f:
        notes = json.load(f)

    response = ""
    count = 1
    keyboard = []

    for idx, note in enumerate(notes):
        if note["command"] == command:
            formatted_note = note['note'].replace('\n', '\n┃ ')
            response += f"📦 Note {count}:\n┏━━\n┃ {formatted_note}\n┗━━━━━━━━━━━━\n"
            keyboard.append([
                InlineKeyboardButton(text=f"Edit {count}", callback_data=f"edit_{idx}_{count}"),
                InlineKeyboardButton(text=f"Delete {count}", callback_data=f"delete_{idx}_{count}")
            ])
            count += 1

    if response:
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Clear previous inline keyboard if exists and if it's different from the new one
        last_displayed_message_id = context.user_data.get("last_displayed_message_id")
        if last_displayed_message_id:
            try:
                context.bot.edit_message_reply_markup(
                    chat_id=update.message.chat_id,
                    message_id=last_displayed_message_id,
                    reply_markup=None
                )
            except BadRequest:
                pass

        # Send the new message with the new inline keyboard and store its message ID
        sent_message = update.message.reply_text(response, reply_markup=reply_markup)
        context.user_data["last_displayed_message_id"] = sent_message.message_id
    else:
        update.message.reply_text("No notes found for this command.")
def should_save_note(update: Update, context: CallbackContext) -> bool:
    return "edit_note" not in context.user_data
def handle_callback(update: Update, context: CallbackContext) -> None:
    callback_query = update.callback_query
    callback_data = callback_query.data
    command, note_number, display_number = callback_data.split("_")
    note_number = int(note_number)
    display_number = int(display_number)

    # Load notes
    with open("notes.json", "r") as f:
        notes = json.load(f)

    if command == "edit":
        callback_query.edit_message_text("Please send the updated note text.")
        context.user_data["edit_note"] = note_number
        context.user_data["note_command"] = notes[note_number]["command"]
        context.user_data["is_editing"] = True
    elif command == "delete":
        # Filter notes, removing the note with the matching note_number
        notes = [note for index, note in enumerate(notes) if index != note_number]
        backup_notes()

        # Save updated notes
        with open("notes.json", "w") as f:
            json.dump(notes, f)

        callback_query.edit_message_text(f"Note {display_number} has been deleted.")

        # Update bot commands
        bot_commands = [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="logs", description="Upload logs"),
            BotCommand(command="clearall", description="Clear all notes"),
            BotCommand(command="bot_logs", description="Upload bot logs"),
        ]

        unique_commands = set()

        for note in notes:
            sanitized_command = sanitize_command(note["command"][1:])
            if sanitized_command not in unique_commands:
                bot_commands.append(
                    BotCommand(command=sanitized_command, description=f"{sanitized_command.capitalize()} Notes"))
                unique_commands.add(sanitized_command)

        context.bot.set_my_commands(bot_commands)

        # Send available commands
        send_available_commands_callback(callback_query, context)

    else:
        callback_query.answer("Unknown action.")
def upload_logs(update: Update, context: CallbackContext) -> None:
    if not is_user_authorized(update.effective_user.id):
        update.message.reply_text("You don't have access to this bot. Please contact @TheCodingWizard.")
        return
    if os.path.exists("notes.json"):
        with open("notes.json", "rb") as f:
            update.message.reply_document(document=f, filename="notes.json")
    else:
        update.message.reply_text("No logs found.")
def clear_all(update: Update, context: CallbackContext) -> None:
    if not is_user_authorized(update.effective_user.id):
        update.message.reply_text("You don't have access to this bot. Please contact @TheCodingWizard.")
        return
    keyboard = [
        [
            InlineKeyboardButton(text="Yes", callback_data="confirm_clear_all_yes"),
            InlineKeyboardButton(text="No", callback_data="confirm_clear_all_no"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Are you sure you want to clear all notes?", reply_markup=reply_markup)


def confirm_clear_all(update: Update, context: CallbackContext) -> None:
    callback_query = update.callback_query
    callback_data = callback_query.data

    if callback_data == "confirm_clear_all_yes":
        backup_notes()
        if os.path.exists("notes.json"):
            os.remove("notes.json")
            update.callback_query.answer()

            # Update the bot commands
            bot_commands = [
                BotCommand(command="start", description="Start the bot"),
                BotCommand(command="logs", description="Upload logs"),
                BotCommand(command="clearall", description="Clear all notes"),
                BotCommand(command="bot_logs", description="Upload bot logs"),
            ]
            context.bot.set_my_commands(bot_commands)

            callback_query.edit_message_text("All notes have been cleared.")
        else:
            callback_query.edit_message_text("There are no notes to clear.")
    else:
        callback_query.edit_message_text("Clear all notes has been canceled.")
def main() -> None:
    TOKEN = "Replace with your token"

    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("logs", upload_logs))
    dispatcher.add_handler(CommandHandler("clearall", clear_all))
    dispatcher.add_handler(CallbackQueryHandler(confirm_clear_all, pattern="^confirm_clear_all_"))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, save_note, pass_user_data=True, run_async=True))
    dispatcher.add_handler(MessageHandler(Filters.command, display_notes))
    dispatcher.add_handler(CallbackQueryHandler(handle_callback))
    bot_logs_handler = CommandHandler('bot_logs', bot_logs)
    dispatcher.add_handler(bot_logs_handler)
    dispatcher.add_error_handler(error_handler)
    logger.info("Bot started")

    try:
        updater.start_polling()
        updater.idle()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception("Bot stopped due to an unhandled exception")
    finally:
        logger.info("Bot exited")


if __name__ == "__main__":
    main()
