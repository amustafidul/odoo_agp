from odoo import models, fields, api

class KKHCInherit(models.Model):
    _inherit = 'account.keuangan.kkhc'

    total_nominal_disetujui_4_bca = fields.Float(compute='_compute_total_nominal_disetujui_4_bca', string='Total Nominal Disetujui 4 BCA')
    total_nominal_disetujui_4_bni = fields.Float(compute='_compute_total_nominal_disetujui_4_bni', string='Total Nominal Disetujui 4 BNI')
    total_nominal_disetujui_4_cimb = fields.Float(compute='_compute_total_nominal_disetujui_4_cimb', string='Total Nominal Disetujui 4 CIMB')
    total_nominal_disetujui_4_va = fields.Float(compute='_compute_total_nominal_disetujui_4_va', string='Total Nominal Disetujui 4 VA')

    total_nominal_disetujui_5_bca = fields.Float(compute='_compute_total_nominal_disetujui_5_bca', string='Total Nominal Disetujui 5 BCA')
    total_nominal_disetujui_5_bni = fields.Float(compute='_compute_total_nominal_disetujui_5_bni', string='Total Nominal Disetujui 5 BNI')
    total_nominal_disetujui_5_cimb = fields.Float(compute='_compute_total_nominal_disetujui_5_cimb', string='Total Nominal Disetujui 5 CIMB')
    total_nominal_disetujui_5_va = fields.Float(compute='_compute_total_nominal_disetujui_5_va', string='Total Nominal Disetujui 5 VA')

    total_nominal_disetujui_6_bca = fields.Float(compute='_compute_total_nominal_disetujui_6_bca', string='Total Nominal Disetujui 6 BCA')
    total_nominal_disetujui_6_bni = fields.Float(compute='_compute_total_nominal_disetujui_6_bni', string='Total Nominal Disetujui 6 BNI')
    total_nominal_disetujui_6_cimb = fields.Float(compute='_compute_total_nominal_disetujui_6_cimb', string='Total Nominal Disetujui 6 CIMB')
    total_nominal_disetujui_6_va = fields.Float(compute='_compute_total_nominal_disetujui_6_va', string='Total Nominal Disetujui 6 VA')

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_4_bca(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('4') and 'BCA' in line.bank_account_id.acc_number)
            record.total_nominal_disetujui_4_bca = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_4_bni(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('4') and line.bank_account_id.acc_number.startswith('BNI '))
            record.total_nominal_disetujui_4_bni = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_4_cimb(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('4') and 'CIMB' in line.bank_account_id.acc_number)
            record.total_nominal_disetujui_4_cimb = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_4_va(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('4') and line.bank_account_id.acc_number.startswith('VA '))
            record.total_nominal_disetujui_4_va = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_5_bca(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('5') and 'BCA' in line.bank_account_id.acc_number)
            record.total_nominal_disetujui_5_bca = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_5_bni(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('5') and line.bank_account_id.acc_number.startswith('BNI '))
            record.total_nominal_disetujui_5_bni = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_5_cimb(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('5') and 'CIMB' in line.bank_account_id.acc_number)
            record.total_nominal_disetujui_5_cimb = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_5_va(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('5') and line.bank_account_id.acc_number.startswith('VA '))
            record.total_nominal_disetujui_5_va = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_6_bca(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('6') and 'BCA' in line.bank_account_id.acc_number)
            record.total_nominal_disetujui_6_bca = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_6_bni(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('6') and line.bank_account_id.acc_number.startswith('BNI '))
            record.total_nominal_disetujui_6_bni = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_6_cimb(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('6') and 'CIMB' in line.bank_account_id.acc_number)
            record.total_nominal_disetujui_6_cimb = total

    @api.depends('kkhc_line_ids.nominal_disetujui', 'kkhc_line_ids.kode_anggaran_id.kode_anggaran', 'kkhc_line_ids.bank_account_id.acc_number')
    def _compute_total_nominal_disetujui_6_va(self):
        for record in self:
            total = sum(line.nominal_disetujui for line in record.kkhc_line_ids 
                        if line.kode_anggaran_id.kode_anggaran.startswith('6') and line.bank_account_id.acc_number.startswith('VA '))
            record.total_nominal_disetujui_6_va = total

    def get_bca_account(self):
        for record in self:
            if record.kkhc_line_ids:
                for line in record.kkhc_line_ids:
                    if line.bank_account_id:
                        if 'BCA' in line.bank_account_id.acc_number:
                            return line.bank_account_id.acc_number.split("-")[-1]
                    else:
                        return 'False'
        return ''
    
    def get_bni_account(self):
        for record in self:
            if record.kkhc_line_ids:
                for line in record.kkhc_line_ids:
                    if line.bank_account_id:
                        if line.bank_account_id.acc_number.startswith("BNI "):
                            return line.bank_account_id.acc_number.split("-")[-1]
                    else:
                        return 'False'
        return ''
    
    def get_cimb_account(self):
        for record in self:
            if record.kkhc_line_ids:
                for line in record.kkhc_line_ids:
                    if line.bank_account_id:
                        if 'CIMB' in line.bank_account_id.acc_number:
                            return line.bank_account_id.acc_number.split("-")[-1]
                    else:
                        return 'False'
        return ''
    
    def get_branch_va_account(self):
        for record in self:
            if record.kkhc_line_ids:
                for line in record.kkhc_line_ids:
                    if line.bank_account_id:
                        if line.bank_account_id.acc_number.startswith("VA "):
                            return line.bank_account_id.acc_number.split("-")[-1]
                    else:
                        return 'False'
        return ''


