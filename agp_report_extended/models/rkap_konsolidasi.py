from odoo import models, fields, api

class RKAPKonsolidasi(models.Model):
    _name = 'account.keuangan.rkap.konsolidasi'
    _description = 'Konsolidasi RKAP Semua Cabang'

    kode = fields.Char(string='Kode', required=True)
    coa = fields.Char(string='COA', required=True)
    uraian = fields.Char(string='Uraian')

    balikpapan = fields.Float(string='Balikpapan')
    banjarmasin = fields.Float(string='Banjarmasin')
    batam = fields.Float(string='Batam')
    belawan = fields.Float(string='Belawan')
    cilacap = fields.Float(string='Cilacap')
    gresik = fields.Float(string='Gresik')
    jawa_barat = fields.Float(string='Jawa Barat')
    lhokseumawe = fields.Float(string='Lhokseumawe')
    makassar = fields.Float(string='Makassar')
    merak = fields.Float(string='Merak')
    nusa_tenggara = fields.Float(string='Nusa Tenggara')
    padang = fields.Float(string='Padang')
    paiton = fields.Float(string='Paiton')
    panjang = fields.Float(string='Panjang')
    tanjung_jati_b = fields.Float(string='Tanjung Jati B')

    _sql_constraints = [
        ('unique_konsolidasi', 'unique(kode, coa)', 'The combination of Kode and COA must be unique.')
    ]

    # @api.model
    # def init(self):
    #     # Retrieve branch information
    #     self._cr.execute("""
    #         SELECT id, UPPER(name) AS name FROM res_branch ORDER BY name
    #     """)
    #     branches = self._cr.fetchall()

    #     # Construct dynamic sub-query for saldo
    #     sub_query = ", ".join(
    #         f"SUM(CASE WHEN acc_saldo.branch_id = {b[0]} THEN acc_saldo.saldo ELSE 0 END) AS {b[1].replace(' ', '_')}"
    #         for b in branches
    #     )

    #     # Fetch consolidated saldo data
    #     query = f"""
    #         SELECT anggaran.kode_anggaran, acc.code, anggaran.deskripsi, {sub_query}
    #         FROM account_keuangan_saldo AS acc_saldo
    #         INNER JOIN account_keuangan_kode_anggaran AS anggaran ON acc_saldo.kode_anggaran_id = anggaran.id
    #         INNER JOIN account_account AS acc ON anggaran.account_code_id = acc.id
    #         GROUP BY anggaran.kode_anggaran, acc.code, anggaran.deskripsi
    #         ORDER BY anggaran.kode_anggaran;
    #     """
    #     self._cr.execute(query)
    #     query_results = self._cr.fetchall()

    #     # Process and insert records
    #     for row in query_results:
    #         vals = {
    #             'kode': row[0],
    #             'coa': row[1],
    #             'uraian': row[2],
    #             'balikpapan': row[3], 'banjarmasin': row[4], 'batam': row[5], 'belawan': row[6],
    #             'cilacap': row[7], 'gresik': row[8], 'jawa_barat': row[9], 'lhokseumawe': row[10],
    #             'makassar': row[11], 'merak': row[12], 'nusa_tenggara': row[13], 'padang': row[14],
    #             'paiton': row[15], 'panjang': row[16], 'tanjung_jati_b': row[17]
    #         }

    #         # Check if the record already exists
    #         existing_record = self.env['account.keuangan.rkap.konsolidasi'].search(
    #             [('kode', '=', vals['kode']), ('coa', '=', vals['coa'])], limit=1
    #         )
    #         if not existing_record:
    #             self.env['account.keuangan.rkap.konsolidasi'].create(vals)
