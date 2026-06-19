import os
import sys

# Make the src-layout package importable without an editable install.
SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
