
from odoo import fields, api, models, _
from odoo.exceptions import UserError
from datetime import datetime


class CompareTaxWizard(models.Model):
    _name = "compare.tax.wizard"
    _description = "Compare Tax Wizard"
    
    range_bulan = [(str(bulan), str(bulan)) for bulan in range(1, 13)]
    bulan_start = fields.Selection(range_bulan, string='Bulan Start', required=True)
    bulan_end = fields.Selection(range_bulan, string='Bulan End', required=True)
    tahun = fields.Selection(
        [(str(year), str(year)) for year in range(datetime.now().year - 100, datetime.now().year + 100)]
        , default=str(datetime.now().year)
        , string='Tahun', required=True)
    type = fields.Selection([("masuk","Masuk"),("keluar","Keluar")], string='Masuk/Keluar', required=True)

    date_start = fields.Date(string='Date Start')
    date_end = fields.Date(string='Date End')

    def action_view(self):
        data = {}
        data['form'] = self.read()[0]

        data['type'] = self.type
        
        lines = self.get_lines()
        data['lines'] = lines
        return self.env.ref('report_multi_branch.action_report_compare_tax').report_action(self, data=data)

    def check_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/compare_tax/export/%s' % (self.id),
            'target': 'new',
        }

    
    def get_lines(self):
        # Query untuk data pajak
        where_pajak = """
            WHERE dp.tahun = '{}' 
            AND dp.bulan >= {} 
            AND dp.bulan <= {}
        """.format(self.tahun, int(self.bulan_start), int(self.bulan_end))

        # Menentukan tipe invoice (masuk/keluar)
        if self.type == 'masuk':
            where_pajak += " AND (am.move_type = 'in_invoice' OR am.move_type IS NULL) "
        elif self.type == 'keluar':
            where_pajak += " AND (am.move_type = 'out_invoice' OR am.move_type IS NULL) "

        # Query untuk menggabungkan pajak dan invoice
        self.env.cr.execute("""
            SELECT 
                COALESCE(dp.no_npwp, '') AS no_npwp,
                COALESCE(dp.nama_pt, '') AS nama_pt,
                COALESCE(dp.name, '') AS no_faktur,
                COALESCE(dp.nominal_invoice, 0.0) AS nominal_invoice,
                COALESCE(dp.nominal_ppn, 0.0) AS nominal_ppn,
                COALESCE(SUM(am.amount_tax), 0.0) AS total_pajak_odoo,
                STRING_AGG(am.name, ', ') AS invoice
            FROM dirjen_pajak dp
            FULL OUTER JOIN account_move am ON dp.no_invoice_odoo = am.nomor_ref
            {where_pajak}
            GROUP BY 
                dp.no_npwp,
                dp.nama_pt,
                dp.name,
                dp.nominal_invoice,
                dp.nominal_ppn
        """.format(where_pajak=where_pajak))
        result_pajak = self.env.cr.dictfetchall()

        # Query untuk mengambil data invoice yang belum memiliki pasangan di dirjen pajak
        where_invoice_only = """
            WHERE am.invoice_date IS NOT NULL
        """
        
        if self.type == 'masuk':
            where_invoice_only += " AND am.move_type = 'in_invoice' "
        elif self.type == 'keluar':
            where_invoice_only += " AND am.move_type = 'out_invoice' "

        self.env.cr.execute("""
            SELECT 
                COALESCE(dp.no_npwp, '') AS no_npwp,
                COALESCE(dp.nama_pt, '') AS nama_pt,
                COALESCE(dp.name, '') AS no_faktur,
                COALESCE(dp.nominal_invoice, 0.0) AS nominal_invoice,
                COALESCE(dp.nominal_ppn, 0.0) AS nominal_ppn,
                COALESCE(SUM(am.amount_tax), 0.0) AS total_pajak_odoo,
                STRING_AGG(am.name, ', ') AS invoice
            FROM account_move am
            LEFT JOIN dirjen_pajak dp ON am.nomor_ref = dp.no_invoice_odoo
            {where_invoice_only}
            GROUP BY 
                dp.no_npwp,
                dp.nama_pt,
                dp.name,
                dp.nominal_invoice,
                dp.nominal_ppn        
        """.format(where_invoice_only=where_invoice_only))  
        result_invoice = self.env.cr.dictfetchall()

        result_combined = result_pajak + result_invoice

        return result_combined
