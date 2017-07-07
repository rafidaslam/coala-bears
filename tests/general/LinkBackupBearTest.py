import logging
import requests
import requests_mock
import os

import tubeup.__main__ as tubeup

from tubeup.__main__ import internetarchive

from queue import Queue

from bears.general.LinkBackupBear import (
    LinkBackupBear, known_archive_method,
    check_is_content_already_in_archiveorg)
from bears.general.URLBear import URLBear

from coalib.results.Result import Result
from coalib.settings.Section import Section
from coalib.results.RESULT_SEVERITY import RESULT_SEVERITY
from coalib.testing.LocalBearTestHelper import LocalBearTestHelper, get_results

from .MementoBearTest import custom_matcher, memento_archive_status_mock


def mocked_ia_configure(*args):
    pass


class LinkBackupBearTest(LocalBearTestHelper):

    def setUp(self):
        self.mb_check_prerequisites = URLBear.check_prerequisites
        self.section = Section('')
        URLBear.check_prerequisites = lambda *args: True
        self.uut = LinkBackupBear(self.section, Queue())

    def tearDown(self):
        URLBear.check_prerequisites = self.mb_check_prerequisites

    def test_archiveorg_success_submit_link(self):
        unarchived_urls = """
        http://iamunarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamunarchived.com', False)
            m.head('https://web.archive.org/save/http://iamunarchived.com',
                   status_code=200)

            with self.assertLogs(logging.getLogger()) as log:
                self.check_validity(self.uut, unarchived_urls)
                self.assertEqual(
                    log.output,
                    ['INFO:root:This link (http://iamunarchived.com) successfu'
                     'lly submitted with archive.org method'])

    def test_archiveis_success_submit_link(self):
        unarchived_urls = """
        http://iamunarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamunarchived.com', False)
            m.post('https://archive.is/submit/',
                   status_code=200)

            with self.assertLogs(logging.getLogger()) as log:
                self.check_validity(self.uut, unarchived_urls,
                                    settings={'archiver': 'archive.is'})
                self.assertEqual(
                    log.output,
                    ['INFO:root:This link (http://iamunarchived.com) successfu'
                     'lly submitted with archive.is method'])

    def test_youtube_to_archive_org_success_submit_link(self):
        unarchived_urls = """
        https://www.youtube.com/watch?v=unarchivedVideo
        """.splitlines()

        def mocked_tubeup_main():
            print(':: Upload Finished. Item information:')

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            # If an internet archive service had already archived the url
            # before, we still check whether the link has a relation with files
            # in archive.org. If there's no file in archive.org related to
            # the link, then we archive it.
            # We do this because most of the internet archive services
            # were not able to archive YouTube videos (they usually just
            # save the page, not the video).
            memento_archive_status_mock(
                m, 'https://www.youtube.com/watch?v=unarchivedVideo', True)

            m.get('https://archive.org/advancedsearch.php?q=originalurl%3A%22'
                  'https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DunarchivedVide'
                  'o%22&rows=50&page=1&output=json',
                  content=b'{"response": {"numFound": 0}}')

            tubeup.main = mocked_tubeup_main
            internetarchive.configure = mocked_ia_configure

            with self.assertLogs(logging.getLogger()) as log:
                self.check_validity(
                    self.uut, unarchived_urls,
                    settings={'archiver': 'youtube_to_archive.org',
                              'archiveorg_email': 'test@test.com',
                              'archiveorg_password': 'password123'})

                self.assertEqual(
                    log.output,
                    [('INFO:root:'
                      'https://www.youtube.com/watch?v=unarchivedVideo not '
                      'found in archive.org'),
                     ('INFO:root:Archiving '
                      'https://www.youtube.com/watch?v=unarchivedVideo '
                      'with tubeup.'),
                     ('INFO:root:This link '
                      '(https://www.youtube.com/watch?v=unarchivedVideo) '
                      'successfully submitted with youtube_to_archive.org '
                      'method')
                     ])

    def test_youtube_to_archive_org_ia_not_configured(self):
        unarchived_urls = """
        https://www.youtube.com/watch?v=unarchivedVideo
        """.splitlines()

        msg = (
            'youtube_to_archive.org archiving method needs email and '
            'password of an archive.org account to operate, '
            'which can be set from `archiveorg_email` and '
            '`archiveorg_password` settings, or by setting '
            '`ARCHIVEORG_EMAIL` and `ARCHIVEORG_PASSWORD` in the '
            'system environment variable.')

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(
                m, 'https://www.youtube.com/watch?v=unarchivedVideo', True)

            with self.assertLogs(logging.getLogger()) as log:
                with self.assertRaisesRegex(Exception, msg):
                    get_results(
                        self.uut, unarchived_urls,
                        settings={'archiver': 'youtube_to_archive.org'})

                self.assertEqual(
                    log.output,
                    ['ERROR:root:youtube_to_archive.org archiving method '
                     'needs email and password of an archive.org account '
                     'to operate, which can be set from `archiveorg_email` '
                     'and `archiveorg_password` settings, or by setting '
                     '`ARCHIVEORG_EMAIL` and `ARCHIVEORG_PASSWORD` in the '
                     'system environment variable.'])

    def test_youtube_to_archive_org_configure_ia_with_os_environment(self):
        unarchived_urls = """
        https://www.youtube.com/watch?v=unarchivedVideo
        """.splitlines()

        def mocked_tubeup_main():
            print(':: Upload Finished. Item information:')

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(
                m, 'https://www.youtube.com/watch?v=unarchivedVideo', True)

            m.get('https://archive.org/advancedsearch.php?q=originalurl%3A%22'
                  'https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DunarchivedVide'
                  'o%22&rows=50&page=1&output=json',
                  content=b'{"response": {"numFound": 0}}')

            tubeup.main = mocked_tubeup_main
            internetarchive.configure = mocked_ia_configure

            os.environ['ARCHIVEORG_EMAIL'] = 'test@test.com'
            os.environ['ARCHIVEORG_PASSWORD'] = 'password123'

            with self.assertLogs(logging.getLogger()) as log:
                self.check_validity(
                    self.uut, unarchived_urls,
                    settings={'archiver': 'youtube_to_archive.org'})

                self.assertEqual(
                    log.output,
                    [('INFO:root:'
                      'https://www.youtube.com/watch?v=unarchivedVideo not '
                      'found in archive.org'),
                     ('INFO:root:Archiving '
                      'https://www.youtube.com/watch?v=unarchivedVideo '
                      'with tubeup.'),
                     ('INFO:root:This link '
                      '(https://www.youtube.com/watch?v=unarchivedVideo) '
                      'successfully submitted with youtube_to_archive.org '
                      'method')
                     ])

            # Clear the environment variable, so that another test that related
            # to configuring the internetarchive library don't fail.
            del (os.environ['ARCHIVEORG_EMAIL'],
                 os.environ['ARCHIVEORG_PASSWORD'])

    def test_youtube_to_archive_org_failed_submit_link(self):
        unarchived_urls = """
        https://www.youtube.com/watch?v=unarchivedVideo
        """.splitlines()

        def mocked_tubeup_main():
            print('This is a tubeup error details')
            raise requests.exceptions.RequestException(
                'RequestException from unittest')

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(
                m, 'https://www.youtube.com/watch?v=unarchivedVideo', True)

            m.get('https://archive.org/advancedsearch.php?q=originalurl%3A%22'
                  'https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DunarchivedVide'
                  'o%22&rows=50&page=1&output=json',
                  content=b'{"response": {"numFound": 0}}')

            tubeup.main = mocked_tubeup_main
            internetarchive.configure = mocked_ia_configure

            with self.assertLogs(logging.getLogger()) as log:
                self.check_results(
                    self.uut,
                    unarchived_urls,
                    [Result.from_values(
                        'LinkBackupBear',
                        ('Failed to submit '
                         'https://www.youtube.com/watch?v=unarchivedVideo with'
                         ' youtube_to_archive.org method'),
                        severity=RESULT_SEVERITY.INFO,
                        line=2,
                        file='default')],
                    filename='default',
                    settings={'archiver': 'youtube_to_archive.org',
                              'archiveorg_email': 'test@test.com',
                              'archiveorg_password': 'password123'})

                self.assertEqual(
                    log.output,
                    [('INFO:root:'
                      'https://www.youtube.com/watch?v=unarchivedVideo not '
                      'found in archive.org'),
                     ('INFO:root:Archiving '
                      'https://www.youtube.com/watch?v=unarchivedVideo '
                      'with tubeup.'),
                     'ERROR:root:RequestException from unittest',
                     ('ERROR:root:Error has been occured from tubeup\n'
                      'Here is the log:\nThis is a tubeup error details\n')
                     ])

    def test_youtube_to_archive_org_unknown_status_submit_link(self):
        # If tubeup prints ":: Upload Finished\. Item information:", then
        # the uploading process will be assumed as done. But there are a
        # few cases when tubeup doesn't print that text, neither any error
        # message.
        unarchived_urls = """
        https://www.youtube.com/watch?v=unarchivedVideo
        """.splitlines()

        def mocked_tubeup_main():
            print('This is a tubeup log detail from tubeup')

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(
                m, 'https://www.youtube.com/watch?v=unarchivedVideo', True)

            m.get('https://archive.org/advancedsearch.php?q=originalurl%3A%22'
                  'https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DunarchivedVide'
                  'o%22&rows=50&page=1&output=json',
                  content=b'{"response": {"numFound": 0}}')

            tubeup.main = mocked_tubeup_main
            internetarchive.configure = mocked_ia_configure

            with self.assertLogs(logging.getLogger()) as log:
                self.check_results(
                    self.uut,
                    unarchived_urls,
                    [Result.from_values(
                        'LinkBackupBear',
                        ('Failed to submit '
                         'https://www.youtube.com/watch?v=unarchivedVideo with'
                         ' youtube_to_archive.org method'),
                        severity=RESULT_SEVERITY.INFO,
                        line=2,
                        file='default')],
                    filename='default',
                    settings={'archiver': 'youtube_to_archive.org',
                              'archiveorg_email': 'test@test.com',
                              'archiveorg_password': 'password123'})

                self.assertEqual(
                    log.output,
                    [('INFO:root:'
                      'https://www.youtube.com/watch?v=unarchivedVideo '
                      'not found in archive.org'),
                     ('INFO:root:Archiving '
                      'https://www.youtube.com/watch?v=unarchivedVideo '
                      'with tubeup.'),
                     ('ERROR:root:tubeup doesn\'t tell the program whether '
                      'the uploading process has been done or not. '
                      '\nHere is the log from tubeup:\nThis is'
                      ' a tubeup log detail from tubeup\n')])

    def test_archiveorg_failed_submit_link(self):
        unarchived_urls = """
        http://iamunarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamunarchived.com', False)
            m.head('https://web.archive.org/save/http://iamunarchived.com',
                   status_code=404)

            with self.assertLogs(logging.getLogger()) as log:
                self.check_results(
                    self.uut,
                    unarchived_urls,
                    [Result.from_values(
                        'LinkBackupBear',
                        ('Failed to submit http://iamunarchived.com with '
                         'archive.org method'),
                        severity=RESULT_SEVERITY.INFO,
                        line=2,
                        file='default')],
                    filename='default')

                self.assertEqual(
                    log.output,
                    ['ERROR:root:web.archive.org responds with code 404 while '
                     'submitting http://iamunarchived.com'])

    def test_archiveis_failed_submit_link(self):
        unarchived_urls = """
        http://iamunarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamunarchived.com', False)
            m.post('https://archive.is/submit/',
                   status_code=404)

            with self.assertLogs(logging.getLogger()) as log:
                self.check_results(
                    self.uut,
                    unarchived_urls,
                    [Result.from_values(
                        'LinkBackupBear',
                        ('Failed to submit http://iamunarchived.com with '
                         'archive.is method'),
                        severity=RESULT_SEVERITY.INFO,
                        line=2,
                        file='default')],
                    settings={'archiver': 'archive.is'},
                    filename='default')

                self.assertEqual(
                    log.output,
                    ['ERROR:root:archive.is responds with code 404 while '
                     'submitting http://iamunarchived.com'])

    def test_archived_link(self):
        archived_urls = """
        http://iamarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamarchived.com')

            self.check_validity(self.uut, archived_urls)

    def test_archiveorg_submit_connection_error(self):
        unarchived_urls = """
        http://iamunarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamunarchived.com', False)

            m.head('https://web.archive.org/save/http://iamunarchived.com',
                   exc=requests.exceptions.RequestException(
                       'Request failed from unittest'))

            with self.assertLogs(logging.getLogger()) as log:
                self.check_results(
                    self.uut,
                    unarchived_urls,
                    [Result.from_values(
                        'LinkBackupBear',
                        ('Failed to submit http://iamunarchived.com with '
                         'archive.org method'),
                        severity=RESULT_SEVERITY.INFO,
                        line=2,
                        file='default')],
                    filename='default')

                self.assertEqual(
                    log.output,
                    ['ERROR:root:Request failed from unittest'])

    def test_archiveis_submit_connection_error(self):
        unarchived_urls = """
        http://iamunarchived.com
        """.splitlines()

        with requests_mock.Mocker() as m:
            m.add_matcher(custom_matcher)
            memento_archive_status_mock(m, 'http://iamunarchived.com', False)

            m.post('https://archive.is/submit/',
                   exc=requests.exceptions.RequestException(
                       'Request failed from unittest'))

            with self.assertLogs(logging.getLogger()) as log:
                self.check_results(
                    self.uut,
                    unarchived_urls,
                    [Result.from_values(
                        'LinkBackupBear',
                        ('Failed to submit http://iamunarchived.com with '
                         'archive.is method'),
                        severity=RESULT_SEVERITY.INFO,
                        line=2,
                        file='default')],
                    settings={'archiver': 'archive.is'},
                    filename='default')

                self.assertEqual(
                    log.output,
                    ['ERROR:root:Request failed from unittest'])

    def test_known_archiver(self):
        self.assertEqual(known_archive_method('archive.org'), 'archive.org')
        self.assertEqual(known_archive_method('archive.is'), 'archive.is')

    def test_known_archiver_invalid(self):
        with self.assertLogs(logging.getLogger()) as log:
            self.assertRaises(ValueError, known_archive_method, 'notarchiver')
            self.assertEqual(
                log.output,
                ['ERROR:root:Invalid archive method option: notarchiver'])

    def test_check_is_content_already_in_archiveorg_available(self):
        with requests_mock.Mocker() as m:
            m.get('https://archive.org/advancedsearch.php?q=originalurl%3A%22'
                  'https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DarchivedVide'
                  'o%22&rows=50&page=1&output=json',
                  content=b'{"response": {"numFound": 2}}')
            self.assertEqual(
                check_is_content_already_in_archiveorg(
                    'https://www.youtube.com/watch?v=archivedVideo'),
                True)

    def test_check_is_content_already_in_archiveorg_not_available(self):
        with requests_mock.Mocker() as m:
            m.get('https://archive.org/advancedsearch.php?q=originalurl%3A%22'
                  'https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DunarchivedVide'
                  'o%22&rows=50&page=1&output=json',
                  content=b'{"response": {"numFound": 0}}')
            self.assertEqual(
                check_is_content_already_in_archiveorg(
                    'https://www.youtube.com/watch?v=unarchivedVideo'),
                False)

    def test_check_is_content_already_in_archiveorg_raise_exception(self):
        with requests_mock.Mocker() as m:
            m.get('https://archive.org/advancedsearch.php?q=originalurl%3A%22'
                  'https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DunknownVide'
                  'o%22&rows=50&page=1&output=json',
                  exc=requests.exceptions.RequestException(
                      'RequestException from unittest'))

            with self.assertLogs(logging.getLogger()) as log:
                with self.assertRaisesRegex(
                    requests.exceptions.RequestException,
                        r'^RequestException from unittest$'):
                    check_is_content_already_in_archiveorg(
                        'https://www.youtube.com/watch?v=unknownVideo')

                self.assertEqual(
                    log.output,
                    ['ERROR:root:RequestException from unittest'])
