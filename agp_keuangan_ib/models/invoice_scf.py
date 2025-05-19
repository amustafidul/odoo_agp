from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math


import base64
import io
import xlsxwriter


class Scf(models.Model):
    _name = 'account.keuangan.scf'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Invoice - SCF'

    name = fields.Char(string='Invoice - SCF Number', required=True, copy=False, readonly=True, default=lambda self: _('New'), tracking=True)

    tahap_scf = fields.Char(strting='Tahap SCF', tracking=True)
    tempo_pelunasan = fields.Char(string='Tempo Pelunasan', tracking=True)
    # potongan = fields.Float(string='Potongan')
    tanggal_pelunasan = fields.Date(string='Tanggal Pelunasan', required=True, tracking=True)
    pengembalian_bunga = fields.Float(string='Pengembalian Bunga', tracking=True)
    
    nominal_diterima = fields.Float(string='Nominal Pendapatan Dari Debitur', compute='_compute_nominal_pendapatan', tracking=True)
    nominal_pelunasan = fields.Float(string='Nominal Peminjaman SCF', compute='_compute_nominal_pelunasan', tracking=True)
    tanggal_bunga_awal = fields.Date(string='Tanggal Bunga Awal', required=True, tracking=True)
    nominal_bunga_awal = fields.Float(string='Nominal Bunga Awal', tracking=True)
    tanggal_bunga_akhir = fields.Date(string='Tanggal Bunga Akhir', required=True, tracking=True)
    pengembalian_bunga_awal = fields.Float(string='Pengembalian Bunga Awal', tracking=True)
    nominal_bunga_asli = fields.Float(string='Nominal Bunga Asli', compute='_compute_nominal_bunga_asli', store=True, tracking=True)
    keterangan = fields.Text(string='Keterangan')
    nominal_penarikan = fields.Float(string='Nominal Penarikan', compute='_compute_nominal_bni', tracking=True)
    sisa_pengembalian = fields.Float(string='Sisa Pengembalian', compute='_compute_sisa_pengembalian', store=True, tracking=True)

    scf_line_ids = fields.One2many('account.keuangan.scf.line', 'scf_id', string='Invoice - SCF Lines', tracking=True, ondelete='cascade')

    # untaxed_amount = fields.Float(string="Untaxed Amount", compute="_compute_amounts", store=True)
    # taxes = fields.Float(string="Taxes", compute="_compute_amounts", store=True)
    # total = fields.Float(string="Total", compute="_compute_amounts", store=True)

    # @api.depends('scf_line_ids.nominal', 'scf_line_ids.tax_ids')
    # def _compute_amounts(self):
    #     for record in self:
    #         untaxed_sum = sum(line.nominal for line in record.scf_line_ids)
    #         tax_sum = 0.0
    #         for line in record.scf_line_ids:
    #             for tax in line.tax_ids:
    #                 tax_amount = tax.amount / 100  # Mengubah persentase ke desimal
    #                 tax_sum += line.nominal * tax_amount
    #         record.untaxed_amount = untaxed_sum
    #         record.taxes = tax_sum
    #         record.total = untaxed_sum + tax_sum
    
    
    @api.depends('nominal_pelunasan', 'nominal_bunga_awal', 'pengembalian_bunga_awal', 'nominal_bunga_asli', 'nominal_penarikan')
    def _compute_sisa_pengembalian(self):
        for record in self:
            bunga = record.pengembalian_bunga_awal if record.pengembalian_bunga_awal else record.nominal_bunga_awal
            record.sisa_pengembalian = record.nominal_pelunasan - bunga - record.nominal_penarikan
    
    @api.depends('scf_line_ids.nominal')
    def _compute_nominal_pelunasan(self):
        for record in self:
            record.nominal_pelunasan = sum(line.total_sebelum_pajak for line in record.scf_line_ids)
   
    @api.depends('scf_line_ids.nominal_bni')
    def _compute_nominal_bni(self):
        for record in self:
            record.nominal_penarikan = sum(line.nominal_bni for line in record.scf_line_ids)
   
    @api.depends('scf_line_ids.total_sesudah_pajak')
    def _compute_nominal_pendapatan(self):
        for record in self:
            record.nominal_diterima = sum(line.total_sesudah_pajak for line in record.scf_line_ids)

    @api.depends('nominal_bunga_awal', 'pengembalian_bunga_awal')
    def _compute_nominal_bunga_asli(self):
        for record in self:
            record.nominal_bunga_asli = record.nominal_bunga_awal - record.pengembalian_bunga_awal

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):            
            # Get the date details
            date_str = vals.get('date', fields.Date.context_today(self))
            date_obj = fields.Date.from_string(date_str) if isinstance(date_str, str) else date_str
            year = date_obj.strftime('%Y')
            month = int(date_obj.strftime('%m'))
            roman_month = self._to_roman(month)
            
            # Get the default branch of the user
            user = self.env.user
            default_branch = user.branch_id[0] if user.branch_id else None
            branch_code = default_branch.code if default_branch else 'KOSONG'
            
            # Get the department code of the user
            # department_code = user.department_id.kode if user.department_id else 'NO_DEPT'
            
            # Generate the custom sequence number
            sequence_code = self.env['ir.sequence'].next_by_code('report.spp') or '0000'

            # Generate the custom sequence
            vals['name'] = f'{sequence_code}/SCF-{branch_code}/{roman_month}/{year}'
        
        return super(Scf, self).create(vals)

    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')


    def export_to_excel(self):
        # Buat file Excel
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('List Invoice')

        # Format
        company_name = self.env.user.company_id.name if self.env.user.company_id else "Nama Perusahaan Tidak Diketahui"
        judul = f"USULAN SCF {company_name.upper()} KEPADA PT BNI (PERSERO)"
        sheet.merge_range('A1:L1', judul, workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'}))

        headers = ['No.', 'Pemberi Kerja', 'Jenis Pekerjaan', 'Periode Pekerjaan', 'PLTU',
                'Nomor', 'Tanggal Invoice', 'DPP', 'PPN', 'Jumlah', 'PPH', 'Dibayar']

        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'align': 'center'})
        sub_header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#B0C4DE'})
        rupiah_format = workbook.add_format({'num_format': '"Rp" #,##0.00'})
        total_format = workbook.add_format({'bold': True, 'bg_color': '#FFD700', 'align': 'center', 'num_format': '"Rp" #,##0.00'})

        # Tulis header tambahan
        sheet.merge_range('A3:A4', 'No.', sub_header_format)
        sheet.merge_range('B3:B4', 'Pemberi Kerja', sub_header_format)
        sheet.merge_range('C3:C4', 'Jenis Pekerjaan', sub_header_format)
        sheet.merge_range('D3:D4', 'Periode Pekerjaan', sub_header_format)
        sheet.merge_range('E3:E4', 'PLTU', sub_header_format)
        sheet.merge_range('F3:F4', 'Nomor', sub_header_format)
        sheet.merge_range('G3:J3', 'Tagihan', sub_header_format)
        sheet.merge_range('K3:L3', 'Yang Akan Diterima', sub_header_format)

        for col, header in enumerate(headers):
            sheet.write(3, col, header, header_format)

        # Simpan semua data dalam list 2D
        all_data = []

        for index, line in enumerate(self.scf_line_ids, start=1):
            row_data = [
                str(index),
                line.partner_id.name or '',
                line.jenis_kegiatan_id.name or '',
                line.periode_pekerjaan or '',
                line.sub_branch_ids.name or '',
                line.nomor_referensi or '',
                line.tanggal_invoices.strftime('%d %B %Y') if line.tanggal_invoices else '',
                line.total_sebelum_pajak,
                line.tax_amount_non_pph,
                line.total_sesudah_pajak,
                line.tax_amount,
                line.dibayar,
            ]
            all_data.append(row_data)

        # Tulis data ke sheet dan hitung lebar maksimum per kolom
        max_widths = [len(str(header)) for header in headers]
        row = 4
        for row_data in all_data:
            for col_num, cell in enumerate(row_data):
                # Tulis data dengan format sesuai kolom
                if col_num >= 7:  # Kolom angka format rupiah
                    sheet.write(row, col_num, cell, rupiah_format)
                    # Hitung lebar berdasarkan format yang ditampilkan
                    cell_as_string = f"Rp {cell:,.2f}"  # Format text seperti Rupiah
                else:
                    sheet.write(row, col_num, cell)
                    # Untuk kolom selain Rupiah, gunakan data asli
                    cell_as_string = str(cell)

                # Hitung lebar maksimum
                max_widths[col_num] = max(max_widths[col_num], len(cell_as_string))

            row += 1

        # Tambahkan baris total
        sheet.merge_range(row, 0, row, 6, 'Total', total_format)
        sheet.write_formula(row, 7, f'=SUM(H5:H{row})', total_format)
        sheet.write_formula(row, 8, f'=SUM(I5:I{row})', total_format)
        sheet.write_formula(row, 9, f'=SUM(J5:J{row})', total_format)
        sheet.write_formula(row, 10, f'=SUM(K5:K{row})', total_format)
        sheet.write_formula(row, 11, f'=SUM(L5:L{row})', total_format)

        # Atur lebar kolom otomatis
        for col_num, width in enumerate(max_widths):
            sheet.set_column(col_num, col_num, width + 2)  # Tambah padding biar lega

        # Selesai
        workbook.close()
        output.seek(0)
        file_data = output.read()
        output.close()

        # Buat attachment dari file
        attachment = self.env['ir.attachment'].create({
            # 'name': f'Detail_Angsuran_{self.name}_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx',
            'name': f'{self.name}_{datetime.now().strftime("%Y%m%d%H%M%S")}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'store_fname': f'Rekap_{self.name}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'account.keuangan.scf',
            'res_id': self.id,
        })

        # Membuka file attachment
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }



