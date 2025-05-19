from odoo import models, fields, api, _


class PayrollSimulation(models.TransientModel):
    _name = 'payroll.simulation'
    _description = 'Wizard Simulasi Pembayaran'

    payroll_id = fields.Many2one('odoo.payroll.master', string='Penggajian')
    employee_id = fields.Many2one('hr.employee', string='Karyawan', readonly=True)
    basic_salary_amount = fields.Monetary('Gaji Dasar', readonly=True)
    tunjangan_posisi_amount = fields.Monetary('Tunjangan Posisi', readonly=True)
    overtime_amount = fields.Monetary('Lembur', readonly=True)
    bpjs_jht_amount = fields.Monetary('BPJS JHT', readonly=True)
    pph_21_amount = fields.Monetary('PPh 21', readonly=True)
    nett_salary_amount = fields.Monetary('Total Bersih', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )