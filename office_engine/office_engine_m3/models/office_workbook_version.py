from odoo import fields, models


class OfficeWorkbookVersionM3(models.Model):
    _inherit = "office.workbook.version"

    data_integrity_receipt_json = fields.Text(readonly=True, copy=False)
