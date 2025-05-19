from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HistoriJabatan(models.Model):
    _name = "hr.employee.histori.jabatan"
    _description = "Histori Jabatan Employee"
    _order = "tmt_date desc"

    EMPLOYMENT_TYPE_MAPPING = {
        'tad': 'TAD',
        'pkwt': 'PKWT',
        'organik': 'Organik',
        'direksi': 'Direksi',
        'jajaran_dekom': 'Dekom & Perangkat Dekom',
        'konsultan_individu': 'Konsultan Individu',
    }

    name = fields.Char('No.')
    sk_doc_attachment_ids = fields.Many2many('ir.attachment', string='Penugasan / SK Document')
    sk_number = fields.Text('No. SK')
    jabatan = fields.Char('Jabatan')
    keterangan_jabatan_id = fields.Many2one('hr.employee.keterangan.jabatan', string='Keterangan')
    jabatan_komplit_id = fields.Many2one('hr.employee.jabatan.komplit', string='Jabatan Komplit')
    fungsi_penugasan_id = fields.Many2one('hr.employee.fungsi.penugasan', string='Fungsi Penugasan')
    tmt_date = fields.Date('TMT', index=True)
    masa_jabatan_bulan = fields.Char('Masa Jabatan', compute='_compute_masa_jabatan', store=True)
    tanggal_pengangkatan = fields.Date('Tanggal Pengangkatan')
    tanggal_selesai_kontrak = fields.Date('Tanggal Selesai Kontrak')
    employment_type = fields.Selection([
        ('tad', 'TAD'),
        ('pkwt', 'PKWT'),
        ('organik', 'Organik'),
        ('direksi', 'Direksi'),
        ('jajaran_dekom', 'Dekom & Perangkat Dekom'),
        ('konsultan_individu', 'Konsultan Individu'),
    ], string="Jenis Pegawai", index=True)
    currency_id = fields.Many2one(
        'res.currency', string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    delta_amount = fields.Monetary('Delta')
    vendor_tad_id = fields.Many2one('agp.vendor.tad', string="Vendor TAD")
    hr_branch_id = fields.Many2one('hr.branch', string='HR Branch')
    grade_id = fields.Many2one('odoo.payroll.grade', string='Grade')
    employee_id = fields.Many2one('hr.employee')
    contract_id = fields.Many2one('hr.contract', string='Related Contract', readonly=True)

    def _get_expected_contract_name(self):
        """
        Build expected contract name based on employment type and position fields.
        Used for syncing contract records.
        """
        self.ensure_one()
        name = self.EMPLOYMENT_TYPE_MAPPING.get(self.employment_type, 'Contract').upper()

        if self.employment_type in ['organik', 'pkwt'] and self.keterangan_jabatan_id:
            name += f" {self.keterangan_jabatan_id.name.upper()}"
        elif self.employment_type == 'tad' and self.fungsi_penugasan_id:
            name += f" {self.fungsi_penugasan_id.name.upper()}"

        if self.tmt_date:
            name += f" - {self.tmt_date.strftime('%Y-%m-%d')}"
        return name

    def _get_expected_old_contract_name(self):
        """
        Build the historical version of the contract name for backward compatibility.
        Used to match old contract names that did not include TMT date.
        """
        self.ensure_one()
        name = self.EMPLOYMENT_TYPE_MAPPING.get(self.employment_type, 'Contract').upper()

        if self.employment_type in ['organik', 'pkwt'] and self.keterangan_jabatan_id:
            name += f" {self.keterangan_jabatan_id.name.upper()}"
        elif self.employment_type == 'tad' and self.fungsi_penugasan_id:
            name += f" {self.fungsi_penugasan_id.name.upper()}"
        return name

    # Cron job method
    @api.model
    def _cron_sync_existing_contract_ids(self):
        """
        Cron job to automatically assign contract_id in history records based on generated contract name.
        Runs periodically to sync existing job history to corresponding contracts.
        """
        all_histories = self.search([('contract_id', '=', False)])
        for record in all_histories:
            contract_name = record._get_expected_contract_name()
            old_contract_name = record._get_expected_old_contract_name()
            existing_contract = self.env['hr.contract'].search([
                ('employee_id', '=', record.employee_id.id),
                '|',
                ('name', 'ilike', contract_name),
                ('name', 'ilike', old_contract_name),
            ], limit=1)
            if existing_contract:
                record.contract_id = existing_contract

    @api.depends('tanggal_pengangkatan', 'tanggal_selesai_kontrak')
    def _compute_masa_jabatan(self):
        """
        Compute the duration of employment from the appointment date to the contract end date or today.
        Result is stored in a human-readable format like '1 tahun, 3 bulan'.
        """
        for record in self:
            if not record.tanggal_pengangkatan:
                record.masa_jabatan_bulan = False
                continue
            start_date = record.tanggal_pengangkatan
            today = fields.Date.today()
            end_date = min(record.tanggal_selesai_kontrak, today) if record.tanggal_selesai_kontrak else today
            delta = relativedelta(end_date, start_date)
            parts = []
            if delta.years:
                parts.append(f"{delta.years} tahun")
            if delta.months:
                parts.append(f"{delta.months} bulan")
            if delta.days:
                parts.append(f"{delta.days} hari")
            record.masa_jabatan_bulan = ', '.join(parts) if parts else "0 hari"

    def action_open_form_histori_jabatan(self):
        """
        Open a form view popup for a specific job history record.
        Used typically in tree or kanban actions.
        """
        view_id = self.env.ref('agp_employee_ib.view_hr_employee_histori_jabatan_form_ib').id
        return {
            'name': 'Histori Jabatan',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.employee.histori.jabatan',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_id': view_id,
            'res_id': self.id,
            'context': {'default_id': self.id},
        }

    def _check_duplicate(self, vals):
        """
        Prevent duplicate job history records for the same employee.
        Checks against employee, employment type, TMT date, and optionally
        job/position identifiers. Raises ValidationError if a match is found.
        """
        domain = [
            ('employee_id', '=', vals.get('employee_id')),
            ('employment_type', '=', vals.get('employment_type')),
            ('tmt_date', '=', vals.get('tmt_date')),
        ]
        if vals.get('keterangan_jabatan_id'):
            domain.append(('keterangan_jabatan_id', '=', vals['keterangan_jabatan_id']))
        if vals.get('fungsi_penugasan_id'):
            domain.append(('fungsi_penugasan_id', '=', vals['fungsi_penugasan_id']))
        if self.sudo().search(domain, limit=1):
            raise ValidationError(_("Histori jabatan dengan data serupa sudah ada."))

    def sync_employee_from_history(self):
        """
        Update the employee record based on the most recent job history data.
        Only executes if the current record is the latest history.
        """
        for rec in self:
            if rec._is_latest_history():
                rec._update_employee_employment_type()
                rec._update_jabatan()
                rec._update_employee_grade()

    def force_sync_employee_fields(self):
        """
        Force update of the employee record based on current job history,
        regardless of whether it's the latest entry.
        """
        for rec in self:
            rec._update_employee_employment_type()
            rec._update_jabatan()
            rec._update_employee_grade()

    @api.model
    def create(self, vals):
        self._check_duplicate(vals)
        record = super().create(vals)
        record._update_or_create_contract()
        record.sync_employee_from_history()
        return record

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            rec._update_or_create_contract()
            rec.sync_employee_from_history()
        return res

    @api.onchange('sk_doc_attachment_ids')
    def _onchange_sk_doc_attachment_ids(self):
        """
        Auto-fill the SK number field based on the names of the attached documents.
        Triggered when SK attachments are changed.
        """
        for record in self:
            if record.sk_doc_attachment_ids:
                file_names = [f"{idx + 1}. {attachment.name}" for idx, attachment in enumerate(record.sk_doc_attachment_ids)]
                record.sk_number = ',\n '.join(file_names)
            else:
                record.sk_number = False

    @api.onchange('employment_type', 'keterangan_jabatan_id', 'fungsi_penugasan_id', 'grade_id')
    def _onchange_histori_jabatan(self):
        """
        Update employee fields in real-time when job history form fields are changed.
        Triggered via form 'onchange'. Should be used carefully as it writes to DB.
        """
        for rec in self:
            employee_id = self._context.get('params', {}).get('id')
            emp = self.env['hr.employee'].browse(employee_id) if employee_id else rec.employee_id

            if not emp or not emp.exists():
                continue

            safe_histories = [h for h in emp.histori_jabatan_ids if h.id]
            latest_history = sorted(safe_histories, key=lambda h: h.id, reverse=True)[:1]

            if latest_history and latest_history[0] == rec._origin:
                employment_type = rec.employment_type or emp.employment_type

                emp.write({'employment_type': employment_type})

                if employment_type in ['organik', 'pkwt']:
                    emp.write({
                        'keterangan_jabatan_id': rec.keterangan_jabatan_id.id,
                        'jabatan_komplit_id': rec.jabatan_komplit_id.id,
                    })
                else:
                    emp.write({
                        'fungsi_penugasan_id': rec.fungsi_penugasan_id.id,
                    })

                emp.grade_id = rec.grade_id.id
                emp._onchange_field_jabatan()

    def unlink(self):
        """
        Override delete to deactivate contract and reset employee fields
        if no other history records exist.
        """
        employee_ids = self.mapped('employee_id').ids
        _logger.info("Unlinking Histori Jabatan IDs: %s", self.ids)

        for rec in self:
            if rec.contract_id:
                rec.contract_id.write({'active': False})

        remaining_histories = self.env['hr.employee.histori.jabatan'].search([
            ('employee_id', 'in', employee_ids),
            ('id', 'not in', self.ids)
        ])

        employees = self.env['hr.employee'].browse(employee_ids)

        for employee in employees:
            histories = remaining_histories.filtered(lambda h: h.employee_id.id == employee.id)
            if histories:
                latest = sorted(
                    histories,
                    key=lambda h: h.create_date or fields.Datetime.now(),
                    reverse=True
                )[0]
                latest.force_sync_employee_fields()
            else:
                employee.write({
                    'employment_type': False,
                    'keterangan_jabatan_id': False,
                    'fungsi_penugasan_id': False,
                    'jabatan_komplit_id': False,
                    'grade_id': False,
                    'hr_branch_id': False,
                })

        return super().unlink()

    def _update_employee_employment_type(self):
        """
        Update the employment type field on the employee record based on this history.
        """
        if self.employee_id:
            self.employee_id.write({'employment_type': self.employment_type})

    def _update_jabatan(self):
        """
        Update the employee's job title and related fields based on this history record.
        Includes handling for different employment types.
        """
        if self.employee_id:
            if self.employment_type in ['organik', 'pkwt']:
                self.employee_id.keterangan_jabatan_id = self.keterangan_jabatan_id.id
                self.employee_id.jabatan_komplit_id = self.jabatan_komplit_id.id
            else:
                self.employee_id.fungsi_penugasan_id = self.fungsi_penugasan_id.id
            self.employee_id._onchange_field_jabatan()

    def _update_employee_grade(self):
        """
        Update the employee's grade field based on the latest available job history.
        Also triggers update to linked contracts if necessary.
        """
        for rec in self:
            if rec.employee_id:
                latest = rec.employee_id.histori_jabatan_ids.sorted('id', reverse=True)[:1]
                if latest:
                    rec.employee_id.grade_id = latest.grade_id.id
                    rec.employee_id._update_contract_grade()

    def _is_latest_history(self):
        """
        Check whether this job history entry is the most recent for the employee.
        Used to determine if a sync should proceed.
        """
        self.ensure_one()
        if not self.employee_id:
            return False
        latest = self.env['hr.employee.histori.jabatan'].search([
            ('employee_id', '=', self.employee_id.id),
            ('tmt_date', '!=', False)
        ], order='tmt_date desc', limit=1)
        return latest.id == self.id

    def _update_contract_history(self, employee):
        """
        Update the contract history record with current active contracts.
        Ensures that HR staff can see linked contracts across history.
        """
        contract_history = self.env['hr.contract.history'].search([('employee_id', '=', employee.id)], limit=1)
        if not contract_history:
            contract_history = self.env['hr.contract.history'].create({'employee_id': employee.id})
        contracts = self.env['hr.contract'].search([('employee_id', '=', employee.id)])
        contract_history.write({'contract_ids': [(6, 0, contracts.ids)]})

    def _update_or_create_contract(self):
        """
        Automatically create or update a contract record based on the job history.
        Sets contract name, branch, grade, and related allowances.
        """
        for record in self.filtered(lambda r: r.employee_id and r.hr_branch_id):

            if not record._is_latest_history():
                continue

            contract_name = record._get_expected_contract_name()

            branch_id = record.hr_branch_id.id
            dearness = self.env['odoo.payroll.nilai.kemahalan'].search(
                [('hr_branch_id', '=', branch_id)], limit=1)
            positional = self.env['odoo.payroll.tunjangan'].search([
                ('hr_branch_id', '=', branch_id),
                ('jabatan_id', 'in', [record.keterangan_jabatan_id.id, record.fungsi_penugasan_id.id])
            ], limit=1)

            contract_vals = {
                'name': contract_name,
                'employee_id': record.employee_id.id,
                'date_start': record.tmt_date,
                'date_end': record.tanggal_selesai_kontrak,
                'grade_id': record.grade_id.id,
                'wage': record.grade_id.grade_amount,
                'resource_calendar_id': record.employee_id.resource_calendar_id.id or False,
                'dearness_id': dearness.id or False,
                'positional_allowance_id': positional.id or False,
            }

            if record.contract_id:
                record.contract_id.write(contract_vals)
            else:
                new_contract = self.env['hr.contract'].create(contract_vals)
                new_contract.invalidate_model()
                record.contract_id = new_contract

            self._update_contract_history(record.employee_id)


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _order = 'id desc'