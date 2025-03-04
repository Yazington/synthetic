# coding: utf-8
"""
Tests for the parts of jsonschema related to the :validator:`format` property.
"""
from unittest import TestCase
from ...jsonschema import FormatChecker, FormatError, ValidationError
from ...jsonschema.validators import Draft4Validator
BOOM = ValueError('Boom!')
BANG = ZeroDivisionError('Bang!')

def boom(thing):
    if thing == 'bang':
        raise BANG
    raise BOOM

class TestFormatChecker(TestCase):

    def test_it_can_validate_no_formats(self):
        checker = FormatChecker(formats=())
        self.assertFalse(checker.checkers)

    def test_it_raises_a_key_error_for_unknown_formats(self):
        with self.assertRaises(KeyError):
            FormatChecker(formats=['o noes'])

    def test_it_can_register_cls_checkers(self):
        original = dict(FormatChecker.checkers)
        self.addCleanup(FormatChecker.checkers.pop, 'boom')
        FormatChecker.cls_checks('boom')(boom)
        self.assertEqual(FormatChecker.checkers, dict(original, boom=(boom, ())))

    def test_it_can_register_checkers(self):
        checker = FormatChecker()
        checker.checks('boom')(boom)
        self.assertEqual(checker.checkers, dict(FormatChecker.checkers, boom=(boom, ())))

    def test_it_catches_registered_errors(self):
        checker = FormatChecker()
        checker.checks('boom', raises=type(BOOM))(boom)
        with self.assertRaises(FormatError) as cm:
            checker.check(instance=12, format='boom')
        self.assertIs(cm.exception.cause, BOOM)
        self.assertIs(cm.exception.__cause__, BOOM)
        with self.assertRaises(type(BANG)):
            checker.check(instance='bang', format='boom')

    def test_format_error_causes_become_validation_error_causes(self):
        checker = FormatChecker()
        checker.checks('boom', raises=ValueError)(boom)
        validator = Draft4Validator({'format': 'boom'}, format_checker=checker)
        with self.assertRaises(ValidationError) as cm:
            validator.validate('BOOM')
        self.assertIs(cm.exception.cause, BOOM)
        self.assertIs(cm.exception.__cause__, BOOM)

    def test_format_checkers_come_with_defaults(self):
        checker = FormatChecker()
        with self.assertRaises(FormatError):
            checker.check(instance='not-an-ipv4', format='ipv4')

    def test_repr(self):
        checker = FormatChecker(formats=())
        checker.checks('foo')(lambda thing: True)
        checker.checks('bar')(lambda thing: True)
        checker.checks('baz')(lambda thing: True)
        self.assertEqual(repr(checker), "<FormatChecker checkers=['bar', 'baz', 'foo']>")

    def test_duration_format(self):
        try:
            from ...jsonschema._format import is_duration
        except ImportError:
            pass
        else:
            checker = FormatChecker()
            self.assertTrue(checker.conforms(1, 'duration'))
            self.assertTrue(checker.conforms('P4Y', 'duration'))
            self.assertFalse(checker.conforms('test', 'duration'))

    def test_uuid_format(self):
        checker = FormatChecker()
        self.assertTrue(checker.conforms(1, 'uuid'))
        self.assertTrue(checker.conforms('6e6659ec-4503-4428-9f03-2e2ea4d6c278', 'uuid'))
        self.assertFalse(checker.conforms('test', 'uuid'))
