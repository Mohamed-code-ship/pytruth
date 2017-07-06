# Copyright 2017 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests convert module."""

import hashlib
import os
import tempfile
import unittest

import convert
os.environ.setdefault('PBR_VERSION', '1.10.0')
from mock import mock
from pyglib import app
import truth


AssertThat = truth.AssertThat     # pylint: disable=invalid-name


class ConvertTest(unittest.TestCase):

  INPUT_PY = 'input.py'
  TRUTH_DIR = os.path.join(
      os.environ['TEST_SRCDIR'], os.environ['TEST_WORKSPACE'], 'truth')
  TESTDATA = os.path.join(TRUTH_DIR, 'testdata')

  @classmethod
  def _Checksum(cls, path):
    with open(path, 'rb') as f:
      return hashlib.sha512(f.read()).hexdigest()

  def setUp(self):
    self.temp_file = tempfile.NamedTemporaryFile(
        prefix='truth-', suffix='.py', delete=False)

  def tearDown(self):
    os.unlink(self.temp_file.name)

  def _Test(self, name, expected_return_code=0):
    """Verifies that the input file is converted as expected."""

    # Copy the contents of the input file to a temporary file.
    with open(os.path.join(self.TESTDATA, '{0}-input.py'.format(name))) as f:
      input_contents = f.read()

    self.temp_file.write(input_contents)
    self.temp_file.close()

    # Convert the temporary file in-place.
    return_code = convert.main([self.temp_file.name])

    # Check the return code.
    AssertThat(return_code).IsEqualTo(expected_return_code)

    # Check the contents line by line.
    # This is not strictly necessary given the SHA-512 verification, but it
    # makes debugging test failures easier.
    expected_path = os.path.join(self.TESTDATA, '{0}-expected.py'.format(name))
    line = 0
    with open(self.temp_file.name) as converted_file:
      with open(expected_path) as expected_file:
        for converted_line in converted_file:
          line += 1
          name = 'at line {0}'.format(line)
          expected_line = expected_file.readline()
          AssertThat(converted_line).Named(name).IsEqualTo(expected_line)

    # Verify the contents are exactly identical.
    actual_hash = self._Checksum(self.temp_file.name)
    expected_hash = self._Checksum(expected_path)
    AssertThat(actual_hash).IsEqualTo(expected_hash)

  def testConvertEverything(self):
    self._Test('everything')

  def testUnbalancedParanthesesDoesNotOverwriteFile(self):
    self._Test('unbalanced', 1)

  def testNoFilesGiven(self):
    AssertThat(convert.main(['convert'])).IsNonZero()

  @mock.patch.object(convert.Converter, '_Check', return_value=False)
  def testCheckFails(self, mock_check):
    AssertThat(convert.main(['convert', self.INPUT_PY])).IsNonZero()
    AssertThat(mock_check).WasCalled().Once()

  @mock.patch.object(os.path, 'isfile', return_value=False)
  def testCheckNonexistentInputFile(self, mock_isfile):
    converter = convert.Converter([self.INPUT_PY])
    AssertThat(converter._Check()).IsFalse()
    AssertThat(mock_isfile).WasCalled().Once().With(self.INPUT_PY)

  @mock.patch.object(os.path, 'isfile', return_value=True)
  @mock.patch.object(os, 'access', return_value=False)
  def testCheckUnreadableInputFile(self, mock_access, mock_isfile):
    converter = convert.Converter([self.INPUT_PY])
    AssertThat(converter._Check()).IsFalse()
    AssertThat(mock_isfile).WasCalled().Once().With(self.INPUT_PY)
    AssertThat(mock_access).WasCalled().Once().With(self.INPUT_PY, os.R_OK)

  @mock.patch.object(os.path, 'isfile', return_value=True)
  @mock.patch.object(os, 'access', side_effect=(True, False))
  def testCheckUnwritableInputFile(self, mock_access, mock_isfile):
    converter = convert.Converter([self.INPUT_PY])
    AssertThat(converter._Check()).IsFalse()
    AssertThat(mock_isfile).WasCalled().Once().With(self.INPUT_PY)
    AssertThat(mock_access).WasCalled().With(self.INPUT_PY, os.R_OK)
    AssertThat(mock_access).WasCalled().LastWith(self.INPUT_PY, os.W_OK)

  @mock.patch.object(os.path, 'isfile', return_value=True)
  @mock.patch.object(os, 'access', side_effect=(True, True))
  def testCheckAccessOk(self, mock_access, mock_isfile):
    converter = convert.Converter([self.INPUT_PY])
    AssertThat(converter._Check()).IsTrue()
    AssertThat(mock_isfile).WasCalled().Once().With(self.INPUT_PY)
    AssertThat(mock_access).WasCalled().With(self.INPUT_PY, os.R_OK)
    AssertThat(mock_access).WasCalled().LastWith(self.INPUT_PY, os.W_OK)


def main(unused_args):
  unittest.main()


if __name__ == '__main__':
  convert.DefineFlags()
  app.run()
