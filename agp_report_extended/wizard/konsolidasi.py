import io
import xlsxwriter
from odoo import models, fields, api
from odoo.tools import pycompat
import base64
from babel.dates import format_date
from odoo.exceptions import ValidationError


class RkapKonsolidasiViaWizard(models.TransientModel):
    _name = 'rkap.konsolidasi.wizard'
    _description = 'Generate RKAP Konsolidasi Wizard'

    is_all = fields.Boolean(string='Semua Cabang', default=True)
    branch_ids = fields.Many2many('res.branch', string='Daftar Cabang')
    today = fields.Date(string='Tanggal', default=lambda self: fields.Date.today())
    tahun = fields.Char(string='Tahun', compute='_compute_tahun', store=True)
    
    @api.depends('today')
    def _compute_tahun(self):
        for record in self:
            record.tahun = str(record.today.year) if record.today else ''

    def get_lines_dict(self):
        recs = self.get_records_dict()

        if recs:
            return recs[0]['lines']

    def action_print_xls(self):
        return True

    def get_records_dict(self):
        result = {}
        if not self.is_all and len(self.branch_ids) > 0:
            # coming soon, leave this one untouched!!!
            raise ValidationError('Bisa Milih Cabang, Ntar Dulu!!')

        elif self.is_all:
            self._cr.execute("""
                SELECT id, UPPER(name) AS name FROM res_branch ORDER BY name
            """)
            branches = self._cr.fetchall()

            # Construct dynamic sub-query for saldo
            sub_query = ", ".join(
                f"SUM(CASE WHEN acc_saldo.branch_id = {b[0]} THEN acc_saldo.saldo ELSE 0 END) AS {b[1].replace(' ', '_')}"
                for b in branches
            )

            # Fetch consolidated saldo data
            query = f"""
                SELECT anggaran.kode_anggaran, acc.code, anggaran.deskripsi, {sub_query}
                FROM account_keuangan_saldo AS acc_saldo
                INNER JOIN account_keuangan_kode_anggaran AS anggaran ON acc_saldo.kode_anggaran_id = anggaran.id
                INNER JOIN account_account AS acc ON anggaran.account_code_id = acc.id
                GROUP BY anggaran.kode_anggaran, acc.code, anggaran.deskripsi
                ORDER BY anggaran.kode_anggaran;
            """
            self._cr.execute(query)
            query_results = self._cr.fetchall()

            branch_list = ['kode', 'coa', 'uraian']
            branch_list.extend(b[1].lower().replace(' ', '_') for b in branches)

            lines = []
            for res in query_results:
                line = {branch_list[i]: res[i] for i in range(len(branch_list))}
                lines.append(line)

            result = {
                'headers': branch_list,
                'lines': lines,
            }

        if len(result) > 0:
            return [result]
        else:
            raise ValidationError("Test error result konsolidasi")

    def action_print_pdf(self):
        records = self.env['account.keuangan.rkap'].sudo().search([])
        record_dicts = self.get_records_dict()
        
        if record_dicts:
            return self.env.ref('agp_report_extended.action_report_rkap_konsolidasi').report_action(
                docids=self.ids,
                data={
                    'array': record_dicts[0],
                    'doc_model': 'rkap.konsolidasi.wizard',
                }
            )
