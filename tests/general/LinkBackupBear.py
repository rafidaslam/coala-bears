import requests
import requests_mock

from queue import Queue

from bears.general.LinkBackupBear import LinkBackupBear
from bears.general.URLBear import URLBear

from coalib.results.Result import Result
from coalib.settings.Section import Section
from coalib.results.RESULT_SEVERITY import RESULT_SEVERITY
from coalib.testing.LocalBearTestHelper import LocalBearTestHelper

from .MementoBearTest import custom_matcher, memento_archive_status_mock


def mock_internet_archive_resp(
        m,
        url,
        exception=None,
        code=200,
        archive_service_url=LinkBackupBear.ARCHIVE_SAVE_URL_TEMPLATE):
    save_url = archive_service_url % url
    if exception:
        m.head(save_url,
               exc=exception)
    else:
        m.head(save_url, status_code=code)


class LinkBackupBearTest(LocalBearTestHelper):

    def setUp(self):
        self.mb_check_prerequisites = URLBear.check_prerequisites
        self.section = Section('')
        URLBear.check_prerequisites = lambda *args: True
        self.uut = LinkBackupBear(self.section, Queue())

    def tearDown(self):
        URLBear.check_prerequisites = self.mb_check_prerequisites

    def test_success_submit_link(self):
        unarchived_urls = """
        http://iamunarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamunarchived.com', False)
            mock_internet_archive_resp(m, 'http://iamunarchived.com', code=200)

            self.check_results(
                self.uut,
                unarchived_urls,
                [Result.from_values(
                    'LinkBackupBear',
                    ('This link (http://iamunarchived.com) successfully '
                     'submitted to https://web.archive.org/save/%s'),
                    severity=RESULT_SEVERITY.INFO,
                    line=2,
                    file='default')],
                filename='default')

    def test_failed_submit_link(self):
        unarchived_urls = """
        http://iamunarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamunarchived.com', False)
            mock_internet_archive_resp(m, 'http://iamunarchived.com', code=404)

            self.check_results(
                self.uut,
                unarchived_urls,
                [Result.from_values(
                    'LinkBackupBear',
                    ('Failed to submit http://iamunarchived.com to '
                     'https://web.archive.org/save/%s'),
                    severity=RESULT_SEVERITY.INFO,
                    line=2,
                    file='default')],
                filename='default')

    def test_archived_link(self):
        archived_urls = """
        http://iamarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamarchived.com')

            self.check_validity(self.uut, archived_urls)

    def test_submit_connection_error(self):
        unarchived_urls = """
        http://iamunarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamunarchived.com', False)

            mock_internet_archive_resp(
                m,
                'http://iamunarchived.com',
                exception=requests.exceptions.RequestException)

            self.check_results(
                self.uut,
                unarchived_urls,
                [Result.from_values(
                    'LinkBackupBear',
                    ('Failed to submit http://iamunarchived.com to '
                     'https://web.archive.org/save/%s'),
                    severity=RESULT_SEVERITY.INFO,
                    line=2,
                    file='default')],
                filename='default')
