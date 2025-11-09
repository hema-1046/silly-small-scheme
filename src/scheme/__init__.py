from .scheme import SchemeContext


__all__ = ["SchemeContext"]

if __name__ == '__main__':
    import sys

    context = SchemeContext()
    for arg in sys.argv[1:]:
        with open(arg) as f:
            print(';', arg)
            result = context.evaluate(f.read(-1))
            print(result)
