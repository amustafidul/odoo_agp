from odoo import models, fields, api, _
from cryptography.fernet import Fernet
import logging

_logger = logging.getLogger(__name__)


def _generate_default_fernet_key():
    return Fernet.generate_key().decode()


class HrContract(models.Model):
    _inherit = 'hr.contract'

    grade_id = fields.Many2one('odoo.payroll.grade', string='Grade', readonly=True, copy=False)
    wage_encrypted = fields.Char('Encrypted Wage')
    wage_ui = fields.Monetary(
        string='Wage',
        compute='_compute_wage_ui',
        store=False,
        readonly=True,
    )
    wage = fields.Monetary(
        string='Wage',
        compute='_compute_wage',
        store=True,
        readonly=True,
        help="Employee's monthly gross wage.",
        copy=False
    )
    da = fields.Monetary(compute='_compute_da', store=True)
    da_percentage = fields.Float('DA (%)', help="Dearness Allowance Percentage")
    dearness_id = fields.Many2one(
        'odoo.payroll.nilai.kemahalan',
        string='Dearness',
        compute='_compute_payroll_fields',
        search=True
    )
    positional_allowance_id = fields.Many2one(
        'odoo.payroll.tunjangan',
        string='Positional Allowance',
        compute='_compute_payroll_fields',
        search=True
    )
    positional_allowance = fields.Monetary(
        'Positional Allowance',
        compute='_compute_positional_allowance',
        store=True
    )
    bpfp = fields.Monetary(
        'BPFP',
        compute='_compute_positional_allowance',
        store=True
    )
    prorata_wage = fields.Float(string='Prorata Wage')

    def _get_cipher(self):
        IrConfig = self.env['ir.config_parameter'].sudo()
        param = IrConfig.get_param('hr_contract.fernet_key')
        if not param:
            generated_key = _generate_default_fernet_key()
            _logger.warning(f"Fernet key not found. Creating new random key: {generated_key}")
            IrConfig.set_param('hr_contract.fernet_key', generated_key)
            param = generated_key
        return Fernet(param.encode())

    @api.constrains('employee_id', 'state', 'kanban_state', 'date_start', 'date_end')
    def _check_current_contract(self):
        pass

    @api.model
    def create(self, vals):
        if vals.get('employee_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            if employee.grade_id:
                vals['grade_id'] = employee.grade_id.id
                vals['wage'] = employee.grade_id.grade_amount
        return super(HrContract, self).create(vals)

    @api.depends(
        'dearness_id',
        'dearness_id.hr_branch_id',
        'dearness_id.amount_kemahalan_percent',
        'dearness_id.amount_harga_sebulan',
        'positional_allowance_id',
        'positional_allowance_id.hr_branch_id',
        'positional_allowance_id.amount_tunjangan',
        'positional_allowance_id.amount_bpfp',
        'positional_allowance_id.koef_kemahalan_percent',
        'positional_allowance_id.amount_kemahalan'
    )
    def _compute_da(self):
        for rec in self:
            rec.da = rec.positional_allowance_id.amount_kemahalan if rec.positional_allowance_id else 0.0
            _logger.info(f"rec.da computed: {rec.da}")

    @api.depends('positional_allowance_id', 'positional_allowance_id.amount_tunjangan', 'positional_allowance_id.amount_bpfp')
    def _compute_positional_allowance(self):
        for rec in self:
            rec.positional_allowance = rec.positional_allowance_id.amount_tunjangan if rec.positional_allowance_id else 0.0
            rec.bpfp = rec.positional_allowance_id.amount_bpfp if rec.positional_allowance_id else 0.0

    def _compute_payroll_fields(self):
        for contract in self:
            job_history = self.env['hr.employee.histori.jabatan'].search([
                ('contract_id', '=', contract.id)
            ], limit=1)

            if job_history:
                dearness = self.env['odoo.payroll.nilai.kemahalan'].search([
                    ('hr_branch_id', '=', job_history.hr_branch_id.id)
                ], limit=1)
                contract.dearness_id = dearness.id if dearness else False

                positional = self.env['odoo.payroll.tunjangan'].search([
                    ('hr_branch_id', '=', job_history.hr_branch_id.id),
                    '|',
                    ('jabatan_id.name', '=', job_history.keterangan_jabatan_id.name),
                    ('jabatan_id.name', '=', job_history.fungsi_penugasan_id.name)
                ], limit=1)
                contract.positional_allowance_id = positional.id if positional else False
            else:
                contract.dearness_id = False
                contract.positional_allowance_id = False

    @api.depends('grade_id')
    def _compute_wage(self):
        for rec in self:
            rec.wage = rec.grade_id.grade_amount

    @api.depends('grade_id')
    def _compute_wage_ui(self):
        for rec in self:
            rec.wage_ui = rec.grade_id.grade_amount

    def _decrypt_wage(self):
        self.ensure_one()
        try:
            if self.wage_encrypted:
                cipher = self._get_cipher()
                decrypted = cipher.decrypt(self.wage_encrypted.encode()).decode()
                return float(decrypted)
        except Exception as e:
            _logger.warning(f"Failed to decrypt wage for contract {self.id}: {e}")
        return 0.0

    def action_refresh_wage(self):
        self._compute_wage()
        return True

    def action_manual_update_payroll_fields(self):
        for rec in self:
            rec._compute_payroll_fields()
            rec._compute_da()
            rec._compute_positional_allowance()

    @api.model
    def secure_missing_wages(self):
        cipher = self._get_cipher()
        contracts = self.search([
            ('grade_id', '!=', False)
        ])
        for contract in contracts:
            contract.action_refresh_wage()
            grade_amount = contract.grade_id.grade_amount
            if grade_amount:
                encrypted_wage = cipher.encrypt(str(grade_amount).encode()).decode()
                contract.write({
                    'wage_encrypted': encrypted_wage,
                    'wage': 0
                })