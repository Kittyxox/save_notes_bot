import json
import os
import re
from telegram import BotCommand
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    update.message.reply_text(f'Hi, {user.first_name}! Please send me any notes, I will save them.')

def sanitize_command(command: str) -> str:
    command = command.lower()
    command = re.sub(r"[^a-z0-9_]", "", command)
    return command
def save_note(update: Update, context: CallbackContext) -> None:
    text = update.message.text

    # Check if we are editing an existing note
    if "edit_note" in context.user_data and "note_command" in context.user_data:
        note_number = context.user_data["edit_note"]
        note_command = context.user_data["note_command"]

        with open("notes.json", "r") as f:
            notes = json.load(f)

        # Update the note text
        for idx, note in enumerate(notes):
            if idx == note_number and note["command"] == note_command:
                note["note"] = text
                break

        with open("notes.json", "w") as f:
            json.dump(notes, f)

        update.message.reply_text(f"Note {note_number + 1} has been updated.")

        # Clear the edit_note and note_command from user_data
        del context.user_data["edit_note"]
        del context.user_data["note_command"]

        return

    # If it's not an edit, continue with the original save_note code
    command = text.split()[0]  # Extract first word from the message
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
    ]

    unique_commands = set()

    for note in notes:
        sanitized_command = sanitize_command(note["command"][1:])
        if sanitized_command not in unique_commands:
            bot_commands.append(
                BotCommand(command=sanitized_command, description=f"{sanitized_command.capitalize()} Notes"))
            unique_commands.add(sanitized_command)

    context.bot.set_my_commands(bot_commands)

def display_notes(update: Update, context: CallbackContext) -> None:
    command = update.message.text

    with open("notes.json", "r") as f:
        notes = json.load(f)

    response = ""
    count = 1
    keyboard = []

    for idx, note in enumerate(notes):
        if note["command"] == command:
            response += f"{count}) Note {count} {command[1:]}\n{note['note']}\n\n"
            keyboard.append([
                InlineKeyboardButton(text=f"Edit {count}", callback_data=f"edit_{idx}"),
                InlineKeyboardButton(text=f"Delete {count}", callback_data=f"delete_{idx}")
            ])
            count += 1

    if response:
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(response, reply_markup=reply_markup)
    else:
        update.message.reply_text("No notes found for this command.")
def handle_callback(update: Update, context: CallbackContext) -> None:
    callback_query = update.callback_query
    callback_data = callback_query.data
    command, note_number = callback_data.split("_")
    note_number = int(note_number)

    # Load notes
    with open("notes.json", "r") as f:
        notes = json.load(f)

    # Remove the unnecessary code that calculates note_command and note_number
    # (code removed)

    if command == "edit":
        callback_query.answer("Please send the updated note text.")
        context.user_data["edit_note"] = note_number
        context.user_data["note_command"] = notes[note_number]["command"]
    elif command == "delete":
        # Filter notes, removing the note with the matching note_number
        notes = [note for index, note in enumerate(notes) if index != note_number]

        # Save updated notes
        with open("notes.json", "w") as f:
            json.dump(notes, f)

        callback_query.answer(f"Note {note_number + 1} has been deleted.")
    else:
        callback_query.answer("Unknown action.")
def upload_logs(update: Update, context: CallbackContext) -> None:
    if os.path.exists("notes.json"):
        with open("notes.json", "rb") as f:
            update.message.reply_document(document=f, filename="notes.json")
    else:
        update.message.reply_text("No logs found.")
def main() -> None:
    TOKEN = "6187304624:AAG3of6VEyzi3AeyDbmzFiCom9wRfZPs7OA"

    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("logs", upload_logs))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, save_note))
    dispatcher.add_handler(MessageHandler(Filters.command, display_notes))
    dispatcher.add_handler(CallbackQueryHandler(handle_callback))

    updater.start_polling()

    updater.idle()
if __name__ == "__main__":
    main()