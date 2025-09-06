#!/usr/bin/env python3
"""
JSONL Log Loader for Agentic Storage

This module provides a best-effort loader to import existing JSONL logs
into the new SQLModel agentic storage schema. 

Usage:
    python -m orchestrator.jsonl_loader logs/app-20250903.jsonl
"""

import json
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Any

from orchestrator.storage.db import get_session, init_db
from orchestrator.storage.models import Run, AgentSpan, Message, ToolCall, ToolResult
from orchestrator.storage.services import save_blob


def parse_jsonl_file(file_path: Path) -> list[dict]:
    """Parse a JSONL file and return a list of log entries."""
    entries = []
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON on line {line_num}: {e}", file=sys.stderr)
                continue
    return entries


def extract_run_ids(entries: list[dict]) -> Set[str]:
    """Extract unique run IDs from log entries."""
    run_ids = set()
    
    for entry in entries:
        message = entry.get('message', '')
        
        # Look for run_id in the message using regex
        run_id_match = re.search(r'run_id=([a-f0-9-]+)', message)
        if run_id_match:
            run_ids.add(run_id_match.group(1))
            continue
            
        # Look for "starting run_chat_tools" messages 
        start_match = re.search(r'starting run_chat_tools.*run_id=([a-f0-9-]+)', message)
        if start_match:
            run_ids.add(start_match.group(1))
            continue
    
    return run_ids


def create_run_from_logs(run_id: str, entries: list[dict]) -> dict:
    """Create run metadata from log entries."""
    run_entries = [e for e in entries if run_id in e.get('message', '')]
    
    if not run_entries:
        return {}
    
    # Get the first and last timestamps for this run
    start_time = min(datetime.fromisoformat(e['ts']) for e in run_entries)
    end_time = max(datetime.fromisoformat(e['ts']) for e in run_entries)
    
    # Try to extract project_id and objective
    project_id = None
    objective = "Unknown objective"
    
    for entry in run_entries:
        message = entry.get('message', '')
        
        # Look for project_id
        project_match = re.search(r'project_id=(\d+)', message)
        if project_match:
            project_id = int(project_match.group(1))
        
        # Look for objective in various message patterns
        if 'starting run_chat_tools' in message and 'project_id=' in message:
            # This is likely the starting message, see if we can extract more context
            pass
    
    return {
        'id': run_id,
        'project_id': project_id,
        'created_at': start_time,
        'status': 'done',  # Assume completed runs
        'meta': {
            'imported_from_jsonl': True,
            'log_entries_count': len(run_entries),
            'duration_seconds': (end_time - start_time).total_seconds()
        }
    }


def extract_messages_from_logs(run_id: str, entries: list[dict]) -> list[dict]:
    """Extract message-like entries from logs."""
    messages = []
    run_entries = [e for e in entries if run_id in e.get('message', '')]
    
    for entry in run_entries:
        message_text = entry.get('message', '')
        level = entry.get('level', 'INFO')
        timestamp = datetime.fromisoformat(entry['ts'])
        
        # Create a generic message entry for significant log events
        if any(keyword in message_text.lower() for keyword in [
            'tool', 'invoke', 'completed', 'failed', 'error', 'result'
        ]):
            messages.append({
                'run_id': run_id,
                'role': 'system',
                'agent_name': entry.get('logger', '').split('.')[-1] if '.' in entry.get('logger', '') else 'system',
                'content': message_text,
                'ts': timestamp,
                'meta': {
                    'log_level': level,
                    'logger': entry.get('logger'),
                    'imported_from_jsonl': True
                }
            })
    
    return messages


def load_jsonl_into_storage(file_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    """Load JSONL logs into the agentic storage system."""
    print(f"Loading JSONL file: {file_path}")
    
    # Parse the file
    entries = parse_jsonl_file(file_path)
    print(f"Parsed {len(entries)} log entries")
    
    # Extract run IDs
    run_ids = extract_run_ids(entries)
    print(f"Found {len(run_ids)} unique run IDs")
    
    if not run_ids:
        print("No run IDs found in logs")
        return {"runs_created": 0, "messages_created": 0}
    
    if dry_run:
        print("DRY RUN: Would create the following runs:")
        for run_id in sorted(run_ids):
            run_data = create_run_from_logs(run_id, entries)
            messages = extract_messages_from_logs(run_id, entries)
            print(f"  - {run_id}: {len(messages)} messages, project_id={run_data.get('project_id')}")
        return {"runs_created": len(run_ids), "messages_created": 0}
    
    # Initialize database
    init_db()
    
    runs_created = 0
    messages_created = 0
    
    with get_session() as session:
        for run_id in run_ids:
            # Check if run already exists
            existing_run = session.get(Run, run_id)
            if existing_run:
                print(f"Run {run_id} already exists, skipping...")
                continue
            
            # Create run
            run_data = create_run_from_logs(run_id, entries)
            if not run_data:
                print(f"Could not extract run data for {run_id}, skipping...")
                continue
            
            run = Run(**run_data)
            session.add(run)
            runs_created += 1
            
            # Create messages
            messages = extract_messages_from_logs(run_id, entries)
            for msg_data in messages:
                # Save content as blob
                content_ref = save_blob("text", msg_data['content'], session=session)
                
                # Create message
                message = Message(
                    run_id=msg_data['run_id'],
                    role=msg_data['role'],
                    agent_name=msg_data.get('agent_name'),
                    content_ref=content_ref,
                    ts=msg_data['ts']
                )
                session.add(message)
                messages_created += 1
            
            print(f"Created run {run_id} with {len(messages)} messages")
        
        session.commit()
    
    print(f"Import complete: {runs_created} runs, {messages_created} messages")
    return {"runs_created": runs_created, "messages_created": messages_created}


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m orchestrator.jsonl_loader <jsonl_file> [--dry-run]")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist")
        sys.exit(1)
    
    dry_run = "--dry-run" in sys.argv
    
    try:
        result = load_jsonl_into_storage(file_path, dry_run=dry_run)
        print("Import successful:", result)
    except Exception as e:
        print(f"Error during import: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()