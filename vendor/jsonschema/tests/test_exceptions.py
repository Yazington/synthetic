# coding: utf-8
from unittest import TestCase
import textwrap
from ...jsonschema import Draft4Validator, exceptions

class TestBestMatch(TestCase):

    def best_match(self, errors):
        errors = list(errors)
        best = exceptions.best_match(errors)
        reversed_best = exceptions.best_match(reversed(errors))
        msg = "Didn't return a consistent best match!\nGot: {0}\n\nThen: {1}"
        self.assertEqual(best._contents(), reversed_best._contents(), msg=msg.format(best, reversed_best))
        return best

    def test_shallower_errors_are_better_matches(self):
        validator = Draft4Validator({'properties': {'foo': {'minProperties': 2, 'properties': {'bar': {'type': 'object'}}}}})
        best = self.best_match(validator.iter_errors({'foo': {'bar': []}}))
        self.assertEqual(best.validator, 'minProperties')

    def test_oneOf_and_anyOf_are_weak_matches(self):
        """
        A property you *must* match is probably better than one you have to
        match a part of.
        """
        validator = Draft4Validator({'minProperties': 2, 'anyOf': [{'type': 'string'}, {'type': 'number'}], 'oneOf': [{'type': 'string'}, {'type': 'number'}]})
        best = self.best_match(validator.iter_errors({}))
        self.assertEqual(best.validator, 'minProperties')

    def test_if_the_most_relevant_error_is_anyOf_it_is_traversed(self):
        """
        If the most relevant error is an anyOf, then we traverse its context
        and select the otherwise *least* relevant error, since in this case
        that means the most specific, deep, error inside the instance.

        I.e. since only one of the schemas must match, we look for the most
        relevant one.
        """
        validator = Draft4Validator({'properties': {'foo': {'anyOf': [{'type': 'string'}, {'properties': {'bar': {'type': 'array'}}}]}}})
        best = self.best_match(validator.iter_errors({'foo': {'bar': 12}}))
        self.assertEqual(best.validator_value, 'array')

    def test_if_the_most_relevant_error_is_oneOf_it_is_traversed(self):
        """
        If the most relevant error is an oneOf, then we traverse its context
        and select the otherwise *least* relevant error, since in this case
        that means the most specific, deep, error inside the instance.

        I.e. since only one of the schemas must match, we look for the most
        relevant one.
        """
        validator = Draft4Validator({'properties': {'foo': {'oneOf': [{'type': 'string'}, {'properties': {'bar': {'type': 'array'}}}]}}})
        best = self.best_match(validator.iter_errors({'foo': {'bar': 12}}))
        self.assertEqual(best.validator_value, 'array')

    def test_if_the_most_relevant_error_is_allOf_it_is_traversed(self):
        """
        Now, if the error is allOf, we traverse but select the *most* relevant
        error from the context, because all schemas here must match anyways.
        """
        validator = Draft4Validator({'properties': {'foo': {'allOf': [{'type': 'string'}, {'properties': {'bar': {'type': 'array'}}}]}}})
        best = self.best_match(validator.iter_errors({'foo': {'bar': 12}}))
        self.assertEqual(best.validator_value, 'string')

    def test_nested_context_for_oneOf(self):
        validator = Draft4Validator({'properties': {'foo': {'oneOf': [{'type': 'string'}, {'oneOf': [{'type': 'string'}, {'properties': {'bar': {'type': 'array'}}}]}]}}})
        best = self.best_match(validator.iter_errors({'foo': {'bar': 12}}))
        self.assertEqual(best.validator_value, 'array')

    def test_one_error(self):
        validator = Draft4Validator({'minProperties': 2})
        (error,) = validator.iter_errors({})
        self.assertEqual(exceptions.best_match(validator.iter_errors({})).validator, 'minProperties')

    def test_no_errors(self):
        validator = Draft4Validator({})
        self.assertIsNone(exceptions.best_match(validator.iter_errors({})))

