# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import base64
import datetime
import shutil
import tempfile
import uuid

from oslo_utils import timeutils

from keystone.common import config
from keystone import exception
from keystone.tests import unit as tests
from keystone.token.providers import fernet
from keystone.token.providers.fernet import token_formatters
from keystone.token.providers.fernet import utils


CONF = config.CONF


class KeyRepositoryTestMixin(object):
    def setUpKeyRepository(self):
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        self.config_fixture.config(group='fernet_tokens',
                                   key_repository=directory)

        utils.create_key_directory()
        utils.initialize_key_repository()


class TestFernetTokenProvider(tests.TestCase, KeyRepositoryTestMixin):
    def setUp(self):
        super(TestFernetTokenProvider, self).setUp()
        self.setUpKeyRepository()
        self.provider = fernet.Provider()

    def test_issue_v2_token_raises_not_implemented(self):
        """Test that exception is raised when call creating v2 token."""
        token_ref = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider.issue_v2_token,
                          token_ref)

    def test_validate_v2_token_raises_not_implemented(self):
        """Test that exception is raised when validating a v2 token."""
        token_ref = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider.validate_v2_token,
                          token_ref)

    def test_get_token_id_raises_not_implemented(self):
        """Test that an exception is raised when calling _get_token_id."""
        token_data = {}
        self.assertRaises(exception.NotImplemented,
                          self.provider._get_token_id, token_data)

    def test_invalid_token(self):
        self.assertRaises(
            exception.Unauthorized,
            self.provider.validate_v3_token,
            uuid.uuid4().hex)


class TestPayloads(tests.TestCase, KeyRepositoryTestMixin):
    def test_uuid_hex_to_byte_conversions(self):
        payload_cls = token_formatters.BasePayload

        expected_hex_uuid = uuid.uuid4().hex
        uuid_obj = uuid.UUID(expected_hex_uuid)
        expected_uuid_in_bytes = uuid_obj.bytes
        actual_uuid_in_bytes = payload_cls.convert_uuid_hex_to_bytes(
            expected_hex_uuid)
        self.assertEqual(expected_uuid_in_bytes, actual_uuid_in_bytes)
        actual_hex_uuid = payload_cls.convert_uuid_bytes_to_hex(
            expected_uuid_in_bytes)
        self.assertEqual(expected_hex_uuid, actual_hex_uuid)

    def test_time_string_to_int_conversions(self):
        payload_cls = token_formatters.BasePayload

        expected_time_str = timeutils.isotime()
        time_obj = timeutils.parse_isotime(expected_time_str)
        expected_time_int = (
            (timeutils.normalize_time(time_obj) -
             datetime.datetime.utcfromtimestamp(0)).total_seconds())

        actual_time_int = payload_cls._convert_time_string_to_int(
            expected_time_str)
        self.assertEqual(expected_time_int, actual_time_int)

        actual_time_str = payload_cls._convert_int_to_time_string(
            actual_time_int)
        self.assertEqual(expected_time_str, actual_time_str)

    def test_unscoped_payload(self):
        exp_user_id = uuid.uuid4().hex
        exp_expires_at = timeutils.isotime(timeutils.utcnow())
        exp_audit_ids = base64.urlsafe_b64encode(uuid.uuid4().bytes)[:-2]

        payload = token_formatters.UnscopedPayload.assemble(
            exp_user_id, exp_expires_at, exp_audit_ids)

        (user_id, expires_at, audit_ids) = (
            token_formatters.UnscopedPayload.disassemble(payload))

        self.assertEqual(exp_user_id, user_id)
        self.assertEqual(exp_expires_at, expires_at)
        self.assertEqual(exp_audit_ids, audit_ids)

    def test_project_scoped_payload(self):
        exp_user_id = uuid.uuid4().hex
        exp_project_id = uuid.uuid4().hex
        exp_expires_at = timeutils.isotime(timeutils.utcnow())
        exp_audit_ids = base64.urlsafe_b64encode(uuid.uuid4().bytes)[:-2]

        payload = token_formatters.ProjectScopedPayload.assemble(
            exp_user_id, exp_project_id, exp_expires_at, exp_audit_ids)

        (user_id, project_id, expires_at, audit_ids) = (
            token_formatters.ProjectScopedPayload.disassemble(payload))

        self.assertEqual(exp_user_id, user_id)
        self.assertEqual(exp_project_id, project_id)
        self.assertEqual(exp_expires_at, expires_at)
        self.assertEqual(exp_audit_ids, audit_ids)

    def test_domain_scoped_payload(self):
        exp_user_id = uuid.uuid4().hex
        exp_domain_id = uuid.uuid4().hex
        exp_expires_at = timeutils.isotime(timeutils.utcnow())
        exp_audit_ids = base64.urlsafe_b64encode(uuid.uuid4().bytes)[:-2]

        payload = token_formatters.DomainScopedPayload.assemble(
            exp_user_id, exp_domain_id, exp_expires_at, exp_audit_ids)

        (user_id, domain_id, expires_at, audit_ids) = (
            token_formatters.DomainScopedPayload.disassemble(payload))

        self.assertEqual(exp_user_id, user_id)
        self.assertEqual(exp_domain_id, domain_id)
        self.assertEqual(exp_expires_at, expires_at)
        self.assertEqual(exp_audit_ids, audit_ids)

    def test_domain_scoped_payload_with_default_domain(self):
        exp_user_id = uuid.uuid4().hex
        exp_domain_id = CONF.identity.default_domain_id
        exp_expires_at = timeutils.isotime(timeutils.utcnow())
        exp_audit_ids = base64.urlsafe_b64encode(uuid.uuid4().bytes)[:-2]

        payload = token_formatters.DomainScopedPayload.assemble(
            exp_user_id, exp_domain_id, exp_expires_at, exp_audit_ids)

        (user_id, domain_id, expires_at, audit_ids) = (
            token_formatters.DomainScopedPayload.disassemble(payload))

        self.assertEqual(exp_user_id, user_id)
        self.assertEqual(exp_domain_id, domain_id)
        self.assertEqual(exp_expires_at, expires_at)
        self.assertEqual(exp_audit_ids, audit_ids)

    def test_trust_scoped_payload(self):
        exp_user_id = uuid.uuid4().hex
        exp_project_id = uuid.uuid4().hex
        exp_expires_at = timeutils.isotime(timeutils.utcnow())
        exp_audit_ids = base64.urlsafe_b64encode(uuid.uuid4().bytes)[:-2]
        exp_trust_id = uuid.uuid4().hex

        payload = token_formatters.TrustScopedPayload.assemble(
            exp_user_id, exp_project_id, exp_expires_at, exp_audit_ids,
            exp_trust_id)

        (user_id, project_id, expires_at, audit_ids, trust_id) = (
            token_formatters.TrustScopedPayload.disassemble(payload))

        self.assertEqual(exp_user_id, user_id)
        self.assertEqual(exp_project_id, project_id)
        self.assertEqual(exp_expires_at, expires_at)
        self.assertEqual(exp_audit_ids, audit_ids)
        self.assertEqual(exp_trust_id, trust_id)