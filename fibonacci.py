
def fibonacci(n):
    """Generate a list of Fibonacci numbers up to the nth number."""
    if n <= 0:
        return []  # Return empty list for non-positive inputs
    elif n == 1:
        return [0]  # Only one element in sequence when n is 1

    fib = [0, 1]
    while len(fib) < n:
        fib.append(fib[-1] + fib[-2])
    return fib

def main():
    try:
        num = int(input("Enter a number: "))
        if num < 1:
            print("Please enter a positive integer greater than zero.")
        else:
            print(*fibonacci(num))
    except ValueError:
        print("Invalid input. Please enter an integer.")

if __name__ == "__main__":
    main()