import sqlite3
import logging
from typing import List, Dict, Optional

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
        return sqlite3.connect(self.db_name)

    def add_task(self, description: str, priority: str, created_by: str) -> bool:
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

    # ... (keep other methods but remove user_id filters)
