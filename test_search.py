from agent.tools import ToolRegistry

registry = ToolRegistry()

print("--- Testing Search Robustness ---")

# Test 1: Normal Search
print("\nTest 1: Normal Search")
res = registry.search_web("python list comprehension")
print(res[:100] + "...")

# Test 2: Empty results (nonsense query)
print("\nTest 2: Nonsense Query")
res = registry.search_web("sdfkjsdhfkjshdfkjhsdkfjhsdkfjh")
print(res)

# Test 3: Empty string
print("\nTest 3: Empty String")
res = registry.search_web("")
print(res)
