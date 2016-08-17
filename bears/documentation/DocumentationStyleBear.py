from coalib.bearlib.languages.documentation.DocumentationComment import (
    DocumentationComment)
from coalib.bearlib.languages.documentation.DocstyleDefinition import (
    DocstyleDefinition)
from coalib.bearlib.languages.documentation.DocumentationExtraction import (
    extract_documentation)
from coalib.bears.LocalBear import LocalBear
from coalib.results.Diff import Diff
from coalib.results.Result import Result


class DocumentationStyleBear(LocalBear):
    LANGUAGES = {language for docstyle, language in
                 DocstyleDefinition.get_available_definitions()}
    AUTHORS = {'The coala developers'}
    AUTHORS_EMAILS = {'coala-devel@googlegroups.com'}
    LICENSE = 'AGPL-3.0'
    ASCIINEMA_URL = 'https://asciinema.org/a/7sfk3i9oxs1ixg2ncsu3pym0u'
    CAN_DETECT = {'Documentation'}

    def run(self, filename, file, docstyle: str, language: str):
        """
        Checks for certain in-code documentation styles.

        It currently checks for the following style: ::

            hello
            :param x:
                4 space indent
            :return:
                also 4 space indent
                following lines are also 4 space indented

        :param docstyle: The docstyle to use.
        :param language: The programming language of the file(s).
        """
        for doc_comment in extract_documentation(file, language, docstyle):
            metadata = iter(doc_comment.parse())

            # Assuming that the first element is always the only description.
            new_metadata = [next(metadata)]
            for m in metadata:
                stripped_desc = list(map(str.lstrip, m.desc.splitlines(True)))
                stripped_desc_length = len(stripped_desc)
                new_desc = ""
                if stripped_desc_length == 1:
                    stripped_desc[0] = ('\n' + ' ' * 4 + stripped_desc[0]
                                        if not stripped_desc[0] == ''
                                        else stripped_desc[0])

                if stripped_desc_length == 2:
                    stripped_desc[0] = ('\n' + ' ' * 4 + stripped_desc[0]
                                        if stripped_desc[0] == '' or
                                        stripped_desc[1].endswith("\n")
                                        else stripped_desc[0])
                    new_desc = stripped_desc[0] + stripped_desc[1]
                elif stripped_desc_length != 0:
                    new_desc = ''.join(('\n' if line == '' else ' ' * 4) +
                                       line for line in stripped_desc)
                new_metadata.append(m._replace(desc=new_desc.lstrip(' ')))

            new_comment = DocumentationComment.from_metadata(
                new_metadata, doc_comment.docstyle_definition,
                doc_comment.marker, doc_comment.indent, doc_comment.range)

            if new_comment != doc_comment:
                # Something changed, let's apply a result.
                diff = Diff(file)

                # Delete the old comment
                diff.delete_lines(doc_comment.range.start.line,
                                  doc_comment.range.end.line)

                # Apply the new comment
                assembled = new_comment.assemble().splitlines(True)

                end_line = new_comment.range.end.line
                end_marker_pos = file[end_line - 1].find(
                    new_comment.marker[2]) + len(new_comment.marker[2])
                diff.add_lines(new_comment.range.start.line, assembled[:-1])
                diff.add_lines(
                    end_line,
                    [assembled[-1] + file[end_line - 1][end_marker_pos:]])

                yield Result(
                    origin=self,
                    message="Documentation does not have correct style.",
                    affected_code=(diff.range(filename),),
                    diffs={filename: diff})
