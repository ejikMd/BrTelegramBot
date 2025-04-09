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
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def _get_connection(self):
        """Get a new database connection"""
        return sqlite3.connect(self.db_name)

    def add_task(self, description: str, priority: str, created_by: str) -> bool:
        """Add a new shared task"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    'INSERT INTO tasks (description, priority, created_by) VALUES (?, ?, ?)',
                    (description, priority, created_by)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            return False

    def get_all_tasks(self) -> List[Dict]:
        """Get all tasks for all users"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    'SELECT id, description, priority, created_by FROM tasks ORDER BY priority DESC, created_at'
                )
                return [{
                    'id': row[0],
                    'description': row[1],
                    'priority': row[2],
                    'created_by': row[3]
                } for row in cursor.fetchall()]
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
                    'SELECT id, description, priority, created_by FROM tasks WHERE id = ?',
                    (task_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'description': row[1],
                        'priority': row[2],
                        'created_by': row[3]
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None
