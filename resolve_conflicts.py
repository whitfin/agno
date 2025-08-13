#!/usr/bin/env python3

import re
import sys
import subprocess
from pathlib import Path

def get_conflicted_files():
    """Get list of files with merge conflicts"""
    result = subprocess.run(['git', 'status', '--porcelain'], 
                          capture_output=True, text=True)
    files = []
    for line in result.stdout.strip().split('\n'):
        if line.startswith('UU '):
            files.append(line[3:])
    return files

def resolve_conflict_patterns(content):
    """Resolve common conflict patterns in content"""
    
    # Pattern 1: Simple type renames in conflict blocks
    patterns = [
        # RunResponseContentEvent -> RunContentEvent
        (r'<<<<<<< HEAD.*?\n.*?RunResponseContentEvent.*?\n=======.*?\n.*?RunContentEvent.*?\n>>>>>>> .*?\n', 
         lambda m: f"    RunContentEvent,\n"),
        
        # Variable and type renames in conflict blocks - more specific
        (r'<<<<<<< HEAD[^\n]*\n(.*?)run_response_event(.*?)\n=======[^\n]*\n.*?run_output_event.*?\n>>>>>>> [^\n]*\n',
         lambda m: f"{m.group(1)}run_output_event{m.group(2)}\n"),
        
        # Event type renames in if statements
        (r'<<<<<<< HEAD[^\n]*\n.*?if run_response_event\.event in \[(.*?)\]:(.*?)\n=======[^\n]*\n.*?if run_output_event\.event in \[(.*?)\]:(.*?)\n>>>>>>> [^\n]*\n',
         lambda m: f"        if run_output_event.event in [{m.group(3)}]:{m.group(4)}\n"),
         
        # RunEvent content type renames
        (r'<<<<<<< HEAD[^\n]*\n.*?RunEvent\.run_response_content.*?\n=======[^\n]*\n.*?RunEvent\.run_content.*?\n>>>>>>> [^\n]*\n',
         lambda m: "        if run_output_event.event in [RunEvent.run_content]:\n"),
         
        # TeamRunEvent content type renames  
        (r'<<<<<<< HEAD[^\n]*\n.*?TeamRunEvent\.run_response_content.*?\n=======[^\n]*\n.*?TeamRunEvent\.run_content.*?\n>>>>>>> [^\n]*\n',
         lambda m: "        if run_output_event.event in [TeamRunEvent.run_content]:\n"),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # More general conflict resolution - choose the "new" version (after =======)
    def resolve_general_conflict(match):
        lines = match.group(0).split('\n')
        in_new_section = False
        new_lines = []
        
        for line in lines:
            if line.startswith('======='):
                in_new_section = True
                continue
            elif line.startswith('>>>>>>> '):
                break
            elif line.startswith('<<<<<<< '):
                continue
            elif in_new_section:
                new_lines.append(line)
        
        return '\n'.join(new_lines) + '\n'
    
    # Handle remaining conflicts by taking the "new" version
    content = re.sub(r'<<<<<<< HEAD.*?=======.*?>>>>>>> [^\n]*\n', 
                     resolve_general_conflict, content, flags=re.DOTALL)
    
    return content

def main():
    conflicted_files = get_conflicted_files()
    print(f"Found {len(conflicted_files)} conflicted files")
    
    for file_path in conflicted_files:
        print(f"Resolving conflicts in {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Resolve conflicts
            resolved_content = resolve_conflict_patterns(content)
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(resolved_content)
                
            print(f"  ✓ Resolved {file_path}")
                
        except Exception as e:
            print(f"  ✗ Error resolving {file_path}: {e}")
    
    print("\nConflict resolution complete!")
    print("Run 'git add .' and 'git cherry-pick --continue' to complete the operation")

if __name__ == "__main__":
    main()
