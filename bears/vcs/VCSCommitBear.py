import abc
import re

from coalib.bears.GlobalBear import GlobalBear
from coalib.results.HiddenResult import HiddenResult
from coalib.misc.Shell import run_shell_command
from collections import namedtuple
from coala_utils.decorators import (enforce_signature, generate_ordering,
                                    generate_repr)


@generate_repr(('id', hex),
               'origin',
               'raw_commit_message',
               'commit_sha',
               'commit_type',
               'modified_files',
               'added_files',
               'deleted_files',
               'message')
@generate_ordering('raw_commit_message',
                   'commit_sha',
                   'commit_type',
                   'modified_files',
                   'added_files',
                   'deleted_files',
                   'severity',
                   'confidence',
                   'origin',
                   'message_base',
                   'message_arguments',
                   'aspect',
                   'additional_info',
                   'debug_msg')
class CommitResult(HiddenResult):

    @enforce_signature
    def __init__(self, origin, raw_commit_message: str,
                 commit_sha: str, commit_type: list, modified_files: list,
                 added_files: list, deleted_files: list):
        HiddenResult.__init__(self, origin, '')
        self.raw_commit_message = raw_commit_message
        self.commit_sha = commit_sha
        self.commit_type = commit_type
        self.modified_files = modified_files
        self.added_files = added_files
        self.deleted_files = deleted_files
        self.message = 'HEAD commit information'


class VCSCommitBear(GlobalBear):
    __metaclass__ = abc.ABCMeta
    LANGUAGES = {'Git'}
    AUTHORS = {'The coala developers'}
    AUTHORS_EMAILS = {'coala-devel@googlegroups.com'}
    LICENSE = 'AGPL-3.0'

    @abc.abstractmethod
    def get_head_commit(self):
        """
        Return the commit message from the head commit
        """

    def analyze_git_commit(self, head_commit):
        commit_info = namedtuple('Commit_Info',
                                 'raw_commit_message commit_sha commit_type '
                                 'modified_files added_files deleted_files')

        raw_commit_message = head_commit

        commit_sha = run_shell_command('git rev-parse HEAD')[0].strip('\n')

        commit_type = []

        head_commit = head_commit.strip('\n')

        ciskip_regex = re.compile(r'\[ci skip\]|\[skip ci\]')
        match = re.search(ciskip_regex, head_commit)
        if match:
            commit_type.append('ci_skip_commit')

        get_parent_commits = 'git log --pretty=%P -n 1 ' + commit_sha
        parent_commits = run_shell_command(get_parent_commits)[0]
        parent_commits_list = parent_commits.split('\n')

        if len(parent_commits_list) >= 2:
            commit_type.append('merge_commit')

        get_all_committed_files = ('git show --pretty="" --name-status ' +
                                   commit_sha)
        all_committed_files = run_shell_command(get_all_committed_files)[0]
        all_committed_files = all_committed_files.split('\n')

        modified_files_list = []
        added_files_list = []
        deleted_files_list = []

        for line in all_committed_files:
            pos = line.find('\t')
            change = line[:pos]
            if change == 'M':
                modified_files_list.append(line[pos+1:])
            elif change == 'A':
                added_files_list.append(line[pos+1:])
            elif change == 'D':
                deleted_files_list.append(line[pos+1:])

        commit_info.raw_commit_message = raw_commit_message
        commit_info.commit_sha = commit_sha
        commit_info.commit_type = commit_type
        commit_info.modified_files = modified_files_list
        commit_info.added_files = added_files_list
        commit_info.deleted_files = deleted_files_list

        return (raw_commit_message, commit_sha, commit_type,
                modified_files_list, added_files_list, deleted_files_list)

    def run(self, **kwargs):
        head_commit, error = self.get_head_commit()

        if error:
            vcs_name = list(self.LANGUAGES)[0].lower()+':'
            self.err(vcs_name, repr(error))
            return

        (raw_commit_message, commit_sha, commit_type, modified_files,
            added_files, deleted_files) = self.analyze_git_commit(
            head_commit)

        yield CommitResult(self, raw_commit_message, commit_sha, commit_type,
                           modified_files, added_files, deleted_files)
