import os
from agent.tools import ToolRegistry

registry = ToolRegistry()
test_file = "test_reproduce.txt"
registry.write_file(test_file, "Line A\nLine B\nLine C\n")

# Case 1: Trailing space after SEARCH
diff_trailing_space = """<<<<<<< SEARCH 
Line B
=======
Line B (mod)
>>>>>>> REPLACE"""

# Case 2: Missing newline after SEARCH
diff_missing_newline = """<<<<<<< SEARCH Line B
=======
Line B (mod)
>>>>>>> REPLACE"""

# Case 3: Space between markers
diff_space_markers = """<<<<<<< SEARCH
Line B
======= 
Line B (mod)
>>>>>>> REPLACE"""

# Case 4: Wrong number of brackets
diff_wrong_brackets = """<<<<<< SEARCH
Line B
=======
Line B (mod)
>>>>>> REPLACE"""

print("--- Testing Reproduction ---")
for i, diff in enumerate([diff_trailing_space, diff_missing_newline, diff_space_markers, diff_wrong_brackets], 1):
    # Reset file (delete first to avoid read-check policy issue in test)
    if os.path.exists(test_file):
        os.remove(test_file)
    registry.write_file(test_file, "Line A\nLine B\nLine C\n")
    print(f"Case {i}:")
    res = registry.apply_diff(test_file, diff)
    print(res)
