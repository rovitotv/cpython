#!/usr/bin/env python

"""Unit tests for the with statement specified in PEP 343."""

__author__ = "Mike Bland"
__email__ = "mbland at acm dot org"

import unittest
from test.contextmanager import GeneratorContextManager
from test.nested import nested
from test.test_support import run_unittest


class MockContextManager(GeneratorContextManager):
    def __init__(self, gen):
        GeneratorContextManager.__init__(self, gen)
        self.context_called = False
        self.enter_called = False
        self.exit_called = False
        self.exit_args = None

    def __context__(self):
        self.context_called = True
        return GeneratorContextManager.__context__(self)

    def __enter__(self):
        self.enter_called = True
        return GeneratorContextManager.__enter__(self)

    def __exit__(self, type, value, traceback):
        self.exit_called = True
        self.exit_args = (type, value, traceback)
        return GeneratorContextManager.__exit__(self, type, value, traceback)


def mock_contextmanager(func):
    def helper(*args, **kwds):
        return MockContextManager(func(*args, **kwds))
    return helper


class MockResource(object):
    def __init__(self):
        self.yielded = False
        self.stopped = False


@mock_contextmanager
def mock_contextmanager_generator():
    mock = MockResource()
    try:
        mock.yielded = True
        yield mock
    finally:
        mock.stopped = True


class MockNested(nested):
    def __init__(self, *contexts):
        nested.__init__(self, *contexts)
        self.context_called = False
        self.enter_called = False
        self.exit_called = False
        self.exit_args = None

    def __context__(self):
        self.context_called = True
        return nested.__context__(self)

    def __enter__(self):
        self.enter_called = True
        return nested.__enter__(self)

    def __exit__(self, *exc_info):
        self.exit_called = True
        self.exit_args = exc_info
        return nested.__exit__(self, *exc_info)

 
class FailureTestCase(unittest.TestCase):
    def testNameError(self):
        def fooNotDeclared():
            with foo: pass
        self.assertRaises(NameError, fooNotDeclared)

    def testContextAttributeError(self):
        class LacksContext(object):
            def __enter__(self):
                pass

            def __exit__(self, type, value, traceback):
                pass

        def fooLacksContext():
            foo = LacksContext()
            with foo: pass
        self.assertRaises(AttributeError, fooLacksContext)

    def testEnterAttributeError(self):
        class LacksEnter(object):
            def __context__(self):
                pass

            def __exit__(self, type, value, traceback):
                pass

        def fooLacksEnter():
            foo = LacksEnter()
            with foo: pass
        self.assertRaises(AttributeError, fooLacksEnter)

    def testExitAttributeError(self):
        class LacksExit(object):
            def __context__(self):
                pass

            def __enter__(self):
                pass

        def fooLacksExit():
            foo = LacksExit()
            with foo: pass
        self.assertRaises(AttributeError, fooLacksExit)

    def assertRaisesSyntaxError(self, codestr):
        def shouldRaiseSyntaxError(s):
            compile(s, '', 'single')
        self.assertRaises(SyntaxError, shouldRaiseSyntaxError, codestr)

    def testAssignmentToNoneError(self):
        self.assertRaisesSyntaxError('with mock as None:\n  pass')
        self.assertRaisesSyntaxError(
            'with mock as (None):\n'
            '  pass')

    def testAssignmentToEmptyTupleError(self):
        self.assertRaisesSyntaxError(
            'with mock as ():\n'
            '  pass')

    def testAssignmentToTupleOnlyContainingNoneError(self):
        self.assertRaisesSyntaxError('with mock as None,:\n  pass')
        self.assertRaisesSyntaxError(
            'with mock as (None,):\n'
            '  pass')

    def testAssignmentToTupleContainingNoneError(self):
        self.assertRaisesSyntaxError(
            'with mock as (foo, None, bar):\n'
            '  pass')

    def testContextThrows(self):
        class ContextThrows(object):
            def __context__(self):
                raise RuntimeError("Context threw")

        def shouldThrow():
            ct = ContextThrows()
            self.foo = None
            with ct as self.foo:
                pass
        self.assertRaises(RuntimeError, shouldThrow)
        self.assertEqual(self.foo, None)

    def testEnterThrows(self):
        class EnterThrows(object):
            def __context__(self):
                return self

            def __enter__(self):
                raise RuntimeError("Context threw")

            def __exit__(self, *args):
                pass

        def shouldThrow():
            ct = EnterThrows()
            self.foo = None
            with ct as self.foo:
                pass
        self.assertRaises(RuntimeError, shouldThrow)
        self.assertEqual(self.foo, None)

    def testExitThrows(self):
        class ExitThrows(object):
            def __context__(self):
                return self
            def __enter__(self):
                return
            def __exit__(self, *args):
                raise RuntimeError(42)
        def shouldThrow():
            with ExitThrows():
                pass
        self.assertRaises(RuntimeError, shouldThrow)

