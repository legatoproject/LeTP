"""!@package module_test_report_template renders the contents to report template.

Report can be any text-based format
"""
import os
from jinja2 import FileSystemLoader, Environment


class TemplateRender:
    """!Render the contents to the generic template."""

    def __init__(self):
        template_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "templates"
        )
        file_loader = FileSystemLoader(template_folder)
        self.env = Environment(loader=file_loader)
        self.contents = {}

    def render(self):
        """!Render the data."""
        raise NotImplementedError


class HTMLRenderModuel(TemplateRender):
    """!Render the contents to the html-based template.

    HTML template contains sections: summary environment test results
    """

    def __init__(self, template_file):
        super().__init__()
        self.env.filters["html_encoding"] = self._html_encoding
        self.env.filters["clean_pytest_name"] = self._clean_pytest_name
        self.template = self.env.get_template(template_file)

    def _html_encoding(self, msg):
        """Process text before it is displayed in HTML."""
        if not msg:
            return msg
        msg = self._convert_special_character(msg)
        return self._convert_colors(msg)

    @staticmethod
    def _convert_special_character(msg):
        """!Replace special characters with HTML encoded characters."""
        msg = msg.replace("&", '&amp;')
        msg = msg.replace("<", '&lt;')
        msg = msg.replace(">", '&gt;')
        msg = msg.replace('"', '&quot;')
        msg = msg.replace("'", '&apos;')
        return msg

    @staticmethod
    def _convert_colors(msg):
        """!Replace ansi color by html colors."""
        msg = msg.replace("\x1b[0m", "</font>")
        msg = msg.replace("\x1b[01m", '<font class="bold">')
        msg = msg.replace("\x1b[02m", "</font>")
        msg = msg.replace("\x1b[31m", '<font class="black">')
        msg = msg.replace("\x1b[31m", '<font class="red">')
        msg = msg.replace("\x1b[01;31m", '<font class="red bold">')
        msg = msg.replace("\x1b[32m", '<font class="green">')
        msg = msg.replace("\x1b[33m", '<font class="yellow">')
        msg = msg.replace("\x1b[01;33m", '<font class="yellow bold">')
        msg = msg.replace("\x1b[34m", '<font class="blue">')
        msg = msg.replace("\x1b[35m", '<font class="magenta">')
        msg = msg.replace("\x1b[36m", '<font class="cyan">')
        msg = msg.replace("\x1b[37m", '<font class="white">')
        return msg

    @staticmethod
    def _clean_pytest_name(name):
        """!Sanitize the test name.

        Tests can be parametrized in pytest. Use of [ and ] does not
        work in html links
        """
        name = name.replace("[", "_")
        name = name.replace("]", "_")
        return name

    def _render_all_sections(self):
        """!Render a completed html report."""
        return self.template.render(**self.contents)

    def _render_summary_sections(self):
        """!Render summary section only in the html report."""
        return self.template.render(
            title=self.contents.get("title"),
            basic=self.contents.get("basic"),
            summary=self.contents.get("summary"),
            summary_headers=self.contents.get("summary_headers"),
            environment_dict={},
            section=self.contents.get("section"),
            baisc=self.contents.get("basic"),
        )

    def render(self):
        """!Render the data."""
        if self.contents:
            section = self.contents.get("section").lower()

            if "all" in section:
                return self._render_all_sections()
            elif "summary" in section:
                return self._render_summary_sections()

        return None

    def diff(self):
        """!Render the data."""
        return self._render_all_sections()
