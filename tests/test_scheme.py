from scheme.scheme import *
import unittest


class SymbolTest(unittest.TestCase):
    def setUp(self):
        self.fixture = Symbol('a')

    def test_equal_to_equal(self):
        self.assertEqual(Symbol('a'), self.fixture)

    def test_equals_have_equal_hash(self):
        self.assertEqual(hash(Symbol('a')), hash(self.fixture))
        

class ClosureTest(unittest.TestCase):
    def test_callable(self):
        fixture = Closure([Symbol('x')], [Symbol('x')], Frame())
        self.assertEqual(4, fixture(4))

        
class FrameTest(unittest.TestCase):
    def setUp(self):
        self.parent = Frame(bindings={Symbol('b'): 17})
        self.fixture = Frame(bindings={Symbol('a'): 42}, parent=self.parent)
        
    def test_lookup_bound_symbol(self):
        self.assertEqual(42, self.fixture.lookup(Symbol('a')))

    def test_lookup_linked_bound_symbol(self):
        self.assertEqual(17, self.fixture.lookup(Symbol('b')))

    def test_bind(self):
        self.fixture.bind(Symbol('x'), 19)
        self.assertEqual(19, self.fixture.lookup(Symbol('x')))

    def test_set_existing(self):
        self.fixture.set(Symbol('b'), 5)
        self.assertEqual(5, self.parent.lookup(Symbol('b')))
                         

class EvaluationTest(unittest.TestCase):
    def setUp(self):
        self.frame = Frame(bindings={Symbol('a'):17})
        
    def test_self_evaluates_number(self):
        self.assertEqual(42, evaluate(42, self.frame))

    def test_self_evaluates_empty_list(self):
        self.assertEqual([], evaluate([], self.frame))
        
    def test_self_evaluates_native_function(self):
        self.assertEqual(3, evaluate(lambda x, y: x + y, self.frame)(1, 2))
        
    def test_lookup_symbol(self):
        self.assertEqual(17, evaluate(Symbol('a'), self.frame))

    def test_lookup_unbound_symbol(self):
        with self.assertRaises(SchemeError):
            evaluate(Symbol('x'), self.frame)

    def test_quote(self):
        self.assertEqual(Symbol('abc'), evaluate([Symbol('quote'), Symbol('abc')], self.frame))

    def test_applies_native(self):
        self.assertEqual(3, evaluate([lambda x, y: x + y, 1, 2], self.frame))

    def test_progn(self):
        value = [Symbol('progn'), 1, 2]
        self.assertEqual(2, evaluate(value, self.frame))
        
    def test_if(self):
        value = [Symbol('if'), True, 1, 2]
        self.assertEqual(1, evaluate(value, self.frame))

    def test_cond(self):
        value = [Symbol('cond'), [False, 1], [True, 2]]
        self.assertEqual(2, evaluate(value, self.frame))

    def test_cond_without_branch_returns_nil(self):
        value = [Symbol('cond'), [False, 1], [False, 2]]
        self.assertEqual([], evaluate(value, self.frame))
                         
    def test_define_returns_empty_list(self):
        value = [Symbol('define'), [Symbol('x')], 42]
        self.assertEqual([], evaluate(value, self.frame))

    def test_define_creates_closure(self):
        value = [Symbol('define'), [Symbol('x')], 42]
        evaluate(value, self.frame)
        self.assertEqual(Closure, type(self.frame.lookup(Symbol('x'))))

    def test_lambda_creates_closure(self):
        value = [Symbol('lambda'), [Symbol('x')], Symbol('x')]
        self.assertEqual(Closure, type(evaluate(value, self.frame)))

    def test_set_returns_empty_list(self):
        value = [Symbol('set'), Symbol('x'), 3]
        self.assertEqual([], evaluate(value, self.frame))

    def test_set_binds_value(self):
        value = [Symbol('set'), Symbol('x'), 3]
        evaluate(value, self.frame)
        self.assertEqual(3, self.frame.lookup(Symbol('x')))

    def test_let_creates_frame(self):
        value = [Symbol('let'), [[Symbol('a'), 12]], Symbol('a')]
        self.assertEqual(12, evaluate(value, self.frame))

    def test_and(self):
        value = [Symbol('and'), 1, 2, 3]
        self.assertEqual(True, evaluate(value, self.frame))

    def test_or(self):
        value = [Symbol('or'), [], False, False]
        self.assertEqual(False, evaluate(value, self.frame))
        

