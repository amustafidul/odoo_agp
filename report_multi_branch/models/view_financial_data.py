from odoo import models, fields, api


class FinancialData(models.Model):
    _name = 'financial.data'
    _description = 'Financial Data'

    date = fields.Date(string='Date')
    total_balance = fields.Float(string='Total Balance')
    source = fields.Selection([
        ('kas_dan_setara_kas', 'Kas dan setara kas'),
        ('piutang_usaha', 'Piutang usaha'),
        ('pendapatan_yang_masih_harus_diterima', 'Pendapatan yang masih harus diterima'),
        ('piutang_lain_lain', 'Piutang lain-lain'),
        ('pajak_dibayar_dimuka', 'Pajak dibayar dimuka'),
        ('pembayaran_dimuka', 'Pembayaran dimuka'),
        ('aset_tetap_bersih', 'Aset tetap bersih'),
        ('aset_hak_guna', 'Aset hak guna'),
        ('aset_pajak_tangguhan', 'Aset pajak tangguhan'),
        ('aset_lain_lain', 'Aset lain-lain'),
        ('utang_usaha', 'Utang usaha'),
        ('penerimaan_dimuka', 'Penerimaan dimuka'),
        ('utang_pajak', 'Utang pajak'),
        ('biaya_yang_masih_harus_dibayar', 'Biaya yang masih harus dibayar'),
        ('utang_lain_lain_jangka_pendek', 'Utang lain lain jangka pendek'),
        ('utang_bank_jangka_pendek', 'Utang bank jangka pendek'),
        ('utang_sewa_hak_guna_jangka_pendek', 'Utang sewa hak guna jangka pendek'),
        ('utang_bank', 'Utang bank'),
        ('liabilitas_imbalan_pasca_kerja', 'Liabilitas imbalan pasca kerja'),
        ('utang_sewa_hak_guna_jangka_panjang', 'Utang sewa hak guna jangka panjang'),
        ('utang_lain_lain_jangka_panjang', 'Utang lain-lain jangka panjang'),
        ('surat_utang_jangka_menengah', 'Surat utang jangka menengah'),
        ('modal_saham', 'Modal saham'),
        ('tambahan_modal_disetor', 'Tambahan modal disetor'),
        ('saldo_laba', 'Saldo laba')
    ], string='Source')

    source_2 = fields.Char(string='Source')

    @api.model
    def init(self):
        self.env.cr.execute("DELETE FROM financial_data")
        self.env.cr.execute("""
                INSERT INTO financial_data (id, date, total_balance, source_2)
                ( SELECT row_number() OVER () AS id,
    aml.date,
    sum(aml.balance) AS total_balance,
        CASE
            WHEN aa.code::integer = ANY (ARRAY[1101100, 1101201101, 1101201102, 1101201103, 1101201201, 1101201202, 1101201203, 1101201204, 1101201205, 1101201230, 1101201301, 1101201401, 1101201501, 1101201601, 1101201701, 1101201801, 1101202101, 1101202102, 1101202201, 1101202301, 1101203101, 1101204101, 1101205101, 1101301101, 1101301102, 1101301201, 1101301301, 1101301401, 1101302101, 1101302201, 1101302301, 1101400101, 1101400201]) THEN 'Kas dan setara kas'::text
            WHEN aa.code::integer = ANY (ARRAY[1103201, 1103202, 1103203, 1103204, 1103205, 1103206, 1103207, 1103301, 1103302, 1103303, 1103304, 1103305, 1103306, 1103307]) THEN 'Piutang usaha'::text
            WHEN aa.code::integer = ANY (ARRAY[1107101, 1107102, 1107103, 1107104, 1107105, 1107106, 1107107, 1107201, 1107202, 1107203, 1107204, 1107205, 1107206, 1107207]) THEN 'Pendapatan yang masih harus diterima'::text
            WHEN aa.code::integer = ANY (ARRAY[1103701, 1103702, 1103703, 1103704, 1103801, 1103802, 1103803, 1103804, 1103805, 1103806, 1103807, 1103810, 1103901, 1103902, 1103903, 1103904, 1103905, 1103906, 1103907, 1103910]) THEN 'Piutang lain-lain'::text
            WHEN aa.code::integer = ANY (ARRAY[1106101101, 1106101102, 1106102, 1106103]) THEN 'Pajak dibayar dimuka'::text
            WHEN aa.code::integer = ANY (ARRAY[1105101, 1105102, 1105103, 1105104, 1105105, 1105106, 1105107, 1105201, 1105202, 1105301, 1105302]) THEN 'Pembayaran dimuka'::text
            WHEN aa.code::integer = ANY (ARRAY[1201101, 1201102, 1201103, 1201104, 1201105, 1201106, 1201107, 1202101, 1202102, 1202103, 1202104, 1202105, 1202106, 1203101, 1203102, 1204101, 1204102, 1204103, 1205101, 1205102, 1205103]) THEN 'Aset tetap bersih'::text
            WHEN aa.code::integer = ANY (ARRAY[1207101, 1207102, 1207103, 1207104, 1207105, 1208101, 1208102, 1208103, 1208104, 1208105]) THEN 'Aset hak guna'::text
            WHEN aa.code::integer = 1206102 THEN 'Aset pajak tangguhan'::text
            WHEN aa.code::integer = ANY (ARRAY[1206101, 1206103, 1206104, 1206201]) THEN 'Aset lain-lain'::text
            WHEN aa.code::integer = ANY (ARRAY[2101101, 2101102, 2101103, 2101104, 2101105, 2101106, 2101107]) THEN 'Utang usaha'::text
            WHEN aa.code::integer = ANY (ARRAY[2105101, 2105102, 2105103, 2105104, 2105105, 2105106, 2105107, 2105999]) THEN 'Penerimaan dimuka'::text
            WHEN aa.code::integer = ANY (ARRAY[2102101, 2102102, 2102103, 2102104, 2102105, 2102106, 2102107]) THEN 'Utang pajak'::text
            WHEN aa.code::integer = ANY (ARRAY[2103101, 2103102, 2103103, 2103104, 2103105, 2103106, 2103107, 2103201, 2103202, 2103203, 2103301, 2103302, 2104101, 2104102, 2104103, 2104104, 2104105, 2104106, 2104107, 2104109]) THEN 'Biaya yang masih harus dibayar'::text
            WHEN aa.code::integer = ANY (ARRAY[2201100, 2202100]) THEN 'Utang lain lain jangka pendek'::text
            WHEN aa.code::integer = 2109000 THEN 'Utang bank jangka pendek'::text
            WHEN aa.code::integer = 2109100 THEN 'Utang sewa hak guna jangka pendek'::text
            WHEN aa.code::integer = 2204200 THEN 'Utang bank'::text
            WHEN aa.code::integer = 2202100 THEN 'Liabilitas imbalan pasca kerja'::text
            WHEN aa.code::integer = 2202101 THEN 'Utang sewa hak guna jangka panjang'::text
            WHEN aa.code::integer = ANY (ARRAY[2201100, 2203100, 2203101, 2203102, 2203103, 2203104, 2203105, 2203200, 2203301, 2203302, 2203303, 2203304, 2203305]) THEN 'Utang lain-lain jangka panjang'::text
            WHEN aa.code::integer = 2204100 THEN 'Surat utang jangka menengah'::text
            WHEN aa.code::integer = ANY (ARRAY[3101001, 3101002]) THEN '"Modal saham
  Modal dasar terdiri dari Rp8.000.000.000 terdiri dari 8.000 saham, ditempatkan dan disetor penuh 4,596, dengan nilai Rp1.000.000 per saham"'::text
            WHEN aa.code::integer = ANY (ARRAY[3201001, 3201002, 3203001, 3203002, 3202001, 3202002]) THEN 'Tambahan modal disetor'::text
            WHEN aa.code::integer = 3302 THEN 'Saldo laba'::text
            ELSE NULL::text
        END AS source_2
   FROM account_account aa
     LEFT JOIN account_move_line aml ON aml.account_id = aa.id
  GROUP BY aml.date, (
        CASE
            WHEN aa.code::integer = ANY (ARRAY[1101100, 1101201101, 1101201102, 1101201103, 1101201201, 1101201202, 1101201203, 1101201204, 1101201205, 1101201230, 1101201301, 1101201401, 1101201501, 1101201601, 1101201701, 1101201801, 1101202101, 1101202102, 1101202201, 1101202301, 1101203101, 1101204101, 1101205101, 1101301101, 1101301102, 1101301201, 1101301301, 1101301401, 1101302101, 1101302201, 1101302301, 1101400101, 1101400201]) THEN 'Kas dan setara kas'::text
            WHEN aa.code::integer = ANY (ARRAY[1103201, 1103202, 1103203, 1103204, 1103205, 1103206, 1103207, 1103301, 1103302, 1103303, 1103304, 1103305, 1103306, 1103307]) THEN 'Piutang usaha'::text
            WHEN aa.code::integer = ANY (ARRAY[1107101, 1107102, 1107103, 1107104, 1107105, 1107106, 1107107, 1107201, 1107202, 1107203, 1107204, 1107205, 1107206, 1107207]) THEN 'Pendapatan yang masih harus diterima'::text
            WHEN aa.code::integer = ANY (ARRAY[1103701, 1103702, 1103703, 1103704, 1103801, 1103802, 1103803, 1103804, 1103805, 1103806, 1103807, 1103810, 1103901, 1103902, 1103903, 1103904, 1103905, 1103906, 1103907, 1103910]) THEN 'Piutang lain-lain'::text
            WHEN aa.code::integer = ANY (ARRAY[1106101101, 1106101102, 1106102, 1106103]) THEN 'Pajak dibayar dimuka'::text
            WHEN aa.code::integer = ANY (ARRAY[1105101, 1105102, 1105103, 1105104, 1105105, 1105106, 1105107, 1105201, 1105202, 1105301, 1105302]) THEN 'Pembayaran dimuka'::text
            WHEN aa.code::integer = ANY (ARRAY[1201101, 1201102, 1201103, 1201104, 1201105, 1201106, 1201107, 1202101, 1202102, 1202103, 1202104, 1202105, 1202106, 1203101, 1203102, 1204101, 1204102, 1204103, 1205101, 1205102, 1205103]) THEN 'Aset tetap bersih'::text
            WHEN aa.code::integer = ANY (ARRAY[1207101, 1207102, 1207103, 1207104, 1207105, 1208101, 1208102, 1208103, 1208104, 1208105]) THEN 'Aset hak guna'::text
            WHEN aa.code::integer = 1206102 THEN 'Aset pajak tangguhan'::text
            WHEN aa.code::integer = ANY (ARRAY[1206101, 1206103, 1206104, 1206201]) THEN 'Aset lain-lain'::text
            WHEN aa.code::integer = ANY (ARRAY[2101101, 2101102, 2101103, 2101104, 2101105, 2101106, 2101107]) THEN 'Utang usaha'::text
            WHEN aa.code::integer = ANY (ARRAY[2105101, 2105102, 2105103, 2105104, 2105105, 2105106, 2105107, 2105999]) THEN 'Penerimaan dimuka'::text
            WHEN aa.code::integer = ANY (ARRAY[2102101, 2102102, 2102103, 2102104, 2102105, 2102106, 2102107]) THEN 'Utang pajak'::text
            WHEN aa.code::integer = ANY (ARRAY[2103101, 2103102, 2103103, 2103104, 2103105, 2103106, 2103107, 2103201, 2103202, 2103203, 2103301, 2103302, 2104101, 2104102, 2104103, 2104104, 2104105, 2104106, 2104107, 2104109]) THEN 'Biaya yang masih harus dibayar'::text
            WHEN aa.code::integer = ANY (ARRAY[2201100, 2202100]) THEN 'Utang lain lain jangka pendek'::text
            WHEN aa.code::integer = 2109000 THEN 'Utang bank jangka pendek'::text
            WHEN aa.code::integer = 2109100 THEN 'Utang sewa hak guna jangka pendek'::text
            WHEN aa.code::integer = 2204200 THEN 'Utang bank'::text
            WHEN aa.code::integer = 2202100 THEN 'Liabilitas imbalan pasca kerja'::text
            WHEN aa.code::integer = 2202101 THEN 'Utang sewa hak guna jangka panjang'::text
            WHEN aa.code::integer = ANY (ARRAY[2201100, 2203100, 2203101, 2203102, 2203103, 2203104, 2203105, 2203200, 2203301, 2203302, 2203303, 2203304, 2203305]) THEN 'Utang lain-lain jangka panjang'::text
            WHEN aa.code::integer = 2204100 THEN 'Surat utang jangka menengah'::text
            WHEN aa.code::integer = ANY (ARRAY[3101001, 3101002]) THEN '"Modal saham
  Modal dasar terdiri dari Rp8.000.000.000 terdiri dari 8.000 saham, ditempatkan dan disetor penuh 4,596, dengan nilai Rp1.000.000 per saham"'::text
            WHEN aa.code::integer = ANY (ARRAY[3201001, 3201002, 3203001, 3203002, 3202001, 3202002]) THEN 'Tambahan modal disetor'::text
            WHEN aa.code::integer = 3302 THEN 'Saldo laba'::text
            ELSE NULL::text
        END))
            """)
