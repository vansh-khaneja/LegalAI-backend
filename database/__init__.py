"""
Database package for the Legal AI application.

This package provides database connectivity and operations.
"""

from database.db_utils import (
    init_database,
    add_entry,
    get_data_by_file_id,
    get_all_entries,
    update_entry,
    delete_entry,
    clear_database,
    create_default_user,
    update_user_fields,
    get_user,
    append_to_context_history_queue,
    # Legacy names for backward compatibility
    InitDatabase,
    AddEntry,
    GetDataByFileId,
    ClearDataBase
)

__all__ = [
    'init_database',
    'add_entry',
    'get_data_by_file_id',
    'get_all_entries',
    'update_entry',
    'delete_entry',
    'clear_database',
    'create_default_user',
    'update_user_fields',
    'get_user',
    'append_to_context_history_queue',
    # Legacy names
    'InitDatabase',
    'AddEntry',
    'GetDataByFileId',
    'ClearDataBase'
]