class ApplyTest(unittest.TestCase):
    def test_apply_closure(self):
        closure = Closure([Symbol('x')], [Symbol('x')], Frame())
        self.assertEqual(2, apply(closure, [2]))
        
    def test_apply_native_function(self):
        self.assertEqual(5, apply(lambda x, y: x + y, [1, 4]))

    def test_raises_error(self):
        with self.assertRaises(SchemeError):
            apply(123, [])


class TokenizerTest(unittest.TestCase):
    def test_tokenize_boolean(self):
        self.assertEqual([('BOOLEAN', '#t')], tokenize('#t'))
        
    def test_tokenize_number(self):
        self.assertEqual([('NUMBER', '123')], tokenize("123"))

    def test_skip_whitespace(self):
        self.assertEqual([('NUMBER', '1'), ('NUMBER', '2')], tokenize("1 2"))

    def test_tokenize_symbol(self):
        self.assertEqual([('SYMBOL', 'abc')], tokenize('abc'))

    def test_tokenize_string(self):
        self.assertEqual([('STRING', 'abc')], tokenize('"abc"'))

    def test_tokenize_empty_string(self):
        self.assertEqual([('STRING', '')], tokenize('""'))

    def test_tokenize_list(self):
        self.assertEqual([('LP', '('), ('RP', ')')], tokenize('()'))

    def test_tokenize_quote(self):
        self.assertEqual([('QUOTE', '`')], tokenize('`'))


class ParserTest(unittest.TestCase):
    def test_parse_boolean(self):
        self.assertEqual(True, parse('#t'))
        
    def test_parse_integer(self):
        self.assertEqual(123, parse('123'))

    def test_parse_float(self):
        self.assertEqual(2.3, parse('2.3'))

    def test_parse_string(self):
        self.assertEqual('abc', parse('"abc"'))

    def test_parse_symbol(self):
        self.assertEqual(Symbol('abc'), parse('abc'))

    def test_parse_empty_list(self):
        self.assertEqual([], parse('()'))
        
    def test_parse_nonempty_list(self):
        self.assertEqual([123], parse('(123)'))

    def test_parse_quote(self):
        self.assertEqual([Symbol('quote'), Symbol('abc')],
                         parse('`abc'))

    def test_parse_implicit_progn(self):
        self.assertEqual([Symbol('progn'), 1, 2], parse('1 2'))
        

class SchemeContextTest(unittest.TestCase):
    def setUp(self):
        self.fixture = SchemeContext()

    def evaluate(self, string):
        return self.fixture.evaluate(string)
        
    def test_evaluate_number(self):
        self.assertEqual(123, self.evaluate('123'))

    def test_evaluate_addition(self):
        self.assertEqual(5, self.evaluate('(+ 2 3)'))

    def test_evaluate_subtraction(self):
        self.assertEqual(-1, self.evaluate('(- 2 3)'))

    def test_evaluate_null_predicate(self):
        self.assertEqual(True, self.evaluate('(null? ())'))

    def test_evaluate_cons(self):
        self.assertEqual([1, 2, 3], self.evaluate('(cons 1 `(2 3))'))
        
    def test_evaluate_car(self):
        self.assertEqual(1, self.evaluate('(car `(1 2 3))'))

    def test_evaluate_cdr(self):
        self.assertEqual([2, 3], self.evaluate('(cdr `(1 2 3))'))

    def test_evaluate_equal(self):
        self.assertEqual(True, self.evaluate('(= 2 2.0)'))
        self.assertEqual(False, self.evaluate('(eq? 2 2.0)'))

    def test_evaluate_not(self):
        self.assertFalse(self.evaluate('(not (= 1 1))'))
        
    def test_define(self):
        self.evaluate('(define (+1 x) (+ 1 x))')
        self.assertEqual(7, self.evaluate('(+1 6)'))

    def test_length(self):
        self.assertEqual(4, self.evaluate('(length `(1 2 3 4))'))

    def test_map(self):
        self.evaluate('(define (+1 x) (+ 1 x))')
        self.assertEqual([2, 3, 4, 5], self.evaluate('(map +1 `(1 2 3 4))'))

    def test_filter(self):
        self.evaluate('(define (even? x) (= (mod x 2) 0))')
        self.assertEqual([2, 4, 6], self.evaluate('(filter even? `(1 2 3 4 5 6))'))

    def test_apply(self):
        self.assertEqual(12, self.evaluate('(apply (lambda (x) (/ x 2)) `(24))'))

    def test_eval(self):
        self.assertEqual(5, self.evaluate('(eval `(+ 4 1))'))

    def test_let(self):
        self.assertEqual(3,
                         self.evaluate('(let ((a (lambda (x y) (+ x y)))) (a 1 2))'))
    
        
if __name__ == '__main__':
    unittest.main()
