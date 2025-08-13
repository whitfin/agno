#!/bin/bash

echo "🔧 Auto-resolving merge conflicts..."

# Get list of conflicted files
conflicted_files=$(git status --porcelain | grep "^UU" | cut -c4-)

if [ -z "$conflicted_files" ]; then
    echo "No conflicted files found!"
    exit 0
fi

echo "Found conflicted files:"
echo "$conflicted_files"
echo ""

# Function to resolve conflicts in a file
resolve_file_conflicts() {
    local file="$1"
    echo "Resolving: $file"
    
    # Create temp file
    temp_file=$(mktemp)
    
    # Process the file line by line to resolve conflicts
    python3 -c "
import re
import sys

with open('$file', 'r') as f:
    content = f.read()

# Resolve specific conflict patterns by choosing the 'new' version (after =======)
def resolve_conflict(match):
    full_match = match.group(0)
    lines = full_match.split('\n')
    
    # Find the ======= separator
    separator_idx = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('======='):
            separator_idx = i
            break
    
    if separator_idx == -1:
        return full_match  # No separator found, return original
    
    # Find the end marker
    end_idx = -1
    for i in range(separator_idx + 1, len(lines)):
        if lines[i].strip().startswith('>>>>>>> '):
            end_idx = i
            break
    
    if end_idx == -1:
        return full_match  # No end marker found, return original
    
    # Extract the 'new' version (between ======= and >>>>>>>)
    new_lines = lines[separator_idx + 1:end_idx]
    
    # Handle empty conflicts or preserve indentation
    if not new_lines or all(not line.strip() for line in new_lines):
        return ''
    
    return '\n'.join(new_lines) + '\n'

# Apply the conflict resolution
resolved = re.sub(r'<<<<<<< HEAD.*?>>>>>>> [^\n]*\n', resolve_conflict, content, flags=re.DOTALL)

with open('$temp_file', 'w') as f:
    f.write(resolved)
"
    
    # Replace original with resolved version
    if [ $? -eq 0 ]; then
        mv "$temp_file" "$file"
        echo "  ✓ Resolved"
    else
        rm -f "$temp_file"
        echo "  ✗ Failed to resolve"
    fi
}

# Process each conflicted file
while IFS= read -r file; do
    if [ -f "$file" ]; then
        resolve_file_conflicts "$file"
    fi
done <<< "$conflicted_files"

echo ""
echo "🎉 All conflicts resolved! Adding files..."

# Add resolved files
git add .

echo "✅ Files staged. You can now run: git cherry-pick --continue"
