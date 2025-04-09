import os
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import logging
from threading import Thread
from database import TaskDB

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Flask app for health check
app = Flask(__name__)

# Initialize database
task_db = TaskDB()

# Track active users for notifications
active_users = set()

# Constants
PRIORITIES = ['High', 'Medium', 'Low']

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

async def notify_all_users(context: ContextTypes.DEFAULT_TYPE, message: str, exclude_user_id: str = None):
    """Notify all active users except the excluded one"""
    for user_id in active_users:
        if user_id != exclude_user_id:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")

# Telegram Bot Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    active_users.add(user_id)
    
    help_text = """
    📝 *Shared Task Manager Bot* 📝
    
    *All users see and manage the same task list*
    
    *Commands:*
    /start - Show this message
    /add - Add a new task (notifies everyone)
    /list - Show all tasks
    /edit - Edit a task
    /delete - Delete a task
    /help - Show help
    
    Tasks can have High, Medium, or Low priority.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    📝 *Available Commands* 📝
    
    */add* - Add a new shared task (notifies all users)
    */list* - Show all tasks
    */edit* - Edit an existing task
    */delete* - Remove a task
    */help* - Show this help message
    
    All changes are visible to everyone immediately!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['awaiting_task'] = True
    await update.message.reply_text("Please enter the task description (visible to all users):")

async def receive_task_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'awaiting_task' in context.user_data:
        context.user_data['task_description'] = update.message.text
        context.user_data['awaiting_task'] = False
        context.user_data['awaiting_priority'] = True
        
        keyboard = [
            [InlineKeyboardButton("High 🔴", callback_data='priority_High')],
            [InlineKeyboardButton("Medium 🟡", callback_data='priority_Medium')],
            [InlineKeyboardButton("Low 🟢", callback_data='priority_Low')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Please select the task priority:",
            reply_markup=reply_markup
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data
    
    if data.startswith('priority_'):
        priority = data.split('_')[1]
        if 'task_description' in context.user_data:
            description = context.user_data['task_description']
            creator_name = update.effective_user.full_name
            
            if task_db.add_task(description, priority, creator_name):
                # Notify all users about the new task
                notification = (
                    f"📢 New shared task added by {creator_name}:\n\n"
                    f"*{description}*\n"
                    f"Priority: {priority}"
                )
                await notify_all_users(
                    context,
                    notification,
                    exclude_user_id=user_id
                )
                
                await query.edit_message_text(
                    f"✅ Task added with {priority} priority!\n"
                    f"All users have been notified."
                )
            else:
                await query.edit_message_text("⚠️ Failed to add task. Please try again.")
            
            # Clean up context
            if 'task_description' in context.user_data:
                del context.user_data['task_description']
            if 'awaiting_priority' in context.user_data:
                del context.user_data['awaiting_priority']
    
    elif data.startswith('delete_'):
        task_id = int(data.split('_')[1])
        task = task_db.get_task(task_id)
        
        if task:
            if task_db.delete_task(task_id):
                await query.edit_message_text(f"🗑 Task deleted: {task['description']}")
                
                # Notify about deletion
                notification = (
                    f"🗑 Task deleted by {update.effective_user.full_name}:\n\n"
                    f"*{task['description']}*"
                )
                await notify_all_users(context, notification, exclude_user_id=user_id)
            else:
                await query.edit_message_text("⚠️ Failed to delete task. Please try again.")
        else:
            await query.edit_message_text("⚠️ Task not found!")
    
    elif data.startswith('edit_'):
        parts = data.split('_')
        task_id = int(parts[1])
        action = parts[2]
        task = task_db.get_task(task_id)
        
        if not task:
            await query.edit_message_text("⚠️ Task not found!")
            return
        
        if action == 'select':
            keyboard = [
                [
                    InlineKeyboardButton("Edit Description", callback_data=f'edit_{task_id}_description'),
                    InlineKeyboardButton("Edit Priority", callback_data=f'edit_{task_id}_priority')
                ],
                [InlineKeyboardButton("Cancel", callback_data=f'edit_{task_id}_cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"What would you like to edit for this task?\n\n"
                f"Current: *{task['description']}* ({task['priority']} priority)",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif action == 'description':
            context.user_data['editing_task'] = task_id
            context.user_data['editing_field'] = 'description'
            await query.edit_message_text("Please send the new task description:")
        
        elif action == 'priority':
            keyboard = [
                [InlineKeyboardButton("High 🔴", callback_data=f'edit_{task_id}_setpriority_High')],
                [InlineKeyboardButton("Medium 🟡", callback_data=f'edit_{task_id}_setpriority_Medium')],
                [InlineKeyboardButton("Low 🟢", callback_data=f'edit_{task_id}_setpriority_Low')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "Select the new priority:",
                reply_markup=reply_markup
            )
        
        elif action.startswith('setpriority'):
            new_priority = action.split('_')[1]
            if task_db.update_task_priority(task_id, new_priority):
                await query.edit_message_text(f"✅ Priority updated to {new_priority}!")
                
                # Notify about the change
                notification = (
                    f"✏️ Task updated by {update.effective_user.full_name}:\n\n"
                    f"*{task['description']}*\n"
                    f"New priority: {new_priority}"
                )
                await notify_all_users(context, notification, exclude_user_id=user_id)
            else:
                await query.edit_message_text("⚠️ Failed to update priority. Please try again.")
            
            # Clean up context
            if 'editing_task' in context.user_data:
                del context.user_data['editing_task']
            if 'editing_field' in context.user_data:
                del context.user_data['editing_field']
        
        elif action == 'cancel':
            await query.edit_message_text("Edit operation cancelled.")
            if 'editing_task' in context.user_data:
                del context.user_data['editing_task']
            if 'editing_field' in context.user_data:
                del context.user_data['editing_field']

async def receive_edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'editing_task' in context.user_data and 'editing_field' in context.user_data:
        task_id = context.user_data['editing_task']
        new_description = update.message.text
        task = task_db.get_task(task_id)
        
        if task and context.user_data['editing_field'] == 'description':
            if task_db.update_task_description(task_id, new_description):
                await update.message.reply_text("✅ Task description updated!")
                
                # Notify about the change
                notification = (
                    f"✏️ Task updated by {update.effective_user.full_name}:\n\n"
                    f"Old: {task['description']}\n"
                    f"New: *{new_description}*"
                )
                await notify_all_users(context, notification, exclude_user_id=str(update.effective_user.id))
            else:
                await update.message.reply_text("⚠️ Failed to update description. Please try again.")
            
            # Clean up context
            del context.user_data['editing_task']
            del context.user_data['editing_field']

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = task_db.get_all_tasks()
    
    if not tasks:
        await update.message.reply_text("No tasks yet! Use /add to create the first one.")
        return
    
    message = "📋 *Shared Task List* 📋\n\n"
    for task in tasks:
        priority_icon = '🔴' if task['priority'] == 'High' else '🟡' if task['priority'] == 'Medium' else '🟢'
        creator = f" (by {task['created_by']})" if task['created_by'] else ""
        message += f"{task['id']}. {priority_icon} *{task['description']}*{creator}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def edit_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = task_db.get_all_tasks()
    
    if not tasks:
        await update.message.reply_text("No tasks to edit yet! Use /add to create one.")
        return
    
    keyboard = []
    for task in tasks:
        keyboard.append([
            InlineKeyboardButton(
                f"{task['id']}. {task['description'][:20]}... ({task['priority']})",
                callback_data=f'edit_{task["id"]}_select'
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Select a task to edit:",
        reply_markup=reply_markup
    )

async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = task_db.get_all_tasks()
    
    if not tasks:
        await update.message.reply_text("No tasks to delete yet! Use /add to create one.")
        return
    
    keyboard = []
    for task in tasks:
        keyboard.append([
            InlineKeyboardButton(
                f"{task['id']}. {task['description'][:20]}...",
                callback_data=f'delete_{task["id"]}'
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Select a task to delete:",
        reply_markup=reply_markup
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and update.message:
        await update.message.reply_text('An error occurred. Please try again.')

def setup_bot():
    # Get Telegram bot token from environment variable
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
    
    # Create Application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('add', add_task))
    application.add_handler(CommandHandler('list', list_tasks))
    application.add_handler(CommandHandler('edit', edit_task))
    application.add_handler(CommandHandler('delete', delete_task))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_task_description))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_edit_description))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.add_error_handler(error_handler)
    
    return application

def run_flask():
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    # Start Flask server in a separate thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Start Telegram bot
    application = setup_bot()
    application.run_polling()