class ContextmanagerAssertionMixin(object):
    TEST_EXCEPTION = RuntimeError("test exception")

    def assertInWithManagerInvariants(self, mock_manager):
        self.assertTrue(mock_manager.context_called)
        self.assertTrue(mock_manager.enter_called)
        self.assertFalse(mock_manager.exit_called)
        self.assertEqual(mock_manager.exit_args, None)

    def assertAfterWithManagerInvariants(self, mock_manager, exit_args):
        self.assertTrue(mock_manager.context_called)
        self.assertTrue(mock_manager.enter_called)
        self.assertTrue(mock_manager.exit_called)
        self.assertEqual(mock_manager.exit_args, exit_args)

    def assertAfterWithManagerInvariantsNoError(self, mock_manager):
        self.assertAfterWithManagerInvariants(mock_manager,
            (None, None, None))

    def assertInWithGeneratorInvariants(self, mock_generator):
        self.assertTrue(mock_generator.yielded)
        self.assertFalse(mock_generator.stopped)

    def assertAfterWithGeneratorInvariantsNoError(self, mock_generator):
        self.assertTrue(mock_generator.yielded)
        self.assertTrue(mock_generator.stopped)

    def raiseTestException(self):
        raise self.TEST_EXCEPTION

    def assertAfterWithManagerInvariantsWithError(self, mock_manager):
        self.assertTrue(mock_manager.context_called)
        self.assertTrue(mock_manager.enter_called)
        self.assertTrue(mock_manager.exit_called)
        self.assertEqual(mock_manager.exit_args[0], RuntimeError)
        self.assertEqual(mock_manager.exit_args[1], self.TEST_EXCEPTION)

    def assertAfterWithGeneratorInvariantsWithError(self, mock_generator):
        self.assertTrue(mock_generator.yielded)
        self.assertTrue(mock_generator.stopped)


class NonexceptionalTestCase(unittest.TestCase, ContextmanagerAssertionMixin):
    def testInlineGeneratorSyntax(self):
        with mock_contextmanager_generator():
            pass

    def testUnboundGenerator(self):
        mock = mock_contextmanager_generator()
        with mock:
            pass
        self.assertAfterWithManagerInvariantsNoError(mock)

    def testInlineGeneratorBoundSyntax(self):
        with mock_contextmanager_generator() as foo:
            self.assertInWithGeneratorInvariants(foo)
        # FIXME: In the future, we'll try to keep the bound names from leaking
        self.assertAfterWithGeneratorInvariantsNoError(foo)

    def testInlineGeneratorBoundToExistingVariable(self):
        foo = None
        with mock_contextmanager_generator() as foo:
            self.assertInWithGeneratorInvariants(foo)
        self.assertAfterWithGeneratorInvariantsNoError(foo)

    def testInlineGeneratorBoundToDottedVariable(self):
        with mock_contextmanager_generator() as self.foo:
            self.assertInWithGeneratorInvariants(self.foo)
        self.assertAfterWithGeneratorInvariantsNoError(self.foo)

    def testBoundGenerator(self):
        mock = mock_contextmanager_generator()
        with mock as foo:
            self.assertInWithGeneratorInvariants(foo)
            self.assertInWithManagerInvariants(mock)
        self.assertAfterWithGeneratorInvariantsNoError(foo)
        self.assertAfterWithManagerInvariantsNoError(mock)

    def testNestedSingleStatements(self):
        mock_a = mock_contextmanager_generator()
        with mock_a as foo:
            mock_b = mock_contextmanager_generator()
            with mock_b as bar:
                self.assertInWithManagerInvariants(mock_a)
                self.assertInWithManagerInvariants(mock_b)
                self.assertInWithGeneratorInvariants(foo)
                self.assertInWithGeneratorInvariants(bar)
            self.assertAfterWithManagerInvariantsNoError(mock_b)
            self.assertAfterWithGeneratorInvariantsNoError(bar)
            self.assertInWithManagerInvariants(mock_a)
            self.assertInWithGeneratorInvariants(foo)
        self.assertAfterWithManagerInvariantsNoError(mock_a)
        self.assertAfterWithGeneratorInvariantsNoError(foo)