class ScfLine(models.Model):
    _name = 'account.keuangan.scf.line'
    _description = 'Invoice - SCF'


    scf_id = fields.Many2one('account.keuangan.scf', string='Invoice - SCF', required=True, tracking=True, ondelete='cascade')
    
    is_bni = fields.Boolean(string='Pembayaran BNI', default=False, tracking=True)

    invoice_id = fields.Many2one('account.keuangan.invoice', string='Nomor Invoice', required=True, tracking=True)
        
    partner_id = fields.Many2one('res.partner', string='Nama Perusahaan', related='invoice_id.ditujukan_kepada', readonly=True, tracking=True)
    
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, tracking=True)

    jenis_kegiatan_id = fields.Many2one('jenis.kegiatan', string='Jenis Kegiatan', related='invoice_id.jenis_kegiatan_id', readonly=True, tracking=True)
    tanggal_invoices = fields.Date(string='Tanggal Invoice', related='invoice_id.tanggal_invoice', readonly=True, tracking=True)
    sub_branch_ids = fields.Many2many(string='PLTU', related='invoice_id.sub_branch_ids', readonly=True, tracking=True)

    nomor_referensi = fields.Char(string='Nomor Invoice', related='invoice_id.nomor_referensi', readonly=False, store=True, tracking=True)
    nominal = fields.Float(string='Nominal Invoice', related='invoice_id.total_jumlah', readonly=False, store=True, tracking=True)
    periode_mulai = fields.Date(string='Period Mulai', related='invoice_id.periode_mulai', readonly=False, store=True, tracking=True)
    periode_akhir = fields.Date(string='Period Akhir', related='invoice_id.periode_akhir', readonly=False, store=True, tracking=True)
    periode_pekerjaan = fields.Char(string="Period Pekerjaan", store=True, tracking=True)
    nominal_bni = fields.Float(string='Nominal')
    total_sebelum_pajak = fields.Float(string='Total Sebelum Pajak', related='invoice_id.total_sebelum_pajak', readonly=True, store=True, tracking=True)
    total_sesudah_pajak = fields.Float(string='Total Setelah Pajak', compute='_compute_setelah_pajak', tracking=True)
    tax_amount = fields.Float(string='Pajak', related='invoice_id.total_pajak', readonly=True, store=True, tracking=True)

    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True, tracking=True)

    # tax_amount_pph = fields.Float(string='Nilai PPh', compute='_compute_tax_amount_pph', store=True, tracking=True)
    tax_amount_non_pph = fields.Float(string='PPN', compute='_compute_tax_amount_non_pph', store=True, tracking=True)
    
    dibayar = fields.Float(
        string='Dibayar',
        compute='_compute_dibayar',
        store=True,
        tracking=True
    )

    tax_ids = fields.Many2many(
        'account.tax', 
        string="PPh Taxes",
        domain=[('type_tax_use', '=', 'purchase'), ('name', 'ilike', 'PPh')]
    )

    tax_amount = fields.Monetary(string="Nilai PPh", compute="_compute_tax_amount", store=True)
    currency_id = fields.Many2one('res.currency', string="Currency")


    @api.depends('total_sebelum_pajak', 'tax_ids')
    def _compute_tax_amount(self):
        for record in self:
            total_tax = 0.0
            if record.tax_ids:
                for tax in record.tax_ids:
                    pph_amount = record.total_sebelum_pajak * (abs(tax.amount) / 100)
                    total_tax += pph_amount
            record.tax_amount = total_tax

   
    # @api.depends('invoice_id.line_ids')  # Menggunakan line_ids dari invoice
    # def _compute_tax_amount_pph(self):
    #     for record in self:
    #         total_pph_amount = 0.0
    #         if record.invoice_id:
    #             print(f"Processing invoice: {record.invoice_id.name}")  # Menampilkan nama invoice yang sedang diproses
    #             total_before_tax = record.invoice_id.total_sebelum_pajak  # Mengambil total sebelum pajak
                
    #             for line in record.invoice_id.line_ids:
    #                 if line.tax_ids:  # Pastikan ada pajak yang diterapkan
    #                     for tax in line.tax_ids:
    #                         # Print informasi tentang pajak yang diperiksa
    #                         print(f"Checking tax: {tax.name}, type: {tax.type_tax_use}, amount: {tax.amount}")
                            
    #                         if tax.type_tax_use == 'sale' and 'pph' in tax.name.lower():  
    #                             # Hitung nilai PPh sebagai persentase dari total sebelum pajak
    #                             pph_value = total_before_tax * (abs(tax.amount) / 100)  # Menggunakan nilai absolut untuk pajak
    #                             total_pph_amount += pph_value
    #                             # Print nilai PPh yang dihitung
    #                             print(f"Total before tax: {total_before_tax}, Tax Amount PPh: {pph_value}")
    #                             print(f"Skipping negative tax amount: {tax.amount}")

    #         record.tax_amount_pph = total_pph_amount
    #         print(f"Total PPh amount for invoice {record.invoice_id.name}: {total_pph_amount}")  # Print total PPh yang dihitung
    
    
    @api.depends('invoice_id.line_ids')  # Menggunakan line_ids dari invoice
    def _compute_tax_amount_non_pph(self):
        for record in self:
            total_non_pph_amount = 0.0
            if record.invoice_id:
                print(f"Processing invoice: {record.invoice_id.name}")  # Menampilkan nama invoice yang sedang diproses
                total_before_tax = record.invoice_id.total_sebelum_pajak  # Mengambil total sebelum pajak

                for line in record.invoice_id.line_ids:
                    if line.tax_ids:  # Pastikan ada pajak yang diterapkan
                        for tax in line.tax_ids:
                            # Print informasi tentang pajak yang diperiksa
                            print(f"Checking tax: {tax.name}, type: {tax.type_tax_use}, amount: {tax.amount}")
                            
                            # Memproses pajak selain PPh
                            if tax.type_tax_use == 'sale' and 'pph' not in tax.name.lower():
                                # Hitung nilai pajak sebagai persentase dari total sebelum pajak
                                tax_value = total_before_tax * (abs(tax.amount) / 100)  # Menggunakan nilai absolut untuk pajak
                                total_non_pph_amount += tax_value
                                # Print nilai pajak yang dihitung
                                print(f"Total before tax: {total_before_tax}, Non-PPh Tax Amount: {tax_value}")

            record.tax_amount_non_pph = total_non_pph_amount
            print(f"Total non-PPh tax amount for invoice {record.invoice_id.name}: {total_non_pph_amount}")  # Print total pajak non-PPh yang dihitung


    @api.depends('total_sesudah_pajak', 'is_bni', 'tax_amount')
    def _compute_dibayar(self):
        for record in self:
        #     record.dibayar = 0.0 if record.is_bni else record.total_sebelum_pajak

            # Tentukan jumlah yang harus dibayar berdasarkan kondisi
            if record.is_bni:
                record.dibayar = 0.0
            elif not record.is_bni:
                record.dibayar = record.total_sebelum_pajak - record.tax_amount
            else:
                record.dibayar = 0.0


    # @api.onchange('invoice_id')
    # def _onchange_invoice_id(self):
    #     if self.invoice_id:
    #         self.tax_amount_pph = self.invoice_id.tax_amount_pph  # Pastikan ini sesuai
    #         # Tambahkan pengisian field lain sesuai kebutuhan
   
    @api.depends('nominal')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.nominal

    @api.depends('total_sebelum_pajak', 'tax_amount_non_pph', 'tax_amount')
    def _compute_setelah_pajak(self):
        for line in self:
            line.total_sesudah_pajak = line.total_sebelum_pajak  + line.tax_amount_non_pph


    # @api.depends('product_id', 'product_uom_id')
    # def _compute_tax_ids(self):
    #     for line in self:
    #         if line.display_type in ('line_section', 'line_note', 'payment_term'):
    #             continue
    #         # /!\ Don't remove existing taxes if there is no explicit taxes set on the account.
    #         if line.product_id or line.account_id.tax_ids or not line.tax_ids:
    #             line.tax_ids = line._get_computed_taxes()
