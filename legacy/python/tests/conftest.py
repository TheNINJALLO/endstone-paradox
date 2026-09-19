import sys
import types
from pathlib import Path


package_path = Path(__file__).resolve().parents[1] / "src" / "endstone_paradox"
package = types.ModuleType("endstone_paradox")
package.__path__ = [str(package_path)]
sys.modules.setdefault("endstone_paradox", package)
