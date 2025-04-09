import os
from flask import Flask, request, jsonify
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    Updater,
    Dispatcher,
    CallbackContext
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

# Constants
PRIORITIES = ['High', 'Medium', 'Low']

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

# Telegram Bot Commands
def start(update: Update, context: CallbackContext):
    help_text = """
    📝 *Task Manager Bot* 📝
    
    *Commands:*
    /start - Show this message
    /add - Add a new task
    /list - Show all your tasks
    /edit - Edit a task
    /delete - Delete a task
    /help - Show help
    
    Manage your tasks easily with priorities!
    """
    update.message.reply_text(help_text, parse_mode='Markdown')

def help_command(update: Update, context: CallbackContext):
    help_text = """
    📝 *Available Commands* 📝
    
    */add* - Add a new task with priority
    */list* - Show all your tasks
    */edit* - Edit an existing task
    */delete* - Remove a task
    */help* - Show this help message
    
    Tasks can have High, Medium, or Low priority.
    """
    update.message.reply_text(help_text, parse_mode='Markdown')

def add_task(update: Update, context: CallbackContext):
    context.user_data['awaiting_task'] = True
    update.message.reply_text("Please enter the task description:")

def receive_task_description(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if 'awaiting_task' in context.user_data:
        context.user_data['task_description'] = update.message.text
        context.user_data['awaiting_task'] = False
        context.user_data['awaiting_priority'] = True
        
        keyboard = [
            [InlineKeyboardButton("High", callback_data='priority_High')],
            [InlineKeyboardButton("Medium", callback_data='priority_Medium')],
            [InlineKeyboardButton("Low", callback_data='priority_Low')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "Please select the task priority:",
            reply_markup=reply_markup
        )

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data
    
    if data.startswith('priority_'):
        priority = data.split('_')[1]
        if 'task_description' in context.user_data:
            description = context.user_data['task_description']
            if task_db.add_task(user_id, description, priority):
                del context.user_data['task_description']
                del context.user_data['awaiting_priority']
                query.edit_message_text(f"✅ Task added with {priority} priority!")
            else:
                query.edit_message_text("⚠️ Failed to add task. Please try again.")
    
    elif data.startswith('delete_'):
        task_id = int(data.split('_')[1])
        task = task_db.get_task(task_id)
        if task and task['user_id'] == user_id:
            if task_db.delete_task(task_id):
                query.edit_message_text(f"🗑 Task deleted: {task['description']}")
            else:
                query.edit_message_text("⚠️ Failed to delete task. Please try again.")
        else:
            query.edit_message_text("⚠️ Invalid task selection!")
    
    elif data.startswith('edit_'):
        parts = data.split('_')
        task_id = int(parts[1])
        action = parts[2]
        task = task_db.get_task(task_id)
        
        if not task or task['user_id'] != user_id:
            query.edit_message_text("⚠️ Invalid task selection!")
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
            query.edit_message_text(
                f"What would you like to edit for task:\n{task['description']}?",
                reply_markup=reply_markup
            )
        
        elif action == 'description':
            context.user_data['editing_task'] = task_id
            context.user_data['editing_field'] = 'description'
            query.edit_message_text("Please send the new task description:")
        
        elif action == 'priority':
            keyboard = [
                [InlineKeyboardButton("High", callback_data=f'edit_{task_id}_setpriority_High')],
                [InlineKeyboardButton("Medium", callback_data=f'edit_{task_id}_setpriority_Medium')],
                [InlineKeyboardButton("Low", callback_data=f'edit_{task_id}_setpriority_Low')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            query.edit_message_text(
                "Select the new priority:",
                reply_markup=reply_markup
            )
        
        elif action.startswith('setpriority'):
            new_priority = action.split('_')[1]
            if task_db.update_task_priority(task_id, new_priority):
                query.edit_message_text(f"✅ Priority updated to {new_priority}!")
            else:
                query.edit_message_text("⚠️ Failed to update priority. Please try again.")
            
            if 'editing_task' in context.user_data:
                del context.user_data['editing_task']
            if 'editing_field' in context.user_data:
                del context.user_data['editing_field']
        
        elif action == 'cancel':
            query.edit_message_text("Edit operation cancelled.")
            if 'editing_task' in context.user_data:
                del context.user_data['editing_task']
            if 'editing_field' in context.user_data:
                del context.user_data['editing_field']

def receive_edit_description(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if 'editing_task' in context.user_data and 'editing_field' in context.user_data:
        task_id = context.user_data['editing_task']
        task = task_db.get_task(task_id)
        
        if task and task['user_id'] == user_id and context.user_data['editing_field'] == 'description':
            new_description = update.message.text
            if task_db.update_task_description(task_id, new_description):
                update.message.reply_text("✅ Task description updated!")
            else:
                update.message.reply_text("⚠️ Failed to update description. Please try again.")
            
            del context.user_data['editing_task']
            del context.user_data['editing_field']

def list_tasks(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    tasks = task_db.get_tasks(user_id)
    
    if not tasks:
        update.message.reply_text("You don't have any tasks yet!")
        return
    
    message = "📋 *Your Tasks* 📋\n\n"
    for task in tasks:
        priority_icon = ''
        if task['priority'] == 'High':
            priority_icon = '🔴'
        elif task['priority'] == 'Medium':
            priority_icon = '🟡'
        else:
            priority_icon = '🟢'
        
        message += f"{task['id']}. {priority_icon} {task['description']} ({task['priority']} priority)\n"
    
    update.message.reply_text(message, parse_mode='Markdown')

def edit_task(update: Update, context: CallbackContext):
    user
