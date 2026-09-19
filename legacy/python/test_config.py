import sys
from pathlib import Path

# Add the src folder to the path
sys.path.insert(0, str(Path(r"c:\Users\Ninjo\OneDrive\Desktop\onistone plugins-updated\endstone plugins-updated\endstone-paradox\src")))

from endstone_paradox.config import ParadoxConfig

class DummyLogger:
    def info(self, msg): print("INFO:", msg)
    def warning(self, msg): print("WARN:", msg)
    def error(self, msg): print("ERROR:", msg)

df = Path("test_data_folder2")
df.mkdir(parents=True, exist_ok=True)

# Initialize it
config = ParadoxConfig(df, DummyLogger())
print("Config loaded!")
print("Path exists?", (df / "config.toml").exists())
