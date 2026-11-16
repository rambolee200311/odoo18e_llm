from odoo import models


class LLMProvider(models.Model):
    _inherit = "llm.provider"

    def _openai_format_tool(self, tool):
        """Send the downstream M3 schema, not the stored M2 base schema.

        The OpenAI adapter prefers ``llm.tool.input_schema`` when populated,
        which bypasses ``get_input_schema()`` and its M3 extension. Resolve the
        effective schema here so Provider Tool Calling receives the same
        contract that Odoo validates during execution.
        """
        if self.service == "openai" and tool.name == "office":
            return self._create_openai_tool_from_schema(tool.get_input_schema(), tool)
        return super()._openai_format_tool(tool)
