import sys

path = r'e:\AI\AI Video Translantion and voice cloning platform\config.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_env = '''
# Database and Message Queue (used in Docker setup)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/jobs.sqlite3")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# API Keys'''

if '# API Keys' in content and 'DATABASE_URL' not in content:
    content = content.replace('# API Keys', new_env)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
        print("Updated config.py")
else:
    print("Already updated or couldn't find hook.")
