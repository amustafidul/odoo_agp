from odoo import models, fields, api

class AccountKeuanganSaldo(models.Model):
    _name = 'account.keuangan.saldo'
    _description = 'Saldo Per Kode Anggaran dan Branch'
    _auto = False  # This model doesn't create a physical table in the database

    kode_anggaran_id = fields.Many2one('account.keuangan.kode.anggaran', string='Kode Anggaran')
    kode_anggaran_value = fields.Char(string='Kode Anggaran')  # Ensure this matches the alias
    branch_name_value = fields.Char(string='Branch Name')  # Ensure this matches the alias
    branch_id = fields.Many2one('res.branch', string='Branch')  # Ensure this matches the alias
    saldo_awal = fields.Float(string='Saldo Awal')
    total_pemakaian = fields.Float(string='Total Pemakaian')
    saldo = fields.Float(string='Saldo')

    @api.model
    def _select(self):
        return """
            SELECT 
                row_number() OVER() AS id,  -- Generate a unique ID for each row
                ra.kode_anggaran_id AS kode_anggaran_id,  -- Use alias for kode_anggaran_id
                ka_ref.kode_anggaran AS kode_anggaran_value,  -- Use alias to avoid conflict
                rb.name AS branch_name_value,  -- Alias for branch name to avoid conflicts
                r.branch_id AS branch_id,  -- Alias for branch_id to avoid conflicts
                COALESCE(ra.nominal, 0) AS saldo_awal,  -- Use COALESCE for saldo_awal
                COALESCE(SUM(CASE WHEN k.branch_id = r.branch_id THEN ka.nominal_disetujui ELSE 0 END), 0) AS total_pemakaian,  -- Sum of pemakaian per branch
                (COALESCE(ra.nominal, 0) - COALESCE(SUM(CASE WHEN k.branch_id = r.branch_id THEN ka.nominal_disetujui ELSE 0 END), 0)) AS saldo  -- Calculated saldo per branch
            FROM 
                account_keuangan_rkap_line ra
            JOIN 
                account_keuangan_rkap r ON ra.rkap_id = r.id
            LEFT JOIN 
                account_keuangan_kkhc_line ka ON ra.kode_anggaran_id = ka.kode_anggaran_id  -- Left join for pemakaian
            LEFT JOIN 
                account_keuangan_kode_anggaran ka_ref ON ra.kode_anggaran_id = ka_ref.id  -- Join for kode_anggaran values
            LEFT JOIN 
                account_keuangan_kkhc k ON ka.kkhc_id = k.id  -- Link kkhc and branch data
            JOIN 
                res_branch rb ON r.branch_id = rb.id  -- Link branch names
            GROUP BY 
                ra.kode_anggaran_id, r.branch_id, rb.name, ra.nominal, ra.id, ka_ref.kode_anggaran  -- Group by fields
            ORDER BY 
                ra.kode_anggaran_id, r.branch_id
        """


    def init(self):
        # Initialize or re-create the view
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS ({self._select()})
        """)