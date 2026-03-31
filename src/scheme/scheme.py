#!/usr/bin/env python3


"""A simple Scheme interpreter."""


import re
import time

class Symbol:
    """A Scheme symbol."""

    def __init__(self, name):
        self._name = name

    def __repr__(self):
        return f"Symbol('{self._name}')"

    def __hash__(self):
        return hash(self._name)

    def __eq__(self, other):
        if self is other:
            return True

        if isinstance(other, Symbol):
            return self._name == other._name

        return False


class Closure:
    """A Scheme closure."""

    def __init__(self, forms, params, frame):
        self._forms = forms
        self._params = params
        self._frame = frame

    def get_forms(self):
        """Return the forms of this closure."""

        return self._forms

    def get_params(self):
        """Return the names of the formal parameters of this closure."""

        return self._params

    def get_frame(self):
        """Return the frame in which this closure was created."""

        return self._frame


class Frame:
    """A Scheme frame is a collection of bindings."""

    def __init__(self, bindings=None, parent=None):
        self._bindings = bindings if bindings else {}
        self._parent = parent

    def lookup(self, symbol):
        """Look up the value bound to the given symbol. """

        if symbol in self._bindings:
            return self._bindings[symbol]

        if self._parent:
            return self._parent.lookup(symbol)

        return None

    def bind(self, symbol, value):
        """Bind the value to the symbol in this frame."""

        self._bindings[symbol] = value

    def set(self, symbol, value):
        """Set the value bound to the given symbol.

        This updates the binding in the nearest frame in
        which the symbol is bound.
        If the symbol is not bound in any frame, it
        creates a new binding in this frame.
        """

        if symbol in self._bindings:
            self._bindings[symbol] = value
        elif self._parent and self._parent.lookup(symbol):
            self._parent.set(symbol, value)
        else:
            self._bindings[symbol] = value


class SchemeError(Exception):
    """An error that occurred during Scheme evaluation."""


BUILTIN_FUNCTIONS_BY_NAME = {
    '+': lambda x, y: x + y,
    '-': lambda x, y: x - y,
    '*': lambda x, y: x * y,
    'mod': lambda x, y: x % y,
    '/': lambda x, y: x / y,
    '>': lambda x, y: x > y,
    '>=': lambda x, y: x >= y,
    '<': lambda x, y: x <= y,
    '<=': lambda x, y: x <= y,
    '=': lambda x, y: x == y,
    'eq?': lambda x, y: type(x) is type(y) and x == y,
    'null?': lambda x: x == [],
    'car': lambda x: x[0],
    'cdr': lambda x: x[1:],
    'cons': lambda x, y: [x] + y,
    'not': lambda x: not bool(x),
    'length': len,
}

# The default maximum recursion depth of nested evaluations.
DEFAULT_MAX_DEPTH = 100

# The default maximum time for one top-level evaluation, in seconds.
DEFAULT_MAX_TIME = 0.1

