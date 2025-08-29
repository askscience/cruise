"""Database manager for notes storage."""

import sqlite3
import os
from typing import Optional, List, Tuple


class NotesDatabase:
    """Manages SQLite database for storing notes and projects."""
    
    def __init__(self, db_path: str = "data/transcriber_notes.db"):
        """Initialize database connection and create tables if needed."""
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Create projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    audio_filepath TEXT NOT NULL,
                    transcription_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create sentences table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transcription_id INTEGER NOT NULL, 
                    sentence_text TEXT NOT NULL, 
                    start_time REAL, 
                    end_time REAL, 
                    sentence_order INTEGER
                )
            """)
            # Create notes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sentence_id INTEGER NOT NULL, 
                    note_text TEXT, 
                    thinking_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                    FOREIGN KEY(sentence_id) REFERENCES sentences(id)
                )
            """)
            # Add project_id to sentences table
            try:
                cursor.execute("ALTER TABLE sentences ADD COLUMN project_id INTEGER REFERENCES projects(id)")
            except sqlite3.OperationalError:
                pass  # Column already exists

            # Add transcription_text to projects table
            try:
                cursor.execute("ALTER TABLE projects ADD COLUMN transcription_text TEXT")
            except sqlite3.OperationalError:
                pass # Column already exists

            # Add thinking_content to notes table
            try:
                cursor.execute("ALTER TABLE notes ADD COLUMN thinking_content TEXT")
            except sqlite3.OperationalError:
                pass # Column already exists

            # Create chat_history table for study mode conversations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sentence_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(sentence_id) REFERENCES sentences(id)
                )
            """)

    def create_project(self, name: str, audio_filepath: str) -> int:
        """Create a new project and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO projects (name, audio_filepath) VALUES (?, ?)", (name, audio_filepath))
            return cursor.lastrowid

    def get_all_projects(self) -> List[Tuple[int, str, str]]:
        """Get all projects. Returns list of (id, name, audio_filepath)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, audio_filepath FROM projects ORDER BY updated_at DESC")
            projects = cursor.fetchall()
            print(f"DEBUG: get_all_projects returning {len(projects)} projects: {projects}")
            return projects

    def save_transcription_and_notes(self, project_id: int, transcription_result, notes: dict):
        """Save transcription sentences and notes for a project."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Clear existing data for this project
            cursor.execute("DELETE FROM notes WHERE sentence_id IN (SELECT id FROM sentences WHERE project_id = ?)", (project_id,))
            cursor.execute("DELETE FROM sentences WHERE project_id = ?", (project_id,))

            transcription_text = ""
            segments = []
            if isinstance(transcription_result, dict):
                transcription_text = transcription_result.get('text', '')
                segments = transcription_result.get('segments', [])
            elif isinstance(transcription_result, str):
                transcription_text = transcription_result

            # Save full transcription text
            cursor.execute("UPDATE projects SET transcription_text = ? WHERE id = ?",
                           (transcription_text, project_id))

            # Save sentences
            for i, segment in enumerate(segments):
                cursor.execute("""
                    INSERT INTO sentences (project_id, transcription_id, sentence_text, start_time, end_time, sentence_order)
                    VALUES (?, 1, ?, ?, ?, ?)
                """, (project_id, segment['text'], segment['start'], segment['end'], i))
                sentence_id = cursor.lastrowid

                # Save corresponding note if it exists
                if segment['text'] in notes:
                    cursor.execute("INSERT INTO notes (sentence_id, note_text, thinking_content) VALUES (?, ?, ?)", 
                                 (sentence_id, notes[segment['text']], ''))

            # Update project timestamp
            cursor.execute("UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project_id,))

    def load_project_data(self, project_id: int) -> Tuple[Optional[str], dict, dict]:
        """Load audio filepath, transcription, and notes for a project."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Get audio filepath and full transcription text
            cursor.execute("SELECT audio_filepath, transcription_text FROM projects WHERE id = ?", (project_id,))
            project_row = cursor.fetchone()
            if not project_row:
                return None, {}, {}
            audio_filepath, transcription_text = project_row

            # Get sentences to reconstruct transcription segments
            cursor.execute("SELECT sentence_text, start_time, end_time FROM sentences WHERE project_id = ? ORDER BY sentence_order", (project_id,))
            segments = [{'text': row[0], 'start': row[1], 'end': row[2]} for row in cursor.fetchall()]
            transcription = {'text': transcription_text, 'segments': segments}

            # Get notes
            cursor.execute("""
                SELECT s.sentence_text, n.note_text
                FROM notes n
                JOIN sentences s ON n.sentence_id = s.id
                WHERE s.project_id = ?
            """, (project_id,))
            notes = {}
            for row in cursor.fetchall():
                notes[row[0]] = row[1]

            return audio_filepath, transcription, notes
    
    def save_note(self, sentence_text: str, content: str, timestamp: Optional[float] = None) -> int:
        """Save or update a note. Returns note ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # First, find or create a sentence entry
            cursor.execute("SELECT id FROM sentences WHERE sentence_text = ?", (sentence_text,))
            sentence_row = cursor.fetchone()
            
            if not sentence_row:
                # Create a new sentence entry
                cursor.execute("""
                    INSERT INTO sentences (transcription_id, sentence_text, start_time, end_time, sentence_order) 
                    VALUES (1, ?, ?, ?, 0)
                """, (sentence_text, timestamp or 0, timestamp or 0))
                sentence_id = cursor.lastrowid
            else:
                sentence_id = sentence_row[0]
            
            # Check if note with this sentence_id already exists
            cursor.execute("SELECT id FROM notes WHERE sentence_id = ?", (sentence_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing note
                cursor.execute("""
                    UPDATE notes 
                    SET note_text = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (content, existing[0]))
                return existing[0]
            else:
                # Create new note
                cursor.execute("""
                    INSERT INTO notes (sentence_id, note_text, thinking_content) 
                    VALUES (?, ?, '')
                """, (sentence_id, content))
                return cursor.lastrowid
    
    def get_note(self, sentence_text: str) -> Optional[Tuple[int, str, str, float]]:
        """Get note by sentence text. Returns (id, sentence_text, content, timestamp) or None."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT n.id, s.sentence_text, n.note_text, s.start_time 
                FROM notes n
                JOIN sentences s ON n.sentence_id = s.id
                WHERE s.sentence_text = ?
            """, (sentence_text,))
            return cursor.fetchone()
    
    def get_all_notes(self) -> List[Tuple[int, str, str, float]]:
        """Get all notes. Returns list of (id, sentence_text, content, timestamp)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT n.id, s.sentence_text, n.note_text, s.start_time 
                FROM notes n
                JOIN sentences s ON n.sentence_id = s.id
                ORDER BY n.updated_at DESC
            """)
            return cursor.fetchall()
    
    def delete_note(self, note_id: int) -> bool:
        """Delete a note by ID. Returns True if successful."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            return cursor.rowcount > 0

    def delete_project(self, project_id: int) -> bool:
        """Delete a project and all associated data. Returns True if successful."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First check if project exists
                cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
                if not cursor.fetchone():
                    print(f"Project with ID {project_id} not found")
                    return False
                
                # Delete in order to respect foreign key constraints
                # 1. Delete chat history for sentences in this project
                cursor.execute("""
                    DELETE FROM chat_history 
                    WHERE sentence_id IN (
                        SELECT id FROM sentences WHERE project_id = ?
                    )
                """, (project_id,))
                chat_deleted = cursor.rowcount
                print(f"Deleted {chat_deleted} chat history entries")
                
                # 2. Delete notes for sentences in this project
                cursor.execute("""
                    DELETE FROM notes 
                    WHERE sentence_id IN (
                        SELECT id FROM sentences WHERE project_id = ?
                    )
                """, (project_id,))
                notes_deleted = cursor.rowcount
                print(f"Deleted {notes_deleted} notes")
                
                # 3. Delete sentences for this project
                cursor.execute("DELETE FROM sentences WHERE project_id = ?", (project_id,))
                sentences_deleted = cursor.rowcount
                print(f"Deleted {sentences_deleted} sentences")
                
                # 4. Finally delete the project itself
                cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                project_deleted = cursor.rowcount
                print(f"Deleted project: {project_deleted > 0}")
                
                # Commit the transaction
                conn.commit()
                
                return project_deleted > 0
                
        except Exception as e:
            print(f"Error deleting project {project_id}: {e}")
            return False

    def save_chat_message(self, sentence_text: str, role: str, content: str) -> int:
        """Save a chat message for a sentence. Returns message ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # First, find or create a sentence entry
            cursor.execute("SELECT id FROM sentences WHERE sentence_text = ?", (sentence_text,))
            sentence_row = cursor.fetchone()
            
            if not sentence_row:
                # Create a new sentence entry
                cursor.execute("""
                    INSERT INTO sentences (transcription_id, sentence_text, start_time, end_time, sentence_order) 
                    VALUES (1, ?, 0, 0, 0)
                """, (sentence_text,))
                sentence_id = cursor.lastrowid
            else:
                sentence_id = sentence_row[0]
            
            # Save the chat message
            cursor.execute("""
                INSERT INTO chat_history (sentence_id, role, content) 
                VALUES (?, ?, ?)
            """, (sentence_id, role, content))
            return cursor.lastrowid

    def get_chat_history(self, sentence_text: str) -> List[Tuple[str, str]]:
        """Get chat history for a sentence. Returns list of (role, content) tuples."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ch.role, ch.content
                FROM chat_history ch
                JOIN sentences s ON ch.sentence_id = s.id
                WHERE s.sentence_text = ?
                ORDER BY ch.created_at ASC
            """, (sentence_text,))
            return cursor.fetchall()

    def clear_chat_history(self, sentence_text: str) -> bool:
        """Clear chat history for a sentence. Returns True if successful."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM chat_history 
                WHERE sentence_id IN (
                    SELECT id FROM sentences WHERE sentence_text = ?
                )
            """, (sentence_text,))
            return cursor.rowcount > 0