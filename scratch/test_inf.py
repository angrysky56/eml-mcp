import math

def test_inf_to_int():
    v = float('inf')
    try:
        print(f"Testing v={v}")
        if v == int(v):
            print("Equal")
    except Exception as e:
        print(f"Caught expected error: {e}")

if __name__ == "__main__":
    test_inf_to_int()