class NestedNonexceptionalTestCase(unittest.TestCase,
    ContextmanagerAssertionMixin):
    def testSingleArgInlineGeneratorSyntax(self):
        with nested(mock_contextmanager_generator()):
            pass

    def testSingleArgUnbound(self):
        mock_contextmanager = mock_contextmanager_generator()
        mock_nested = MockNested(mock_contextmanager)
        with mock_nested:
            self.assertInWithManagerInvariants(mock_contextmanager)
            self.assertInWithManagerInvariants(mock_nested)
        self.assertAfterWithManagerInvariantsNoError(mock_contextmanager)
        self.assertAfterWithManagerInvariantsNoError(mock_nested)

    def testSingleArgBoundToNonTuple(self):
        m = mock_contextmanager_generator()
        # This will bind all the arguments to nested() into a single list
        # assigned to foo.
        with nested(m) as foo:
            self.assertInWithManagerInvariants(m)
        self.assertAfterWithManagerInvariantsNoError(m)

    def testSingleArgBoundToSingleElementParenthesizedList(self):
        m = mock_contextmanager_generator()
        # This will bind all the arguments to nested() into a single list
        # assigned to foo.
        # FIXME: what should this do:  with nested(m) as (foo,):
        with nested(m) as (foo):
            self.assertInWithManagerInvariants(m)
        self.assertAfterWithManagerInvariantsNoError(m)

    def testSingleArgBoundToMultipleElementTupleError(self):
        def shouldThrowValueError():
            with nested(mock_contextmanager_generator()) as (foo, bar):
                pass
        self.assertRaises(ValueError, shouldThrowValueError)

    def testSingleArgUnbound(self):
        mock_contextmanager = mock_contextmanager_generator()
        mock_nested = MockNested(mock_contextmanager)
        with mock_nested:
            self.assertInWithManagerInvariants(mock_contextmanager)
            self.assertInWithManagerInvariants(mock_nested)
        self.assertAfterWithManagerInvariantsNoError(mock_contextmanager)
        self.assertAfterWithManagerInvariantsNoError(mock_nested)

    def testMultipleArgUnbound(self):
        m = mock_contextmanager_generator()
        n = mock_contextmanager_generator()
        o = mock_contextmanager_generator()
        mock_nested = MockNested(m, n, o)
        with mock_nested:
            self.assertInWithManagerInvariants(m)
            self.assertInWithManagerInvariants(n)
            self.assertInWithManagerInvariants(o)
            self.assertInWithManagerInvariants(mock_nested)
        self.assertAfterWithManagerInvariantsNoError(m)
        self.assertAfterWithManagerInvariantsNoError(n)
        self.assertAfterWithManagerInvariantsNoError(o)
        self.assertAfterWithManagerInvariantsNoError(mock_nested)

    def testMultipleArgBound(self):
        mock_nested = MockNested(mock_contextmanager_generator(),
            mock_contextmanager_generator(), mock_contextmanager_generator())
        with mock_nested as (m, n, o):
            self.assertInWithGeneratorInvariants(m)
            self.assertInWithGeneratorInvariants(n)
            self.assertInWithGeneratorInvariants(o)
            self.assertInWithManagerInvariants(mock_nested)
        self.assertAfterWithGeneratorInvariantsNoError(m)
        self.assertAfterWithGeneratorInvariantsNoError(n)
        self.assertAfterWithGeneratorInvariantsNoError(o)
        self.assertAfterWithManagerInvariantsNoError(mock_nested)