class Scheme:
    """A Scheme evaluation context."""

    def __init__(self, mappings={}):
        """Initializes a new instance."""
        
        bindings = {Symbol(k): v for k, v in BUILTIN_FUNCTIONS_BY_NAME.items()}
        bindings[Symbol('eval')] = lambda x: self._evaluate(x, self._toplevelframe)
        bindings[Symbol('apply')] = lambda func, params: self._apply(func, params)
        bindings[Symbol('map')] = lambda func, elems: [self._apply(func, [elem]) for elem in elems]
        bindings[Symbol('filter')] = lambda func, elems: [elem for elem in elems if self._apply(func, [elem])]
        self._toplevelframe = Frame(bindings)

        if mappings:
            self._toplevelframe = Frame({Symbol(k): v for k, v in mappings.items()},
                                        self._toplevelframe)

        self._max_depth = DEFAULT_MAX_DEPTH
        self._timeout = None
        self._last_evaluation_time = 0

    def last_evaluation_time(self):
        """Returns the duration of the last evaluation in seconds."""
        return self._last_evaluation_time
    
    def evaluate(self, string, *, max_depth=DEFAULT_MAX_DEPTH, max_time=DEFAULT_MAX_TIME):
        """Evaluate the given string in this context."""

        start_time = time.time()
        self._max_depth = max_depth
        self._timeout = (start_time + max_time) if max_time else None
        
        value = parse(string)
        result = self._evaluate(value, self._toplevelframe)
        
        self._last_evaluation_time = time.time() - start_time
        
        return result
    
    def _evaluate(self, value, frame):
        if self._max_depth is not None:
            if self._max_depth < 0:
                raise SchemeError("Too complex")
            self._max_depth -= 1

        result = self._evaluate1(value, frame)

        if self._max_depth is not None:
            self._max_depth += 1

        if self._timeout is not None:
            if self._timeout < time.time():
                raise SchemeError("Timeout.")
            
        return result

    def _evaluate1(self, value, frame):
        # pylint: disable=too-many-branches, too-many-return-statements
        if isinstance(value, Symbol):
            bound = frame.lookup(value)
            if bound is None:
                raise SchemeError("Unbound:" + str(value))

            return bound

        if value == [] or not isinstance(value, list):
            return value

        if value[0] == Symbol('quote'):
            return value[1]

        if value[0] == Symbol('progn'):
            result = []
            for element in value[1:]:
                result = self._evaluate(element, frame)
            return result

        if value[0] == Symbol('if'):
            test = self._evaluate(value[1], frame)
            if test:
                return self._evaluate(value[2], frame)

            return self._evaluate(value[3], frame)

        if value[0] == Symbol('cond'):
            for branch in value[1:]:
                test = self._evaluate(branch[0], frame)
                if test:
                    return self._evaluate(branch[1], frame)
            return []

        if value[0] == Symbol('set'):
            evaluated = self._evaluate(value[2], frame)
            frame.bind(value[1], evaluated)
            return []

        if value[0] == Symbol('define'):
            signature = value[1]
            closure = Closure(value[2:], signature[1:], frame)
            frame.bind(signature[0], closure)
            return []

        if value[0] == Symbol('lambda'):
            return Closure(value[2:], value[1], frame)

        if value[0] == Symbol('let'):
            bindings = {p[0]: self._evaluate(p[1], frame) for p in value[1]}
            return self._evaluate(value[2], Frame(bindings, frame))

        if value[0] == Symbol('and'):
            for v in value[1:]:
                if not self._evaluate(v, frame):
                    return False
            return True

        if value[0] == Symbol('or'):
            for v in value[1:]:
                if self._evaluate(v, frame):
                    return True
            return False

        func = self._evaluate(value[0], frame)
        evaluated = [self._evaluate(arg, frame) for arg in value[1:]]
        return self._apply(func, evaluated)

    def _apply(self, func, params):
        """Apply func to params."""

        if isinstance(func, Closure):
            bindings = {p[0]: p[1] for p in zip(func.get_params(), params)}
            frame = Frame(bindings, func.get_frame())
            result = []
            for form in func.get_forms():
                result = self._evaluate(form, frame)
            return result

        if hasattr(func, '__call__'):
            return func(*params)

        raise SchemeError(func)


TOKEN_SPECS = [
    ('LP', r'\('),
    ('RP', r'\)'),
    ('BOOLEAN', r'#t|#f'),
    ('NUMBER', r'[0-9]+(\.[0-9]*)?'),
    ('SYMBOL', r'[a-zA-Z!+=\-.<>/*]+[a-zA-Z0-9?]*'),
    ('STRING', r'".*"'),
    ('QUOTE', r'`'),
    ('WS', r'\s+'),
    ('REST', r'.'),
]


TOKENIZER_PATTERN = re.compile(
    '|'.join(f"(?P<{p[0]}>{p[1]})" for p in TOKEN_SPECS))


def tokenize(string):
    """Tokenize string into a list of tokens."""

    tokens = []
    for match in TOKENIZER_PATTERN.finditer(string):
        kind = match.lastgroup
        value = match.group(0)
        if kind == 'WS':
            continue

        if kind == 'REST':
            raise SchemeError(value)

        if kind == 'STRING':
            tokens.append(('STRING', value[1:-1]))
        else:
            tokens.append((kind, value))

    return tokens


def parse(string):
    """Parse string into a value."""

    if re.fullmatch(r'\s*', string):
        return []

    tokens = tokenize(string)
    forms = [Symbol('progn')]
    while tokens:
        form = _parse(tokens)
        forms.append(form)

    if len(forms) == 2:
        return forms[1]

    return forms


def _parse(tokens):
    # pylint: disable=too-many-branches, too-many-return-statements
    if not tokens:
        return []

    head = tokens.pop(0)
    if head[0] == 'BOOLEAN':
        if head[1] == '#t':
            return True

        if head[1] == '#f':
            return False

        raise SchemeError(head)

    if head[0] == 'NUMBER':
        try:
            return int(head[1])
        except ValueError:
            return float(head[1])

    if head[0] == 'STRING':
        return head[1]

    if head[0] == 'SYMBOL':
        return Symbol(head[1])

    if head[0] == 'QUOTE':
        return [Symbol('quote'), _parse(tokens)]

    if head[0] == 'LP':
        elements = []
        while tokens and tokens[0][0] != 'RP':
            elements.append(_parse(tokens))

        if not tokens:
            raise SchemeError('Missing RP')

        tokens.pop(0)

        return elements

    raise SchemeError(head)


if __name__ == '__main__':
    import sys

    scheme = Scheme()
    for arg in sys.argv[1:]:
        with open(arg, encoding='utf_8') as f:
            print(';', arg)
            result = scheme.evaluate(f.read(-1))
            print(result)