class TestByRelevance(TestCase):

    def test_short_paths_are_better_matches(self):
        shallow = exceptions.ValidationError('Oh no!', path=['baz'])
        deep = exceptions.ValidationError('Oh yes!', path=['foo', 'bar'])
        match = max([shallow, deep], key=exceptions.relevance)
        self.assertIs(match, shallow)
        match = max([deep, shallow], key=exceptions.relevance)
        self.assertIs(match, shallow)

    def test_global_errors_are_even_better_matches(self):
        shallow = exceptions.ValidationError('Oh no!', path=[])
        deep = exceptions.ValidationError('Oh yes!', path=['foo'])
        errors = sorted([shallow, deep], key=exceptions.relevance)
        self.assertEqual([list(error.path) for error in errors], [['foo'], []])
        errors = sorted([deep, shallow], key=exceptions.relevance)
        self.assertEqual([list(error.path) for error in errors], [['foo'], []])

    def test_weak_validators_are_lower_priority(self):
        weak = exceptions.ValidationError('Oh no!', path=[], validator='a')
        normal = exceptions.ValidationError('Oh yes!', path=[], validator='b')
        best_match = exceptions.by_relevance(weak='a')
        match = max([weak, normal], key=best_match)
        self.assertIs(match, normal)
        match = max([normal, weak], key=best_match)
        self.assertIs(match, normal)

    def test_strong_validators_are_higher_priority(self):
        weak = exceptions.ValidationError('Oh no!', path=[], validator='a')
        normal = exceptions.ValidationError('Oh yes!', path=[], validator='b')
        strong = exceptions.ValidationError('Oh fine!', path=[], validator='c')
        best_match = exceptions.by_relevance(weak='a', strong='c')
        match = max([weak, normal, strong], key=best_match)
        self.assertIs(match, strong)
        match = max([strong, normal, weak], key=best_match)
        self.assertIs(match, strong)

class TestErrorTree(TestCase):

    def test_it_knows_how_many_total_errors_it_contains(self):
        errors = [exceptions.ValidationError('Something', validator=i) for i in range(8)]
        tree = exceptions.ErrorTree(errors)
        self.assertEqual(tree.total_errors, 8)

    def test_it_contains_an_item_if_the_item_had_an_error(self):
        errors = [exceptions.ValidationError('a message', path=['bar'])]
        tree = exceptions.ErrorTree(errors)
        self.assertIn('bar', tree)

    def test_it_does_not_contain_an_item_if_the_item_had_no_error(self):
        errors = [exceptions.ValidationError('a message', path=['bar'])]
        tree = exceptions.ErrorTree(errors)
        self.assertNotIn('foo', tree)

    def test_validators_that_failed_appear_in_errors_dict(self):
        error = exceptions.ValidationError('a message', validator='foo')
        tree = exceptions.ErrorTree([error])
        self.assertEqual(tree.errors, {'foo': error})

    def test_it_creates_a_child_tree_for_each_nested_path(self):
        errors = [exceptions.ValidationError('a bar message', path=['bar']), exceptions.ValidationError('a bar -> 0 message', path=['bar', 0])]
        tree = exceptions.ErrorTree(errors)
        self.assertIn(0, tree['bar'])
        self.assertNotIn(1, tree['bar'])

    def test_children_have_their_errors_dicts_built(self):
        (e1, e2) = (exceptions.ValidationError('1', validator='foo', path=['bar', 0]), exceptions.ValidationError('2', validator='quux', path=['bar', 0]))
        tree = exceptions.ErrorTree([e1, e2])
        self.assertEqual(tree['bar'][0].errors, {'foo': e1, 'quux': e2})

    def test_multiple_errors_with_instance(self):
        (e1, e2) = (exceptions.ValidationError('1', validator='foo', path=['bar', 'bar2'], instance='i1'), exceptions.ValidationError('2', validator='quux', path=['foobar', 2], instance='i2'))
        exceptions.ErrorTree([e1, e2])

    def test_it_does_not_contain_subtrees_that_are_not_in_the_instance(self):
        error = exceptions.ValidationError('123', validator='foo', instance=[])
        tree = exceptions.ErrorTree([error])
        with self.assertRaises(IndexError):
            tree[0]

    def test_if_its_in_the_tree_anyhow_it_does_not_raise_an_error(self):
        """
        If a validator is dumb (like :validator:`required` in draft 3) and
        refers to a path that isn't in the instance, the tree still properly
        returns a subtree for that path.
        """
        error = exceptions.ValidationError('a message', validator='foo', instance={}, path=['foo'])
        tree = exceptions.ErrorTree([error])
        self.assertIsInstance(tree['foo'], exceptions.ErrorTree)

    def test_repr(self):
        (e1, e2) = (exceptions.ValidationError('1', validator='foo', path=['bar', 'bar2'], instance='i1'), exceptions.ValidationError('2', validator='quux', path=['foobar', 2], instance='i2'))
        tree = exceptions.ErrorTree([e1, e2])
        self.assertEqual(repr(tree), '<ErrorTree (2 total errors)>')

