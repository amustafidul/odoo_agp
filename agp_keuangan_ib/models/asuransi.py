from odoo import models, fields, api, _

class Asuransi(models.Model):
    _name = 'account.keuangan.asuransi'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Asuransi'

    name = fields.Char(string='Asuransi Number', required=True, copy=True, readonly=False, default=lambda self: _('New'))
    state = fields.Selection([  
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        # Tambahkan status lain jika perlu
    ], default='draft', tracking=True)

    # Group Kiri
    no_polis = fields.Char(string='No. Polis', tracking=True)
    penerbit_polis = fields.Char(string='Penerbit Polis', tracking=True)
    asset_terdaftar = fields.Char(string='Asset Terdaftar', tracking=True)
    pialang = fields.Char(string='Pialang Asuransi', tracking=True)
    deskripsi_polis = fields.Char(string='Deskripsi Polis', tracking=True)
    biaya_perpanjangan = fields.Float(string='Biaya Perpanjangan', tracking=True)

    # Group Kanan
    tanggal_mulai = fields.Date(string='Tanggal Mulai Polis', required=True, tracking=True)
    tanggal_berakhir = fields.Date(string='Tanggal Berakhir Polis', required=True, tracking=True)
    keterangan = fields.Text(string='Keterangan', tracking=True)
    cakupan = fields.Float(string='Jumlah Cakupan Polis', tracking=True)
    currency_id = fields.Many2one(
        'res.currency', 
        string='Mata Uang', 
        domain="[('active', '=', True)]",  # Hanya mata uang yang aktif
        required=True, 
        tracking=True
    )

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
            department_code = user.department_id.kode if user.department_id else 'NO_DEPT'
            
            # Generate the custom sequence number
            sequence_code = self.env['ir.sequence'].next_by_code('sequence.keuangan.asuransi') or '0000'

            # Generate the custom sequence
            vals['name'] = f'{sequence_code}/AS-{branch_code}/{roman_month}/{year}'
        
        return super(Asuransi, self).create(vals)

    @staticmethod
    def _to_roman(month):
        roman = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI',
            7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII'
        }
        return roman.get(month, '')


    @api.model
    def action_confirm(self):
        for asuransi in self:
            if asuransi.state == 'draft':
                # Change state to posted
                asuransi.state = 'posted'
                # Optionally, add any other logic here
                sequence_code = self.env['ir.sequence'].next_by_code('account.keuangan.asuransi.sequence') or '0000'
                asuransi.name = sequence_code  # Update the name with the new sequence
        return True


    @api.model
    def action_print(self):
        # Logika untuk mencetak invoice
        return self.env.ref('agp_keuangan_ib.report_invoice').report_action(self)  # Ganti dengan ID report yang sesuai