class KKHCLinesInherit(models.Model):
    _inherit = 'account.keuangan.kkhc.line'

    def get_nominal_disetujui_bca(self, line_id):
        for line in self:
            if line_id == line.id:
                if 'BCA' in line.bank_account_id.acc_number or 'BCA' in line.bank_account_id.bank_id.name:
                    return '{:,.0f}'.format(line.nominal_disetujui)
                else:
                    return '0'
                
    def get_nominal_disetujui_bni(self, line_id):
        for line in self:
            if line_id == line.id:
                if line.bank_account_id.acc_number.startswith("BNI ") or 'BNI' in line.bank_account_id.bank_id.name:
                    return '{:,.0f}'.format(line.nominal_disetujui)
                else:
                    return '0'
                
    def get_nominal_disetujui_cimb(self, line_id):
        for line in self:
            if line_id == line.id:
                if 'CIMB' in line.bank_account_id.acc_number or 'CIMB' in line.bank_account_id.bank_id.name:
                    return '{:,.0f}'.format(line.nominal_disetujui)
                else:
                    return '0'

    def get_nominal_disetujui_va(self, line_id):
        for line in self:
            if line_id == line.id:
                if line.bank_account_id.acc_number.startswith("VA ") or 'VA ' in line.bank_account_id.bank_id.name:
                    return '{:,.0f}'.format(line.nominal_disetujui)
                elif line.kode_anggaran_id.kode_anggaran.startswith('5'):
                    if 'BCA' in line.bank_account_id.acc_number or 'BCA' in line.bank_account_id.bank_id.name:
                        return '{:,.0f}'.format(line.nominal_disetujui)
                    elif line.bank_account_id.acc_number.startswith("BNI ") or 'BNI' in line.bank_account_id.bank_id.name:
                        return '{:,.0f}'.format(line.nominal_disetujui)
                    elif 'CIMB' in line.bank_account_id.acc_number or 'CIMB' in line.bank_account_id.bank_id.name:
                        return '{:,.0f}'.format(line.nominal_disetujui)
                elif line.kode_anggaran_id.kode_anggaran.startswith('6'):
                    if 'BCA' in line.bank_account_id.acc_number or 'BCA' in line.bank_account_id.bank_id.name:
                        return '{:,.0f}'.format(line.nominal_disetujui)
                    elif line.bank_account_id.acc_number.startswith("BNI ") or 'BNI' in line.bank_account_id.bank_id.name:
                        return '{:,.0f}'.format(line.nominal_disetujui)
                    elif 'CIMB' in line.bank_account_id.acc_number or 'CIMB' in line.bank_account_id.bank_id.name:
                        return '{:,.0f}'.format(line.nominal_disetujui)
                return '0'
























