from odoo import models, fields, api, _
from odoo.tools.misc import format_date
from odoo.exceptions import AccessError, UserError, ValidationError
from pytz import timezone
from datetime import date, datetime, timedelta
from odoo.tools import float_round

import logging

_logger = logging.getLogger(__name__)


class HrLeaveLembur(models.Model):
    _name = 'hr.leave.lembur'
    _inherit = 'hr.leave'
    _description = 'Lembur'
    _order = 'new_date_field desc'

    lembur_location_id = fields.Many2one('res.branch', string="Penempatan", domain=lambda self: [('id', 'in', self.env.user.branch_id.ids)])
    lembur_purpose = fields.Text(string="Tujuan Lembur")
    lembur_request_hour_from = fields.Selection([
        ('0', '00:00'), ('0.5', '00:30'),
        ('1', '01:00'), ('1.5', '01:30'),
        ('2', '02:00'), ('2.5', '02:30'),
        ('3', '03:00'), ('3.5', '03:30'),
        ('4', '04:00'), ('4.5', '04:30'),
        ('5', '05:00'), ('5.5', '05:30'),
        ('6', '06:00'), ('6.5', '06:30'),
        ('7', '07:00'), ('7.5', '07:30'),
        ('8', '08:00'), ('8.5', '08:30'),
        ('9', '09:00'), ('9.5', '09:30'),
        ('10', '10:00'), ('10.5', '10:30'),
        ('11', '11:00'), ('11.5', '11:30'),
        ('12', '12:00'), ('12.5', '12:30'),
        ('13', '13:00'), ('13.5', '13:30'),
        ('14', '14:00'), ('14.5', '14:30'),
        ('15', '15:00'), ('15.5', '15:30'),
        ('16', '16:00'), ('16.5', '16:30'),
        ('17', '17:00'), ('17.5', '17:30'),
        ('18', '18:00'), ('18.5', '18:30'),
        ('19', '19:00'), ('19.5', '19:30'),
        ('20', '20:00'), ('20.5', '20:30'),
        ('21', '21:00'), ('21.5', '21:30'),
        ('22', '22:00'), ('22.5', '22:30'),
        ('23', '23:00'), ('23.5', '23:30')], string='Hour from')
    lembur_request_hour_to = fields.Selection([
        ('0', '00:00'), ('0.5', '00:30'),
        ('1', '01:00'), ('1.5', '01:30'),
        ('2', '02:00'), ('2.5', '02:30'),
        ('3', '03:00'), ('3.5', '03:30'),
        ('4', '04:00'), ('4.5', '04:30'),
        ('5', '05:00'), ('5.5', '05:30'),
        ('6', '06:00'), ('6.5', '06:30'),
        ('7', '07:00'), ('7.5', '07:30'),
        ('8', '08:00'), ('8.5', '08:30'),
        ('9', '09:00'), ('9.5', '09:30'),
        ('10', '10:00'), ('10.5', '10:30'),
        ('11', '11:00'), ('11.5', '11:30'),
        ('12', '12:00'), ('12.5', '12:30'),
        ('13', '13:00'), ('13.5', '13:30'),
        ('14', '14:00'), ('14.5', '14:30'),
        ('15', '15:00'), ('15.5', '15:30'),
        ('16', '16:00'), ('16.5', '16:30'),
        ('17', '17:00'), ('17.5', '17:30'),
        ('18', '18:00'), ('18.5', '18:30'),
        ('19', '19:00'), ('19.5', '19:30'),
        ('20', '20:00'), ('20.5', '20:30'),
        ('21', '21:00'), ('21.5', '21:30'),
        ('22', '22:00'), ('22.5', '22:30'),
        ('23', '23:00'), ('23.5', '23:30')], string='Hour to')
    date_from = fields.Datetime()
    date_to = fields.Datetime()
    new_date_field = fields.Date(string="Tanggal")
    duration_waktu_lembur = fields.Char(compute='_compute_duration_waktu_lembur')
    duration_waktu_lembur_ori = fields.Float(compute='_compute_duration_waktu_lembur_ori', string="Durasi Lembur (Jam)",
                                         store=False)

    @api.constrains('lembur_request_hour_from', 'new_date_field')
    def _check_pengajuan_minimal_1_jam_sebelum_lembur(self):
        for rec in self:
            now_utc = fields.Datetime.now()
            now = now_utc + timedelta(hours=7)  # WIB
            tanggal_lembur = rec.new_date_field  # <<--- langsung pakai saja!
            jam_lembur_mulai = rec.lembur_request_hour_from
            if not tanggal_lembur or not jam_lembur_mulai:
                continue
            jam_float = float(jam_lembur_mulai)
            jam = int(jam_float)
            menit = int((jam_float - jam) * 60)
            waktu_mulai = datetime.combine(tanggal_lembur, datetime.min.time()) + timedelta(hours=jam, minutes=menit)
            _logger.info('Waktu lembur: %s | Sekarang: %s', waktu_mulai, now)
            if waktu_mulai - now < timedelta(hours=1):
                raise ValidationError(_("Pengajuan lembur harus dilakukan minimal 1 jam sebelum jam mulai lembur!"))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # if 'date_from' in fields_list:
        #     res['new_date_field'] = res.get('date_from') + timedelta(hours=7)
        # else:
        res['new_date_field'] = fields.Date.context_today(self) + timedelta(hours=7)
        return res

    @api.depends('lembur_request_hour_from', 'lembur_request_hour_to')
    def _compute_duration_waktu_lembur(self):
        for record in self:
            if record.lembur_request_hour_from and record.lembur_request_hour_to:
                from_time = float(record.lembur_request_hour_from)
                to_time = float(record.lembur_request_hour_to)

                # Handle case where end time is past midnight
                if to_time < from_time:
                    to_time += 24

                duration = to_time - from_time
                hours = int(duration)
                minutes = int((duration - hours) * 60)

                record.duration_waktu_lembur = f"{hours} hours, {minutes} minutes"
            else:
                record.duration_waktu_lembur = "N/A"

    @api.depends('lembur_request_hour_from', 'lembur_request_hour_to')
    def _compute_duration_waktu_lembur_ori(self):
        for record in self:
            if record.lembur_request_hour_from and record.lembur_request_hour_to:
                from_time = float(record.lembur_request_hour_from)
                to_time = float(record.lembur_request_hour_to)

                # Handle case where end time is past midnight
                if to_time < from_time:
                    to_time += 24

                duration = to_time - from_time
                record.duration_waktu_lembur_ori = duration
            else:
                record.duration_waktu_lembur_ori = 0.0

    lembur_status_id = fields.Many2one(
        "hr.leave.type.lembur", compute='_compute_from_lembur_employee_id', store=True, string="Tipe Lembur", required=False,
        readonly=False,
        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)],
                'validate': [('readonly', True)]},
        domain="[('company_id', '=?', employee_company_id), '|', ('requires_allocation', '=', 'no'), ('has_valid_allocation', '=', True)]",
        tracking=True)

    leave_type_request_unit = fields.Selection(related='lembur_status_id.request_unit', readonly=True)

    request_unit_half = fields.Boolean('Half Day', compute='_compute_request_unit_half', store=True, readonly=False)
    request_unit_hours = fields.Boolean('Custom Hours', compute='_compute_request_unit_hours', store=True,
                                        readonly=False)

    @api.depends('lembur_status_id', 'request_unit_hours')
    def _compute_request_unit_half(self):
        for lembur in self:
            if lembur.lembur_status_id or lembur.request_unit_hours:
                lembur.request_unit_half = False

    @api.depends('lembur_status_id', 'request_unit_half')
    def _compute_request_unit_hours(self):
        for lembur in self:
            if lembur.lembur_status_id or lembur.request_unit_half:
                lembur.request_unit_hours = False

    @api.depends('employee_id', 'employee_ids')
    def _compute_from_lembur_employee_id(self):
        for lembur in self:
            lembur.manager_id = lembur.employee_id.parent_id.id
            if lembur.lembur_status_id.requires_allocation == 'no':
                continue
            if not lembur.employee_id or lembur.employee_ids:
                lembur.lembur_status_id = False
            elif lembur.employee_id.user_id != self.env.user and lembur._origin.employee_id != lembur.employee_id:
                if lembur.employee_id and not lembur.lembur_status_id.with_context(
                        employee_id=lembur.employee_id.id).has_valid_allocation:
                    lembur.lembur_status_id = False

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date(self):
        if self._name != 'hr.leave.lembur':
            super()._check_date()

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id.sudo(False)._get_unusual_days(date_from, date_to)

    @api.model
    def create(self, vals):
        if self._name == 'hr.leave.lembur':
            today = date.today()

            new_date_field = fields.Date.from_string(vals.get('new_date_field'))
            h_minus_1 = today - timedelta(days=1)

            if new_date_field < h_minus_1:
                raise UserError(_("Pengajuan lembur hanya dapat dilakukan dari H-1 hingga hari ini dan seterusnya."))

            # ensure lembur_status_id must be populated
            if not vals.get("lembur_status_id"):
                default_type = self.env.ref("agp_hr_leave_lembur_ib.default_lembur_status_type_lembur",
                                            raise_if_not_found=False)
                if default_type:
                    vals["lembur_status_id"] = default_type.id

            res = super(HrLeaveLembur, self).create(vals)
            for rec in res:
                rec.state = 'draft'

                approval_workflow_obj = self.env['approval.workflow'].sudo().search([
                    ('synced', '=', True),
                    ('res_model.model', '=', rec._name)
                ], limit=1)

                if approval_workflow_obj:
                    approval_workflow = approval_workflow_obj[0]
                    model_obj = self.env[f'{approval_workflow.res_model.model}'].sudo()

                    field_approval_line_ids = f'x_x_{model_obj._name.replace(".", "_")}_approval_line_ids'
                    if hasattr(model_obj, field_approval_line_ids):
                        line_model_name = f'x_{model_obj._name.replace(".", "_")}_approval_line'

                        target_model_records = self.env[model_obj._name].sudo().search([
                            (field_approval_line_ids, '=', False)
                        ])

                        if target_model_records:
                            line_data_list = []
                            for target_record in target_model_records:
                                for line in approval_workflow.line_ids:
                                    line_data = {
                                        'x_sequence': line.sequence,
                                        'x_approver_user_id': line.user_id.id if line.workflow_type == 'user' else None,
                                        'x_approver_jabatan_id': line.approver_jabatan_id.id if line.workflow_type == 'jabatan' else None,
                                        'x_approver_ds_level': line.approver_ds_level if line.workflow_type == 'ds' else None,
                                        'x_approver_role_id': line.approver_role_id.id if line.workflow_type == 'role' else None,
                                        f'x_{model_obj._name.replace(".", "_")}_id': target_record.id
                                    }

                                    if approval_workflow.approval_type == 'nominal':
                                        line_data['x_min_nominal'] = line.min_nominal
                                        line_data['x_max_nominal'] = line.max_nominal

                                    line_data_list.append(line_data)

                            if line_data_list:
                                self.env[line_model_name].sudo().create(line_data_list)

                else:
                    raise ValidationError(_(
                        "Dynamic approval workflow is not set. "
                        "Please check the approval workflow settings."
                    ))

            return res

        else:
            return super().create(vals)

    def write(self, vals):
        if self._name == 'hr.leave.lembur':
            today = date.today()
            if 'new_date_field' in vals:
                new_date_field = fields.Date.from_string(vals.get('new_date_field', self.new_date_field))

                h_minus_1 = today - timedelta(days=1)
                if new_date_field < h_minus_1:
                    raise UserError(
                        _("Pengajuan lembur hanya dapat dilakukan dari H-1 hingga hari ini dan seterusnya."))

        return super().write(vals)

    def copy_data(self, default=None):
        if default and 'date_from' in default and 'date_to' in default:
            default['request_date_from'] = default.get('date_from')
            default['request_date_to'] = default.get('date_to')
            return super().copy_data(default)
        elif self.state in {"cancel", "refuse"}:  # No overlap constraint in these cases
            return super().copy_data(default)
        raise UserError(_('Catatan lembur tidak dapat diduplikat.'))

    def name_get(self):
        res = []
        for leave in self:
            user_tz = timezone(leave.tz)
            date_from_utc = leave.date_from and leave.date_from.astimezone(user_tz).date()
            date_to_utc = leave.date_to and leave.date_to.astimezone(user_tz).date()
            lembur_location = leave.lembur_location_id.name or "Location unspecified"
            lembur_status_name = leave.lembur_status_id.name or "Type unspecified"

            # Dapatkan durasi lembur yang dihitung
            lembur_duration = leave.duration_waktu_lembur if leave.duration_waktu_lembur else "N/A"

            if self.env.context.get('short_name'):
                res.append((leave.id, _("%s at %s : %s") % (
                    leave.name or lembur_status_name, lembur_location, lembur_duration)))
            else:
                if leave.holiday_type == 'company':
                    target = leave.mode_company_id.name or "Company unspecified"
                elif leave.holiday_type == 'department':
                    target = leave.department_id.name or "Department unspecified"
                elif leave.holiday_type == 'category':
                    target = leave.category_id.name or "Category unspecified"
                elif leave.employee_id:
                    target = leave.employee_id.name or "Employee unspecified"
                else:
                    target = ', '.join(leave.employee_ids.mapped('name')) or "Employees unspecified"

                display_date = format_date(self.env, date_from_utc) or ""
                if leave.leave_type_request_unit == 'hour':
                    res.append((
                        leave.id,
                        _("Lembur at %(location)s: %(duration)s on %(date)s") % {
                            'location': lembur_location,
                            'duration': lembur_duration,
                            'date': leave.new_date_field,
                        }
                    ))
                else:
                    if leave.number_of_days > 1 and date_from_utc and date_to_utc:
                        display_date += ' - %s' % format_date(self.env, date_to_utc) or ""
                    res.append((
                        leave.id,
                        _("Lembur at %(location)s: %(duration)s (%(start)s)") % {
                            'location': lembur_location,
                            'duration': lembur_duration,
                            'start': leave.new_date_field,
                        }
                    ))
        return res

    def action_submit_dyamic_approval_timeoff(self):
        # super().action_submit_dyamic_approval_timeoff()
        if self._name == 'hr.leave.lembur':
            for rec in self:
                # Periksa apakah approval line tersedia
                if not hasattr(rec, 'x_x_hr_leave_lembur_approval_line_ids'):
                    raise UserError(_("Dynamic approval configuration not found!"))
                else:
                    self.env.cr.execute("""
                            UPDATE hr_leave_lembur SET state = %s WHERE id = %s;
                        """, ('on_review', tuple(rec.ids)))

                    # rec.state = 'on_review'

                    line_not_approve = self.env['x_hr_leave_lembur_approval_line'].search([
                        ('x_name', '!=', 'approved'),
                        ('x_hr_leave_lembur_id', '=', rec.id)
                    ])

                    line_approval = line_not_approve and line_not_approve[0] or None

                    if line_approval:
                        approver_emails = []
                        approver_names = []

                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        record_url = f"{base_url}/web#id={rec.id}&model=hr.leave.lembur&view_type=form"

                        if line_approval.x_approver_user_id:
                            email = line_approval.x_approver_user_id.employee_id.work_email
                            if email:
                                approver_emails.append(email)
                                approver_names.append(line_approval.x_approver_user_id.employee_id.name)

                        elif line_approval.x_approver_jabatan_id:
                            employees_with_position = self.env['hr.employee'].search([
                                ('fungsi_penugasan_id', '=', line_approval.x_approver_jabatan_id.id)
                            ])
                            approver_emails += [emp.work_email for emp in employees_with_position if emp.work_email]
                            approver_names += [emp.name for emp in employees_with_position]

                        elif line_approval.x_approver_ds_level:
                            manager = rec.employee_id
                            for i in range(int(line_approval.x_approver_ds_level)):
                                manager = manager.parent_id if manager else None
                            if manager and manager.work_email:
                                approver_emails.append(manager.work_email)
                                approver_names.append(manager.name)

                        elif line_approval.x_approver_role_id:
                            role_users = self.env['res.users'].search([
                                ('groups_id', 'in', line_approval.x_approver_role_id.id)
                            ])
                            for user in role_users:
                                email = user.partner_id.email
                                if email:
                                    approver_emails.append(email)
                                    approver_names.append(user.partner_id.name)

                        approver_emails = [email for email in approver_emails if isinstance(email, str) and email]

                        if approver_emails:
                            mail_values = {
                                'subject': _('Approval Needed for Lembur Request'),
                                'email_to': ",".join(approver_emails),
                                'body_html': _(
                                    "<p>Dear Approvers,</p>"
                                    "<p>A new lembur request from %(employee_name)s requires your approval.</p>"
                                    "<p>Lembur Details:</p>"
                                    "<ul>"
                                    "<li><strong>Employee:</strong> %(employee_name)s</li>"
                                    "<li><strong>Date From:</strong> %(date_from)s</li>"
                                    "<li><strong>Date To:</strong> %(date_to)s</li>"
                                    "</ul>"
                                    "<p>Please review the request in the system and take the necessary action.</p>"
                                    "<p><a href='%(record_url)s'>Click here to view the lembur request</a></p>"
                                ) % {
                                                 'employee_name': rec.employee_id.name,
                                                 'date_from': rec.date_from,
                                                 'date_to': rec.date_to,
                                                 'record_url': record_url,
                                             },
                            }
                            self.env['mail.mail'].sudo().create(mail_values)

    is_hr_leave_lembur_model = fields.Boolean(
        string="Is Lembur Model",
        compute='_compute_is_hr_leave_lembur_model',
        store=False
    )

    def _compute_is_hr_leave_lembur_model(self):
        for record in self:
            record.is_hr_leave_lembur_model = record._name == 'hr.leave.lembur'

    rejection_reason = fields.Text(string="Rejection Reason", readonly=True)
    ask_for_revision_reason = fields.Text(string="Reason", readonly=True)

    def action_approve_dynamic_approval(self):
        super().action_approve_dynamic_approval()
        if self._name == 'hr.leave.lembur':
            current_user = self.env.user
            current_employee = self.env['hr.employee'].search([('user_id', '=', current_user.id)], limit=1)

            if not current_employee:
                raise ValidationError("Employee terkait user ini tidak ditemukan.")

            if self.state == 'validate':
                raise ValidationError("Pengajuan ini sudah tervalidasi.")

            current_date = fields.Date.context_today(self)

            line_not_approve = self.env['x_hr_leave_lembur_approval_line'].search([
                ('x_name', '!=', 'approved'),
                ('x_hr_leave_lembur_id', '=', self.id)
            ])

            approver_cache = {}

            def get_effective_approver(employee):
                if employee.id in approver_cache:
                    return approver_cache[employee.id]

                checked_employees = set()
                while employee and employee not in checked_employees:
                    checked_employees.add(employee)
                    leave = self.env['hr.leave.lembur'].search([
                        ('employee_id', '=', employee.id),
                        ('state', '=', 'validate'),
                        ('date_from', '<=', current_date),
                        ('date_to', '>=', current_date)
                    ], limit=1)

                    if leave and leave.delegation_id:
                        employee = leave.delegation_id
                    else:
                        approver_cache[employee.id] = employee
                        return employee

                approver_cache[employee.id] = None
                return None

            if line_not_approve:
                approval = line_not_approve[0]
                if approval:
                    is_approved = False
                    approver_emails = []

                    if approval.x_approver_user_id:
                        effective_approver = get_effective_approver(approval.x_approver_user_id.employee_id)
                        if effective_approver and effective_approver.user_id == current_user:
                            is_approved = True

                    elif approval.x_approver_jabatan_id:
                        employees_with_position = self.env['hr.employee'].search([
                            ('fungsi_penugasan_id', '=', approval.x_approver_jabatan_id.id)
                        ])
                        effective_approvers = {
                            get_effective_approver(emp) for emp in employees_with_position if emp}
                        effective_approvers = {emp for emp in effective_approvers if emp}
                        if current_employee in effective_approvers:
                            is_approved = True
                            approver_emails = [emp.work_email for emp in effective_approvers if emp.work_email]

                    elif approval.x_approver_ds_level:
                        ds_level = int(approval.x_approver_ds_level)
                        manager = self.employee_id
                        for _i in range(ds_level):
                            manager = manager.parent_id if manager else None
                        if manager:
                            effective_approver = get_effective_approver(manager)
                            if effective_approver and effective_approver.user_id == current_user:
                                is_approved = True
                                approver_emails = [effective_approver.work_email]

                    elif approval.x_approver_role_id:
                        role_users = self.env['res.users'].sudo().search(
                            [('groups_id', 'in', approval.x_approver_role_id.id)])
                        effective_approvers = {
                            get_effective_approver(user.employee_id) for user in role_users if user.employee_id}
                        effective_approvers = {emp for emp in effective_approvers if emp}
                        if current_employee in effective_approvers:
                            is_approved = True
                            approver_emails = [emp.work_email for emp in effective_approvers if emp.work_email]

                    if is_approved:
                        approval.write({'x_name': "approved", 'write_date': current_date})

                        next_approvals = self.x_x_hr_leave_lembur_approval_line_ids.filtered(
                            lambda l: l.x_name != "approved").sorted('x_sequence')
                        if next_approvals:
                            next_approvers = next_approvals[0]
                            if next_approvers:
                                self._send_email_to_approvers(next_approvers, next_approvals)

                        if all(line.x_name == "approved" for line in self.x_x_hr_leave_lembur_approval_line_ids):
                            self.write({'state': 'validate'})
                            self._send_final_approval_email()

                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _("Approval Successful"),
                                'message': _('You have successfully approved this lembur request.'),
                                'type': 'success',
                                'sticky': False,
                                'next': {'type': 'ir.actions.client', 'tag': 'reload'}
                            }
                        }
                    else:
                        raise ValidationError("Anda bukan approver yang sesuai untuk level persetujuan ini.")

            raise ValidationError("Tidak ada level persetujuan yang tersedia.")

    def _send_email_to_approvers(self, approver_lines, approval_record):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        record_url = f"{base_url}/web#id={self.id}&model=hr.leave.lembur&view_type=form"
        approver_emails = set()

        for approver_line in approver_lines:
            if approver_line.x_approver_user_id:
                email = approver_line.x_approver_user_id.employee_id.work_email
                if email:
                    approver_emails.add(email)
            elif approver_line.x_approver_jabatan_id:
                employees_with_position = self.env['hr.employee'].search([
                    ('fungsi_penugasan_id', '=', approver_line.x_approver_jabatan_id.id)
                ])
                approver_emails.update(emp.work_email for emp in employees_with_position if emp.work_email)
            elif approver_line.x_approver_ds_level:
                manager = self.employee_id
                for i in range(int(approver_line.x_approver_ds_level)):
                    manager = manager.parent_id if manager else None
                if manager and manager.work_email:
                    approver_emails.add(manager.work_email)
            elif approver_line.x_approver_role_id:
                role_users = self.env['res.users'].search([
                    ('groups_id', 'in', approver_line.x_approver_role_id.id)
                ])
                approver_emails.update(
                    user.partner_id.email for user in role_users if user.partner_id and user.partner_id.email)

        approver_emails = [email for email in approver_emails if isinstance(email, str) and email]

        if approver_emails:
            mail_values_list = []
            for email in approver_emails:
                mail_values_list.append({
                    'subject': _('Approval Required for Lembur Request'),
                    'email_to': email,
                    'body_html': _(
                        "<p>Dear Approver,</p>"
                        "<p>A lembur request from %(employee_name)s requires your approval.</p>"
                        "<p><a href='%(record_url)s'>Click here to review and approve the lembur request</a>.</p>"
                    ) % {
                                     'employee_name': self.employee_id.name,
                                     'record_url': record_url,
                                 },
                })

            self.env['mail.mail'].sudo().create(mail_values_list)

    def _send_final_approval_email(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        record_url = f"{base_url}/web#id={self.id}&model=hr.leave.lembur&view_type=form"

        employee_email = self.employee_id.work_email

        hr_manager_group = self.env.ref('hr.group_hr_manager')
        hr_manager_emails = set()
        if hr_manager_group:
            hr_manager_employees = self.env['hr.employee'].search([('user_id', 'in', hr_manager_group.users.ids)])
            hr_manager_emails.update(
                email.strip() for hr_employee in hr_manager_employees if hr_employee.work_email
                for email in hr_employee.work_email.split(',') if email.strip()
            )

        mail_values_list = []
        if employee_email:
            mail_values_list.append({
                'subject': _('Your Lembur Request Has Been Approved'),
                'email_to': employee_email,
                'body_html': _(
                    "<p>Dear %(employee_name)s,</p>"
                    "<p>Your lembur request has been approved.</p>"
                    "<p><a href='%(record_url)s'>Click here to view your lembur request</a>.</p>"
                ) % {
                                 'employee_name': self.employee_id.name,
                                 'record_url': record_url,
                             },
            })

        # HR Manager
        if hr_manager_emails:
            mail_values_list.append({
                'subject': _('Lembur Request Approved Notification'),
                'email_to': ",".join(hr_manager_emails),
                'body_html': _(
                    "<p>Dear HR Manager,</p>"
                    "<p>A lembur request from %(employee_name)s has been fully approved.</p>"
                    "<p><a href='%(record_url)s'>Click here to view the lembur request</a>.</p>"
                ) % {
                                 'employee_name': self.employee_id.name,
                                 'record_url': record_url,
                             },
            })

        if mail_values_list:
            self.env['mail.mail'].sudo().create(mail_values_list)

    def _check_overtime_deductible(self, leaves):
        if self._name == 'hr.leave':
            # If the type of leave is overtime deductible, we have to check that the employee has enough extra hours
            for leave in leaves:
                if not leave.overtime_deductible:
                    continue
                employee = leave.employee_id.sudo()
                duration = leave.number_of_hours_display
                if duration > employee.total_overtime:
                    if employee.user_id == self.env.user:
                        raise ValidationError(_('You do not have enough extra hours to request this leave'))
                    raise ValidationError(_('The employee does not have enough extra hours to request this leave.'))
                if not leave.overtime_id:
                    leave.sudo().overtime_id = self.env['hr.attendance.overtime'].sudo().create({
                        'employee_id': employee.id,
                        'date': leave.date_from,
                        'adjustment': True,
                        'duration': -1 * duration,
                    })
        else:
            for leave in leaves:
                if not leave.overtime_deductible:
                    continue
                employee = leave.employee_id.sudo()
                duration = leave.number_of_hours_display

                if not leave.overtime_id:
                    leave.sudo().overtime_id = self.env['hr.attendance.overtime'].sudo().create({
                        'employee_id': employee.id,
                        'date': leave.date_from,
                        'adjustment': True,
                        'duration': -1 * duration,
                    })

    def action_draft(self):
        if self._name == 'hr.leave':
            overtime_leaves = self.filtered('overtime_deductible')
            if any([l.employee_overtime < float_round(l.number_of_hours_display, 2) for l in overtime_leaves]):
                if self.employee_id.user_id.id == self.env.user.id:
                    raise ValidationError(_('You do not have enough extra hours to request this leave'))
                raise ValidationError(_('The employee does not have enough extra hours to request this leave.'))

            res = super().action_draft()
            overtime_leaves.overtime_id.sudo().unlink()
            for leave in overtime_leaves:
                overtime = self.env['hr.attendance.overtime'].sudo().create({
                    'employee_id': leave.employee_id.id,
                    'date': leave.date_from,
                    'adjustment': True,
                    'duration': -1 * leave.number_of_hours_display
                })
                leave.sudo().overtime_id = overtime.id
            return res
        else:
            overtime_leaves = self.filtered('overtime_deductible')

            res = super().action_draft()
            overtime_leaves.overtime_id.sudo().unlink()
            for leave in overtime_leaves:
                overtime = self.env['hr.attendance.overtime'].sudo().create({
                    'employee_id': leave.employee_id.id,
                    'date': leave.date_from,
                    'adjustment': True,
                    'duration': -1 * leave.number_of_hours_display
                })
                leave.sudo().overtime_id = overtime.id
            return res

    is_visible_to_current_user = fields.Boolean(
        string="Visible to Current User",
        compute="_compute_is_visible_to_current_user",
        search="_search_is_visible_to_current_user",
        store=False
    )
    persetujuan_visible_or_not = fields.Boolean(related='is_visible_to_current_user')

    def _compute_is_visible_to_current_user(self):
        current_user = self.env.user
        current_employee = current_user.employee_id

        for record in self:
            approval_lines = getattr(record, 'x_x_hr_leave_lembur_approval_line_ids', False)
            if approval_lines:
                record.is_visible_to_current_user = any(
                    line.x_approver_user_id.employee_id == current_employee or
                    (
                            line.x_approver_jabatan_id and
                            current_employee.fungsi_penugasan_id and
                            line.x_approver_jabatan_id in current_employee.fungsi_penugasan_id
                    ) or
                    (line.x_approver_ds_level and record._check_ds_level_approver(line, current_employee)) or
                    (line.x_approver_role_id and current_user in line.x_approver_role_id.users)
                    for line in approval_lines
                )
            else:
                record.is_visible_to_current_user = False

    def _search_is_visible_to_current_user(self, operator, value):
        """Custom search for is_visible_to_current_user."""
        current_user = self.env.user
        current_employee = current_user.employee_id

        record_ids = []
        all_records = self.search([('state', '=', 'on_review')])

        for record in all_records:
            is_visible = False
            for line in record.x_x_hr_leave_lembur_approval_line_ids:
                if line.x_approver_user_id.employee_id == current_employee:
                    is_visible = True
                    break
                if line.x_approver_jabatan_id and current_employee.fungsi_penugasan_id and line.x_approver_jabatan_id == current_employee.fungsi_penugasan_id:
                    is_visible = True
                    break
                if line.x_approver_ds_level and record._check_ds_level_approver(line, current_employee):
                    is_visible = True
                    break
                if line.x_approver_role_id and current_user in line.x_approver_role_id.users:
                    is_visible = True
                    break

            if is_visible:
                record_ids.append(record.id)

        return [('id', 'in', record_ids)]

    def _check_ds_level_approver(self, line, current_employee):
        """Check if the current employee meets the `x_approver_ds_level`."""
        manager = self.employee_id
        for _ in range(int(line.x_approver_ds_level)):
            manager = manager.parent_id if manager else None
        return manager == current_employee

    def activity_update(self):
        if self._name == 'hr.leave.lembur':
            to_clean, to_do = self.env['hr.leave.lembur'], self.env['hr.leave.lembur']
            for holiday in self:
                if holiday._name == 'hr.leave.lembur':
                    note = _(
                        'New Lembur Request created by %(user)s',
                        user=holiday.create_uid.name,
                    )
                else:
                    note = _(
                        'New %(leave_type)s Request created by %(user)s',
                        leave_type=holiday.holiday_status_id.name,
                        user=holiday.create_uid.name,
                    )

                if holiday.state == 'draft':
                    to_clean |= holiday
                elif holiday.state == 'confirm':
                    holiday.with_context(short_name=False).activity_schedule(
                        'hr_holidays.mail_act_leave_approval',
                        note=note,
                        user_id=holiday.sudo()._get_responsible_for_approval().id or self.env.user.id)
                elif holiday.state == 'validate1':
                    holiday.activity_feedback(['hr_holidays.mail_act_leave_approval'])
                    holiday.with_context(short_name=False).activity_schedule(
                        'hr_holidays.mail_act_leave_second_approval',
                        note=note,
                        user_id=holiday.sudo()._get_responsible_for_approval().id or self.env.user.id)
                elif holiday.state == 'validate':
                    to_do |= holiday
                elif holiday.state == 'refuse':
                    to_clean |= holiday

            if to_clean:
                to_clean.activity_unlink(
                    ['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])
            if to_do:
                to_do.activity_feedback(
                    ['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(lembur.state not in ['draft', 'confirm', 'validate', 'validate1'] for lembur in self):
            raise UserError(_('Lembur request must be in draft, confirmed, or validated state to be refused.'))

        validated_lembur_requests = self.filtered(lambda lembur: lembur.state == 'validate1')
        validated_lembur_requests.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_lembur_requests).write({'state': 'refuse', 'second_approver_id': current_employee.id})

        # Deactivate related meetings if any
        self.mapped('meeting_id').write({'active': False})

        # If the lembur request is linked to others, refuse all linked requests
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()

        # Post a message to the employee notifying them of the refusal
        for lembur in self:
            if lembur.employee_id.user_id:
                lembur.message_post(
                    body=_('Your %(lembur_type)s planned on %(date)s has been refused',
                           lembur_type=lembur.dinas_status_id.display_name,
                           date=lembur.date_from),
                    partner_ids=lembur.employee_id.user_id.partner_id.ids)

        self.activity_update()
        return True

    @api.depends('holiday_status_id.leave_validation_type','lembur_status_id.leave_validation_type')
    def _compute_is_dynamic_approval_time_off(self):
        for rec in self:
            if (rec.holiday_status_id or rec.lembur_status_id) and (rec.holiday_status_id.leave_validation_type == 'dynamic_approval' or
                    rec.lembur_status_id.leave_validation_type == 'dynamic_approval'):
                rec.is_dynamic_approval_time_off = True
            else:
                rec.is_dynamic_approval_time_off = False

    def action_update_lembur_status_id(self):
        leave_type = self.env.ref('agp_hr_leave_lembur_ib.default_lembur_status_type_lembur', raise_if_not_found=False)
        if leave_type:
            self.env.cr.execute("""
                UPDATE hr_leave_lembur
                SET lembur_status_id = %s
                WHERE lembur_status_id IS NULL
            """, [leave_type.id])