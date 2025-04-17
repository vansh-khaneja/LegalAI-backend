"""
Database utilities for the Legal AI application.

This module provides functions to interact with the PostgreSQL database,
including initialization, data insertion, retrieval, and cleanup operations.
"""

import json
import logging
import psycopg2
from typing import Dict, Any, Optional, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass


def execute_query(db_url: str, query: str, params: Optional[Tuple] = None, 
                 fetch_one: bool = False, fetch_all: bool = False) -> Any:
    """
    Execute a database query with proper connection handling and error management.
    
    Args:
        db_url: Database connection URL
        query: SQL query to execute
        params: Query parameters (optional)
        fetch_one: Whether to fetch one result
        fetch_all: Whether to fetch all results
        
    Returns:
        Query results if fetch_one or fetch_all is True, None otherwise
        
    Raises:
        DatabaseError: If any database operation fails
    """
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        cursor.execute(query, params or ())
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
            
        conn.commit()
        return None
        
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        error_msg = f"Database error: {e}"
        logger.error(error_msg)
        raise DatabaseError(error_msg)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def init_database(db_url: str) -> None:
    """
    Initialize the database by creating the necessary tables if they don't exist.
    
    Args:
        db_url: Database connection URL
    
    Raises:
        DatabaseError: If table creation fails
    """
    try:
        create_table_query = """
            CREATE TABLE IF NOT EXISTS legalAi (
                file_id INTEGER PRIMARY KEY,
                file_url TEXT NOT NULL,
                file_summary TEXT NOT NULL,
                case_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        execute_query(db_url, create_table_query)
        logger.info("Database initialized successfully. Tables created if they didn't exist.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise DatabaseError(f"Database initialization failed: {e}")


def add_entry(db_url: str, file_id: int, file_url: str, 
             file_summary: str, case_type: str) -> None:
    """
    Insert a new entry into the legalAi table.
    
    Args:
        db_url: Database connection URL
        file_id: Unique identifier for the file
        file_url: URL where the file is stored
        file_summary: Summary of the file content
        case_type: Type of legal case
    
    Raises:
        DatabaseError: If insertion fails
    """
    try:
        # First check if the entry already exists to avoid duplicate key errors
        check_query = "SELECT 1 FROM legalAi WHERE file_id = %s"
        result = execute_query(db_url, check_query, (file_id,), fetch_one=True)
        
        if result:
            # Update existing entry
            update_query = """
                UPDATE legalAi
                SET file_url = %s, file_summary = %s, case_type = %s
                WHERE file_id = %s
            """
            execute_query(db_url, update_query, (file_url, file_summary, case_type, file_id))
            logger.info(f"Updated existing entry in legalAi table with file_id: {file_id}")
        else:
            # Insert new entry
            insert_query = """
                INSERT INTO legalAi (file_id, file_url, file_summary, case_type)
                VALUES (%s, %s, %s, %s)
            """
            execute_query(db_url, insert_query, (file_id, file_url, file_summary, case_type))
            logger.info(f"New entry added to the legalAi table with file_id: {file_id}")
            
    except Exception as e:
        logger.error(f"Failed to add entry: {e}")
        raise DatabaseError(f"Error adding entry: {e}")


def get_data_by_file_id(db_url: str, file_id: int) -> str:
    """
    Retrieve data from the legalAi table for a specific file_id.
    
    Args:
        db_url: Database connection URL
        file_id: Unique identifier for the file to retrieve
    
    Returns:
        JSON string containing the file data or error message
    """
    try:
        select_query = """
            SELECT file_id, file_url, file_summary, case_type
            FROM legalAi
            WHERE file_id = %s
        """
        result = execute_query(db_url, select_query, (file_id,), fetch_one=True)
        
        if result:
            # Log the actual values for debugging
            logger.info(f"Retrieved from database - file_id: {result[0]}, file_url: {result[1]}, file_summary: {result[2]}, case_type: {result[3]}")
            
            data = {
                "file_id": result[0],
                "file_url": result[1],
                "file_summary": result[2],
                "case_type": result[3]
            }
            return json.dumps(data)
        else:
            # Create default/fallback data
            logger.warning(f"No data found for file_id {file_id}, returning default values")
            fallback_data = {
                "file_id": file_id,
                "file_url": "https://placeholder.com/document.pdf",
                "file_summary": "Document summary not available",
                "case_type": "unknown"
            }
            return json.dumps(fallback_data)
    except Exception as e:
        logger.error(f"Error retrieving data for file_id {file_id}: {e}")
        # Return a valid JSON with error information
        error_data = {
            "file_id": file_id,
            "file_url": "https://placeholder.com/error.pdf",
            "file_summary": f"Error retrieving data: {str(e)}",
            "case_type": "error"
        }
        return json.dumps(error_data)


def clear_database(db_url: str) -> None:
    """
    Clear the database by dropping the legalAi table.
    
    Args:
        db_url: Database connection URL
    
    Raises:
        DatabaseError: If table deletion fails
    """
    try:
        drop_table_query = "DROP TABLE IF EXISTS legalAi"
        execute_query(db_url, drop_table_query)
        logger.info("Database cleared. Table dropped if it existed.")
    except Exception as e:
        logger.error(f"Failed to clear database: {e}")
        raise DatabaseError(f"Error clearing database: {e}")


def get_all_entries(db_url: str) -> str:
    """
    Retrieve all entries from the legalAi table.
    
    Args:
        db_url: Database connection URL
    
    Returns:
        JSON string containing all file data or error message
    """
    try:
        select_query = """
            SELECT file_id, file_url, file_summary, case_type
            FROM legalAi
            ORDER BY file_id DESC
        """
        results = execute_query(db_url, select_query, fetch_all=True)
        
        if results:
            data_list = []
            for result in results:
                data = {
                    "file_id": result[0],
                    "file_url": result[1],
                    "file_summary": result[2],
                    "case_type": result[3]
                }
                data_list.append(data)
            return json.dumps({"entries": data_list})
        else:
            return json.dumps({"entries": []})
    except Exception as e:
        logger.error(f"Error retrieving all entries: {e}")
        return json.dumps({"error": f"An error occurred: {e}"})


def update_entry(db_url: str, file_id: int, 
                updates: Dict[str, Any]) -> str:
    """
    Update an existing entry in the legalAi table.
    
    Args:
        db_url: Database connection URL
        file_id: Unique identifier for the file to update
        updates: Dictionary containing fields to update
    
    Returns:
        JSON string with success message or error
    """
    try:
        # Build dynamic update query based on provided fields
        update_fields = []
        update_values = []
        
        for key, value in updates.items():
            if key in ['file_url', 'file_summary', 'case_type']:
                update_fields.append(f"{key} = %s")
                update_values.append(value)
        
        if not update_fields:
            return json.dumps({"error": "No valid fields to update"})
        
        update_query = f"""
            UPDATE legalAi 
            SET {', '.join(update_fields)}
            WHERE file_id = %s
        """
        update_values.append(file_id)
        
        execute_query(db_url, update_query, tuple(update_values))
        return json.dumps({"success": f"Entry with file_id {file_id} updated successfully"})
    except Exception as e:
        logger.error(f"Error updating entry with file_id {file_id}: {e}")
        return json.dumps({"error": f"An error occurred: {e}"})


def delete_entry(db_url: str, file_id: int) -> str:
    """
    Delete an entry from the legalAi table.
    
    Args:
        db_url: Database connection URL
        file_id: Unique identifier for the file to delete
    
    Returns:
        JSON string with success message or error
    """
    try:
        delete_query = "DELETE FROM legalAi WHERE file_id = %s"
        execute_query(db_url, delete_query, (file_id,))
        return json.dumps({"success": f"Entry with file_id {file_id} deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting entry with file_id {file_id}: {e}")
        return json.dumps({"error": f"An error occurred: {e}"})


# For backwards compatibility
InitDatabase = init_database
AddEntry = add_entry
GetDataByFileId = get_data_by_file_id
ClearDataBase = clear_database