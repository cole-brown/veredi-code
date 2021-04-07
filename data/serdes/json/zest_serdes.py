# coding: utf-8

'''
Tests for the JSON serializer/deserializer.
'''

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from typing import Union, Type

import datetime

from veredi.zest.base.unit   import ZestBase
from veredi.zest.zpath       import TestType

from veredi.base             import paths
from veredi.base.context     import UnitTestContext
from veredi.data             import background
from veredi.data.context     import DataAction
from veredi.data.codec       import Codec

from .serdes                 import JsonSerdes

from veredi.zest             import zpath


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Test Code
# -----------------------------------------------------------------------------

class Test_JsonSerdes(ZestBase):

    # -------------------------------------------------------------------------
    # Constasts
    # -------------------------------------------------------------------------

    _DATA_META = {
        'author': 'Cole Brown',
        'date': datetime.date(2020, 5, 22),
        'display-name': 'Veredi Unit-Testing Health Component',
        'doc-type': 'metadata',
        'name': 'veredi.unit-test.component.health',
        'record-type': 'veredi.unit-test',
        'source': 'veredi.unit-test',
        'system': 'unit-test',
        'version': datetime.date(2020, 5, 19)
    }
    '''
    As of [2021-02-08], this is a python dict representation of the
    self.path_meta file.
    '''

    _DATA_COMP = {
        'doc-type': 'component',
        'health': {
            'current': {
                'hit-points': '${sum(${health.current.*})}',
                'permanent': 35,
                'temporary': 11,
            },
            'death': {
                'hit-points': '-${min(0, ${ability.constitution.score})}',
            },
            'maximum': {
                'class': [
                    {
                        'angry-unschooled-fighter': 1,
                        'hit-points': 12,
                    },
                    {
                        'angry-unschooled-fighter': 2,
                        'hit-points': 9,
                    },
                    {
                        'hit-points': 2,
                        'monastery-student': 3,
                    },
                    {
                        'angry-unschooled-fighter': 4,
                        'hit-points': 12,
                    }
                ],
                'hit-points': '${sum(${health.maximum.*.hit-points})}',
                'level': [
                    {
                        'angry-unschooled-fighter': [1, 4],
                        'hit-points': 2,
                    },
                ],
            },
            'resistance': {
                'bludgeoning': 1,
                'piercing': 1,
                'slashing': 1,
            },
            'unconscious': {
                'hit-points': 0,
            },
        },
        'meta': {
            'registry': 'veredi.unit-test.health',
        },
    }

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def set_dotted(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.dotted = __file__

    def set_type(self) -> None:
        '''
        Set test class's `dotted` class-level descriptor.
        '''
        self.type = TestType.UNIT

    def set_up(self):
        self.serdes = JsonSerdes()
        self.codec = Codec()
        self.path_all = zpath.serdes() / 'component.health.json'
        self.path_meta = zpath.serdes() / 'only.meta.json'
        self.path_comp = zpath.serdes() / 'only.component.json'

    def tear_down(self):
        self.serdes = None
        self.codec = None
        self.path_all = None
        self.path_meta = None
        self.path_comp = None

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def context(self,
                test_name: str,
                filepath:  paths.Path) -> UnitTestContext:
        # Serdes don't require their own context - they just use whatever.
        # Usually a DataLoadContext/DataSaveContext, sometimes a
        # DataBareContext...
        #
        # Just use a UnitTestContext so we can assign data easy.
        context = UnitTestContext(self,
                                  test_name=test_name,
                                  data={
                                      'file': filepath,
                                  })
        return context

    def _metadata_check(self,
                        test_name: str,
                        data:      dict,
                        path:      paths.Path) -> bool:
        '''
        Verify that the metadata in 'data' is correct.
        '''
        passed = False
        with self.subTest(test=test_name,
                          name='metadata_check',
                          path=path):
            self.assertIsNotNone(data)
            self.assertIsInstance(data, dict)

            metadata = data

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
            passed = True

        return passed

    def _component_check(self,
                         test_name: str,
                         data:      dict,
                         path:      paths.Path) -> bool:
        '''
        Verify that the component data in 'data' is correct.
        '''
        passed = False
        with self.subTest(test=test_name,
                          name='component_check',
                          path=path):
            self.assertIsNotNone(data)
            self.assertIsInstance(data, dict)

            component = data

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
            passed = True

        return passed

    # -------------------------------------------------------------------------
    # Tests
    # -------------------------------------------------------------------------

    # ------------------------------
    # Simpler Tests
    # ------------------------------

    def test_init(self):
        # ------------------------------
        # Data
        # ------------------------------
        self.assertTrue(self._DATA_META)
        self.assertTrue(self._DATA_COMP)

        # ------------------------------
        # Paths
        # ------------------------------
        self.assertTrue(self.path_all)
        self.assertTrue(self.path_all.exists())
        self.assertTrue(self.path_all.is_file())

        self.assertTrue(self.path_meta)
        self.assertTrue(self.path_meta.exists())
        self.assertTrue(self.path_meta.is_file())

        self.assertTrue(self.path_comp)
        self.assertTrue(self.path_comp.exists())
        self.assertTrue(self.path_comp.is_file())

        # ------------------------------
        # Serdes
        # ------------------------------
        # ---
        # The Serdes Itself
        # ---
        self.assertTrue(self.serdes)
        # (and friend!)
        self.assertTrue(self.codec)

        # ---
        # Background
        # ---
        bg, _ = self.serdes.background
        self.assertTrue(bg)
        self.assertIsInstance(bg, dict)
        self.assertIn('dotted', bg)
        self.assertEqual(bg['dotted'], self.serdes.dotted)
        self.assertEqual(bg['dotted'], 'veredi.serdes.json')
        self.assertIn('type', bg)
        self.assertEqual(bg['type'], self.serdes.name)
        self.assertEqual(bg['type'], 'json')

        # ---
        # Context
        # ---
        test_context = self.context('test_init', self.path_all)
        key = str(background.Name.SERDES)
        self.assertNotIn(key, test_context)
        serdes_context = self.serdes._context_data(test_context,
                                                   DataAction.SAVE,
                                                   self.codec)
        # _context_data() should add to the existing context.
        self.assertIs(test_context, serdes_context)
        self.assertIn(key, serdes_context)
        serdes_data = serdes_context[key]
        self.assertIn('meta', serdes_data)
        self.assertEqual(serdes_data['meta'], bg)
        self.assertIn('action', serdes_data)
        self.assertEqual(serdes_data['action'], DataAction.SAVE)

    # ------------------------------
    # Read Tests
    # ------------------------------

    def test_read_one_meta(self):
        data = None
        with self.path_meta.open('r') as file_stream:
            data = self.serdes._read(
                file_stream,
                self.codec,
                self.context('test_read_one_meta', self.path_meta))

        self.assertIsNotNone(data)
        # We should have only a meta document:
        self.assertIsInstance(data, dict)

        self._metadata_check('test_read_one_meta',
                             data,
                             self.path_meta)

    def test_read_one_comp(self):
        data = None
        with self.path_comp.open('r') as file_stream:
            data = self.serdes._read(
                file_stream,
                self.codec,
                self.context('test_read_one_comp', self.path_comp))

        self.assertIsNotNone(data)
        # We should have only a comp document:
        self.assertIsInstance(data, dict)

        self._component_check('test_read_one_comp',
                              data,
                              self.path_comp)

    def test_read_all(self):
        data = None
        with self.path_all.open('r') as file_stream:
            data = self.serdes._read_all(
                file_stream,
                self.codec,
                self.context('test_read_all', self.path_all))

        self.assertIsNotNone(data)
        self.assertIsInstance(data, list)
        # We should have these documents in this order:
        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], dict)
        self.assertIsInstance(data[1], dict)

        self._metadata_check('test_read_all',
                             data[0],
                             self.path_all)

        self._component_check('test_read_all',
                              data[1],
                              self.path_all)

    # ------------------------------
    # Deserialize Tests
    # ------------------------------

    def test_deserialize_one_meta(self):
        data = None
        with self.path_meta.open('r') as file_stream:
            data = self.serdes.deserialize(
                file_stream,
                self.codec,
                self.context('test_deserialize_one_meta', self.path_meta))

        self.assertIsNotNone(data)
        # We should have only a meta document... but it should have been
        # deserialized into a dict.
        self.assertIsInstance(data, dict)

        self._metadata_check('test_deserialize_one_meta',
                             data,
                             self.path_meta)

    def test_deserialize_one_comp(self):
        data = None
        with self.path_comp.open('r') as file_stream:
            data = self.serdes.deserialize(
                file_stream,
                self.codec,
                self.context('test_deserialize_one_comp', self.path_comp))

        self.assertIsNotNone(data)
        # We should have only a comp document... but it should have been
        # deserialized into a dict.
        self.assertIsInstance(data, dict)

        self._component_check('test_deserialize_one_comp',
                              data,
                              self.path_comp)

    def test_deserialize_all(self):
        data = None
        with self.path_all.open('r') as file_stream:
            data = self.serdes.deserialize_all(
                file_stream,
                self.codec,
                self.context('test_deserialize_all', self.path_all))

        self.assertIsNotNone(data)
        # We should have these documents in this order:
        self.assertEqual(len(data), 2)
        self.assertIsInstance(data[0], dict)
        self.assertIsInstance(data[1], dict)

        self._metadata_check('test_deserialize_all',
                             data[0],
                             self.path_all)

        self._component_check('test_deserialize_all',
                              data[1],
                              self.path_all)

    # ------------------------------
    # Write Tests
    # ------------------------------

    def test_write_one_meta(self):
        # Need something to serialize first...
        write_data = self._DATA_META

        self.assertIsNotNone(write_data)
        self.assertIsInstance(write_data, dict)

        passed = self._metadata_check('test_write_one_meta:write',
                                      write_data,
                                      self.path_meta)
        if not passed:
            self.fail("test_write_one_meta:write - write check failed.")

        context = self.context('test_write_one_meta', self.path_meta)

        # Can't just read file and compare strings... there's no guarentee of
        # preserving ordering. Best we can do is...
        #   1) write,
        #   2) read,
        #   3) and make sure we have the same before & after data.
        read_data = None
        # ---
        # 1) Write!
        # ---
        with self.serdes._write(write_data, self.codec, context) as stream:
            # ---
            # 2) Read!
            # ---
            read_data = self.serdes._read(stream, self.codec, context)

        # ---
        # 3) Check data!
        # ---
        self.assertIsNotNone(read_data)
        self.assertIsInstance(read_data, dict)

        self._metadata_check('test_write_one_meta:read',
                             read_data,
                             self.path_meta)

    def test_write_one_comp(self):
        # Need something to serialize first...
        write_data = self._DATA_COMP

        self.assertIsNotNone(write_data)
        self.assertIsInstance(write_data, dict)

        passed = self._component_check('test_write_one_comp:write',
                                       write_data,
                                       self.path_comp)
        if not passed:
            self.fail("test_write_one_comp:write - write check failed.")

        context = self.context('test_write_one_comp', self.path_comp)

        # Can't just read file and compare strings... there's no guarentee of
        # preserving ordering. Best we can do is...
        #   1) write,
        #   2) read,
        #   3) and make sure we have the same before & after data.
        read_data = None
        # ---
        # 1) Write!
        # ---
        with self.serdes._write(write_data, self.codec, context) as stream:
            # ---
            # 2) Read!
            # ---
            read_data = self.serdes._read(stream, self.codec, context)

        # ---
        # 3) Check data!
        # ---
        self.assertIsNotNone(read_data)
        self.assertIsInstance(read_data, dict)

        self._component_check('test_write_one_comp:read',
                              read_data,
                              self.path_comp)

    def test_write_all(self):
        # Need something to serialize first... A 'write all' needs to be, in
        # this case (to match our self.path_all file data), a list of our meta
        # dict and our comp dict.
        write_data = [self._DATA_META, self._DATA_COMP]

        self.assertIsNotNone(write_data)
        self.assertIsInstance(write_data, list)

        self.assertIsInstance(write_data[0], dict)
        self.assertIsInstance(write_data[1], dict)

        passed = self._metadata_check('test_write_all:write',
                                      write_data[0],
                                      self.path_all)
        if not passed:
            self.fail("test_write_all:write - metadata write check failed.")

        passed = self._component_check('test_write_all:write',
                                       write_data[1],
                                       self.path_all)
        if not passed:
            self.fail("test_write_all:write - component write check failed.")

        context = self.context('test_write_all', self.path_all)

        # Can't just read file and compare strings... there's no guarentee of
        # preserving ordering. Best we can do is...
        #   1) write,
        #   2) read,
        #   3) and make sure we have the same before & after data.
        read_data = None
        # ---
        # 1) Write!
        # ---
        with self.serdes._write(write_data, self.codec, context) as stream:
            # ---
            # 2) Read!
            # ---
            read_data = self.serdes._read(stream, self.codec, context)

        # ---
        # 3) Check data!
        # ---
        self.assertIsNotNone(read_data)
        self.assertIsInstance(read_data, list)
        self.assertEqual(len(read_data), 2)

        self.assertIsInstance(read_data[0], dict)
        self.assertIsInstance(read_data[1], dict)

        self._metadata_check('test_write_all:read',
                             read_data[0],
                             self.path_all)

        self._component_check('test_write_all:read',
                              read_data[1],
                              self.path_all)

    # ------------------------------
    # Serialize Tests
    # ------------------------------

    def test_serialize_one_meta(self):
        # Need something to serialize first...
        serialize_data = self._DATA_META

        self.assertIsNotNone(serialize_data)
        self.assertIsInstance(serialize_data, dict)

        passed = self._metadata_check('test_serialize_one_meta:serialize',
                                      serialize_data,
                                      self.path_meta)
        if not passed:
            self.fail("test_serialize_one_meta:serialize "
                      "- serialize check failed.")

        context = self.context('test_serialize_one_meta', self.path_meta)

        # Can't just read file and compare strings... there's no guarentee of
        # preserving ordering. Best we can do is...
        #   1) serialize,
        #   2) deserialize,
        #   3) and make sure we have the same before & after data.
        deserialize_data = None
        # ---
        # 1) Serialize!
        # ---
        with self.serdes.serialize(serialize_data,
                                   self.codec,
                                   context) as stream:
            # ---
            # 2) Deserialize!
            # ---
            deserialize_data = self.serdes.deserialize(stream,
                                                       self.codec,
                                                       context)

        # ---
        # 3) Check data!
        # ---
        self.assertIsNotNone(deserialize_data)
        self.assertIsInstance(deserialize_data, dict)

        self._metadata_check('test_serialize_one_meta:deserialize',
                             deserialize_data,
                             self.path_meta)

    def test_serialize_one_comp(self):
        # Need something to serialize first...
        serialize_data = self._DATA_COMP

        self.assertIsNotNone(serialize_data)
        self.assertIsInstance(serialize_data, dict)

        passed = self._component_check('test_serialize_one_comp:serialize',
                                       serialize_data,
                                       self.path_comp)
        if not passed:
            self.fail("test_serialize_one_comp:serialize "
                      "- serialize check failed.")

        context = self.context('test_serialize_one_comp', self.path_comp)

        # Can't just read file and compare strings... there's no guarentee of
        # preserving ordering. Best we can do is...
        #   1) serialize,
        #   2) deserialize,
        #   3) and make sure we have the same before & after data.
        deserialize_data = None
        # ---
        # 1) Serialize!
        # ---
        with self.serdes.serialize(serialize_data,
                                   self.codec,
                                   context) as stream:
            # ---
            # 2) Deserialize!
            # ---
            deserialize_data = self.serdes.deserialize(stream,
                                                       self.codec,
                                                       context)

        # ---
        # 3) Check data!
        # ---
        self.assertIsNotNone(deserialize_data)
        self.assertIsInstance(deserialize_data, dict)

        self._component_check('test_serialize_one_comp:deserialize',
                              deserialize_data,
                              self.path_comp)

    def test_serialize_all(self):
        # Need something to serialize first... A 'serialize all' needs to be,
        # in this case (to match our self.path_all file data), a list of our
        # meta dict and our comp dict.
        serialize_data = [self._DATA_META, self._DATA_COMP]

        self.assertIsNotNone(serialize_data)
        self.assertIsInstance(serialize_data, list)

        self.assertIsInstance(serialize_data[0], dict)
        self.assertIsInstance(serialize_data[1], dict)

        passed = self._metadata_check('test_serialize_all:serialize',
                                      serialize_data[0],
                                      self.path_all)
        if not passed:
            self.fail("test_serialize_all:serialize "
                      "- metadata serialize check failed.")

        passed = self._component_check('test_serialize_all:serialize',
                                       serialize_data[1],
                                       self.path_all)
        if not passed:
            self.fail("test_serialize_all:serialize "
                      "- component serialize check failed.")

        context = self.context('test_serialize_all', self.path_all)

        # Can't just read file and compare strings... there's no guarentee of
        # preserving ordering. Best we can do is...
        #   1) serialize,
        #   2) deserialize,
        #   3) and make sure we have the same before & after data.
        deserialize_data = None
        # ---
        # 1) Serialize!
        # ---
        with self.serdes.serialize(serialize_data,
                                   self.codec,
                                   context) as stream:
            # ---
            # 2) Deserialize!
            # ---
            deserialize_data = self.serdes.deserialize(stream,
                                                       self.codec,
                                                       context)

        # ---
        # 3) Check data!
        # ---
        self.assertIsNotNone(deserialize_data)
        self.assertIsInstance(deserialize_data, list)
        self.assertEqual(len(deserialize_data), 2)

        self.assertIsInstance(deserialize_data[0], dict)
        self.assertIsInstance(deserialize_data[1], dict)

        self._metadata_check('test_serialize_all:deserialize',
                             deserialize_data[0],
                             self.path_all)

        self._component_check('test_serialize_all:deserialize',
                              deserialize_data[1],
                              self.path_all)


# --------------------------------Unit Testing---------------------------------
# --                      Main Command Line Entry Point                      --
# -----------------------------------------------------------------------------

# Can't just run file from here... Do:
#   doc-veredi run data/serdes/json/zest_serdes.py

if __name__ == '__main__':
    import unittest
    unittest.main()