class ExceptionalTestCase(unittest.TestCase, ContextmanagerAssertionMixin):
    def testSingleResource(self):
        cm = mock_contextmanager_generator()
        def shouldThrow():
            with cm as self.resource:
                self.assertInWithManagerInvariants(cm)
                self.assertInWithGeneratorInvariants(self.resource)
                self.raiseTestException()
        self.assertRaises(RuntimeError, shouldThrow)
        self.assertAfterWithManagerInvariantsWithError(cm)
        self.assertAfterWithGeneratorInvariantsWithError(self.resource)

    def testNestedSingleStatements(self):
        mock_a = mock_contextmanager_generator()
        mock_b = mock_contextmanager_generator()
        def shouldThrow():
            with mock_a as self.foo:
                with mock_b as self.bar:
                    self.assertInWithManagerInvariants(mock_a)
                    self.assertInWithManagerInvariants(mock_b)
                    self.assertInWithGeneratorInvariants(self.foo)
                    self.assertInWithGeneratorInvariants(self.bar)
                    self.raiseTestException()
        self.assertRaises(RuntimeError, shouldThrow)
        self.assertAfterWithManagerInvariantsWithError(mock_a)
        self.assertAfterWithManagerInvariantsWithError(mock_b)
        self.assertAfterWithGeneratorInvariantsWithError(self.foo)
        self.assertAfterWithGeneratorInvariantsWithError(self.bar)

    def testMultipleResourcesInSingleStatement(self):
        cm_a = mock_contextmanager_generator()
        cm_b = mock_contextmanager_generator()
        mock_nested = MockNested(cm_a, cm_b)
        def shouldThrow():
            with mock_nested as (self.resource_a, self.resource_b):
                self.assertInWithManagerInvariants(cm_a)
                self.assertInWithManagerInvariants(cm_b)
                self.assertInWithManagerInvariants(mock_nested)
                self.assertInWithGeneratorInvariants(self.resource_a)
                self.assertInWithGeneratorInvariants(self.resource_b)
                self.raiseTestException()
        self.assertRaises(RuntimeError, shouldThrow)
        self.assertAfterWithManagerInvariantsWithError(cm_a)
        self.assertAfterWithManagerInvariantsWithError(cm_b)
        self.assertAfterWithManagerInvariantsWithError(mock_nested)
        self.assertAfterWithGeneratorInvariantsWithError(self.resource_a)
        self.assertAfterWithGeneratorInvariantsWithError(self.resource_b)

    def testNestedExceptionBeforeInnerStatement(self):
        mock_a = mock_contextmanager_generator()
        mock_b = mock_contextmanager_generator()
        self.bar = None
        def shouldThrow():
            with mock_a as self.foo:
                self.assertInWithManagerInvariants(mock_a)
                self.assertInWithGeneratorInvariants(self.foo)
                self.raiseTestException()
                with mock_b as self.bar:
                    pass
        self.assertRaises(RuntimeError, shouldThrow)
        self.assertAfterWithManagerInvariantsWithError(mock_a)
        self.assertAfterWithGeneratorInvariantsWithError(self.foo)

        # The inner statement stuff should never have been touched
        self.assertEqual(self.bar, None)
        self.assertFalse(mock_b.context_called)
        self.assertFalse(mock_b.enter_called)
        self.assertFalse(mock_b.exit_called)
        self.assertEqual(mock_b.exit_args, None)

    def testNestedExceptionAfterInnerStatement(self):
        mock_a = mock_contextmanager_generator()
        mock_b = mock_contextmanager_generator()
        def shouldThrow():
            with mock_a as self.foo:
                with mock_b as self.bar:
                    self.assertInWithManagerInvariants(mock_a)
                    self.assertInWithManagerInvariants(mock_b)
                    self.assertInWithGeneratorInvariants(self.foo)
                    self.assertInWithGeneratorInvariants(self.bar)
                self.raiseTestException()
        self.assertRaises(RuntimeError, shouldThrow)
        self.assertAfterWithManagerInvariantsWithError(mock_a)
        self.assertAfterWithManagerInvariantsNoError(mock_b)
        self.assertAfterWithGeneratorInvariantsWithError(self.foo)
        self.assertAfterWithGeneratorInvariantsNoError(self.bar)


