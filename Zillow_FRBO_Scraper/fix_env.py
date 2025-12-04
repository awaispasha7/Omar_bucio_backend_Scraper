import os

env_path = '.env'

# Read content
with open(env_path, 'r', encoding='utf-8-sig') as f:
    content = f.read()

# Write back with utf-8 (no BOM)
with open(env_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed .env file encoding (removed BOM)")
