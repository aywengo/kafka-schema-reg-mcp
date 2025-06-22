#!/usr/bin/env python3
"""
Script to upgrade MCP SDK from legacy mcp[cli]==1.9.4 to FastMCP 2.8.0+
Addresses Issue #32: MCP 2025-06-18 Specification Compliance

This script:
1. Updates all legacy MCP client imports
2. Converts StdioServerParameters + ClientSession patterns to FastMCP Client
3. Updates client usage patterns for FastMCP 2.8.0+
"""

import os
import re
import glob
from pathlib import Path

def update_legacy_mcp_imports(file_path):
    """Update legacy MCP imports to FastMCP."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Remove legacy imports
    content = re.sub(r'from mcp import ClientSession, StdioServerParameters\n', '', content)
    content = re.sub(r'from mcp import ClientSession\n', '', content)
    content = re.sub(r'from mcp\.client\.stdio import stdio_client, StdioServerParameters\n', '', content)
    content = re.sub(r'from mcp\.client\.stdio import.*\n', '', content)
    
    # Add FastMCP import if not present and legacy patterns were found
    if 'ClientSession' in original_content and 'from fastmcp import Client' not in content:
        # Find the last import line and add FastMCP import after it
        import_lines = []
        other_lines = []
        in_imports = True
        
        for line in content.split('\n'):
            if in_imports and (line.startswith('import ') or line.startswith('from ') or line.strip() == '' or line.startswith('#')):
                import_lines.append(line)
            else:
                if in_imports and line.strip():  # First non-import, non-empty, non-comment line
                    in_imports = False
                    import_lines.append('from fastmcp import Client')
                    import_lines.append('')  # Add blank line
                other_lines.append(line)
        
        if in_imports:  # All lines were imports
            import_lines.append('from fastmcp import Client')
            import_lines.append('')
        
        content = '\n'.join(import_lines + other_lines)
    
    return content

def update_legacy_client_patterns(content):
    """Update legacy client usage patterns to FastMCP."""
    
    # Pattern 1: StdioServerParameters + stdio_client + ClientSession
    legacy_pattern = r'''server_params = StdioServerParameters\(
\s*command="python",
\s*args=\[([^\]]+)\],?
\s*env=([^}]+})?
\s*\)
\s*
\s*async with stdio_client\(server_params\) as \(read, write\):
\s*async with ClientSession\(read, write\) as (\w+):'''
    
    def replace_legacy_pattern(match):
        args = match.group(1)
        env = match.group(2) if match.group(2) else '{}'
        session_var = match.group(3)
        
        # Extract script path from args
        script_match = re.search(r'"([^"]+\.py)"', args)
        script_path = script_match.group(1) if script_match else "script.py"
        
        return f'''client = Client(
            "{script_path}",
            env={env}
        )
        
        async with client as {session_var}:'''
    
    content = re.sub(legacy_pattern, replace_legacy_pattern, content, flags=re.MULTILINE | re.DOTALL)
    
    # Pattern 2: Direct Client instantiation fixes
    content = re.sub(r'async with client as (\w+):\s*await \1\.initialize\(\)', 
                    r'async with client as \1:', content)
    
    return content

def process_file(file_path):
    """Process a single Python file to upgrade MCP SDK usage."""
    print(f"Processing: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip if no legacy MCP patterns found
        if not any(pattern in content for pattern in ['ClientSession', 'StdioServerParameters', 'stdio_client']):
            return False
        
        # Update imports
        updated_content = update_legacy_mcp_imports(file_path)
        
        # Update client patterns
        updated_content = update_legacy_client_patterns(updated_content)
        
        # Write back if changed
        if updated_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"  ✅ Updated: {file_path}")
            return True
        else:
            print(f"  ℹ️  No changes: {file_path}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to upgrade all Python files."""
    print("🚀 Starting MCP SDK upgrade to FastMCP 2.8.0+")
    print("📋 Issue #32: MCP 2025-06-18 Specification Compliance")
    print()
    
    # Find all Python files
    python_files = []
    for pattern in ['*.py', 'tests/*.py', 'examples/*.py']:
        python_files.extend(glob.glob(pattern))
    
    # Remove this script from the list
    script_name = os.path.basename(__file__)
    python_files = [f for f in python_files if not f.endswith(script_name)]
    
    print(f"📁 Found {len(python_files)} Python files to check")
    print()
    
    updated_count = 0
    for file_path in sorted(python_files):
        if process_file(file_path):
            updated_count += 1
    
    print()
    print(f"✅ Upgrade complete!")
    print(f"📊 Updated {updated_count} files")
    print()
    print("🔍 Next steps:")
    print("1. Run tests to verify compatibility")
    print("2. Check for any remaining manual updates needed")
    print("3. Update requirements.txt to remove legacy mcp dependency")

if __name__ == "__main__":
    main() 