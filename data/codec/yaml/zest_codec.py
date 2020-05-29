# coding: utf-8

'''
Tests for the generic System class.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import unittest
import datetime

from .codec import YamlCodec
from .document import DocMetadata
from .component import DocComponent

from veredi.zest import zpath


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_YamlCodec(unittest.TestCase):

    def setUp(self):
        self.codec = YamlCodec()
        self.path = zpath.codec() / 'component.health.yaml'

    def tearDown(self):
        self.codec = None
        self.path = None

    def context(self):
        return {
            'unit-test': self.__class__.__name__,
            'file':      self.path,
        }

    def test_init(self):
        self.assertTrue(self.codec)
        self.assertTrue(self.path)
        self.assertTrue(self.path.exists())

    def test_load(self):
        loaded = None
        with self.path.open('r') as f:
            loaded = self.codec._load_all(f, self.context())

        self.assertIsNotNone(loaded)
        # We should have these documents in this order:
        self.assertEqual(len(loaded), 2)
        self.assertEqual(type(loaded[0]), DocMetadata)
        self.assertEqual(type(loaded[1]), DocComponent)

    def test_metadata(self):
        loaded = None
        with self.path.open('r') as f:
            loaded = self.codec._load_all(f, self.context())

        self.assertIsNotNone(loaded)
        self.assertEqual(type(loaded[0]), DocMetadata)
        metadata = loaded[0].decode()

        self.assertEqual(metadata['record-type'],
                         'veredi.unit-test')
        self.assertEqual(metadata['version'],
                         datetime.date(2020, 5, 19))
        self.assertEqual(metadata['source'],
                         'veredi.unit-test')
        self.assertEqual(metadata['author'],
                         'Cole Brown')
        self.assertEqual(metadata['date'],
                         datetime.date(2020, 5, 22))
        self.assertEqual(metadata['system'],
                         'unit-test')
        self.assertEqual(metadata['name'],
                         'veredi.unit-test.component.health')
        self.assertEqual(metadata['display-name'],
                         'Veredi Unit-Testing Health Component')

    def test_component(self):
        loaded = None
        with self.path.open('r') as f:
            loaded = self.codec._load_all(f, self.context())

        self.assertIsNotNone(loaded)
        self.assertEqual(type(loaded[1]), DocComponent)
        component = loaded[1].decode()

        meta = component.get('meta', {})
        self.assertTrue(meta)
        self.assertEqual(meta['registry'],
                         'veredi.unit-test.health')

        health = component.get('health', {})
        self.assertTrue(health)
        current = health.get('current', {})
        self.assertTrue(current)
        self.assertEqual(current['hit-points'],
                         '${sum(${health.current.*})}')
        self.assertEqual(current['permanent'], 35)
        self.assertEqual(current['temporary'], 11)

        maximum = health.get('maximum', {})
        self.assertTrue(maximum)
        klass = maximum.get('class', {})
        self.assertTrue(klass)
        self.assertIsInstance(klass, list)
        self.assertEqual(klass[0]['angry-unschooled-fighter'], 1)
        self.assertEqual(klass[0]['hit-points'], 12)
        self.assertEqual(klass[1]['angry-unschooled-fighter'], 2)
        self.assertEqual(klass[1]['hit-points'], 9)
        self.assertEqual(klass[2]['monastery-student'], 3)
        self.assertEqual(klass[2]['hit-points'], 2)
        self.assertEqual(klass[3]['angry-unschooled-fighter'], 4)
        self.assertEqual(klass[3]['hit-points'], 12)

        level = maximum.get('level', {})
        self.assertTrue(level)
        self.assertIsInstance(level, list)
        self.assertEqual(level[0]['angry-unschooled-fighter'], [1, 4])
        self.assertEqual(level[0]['hit-points'], 2)

        self.assertEqual(maximum['hit-points'],
                         '${sum(${health.maximum.*.hit-points})}')

        unconscious = health.get('unconscious', {})
        self.assertTrue(unconscious)
        self.assertEqual(unconscious['hit-points'], 0)

        death = health.get('death', {})
        self.assertTrue(death)
        self.assertEqual(death['hit-points'],
                         '-${min(0, ${ability.constitution.score})}')

        resistance = health.get('resistance', {})
        self.assertTrue(resistance)
        self.assertEqual(resistance['piercing'], 1)
        self.assertEqual(resistance['bludgeoning'], 1)
        self.assertEqual(resistance['slashing'], 1)
