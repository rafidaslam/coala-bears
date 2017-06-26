import requests

from bears.general.MementoBear import MementoBear

from coalib.bears.LocalBear import LocalBear
from coalib.results.Result import Result
from coalib.results.HiddenResult import HiddenResult
from coalib.results.RESULT_SEVERITY import RESULT_SEVERITY
from dependency_management.requirements.PipRequirement import PipRequirement


class LinkBackupBear(LocalBear):
    LANGUAGES = {'All'}
    REQUIREMENTS = {PipRequirement('requests', '2.12')}
    AUTHORS = {'The coala developers'}
    AUTHORS_EMAILS = {'coala-devel@googlegroups.com'}
    LICENSE = 'AGPL-3.0'
    CAN_DETECT = {'Documentation'}
    BEAR_DEPS = {MementoBear}
    ARCHIVE_SAVE_URL_TEMPLATE = 'https://web.archive.org/save/%s'

    def submit_to_archive_org(self, url):
        try:
            resp = requests.head(self.ARCHIVE_SAVE_URL_TEMPLATE % url)
        except requests.exceptions.RequestException:
            return False
        else:
            if resp.status_code == 200:
                return True
            return False

    def run(self, filename, file, dependency_results=dict(),
            archive_url_template: str=ARCHIVE_SAVE_URL_TEMPLATE):
        """
        Find unarchived links and submit them to archive.org

        Link is considered valid if the link has been archived by any services
        in memento_client.

        This bear can automatically fix redirects.

        Warning: This bear will make HEAD requests to all URLs mentioned in
        your codebase, which can potentially be destructive. As an example,
        this bear would naively just visit the URL from a line that goes like
        `do_not_ever_open = 'https://api.acme.inc/delete-all-data'` wiping out
        all your data.

        :param dependency_results:   Results given by URLBear.
        :param archive_url_template: Internet archive service save url
                                     default to
                                     "https://web.archive.org/save/%s".
        """
        for result in dependency_results.get(MementoBear.name, []):
            if isinstance(result, HiddenResult):
                unarchived_url = result.contents['unarchived_url']
                line_number = result.contents['line_number']

                if self.submit_to_archive_org(unarchived_url):
                    yield Result.from_values(
                        self,
                        ('This link (%s) successfully submitted to %s' %
                         (unarchived_url, self.ARCHIVE_SAVE_URL_TEMPLATE)),
                        file=filename,
                        line=line_number,
                        severity=RESULT_SEVERITY.INFO
                        )
                else:
                    yield Result.from_values(
                        self,
                        ('Failed to submit %s to %s' %
                         (unarchived_url, self.ARCHIVE_SAVE_URL_TEMPLATE)),
                        file=filename,
                        line=line_number,
                        severity=RESULT_SEVERITY.INFO
                        )
