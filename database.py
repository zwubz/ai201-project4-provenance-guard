import sqlite3
import os
from datetime import datetime

DATABASE_FILE = "provenance_guard.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initializes the database and creates the submissions table matching the target schema.
    Includes columns for individual heuristic scores (slv_score, ttr_score).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            content_id TEXT PRIMARY KEY,
            creator_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            text TEXT NOT NULL,
            attribution TEXT NOT NULL,
            confidence REAL NOT NULL,
            llm_score REAL NOT NULL,
            slv_score REAL NOT NULL,
            ttr_score REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'classified',
            appeal_reasoning TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def insert_submission(content_id, creator_id, text, attribution, confidence, llm_score, slv_score, ttr_score):
    """
    Inserts a new content submission evaluation record.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    timestamp = datetime.utcnow().isoformat()[:-3] + "Z"
    
    cursor.execute("""
        INSERT INTO submissions (
            content_id, creator_id, timestamp, text, attribution, 
            confidence, llm_score, slv_score, ttr_score, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'classified')
    """, (content_id, creator_id, timestamp, text, attribution, confidence, llm_score, slv_score, ttr_score))
    
    conn.commit()
    conn.close()

def get_all_submissions():
    """
    Retrieves all audit log entries, returning keys matching the target schema.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT content_id, creator_id, timestamp, text, attribution, 
               confidence, llm_score, slv_score, ttr_score, status, appeal_reasoning 
        FROM submissions 
        ORDER BY timestamp DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    entries = []
    for row in rows:
        entries.append({
            "content_id": row["content_id"],
            "creator_id": row["creator_id"],
            "timestamp": row["timestamp"],
            "text": row["text"],
            "attribution": row["attribution"],
            "confidence": row["confidence"],
            "llm_score": row["llm_score"],
            "slv_score": row["slv_score"],
            "ttr_score": row["ttr_score"],
            "status": row["status"],
            "appeal_reasoning": row["appeal_reasoning"]
        })
        
    return entries

def register_appeal(content_id: str, creator_reasoning: str) -> bool:
    """
    Updates the submission's status to 'under_review' and saves the appeal reasoning.
    Returns True if an entry was updated, False if the content_id was not found.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE submissions 
        SET status = 'under_review', appeal_reasoning = ? 
        WHERE content_id = ?
    """, (creator_reasoning, content_id))
    
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    return rows_affected > 0

if __name__ == "__main__":
    init_db()
