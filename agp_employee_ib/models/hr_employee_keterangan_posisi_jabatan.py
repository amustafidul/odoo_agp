from odoo import models, fields, api, _


class HrEmployeeKeteranganJabatan(models.Model):
    _name = "hr.employee.keterangan.jabatan"
    _description = "Keterangan Posisi/Jabatan"
    _check_company_auto = True

    name = fields.Char("Posisi/Jabatan", index='trigram', required=True)
    type = fields.Selection([
        ('struktural', 'Struktural'),
        ('umum', 'Umum')
    ], string="Type", required=True)

    # Dinas / SPPD Field Configuration #
    nodin_workflow = fields.Selection([
        ('dirop', 'As a Direktur Operasional'),
        ('dirkeu', 'As a Direktur Keuangan'),
        ('dirut', 'As a Direktur Utama')
    ], string='Nodin Workflow Approval')
    # #

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company, readonly=1)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Ket Jabatan must be unique per company.')
    ]