class TestErrorInitReprStr(TestCase):

    def make_error(self, **kwargs):
        defaults = dict(message='hello', validator='type', validator_value='string', instance=5, schema={'type': 'string'})
        defaults.update(kwargs)
        return exceptions.ValidationError(**defaults)

    def assertShows(self, expected, **kwargs):
        expected = textwrap.dedent(expected).rstrip('\n')
        error = self.make_error(**kwargs)
        (message_line, _, rest) = str(error).partition('\n')
        self.assertEqual(message_line, error.message)
        self.assertEqual(rest, expected)

    def test_it_calls_super_and_sets_args(self):
        error = self.make_error()
        self.assertGreater(len(error.args), 1)

    def test_repr(self):
        self.assertEqual(repr(exceptions.ValidationError(message='Hello!')), "<ValidationError: 'Hello!'>")

    def test_unset_error(self):
        error = exceptions.ValidationError('message')
        self.assertEqual(str(error), 'message')
        kwargs = {'validator': 'type', 'validator_value': 'string', 'instance': 5, 'schema': {'type': 'string'}}
        for attr in kwargs:
            k = dict(kwargs)
            del k[attr]
            error = exceptions.ValidationError('message', **k)
            self.assertEqual(str(error), 'message')

    def test_empty_paths(self):
        self.assertShows("\n            Failed validating 'type' in schema:\n                {'type': 'string'}\n\n            On instance:\n                5\n            ", path=[], schema_path=[])

    def test_one_item_paths(self):
        self.assertShows("\n            Failed validating 'type' in schema:\n                {'type': 'string'}\n\n            On instance[0]:\n                5\n            ", path=[0], schema_path=['items'])

    def test_multiple_item_paths(self):
        self.assertShows("\n            Failed validating 'type' in schema['items'][0]:\n                {'type': 'string'}\n\n            On instance[0]['a']:\n                5\n            ", path=[0, 'a'], schema_path=['items', 0, 1])

    def test_uses_pprint(self):
        self.assertShows("\n            Failed validating 'maxLength' in schema:\n                {0: 0,\n                 1: 1,\n                 2: 2,\n                 3: 3,\n                 4: 4,\n                 5: 5,\n                 6: 6,\n                 7: 7,\n                 8: 8,\n                 9: 9,\n                 10: 10,\n                 11: 11,\n                 12: 12,\n                 13: 13,\n                 14: 14,\n                 15: 15,\n                 16: 16,\n                 17: 17,\n                 18: 18,\n                 19: 19}\n\n            On instance:\n                [0,\n                 1,\n                 2,\n                 3,\n                 4,\n                 5,\n                 6,\n                 7,\n                 8,\n                 9,\n                 10,\n                 11,\n                 12,\n                 13,\n                 14,\n                 15,\n                 16,\n                 17,\n                 18,\n                 19,\n                 20,\n                 21,\n                 22,\n                 23,\n                 24]\n            ", instance=list(range(25)), schema=dict(zip(range(20), range(20))), validator='maxLength')

    def test_str_works_with_instances_having_overriden_eq_operator(self):
        """
        Check for #164 which rendered exceptions unusable when a
        `ValidationError` involved instances with an `__eq__` method
        that returned truthy values.
        """

        class DontEQMeBro(object):

            def __eq__(this, other):
                self.fail("Don't!")

            def __ne__(this, other):
                self.fail("Don't!")
        instance = DontEQMeBro()
        error = exceptions.ValidationError('a message', validator='foo', instance=instance, validator_value='some', schema='schema')
        self.assertIn(repr(instance), str(error))

class TestHashable(TestCase):

    def test_hashable(self):
        set([exceptions.ValidationError('')])
        set([exceptions.SchemaError('')])
