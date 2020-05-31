# coding: utf-8

'''
YAML library subclasses for encoding/decoding components.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import yaml
from pydoc import locate  # For str->type.

from veredi.logger import log
from veredi.data import exceptions
from veredi import mathing

from . import base

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Base yaml.YAMLObject?
# ------------------------------------------------------------------------------

# Â§-TODO-Â§ [2020-05-21]: YAML something or other so we can barf out context in
# our errors? Or should we be throwing YAML errors instead of Veredi errors?


# ------------------------------------------------------------------------------
# Document Types
# ------------------------------------------------------------------------------

class DocComponent(base.VerediYamlDocument):
    yaml_tag = '!component'


class DocComponentExample(base.VerediYamlDocument):
    yaml_tag = '!component.example'


class DocComponentTemplate(base.VerediYamlDocument):
    yaml_tag = '!component.template'


class DocComponentRequirements(base.VerediYamlDocument):
    yaml_tag = '!component.requirements'


# ------------------------------------------------------------------------------
# Template Objects
# ------------------------------------------------------------------------------

# ---
# Property
# ---

class PropertyPsuedo(base.VerediYamlTag):
    yaml_tag = '!veredi.psuedo-property'


# ------------------------------------------------------------------------------
# Requirements Objects
# ------------------------------------------------------------------------------

# ---
# Fallback Value
# ---

class Fallback(base.VerediYamlRequirement):
    yaml_tag = '!fallback'

    def normalize(self):
        if isinstance(self.tag, str):
            value = self.tag.lower()
            self.tag = value
        else:
            raise exceptions.DataRequirementsError(
                f"'{self.yaml_tag}' requires a string for denoting key name, "
                f"got: '{self.tag}' of type '{type(self.tag)}'",
                None, None)

# ---
# Optionals
# ---

class Optional(base.VerediYamlRequirement):
    yaml_tag = '!optional'

    def normalize(self):
        if isinstance(self.tag, str):
            value = self.tag.lower()
            self.tag = value
        else:
            raise exceptions.DataRequirementsError(
                f"'{self.yaml_tag}' requires a string for denoting conditions, "
                f"got: '{self.tag}' of type '{type(self.tag)}'",
                None, None)


class OptionalInt(Optional):
    yaml_tag = '!optional.int'

    def __init__(self, value):
        super().__init__(value)

        if self.tag == 0:
            self._valid_value_fn = int.__ge__
            self._valid_comparison = 0

        elif self.tag > 0:
            self._valid_value_fn = int.__gt__
            self._valid_comparison = 0

        elif self.tag < 0:
            self._valid_value_fn = int.__lt__
            self._valid_comparison = 0

        else:
            raise exceptions.DataRequirementsError(
                f"'{self.yaml_tag}' requires integer for comparison: "
                f"negative (e.g. -1) means less-than zero; "
                f"zero (e.g. 0) means greater-than-or-equal-to zero; "
                f"positive (e.g. 1) means greater-than zero. "
                f"got: '{value}' of type '{type(value)}'",
                None, None)

    def normalize(self):
        '''
        Attempts to normalize self.tag, throws DataRequirementsError if it finds
        something invalid.
        '''
        value = self.tag
        if value is None:
            raise exceptions.DataRequirementsError(
                f"'{self.yaml_tag}' requires a value, "
                f"got: '{self.tag}' of type '{type(self.tag)}'",
                None, None)

        if isinstance(value, str):
            value = value.lower()
            cast = None
            try:
                cast = int(value)
            except ValueError:
                pass

            if cast is not None:
                value = cast
            elif (value == 'positive'
                  or value == '>'):
                value = 1
            elif (value == 'non-negative'
                  or value == '>='):
                value = 0
            elif (value == 'any'
                  or value == 'all'
                  or value == '<'):
                value = -1

        if isinstance(value, int):
            value = mathing.sign(value)
        else:
            raise exceptions.DataRequirementsError(
                f"'{self.yaml_tag}' requires: an integer or exactly "
                f"these strings: "
                f"'positive'/'>', "
                f"'non-negative'/'zero'/'>=', "
                f"or 'any'/'all'/'<'. "
                f"Got: '{value}' of type '{type(value)}'",
                None, None)

        # Ok... finally done; save our normalized value back to instance var.
        self.tag = value


    def _valid_amount(self, amount):
        return self._valid_comparison(amount, self.tag)

    @staticmethod
    def _valid_type(value):
        return (value is not None
                and isinstance(value, int))

    def valid(self, check):
        return (self._valid_type(check)
                and self._valid_amount(check))


class OptionalFromComponent(Optional):
    yaml_tag = '!optional.from.component'

    def __init__(self, value):
        super().__init__(value)
        # TODO: check that component exists?

    def normalize(self):
        # We're fine with just a string.
        pass

    def valid(self, check):
        return (value is not None
                and isinstance(value, str))

class OptionalFromComponents(Optional):
    yaml_tag = '!optional.from.components'

    def __init__(self, value):
        super().__init__(value)
        # TODO: check that components exists?

    def normalize(self):
        # We're fine with just a string.
        pass

    def valid(self, check):
        return (value is not None
                and isinstance(value, str))


class OptionalEntries(Optional):
    yaml_tag = '!optional.entries'

    _VALUES_VALID = {
        # canonical: [list, of, alternatives]
        'repeat':   ['repeating'],
    }

    def __init__(self, value):
        super().__init__(value)
        # TODO: check that component exists?

    def normalize(self):
        value = self.tag.lower()
        validated = None
        if value in self._VALUES_VALID:
            # Already a canonical name.
            validated = value
        else:
            # Look for a canonical name in the alternatives.
            for key in self._VALUES_VALID:
                alternatives = self._VALUES_VALID[key]
                if value in alternatives:
                    validated = key
                    break

        if validated:
            self.tag = validated
        else:
            raise exceptions.DataRequirementsError(
                f"'{self.yaml_tag}' requires one of these strings: "
                f"'repeat'/'repeating'. "
                f"Got: '{value}' of type '{type(value)}'",
                None, None)

    def valid(self, check):
        # No idea?
        return False


class OptionalList(Optional):
    yaml_tag = '!optional.list'

    def normalize(self):
        if (self.tag is None
                or not isinstance(self.tag, str)):
            raise exceptions.DataRequirementsError(
                f"'{self.yaml_tag}' requires string for denoting type, "
                f"got: '{self.tag}' of type '{type(self.tag)}'",
                None, None)

        try:
            value = locate(self.tag)
            self.tag = value
        except Exception as err:
            raise exceptions.DataRequirementsError(
                f"'{self.yaml_tag}' could not determine type data from "
                f"'{self.tag}'.",
                err, None) from err

    def valid(self, check):
        return (check is not None
                and isinstance(check, list)
                and all([type(each) == self.tag for each in check]))


# ---
# Requirements
# ---

class Requires(Optional):
    yaml_tag = '!require'


class RequiresInt(OptionalInt):
    yaml_tag = '!require.int'


class RequiresList(OptionalList):
    yaml_tag = '!require.list'


class RequiresFromComponent(OptionalFromComponent):
    yaml_tag = '!require.from.component'


class RequiresFromComponents(OptionalFromComponents):
    yaml_tag = '!require.from.components'


# ---
# Keys
# ---

class KeyFrom(base.VerediYamlRequirement):
    yaml_tag = '!key.from'

    def __init__(self, value):
        super().__init__(value)
        if not self._valid_type(value):
            raise exceptions.DataRequirementsError(
                f"'{self.yaml_tag}' requires string type, "
                f"got: '{value}' of type '{type(value)}'",
                None, None)

        # TODO: check that component exists?

    def normalize(self):
        # We're fine with just a string... for now.
        pass

    @staticmethod
    def _valid_type(value):
        return (value is not None
                and isinstance(value, str))

    def valid(self, check):
        return self._valid_type(self.tag)


# ---
# Variables
# ---

class Variable(base.VerediYamlRequirement):
    yaml_tag = '!variable'


class VariableLifetime(Variable):
    yaml_tag = '!variable.lifetime'

    _VALUES_VALID = {
        # canonical: [list, of, alternatives]
        'forever':   ['lifetime', 'lifelong'],
        'encounter': ['combat'],
    }

    def normalize(self):
        value = self.tag.lower()
        validated = None
        if value in self._VALUES_VALID:
            # Already a canonical name.
            validated = value
        else:
            # Look for a canonical name in the alternatives.
            for key in self._VALUES_VALID:
                alternatives = self._VALUES_VALID[key]
                if value in alternatives:
                    validated = key
                    break

        if validated:
            self.tag = validated
        else:
            raise exceptions.DataRequirementsError(
                f"'{self.yaml_tag}' requires one of these strings: "
                f"'forever'/'lifetime'/'lifelong', "
                f"'encounter'/'combat'. "
                f"Got: '{value}' of type '{type(value)}'",
                None, None)

    def valid(self, check):
        # No idea?
        return False
