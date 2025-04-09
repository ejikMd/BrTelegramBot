import sqlite3
import logging
from typing import List, Dict, Optional

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TaskDB:
    def __init__(self, db_name: str = 'tasks.db'):
        self.db_name = db_name
        self._init_db()

    def _init_db(self):
        """Initialize the database with required tables"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def _get_connection(self):
        """Get a new database connection"""
        return sqlite3.connect(self.db_name)

    def add_task(self, user_id: str, description: str, priority: str) -> bool:
        """Add a new task for a user"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    'INSERT INTO tasks (user_id, description, priority) VALUES (?, ?, ?)',
                    (user_id, description, priority)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            return False

    def get_tasks(self, user_id: str) -> List[Dict]:
        """Get all tasks for a user"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'SELECT id, description, priority FROM tasks WHERE user_id = ? ORDER BY priority DESC, created_at',
                    (user_id,)
                )
                tasks = []
                for row in cursor.fetchall():
                    tasks.append({
                        'id': row[0],
                        'description': row[1],
                        'priority': row[2]
                    })
                return tasks
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            return []

    def update_task_description(self, task_id: int, new_description: str) -> bool:
        """Update a task's description"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    'UPDATE tasks SET description = ? WHERE id = ?',
                    (new_description, task_id)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating task description: {e}")
            return False

    def update_task_priority(self, task_id: int, new_priority: str) -> bool:
        """Update a task's priority"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    'UPDATE tasks SET priority = ? WHERE id = ?',
                    (new_priority, task_id)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating task priority: {e}")
            return False

    def delete_task(self, task_id: int) -> bool:
        """Delete a task"""
        try:
            with self._get_connection() as conn:
                conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False

    def get_task(self, task_id: int) -> Optional[Dict]:
        """Get a single task by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'SELECT id, user_id, description, priority FROM tasks WHERE id = ?',
                    (task_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'user_id': row[1],
                        'description': row[2],
                        'priority': row[3]
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None