class NonLocalFlowControlTestCase(unittest.TestCase):

    def testWithBreak(self):
        counter = 0
        while True:
            counter += 1
            with mock_contextmanager_generator():
                counter += 10
                break
            counter += 100 # Not reached
        self.assertEqual(counter, 11)

    def testWithContinue(self):
        counter = 0
        while True:
            counter += 1
            if counter > 2:
                break
            with mock_contextmanager_generator():
                counter += 10
                continue
            counter += 100 # Not reached
        self.assertEqual(counter, 12)

    def testWithReturn(self):
        def foo():
            counter = 0
            while True:
                counter += 1
                with mock_contextmanager_generator():
                    counter += 10
                    return counter
                counter += 100 # Not reached
        self.assertEqual(foo(), 11)

    def testWithYield(self):
        def gen():
            with mock_contextmanager_generator():
                yield 12
                yield 13
        x = list(gen())
        self.assertEqual(x, [12, 13])

    def testWithRaise(self):
        counter = 0
        try:
            counter += 1
            with mock_contextmanager_generator():
                counter += 10
                raise RuntimeError
            counter += 100 # Not reached
        except RuntimeError:
            self.assertEqual(counter, 11)
        else:
            self.fail("Didn't raise RuntimeError")


class AssignmentTargetTestCase(unittest.TestCase):

    def testSingleComplexTarget(self):
        targets = {1: [0, 1, 2]}
        with mock_contextmanager_generator() as targets[1][0]:
            self.assertEqual(targets.keys(), [1])
            self.assertEqual(targets[1][0].__class__, MockResource)
        with mock_contextmanager_generator() as targets.values()[0][1]:
            self.assertEqual(targets.keys(), [1])
            self.assertEqual(targets[1][1].__class__, MockResource)
        with mock_contextmanager_generator() as targets[2]:
            keys = targets.keys()
            keys.sort()
            self.assertEqual(keys, [1, 2])
        class C: pass
        blah = C()
        with mock_contextmanager_generator() as blah.foo:
            self.assertEqual(hasattr(blah, "foo"), True)

    def testMultipleComplexTargets(self):
        class C:
            def __context__(self): return self
            def __enter__(self): return 1, 2, 3
            def __exit__(self, *a): pass
        targets = {1: [0, 1, 2]}
        with C() as (targets[1][0], targets[1][1], targets[1][2]):
            self.assertEqual(targets, {1: [1, 2, 3]})
        with C() as (targets.values()[0][2], targets.values()[0][1], targets.values()[0][0]):
            self.assertEqual(targets, {1: [3, 2, 1]})
        with C() as (targets[1], targets[2], targets[3]):
            self.assertEqual(targets, {1: 1, 2: 2, 3: 3})
        class B: pass
        blah = B()
        with C() as (blah.one, blah.two, blah.three):
            self.assertEqual(blah.one, 1)
            self.assertEqual(blah.two, 2)
            self.assertEqual(blah.three, 3)


def test_main():
    run_unittest(FailureTestCase, NonexceptionalTestCase,
                 NestedNonexceptionalTestCase, ExceptionalTestCase,
                 NonLocalFlowControlTestCase,
                 AssignmentTargetTestCase)


if __name__ == '__main__':
    test_main()
