from odoo import models, fields, api, _
from odoo.exceptions import AccessError, MissingError, ValidationError, UserError
from datetime import date, datetime, timedelta
from odoo import api, SUPERUSER_ID
import random

import logging
import cProfile
import pstats

_logger = logging.getLogger(__name__)


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    is_cuti = fields.Boolean()

    @api.constrains('date_from', 'date_to', 'calendar_id')
    def _check_compare_dates(self):
        all_existing_leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', 'in', self.company_id.ids),
            ('date_from', '<=', max(self.mapped('date_to'))),
            ('date_to', '>=', min(self.mapped('date_from'))),
        ])
        for record in self:
            if not record.resource_id:
                existing_leaves = all_existing_leaves.filtered(lambda leave:
                                                               record.id != leave.id
                                                               and record['company_id'] == leave['company_id']
                                                               and record['date_from'] <= leave['date_to']
                                                               and record['date_to'] >= leave['date_from'])
                if record.calendar_id:
                    existing_leaves = existing_leaves.filtered(
                        lambda l: not l.calendar_id or l.calendar_id == record.calendar_id)
                if existing_leaves:
                    pass


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    original_state = fields.Char('Original Status')
    delegation_id = fields.Many2one('hr.employee', string='Delegation', domain=lambda self: self._get_delegation_domain())
    is_sick_time_off = fields.Boolean(compute='_compute_is_sick_paid_spd_time_off')
    is_paid_time_off = fields.Boolean(compute='_compute_is_sick_paid_spd_time_off')
    is_spd_time_off = fields.Boolean(compute='_compute_is_sick_paid_spd_time_off')
    pemberi_perintah_perjalanan = fields.Many2one('hr.employee', string="Pemberi Perintah Perjalanan")
    maksud_perjalanan_dinas = fields.Text("Maksud Perjalanan Dinas")
    hr_leave_transport_id = fields.Many2many('hr.leave.spd.transport', string="Transport By")
    departure_from = fields.Char('Tempat Berangkat')
    destination_place = fields.Char('Tujuan Dinas')
    paid_time_off_type_id = fields.Many2one('hr.leave.paid.timeoff.type', string="Jenis Cuti")
    rejection_reason = fields.Text(string="Rejection Reason", readonly=True)
    ask_for_revision_reason = fields.Text(string="Reason", readonly=True)

    is_hr_leave_model = fields.Boolean(
        string="Is HR Leave Model",
        compute='_compute_is_hr_leave_model',
        store=False
    )

    def _compute_is_hr_leave_model(self):
        for record in self:
            record.is_hr_leave_model = record._name == 'hr.leave'

    def _get_all_managers(self, employee):
        """
        Fungsi rekursif untuk mengambil semua manajer current employee logged-in, dari level saat ini hingga ke atas (terakhir).
        Misalnya, current logged-in adalah Ibad, maka ini akan mengambil semua manager di atasnya ibad yg masih berada dalam 1 line.
        E.g. Ibad:
        1. Dola
        2. Lola
        3. Faris
        4. Izhar
        ..................
        """
        managers = set()
        while employee and employee.parent_id and employee.parent_id.id not in managers:
            managers.add(employee.parent_id.id)
            employee = employee.parent_id
        return list(managers)

    @api.model
    def _get_delegation_domain(self):
        current_user_employee = self.env.user.employee_id

        if not current_user_employee:
            return [('id', '=', False)]

        eligible_employee_ids = self._get_all_managers(current_user_employee)
        return [('id', 'in', eligible_employee_ids)]

    def set_to_draft(self):
        self.state = 'draft'

    @api.depends('holiday_status_id.name')
    def _compute_is_sick_paid_spd_time_off(self):
        status_mapping = {
            'Sick Time Off': 'is_sick_time_off',
            'Paid Time Off': 'is_paid_time_off',
            'SPPD': 'is_spd_time_off'
        }

        for rec in self:
            rec.is_sick_time_off = False
            rec.is_paid_time_off = False
            rec.is_spd_time_off = False

            field_name = status_mapping.get(rec.holiday_status_id.name)
            if field_name:
                setattr(rec, field_name, True)

    is_dynamic_approval_time_off = fields.Boolean(compute='_compute_is_dynamic_approval_time_off')

    @api.depends('holiday_status_id.leave_validation_type')
    def _compute_is_dynamic_approval_time_off(self):
        for rec in self:
            if rec.holiday_status_id and rec.holiday_status_id.leave_validation_type == 'dynamic_approval':
                rec.is_dynamic_approval_time_off = True
            else:
                rec.is_dynamic_approval_time_off = False

    def action_submit_dyamic_approval_timeoff(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        self.env.cr.execute("""
            UPDATE hr_leave SET state = %s WHERE id IN %s;
        """, ('on_review', tuple(self.ids)))

        approval_lines = self.env['x_hr_leave_approval_line'].search([
            ('x_hr_leave_id', 'in', self.ids)
        ])

        approval_lines_by_leave = {}
        for line in approval_lines:
            key = (line.x_hr_leave_id.id, line.x_holiday_status_id.id)
            approval_lines_by_leave.setdefault(key, [])
            approval_lines_by_leave[key].append(line)

        for rec in self:
            if not hasattr(rec, 'x_x_hr_leave_approval_line_ids'):
                raise UserError(_("Dynamic approval configuration not found!"))

            key = (rec.id, rec.holiday_status_id.id)
            lines = approval_lines_by_leave.get(key, [])
            line_approval = lines[0] if lines else None

            if not line_approval:
                raise ValidationError("Tidak ada line approval yang tersedia.")

            approver_emails = []
            approver_names = []
            record_url = f"{base_url}/web#id={rec.id}&model=hr.leave&view_type=form"

            if line_approval.x_approver_user_id:
                user = line_approval.x_approver_user_id
                if user.employee_id and user.employee_id.work_email:
                    approver_emails.append(user.employee_id.work_email)
                    approver_names.append(user.employee_id.name)

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
                    if user.partner_id and user.partner_id.email:
                        approver_emails.append(user.partner_id.email)
                        approver_names.append(user.partner_id.name)

            approver_emails = list(filter(lambda x: isinstance(x, str) and x, approver_emails))

            if approver_emails:
                mail_values = {
                    'subject': _('Approval Needed for Leaves Request'),
                    'email_to': ",".join(approver_emails),
                    'body_html': _(
                        "<p>Dear Approvers,</p>"
                        "<p>A new leave request from %(employee_name)s requires your approval.</p>"
                        "<p>Leave Details:</p>"
                        "<ul>"
                        "<li><strong>Employee:</strong> %(employee_name)s</li>"
                        "<li><strong>Leave Type:</strong> %(leave_type)s</li>"
                        "<li><strong>Date From:</strong> %(date_from)s</li>"
                        "<li><strong>Date To:</strong> %(date_to)s</li>"
                        "</ul>"
                        "<p>Please review the request in the system and take the necessary action.</p>"
                        "<p><a href='%(record_url)s'>Click here to view the leave request</a></p>"
                    ) % {
                                     'employee_name': rec.employee_id.name,
                                     'leave_type': rec.holiday_status_id.name,
                                     'date_from': rec.date_from,
                                     'date_to': rec.date_to,
                                     'record_url': record_url,
                                 },
                }
                self.env['mail.mail'].sudo().create(mail_values)
            else:
                raise ValidationError("Tidak ada line approval yang tersedia.")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pesan Terkirim'),
                'message': _('Pesan telah berhasil dikirim.'),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_validate(self):
        if self._name != 'hr.leave':
            return True

        current_employee = self.env.user.employee_id
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            raise ValidationError(
                _('The following employees are not supposed to work during that period:\n %s') % ','.join(
                    leaves.mapped('employee_id.name')))

        if any(holiday.state not in ['confirm', 'validate1'] and holiday.validation_type != 'no_validation' for holiday
               in self):
            raise UserError(_('Leave request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})

        leaves_second_approver = self.env['hr.leave']
        leaves_first_approver = self.env['hr.leave']

        for leave in self:
            if leave.validation_type == 'both':
                leaves_second_approver += leave
            else:
                leaves_first_approver += leave

            if leave.holiday_type != 'employee' or (leave.holiday_type == 'employee' and len(leave.employee_ids) > 1):
                employees = leave._get_employees_from_holiday_type()

                conflicting_leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True
                ).search([
                    ('date_from', '<=', leave.date_to),
                    ('date_to', '>', leave.date_from),
                    ('state', 'not in', ['cancel', 'refuse']),
                    ('holiday_type', '=', 'employee'),
                    ('employee_id', 'in', employees.ids)
                ])

                if conflicting_leaves:
                    if leave.leave_type_request_unit != 'day' or any(
                            l.leave_type_request_unit == 'hour' for l in conflicting_leaves):
                        raise ValidationError(_('You cannot have two leaves that overlap on the same day.'))

                    target_states = {l.id: l.state for l in conflicting_leaves}
                    conflicting_leaves.action_refuse()

                    split_leaves_vals = []
                    for conflicting_leave in conflicting_leaves:
                        if conflicting_leave.leave_type_request_unit == 'half_day' and conflicting_leave.request_unit_half:
                            continue

                        if conflicting_leave.date_from < leave.date_from:
                            before_leave_vals = conflicting_leave.copy_data({
                                'date_from': conflicting_leave.date_from.date(),
                                'date_to': leave.date_from.date() - timedelta(days=1),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            before_leave = self.env['hr.leave'].new(before_leave_vals)
                            before_leave._compute_date_from_to()
                            if before_leave.date_from < before_leave.date_to:
                                split_leaves_vals.append(before_leave._convert_to_write(before_leave._cache))

                        if conflicting_leave.date_to > leave.date_to:
                            after_leave_vals = conflicting_leave.copy_data({
                                'date_from': leave.date_to.date() + timedelta(days=1),
                                'date_to': conflicting_leave.date_to.date(),
                                'state': target_states[conflicting_leave.id],
                            })[0]
                            after_leave = self.env['hr.leave'].new(after_leave_vals)
                            after_leave._compute_date_from_to()
                            if after_leave.date_from < after_leave.date_to:
                                split_leaves_vals.append(after_leave._convert_to_write(after_leave._cache))

                    split_leaves = self.env['hr.leave'].with_context(
                        tracking_disable=True,
                        mail_activity_automation_skip=True,
                        leave_fast_create=True,
                        leave_skip_state_check=True
                    ).create(split_leaves_vals)

                    split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

                values = leave._prepare_employees_holiday_values(employees)
                leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True,
                    no_calendar_sync=True,
                    leave_skip_state_check=True,
                    leave_compute_date_from_to=True,
                ).create(values)

                leaves._validate_leave_request()

        leaves_second_approver.write({'second_approver_id': current_employee.id})
        leaves_first_approver.write({'first_approver_id': current_employee.id})

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True

    @api.model
    def create(self, vals):
        if self._name == 'hr.leave':

            # cek jika sick_time_off true, lakukan pengecekan
            # apakah ada cuti sakit pada hari sebelumnya
            # jika ada, cek berapa hari

            holiday_status_id = self.env['hr.leave.type'].browse(vals.get('holiday_status_id'))
            employee_id = vals.get('employee_id')

            if holiday_status_id.sick_time_off:
                today = date.today()
                start_of_year = date(today.year, 1, 1)

                sick_leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee_id),
                    ('holiday_status_id.sick_time_off', '=', True),
                    ('state', '=', 'validate'),
                    ('request_date_from', '>=', start_of_year)
                ])

                total_sick_days = sum(sick_leave.number_of_days for sick_leave in sick_leaves)

                if total_sick_days > 1:
                    raise ValidationError(_(
                        "Anda mengajukan Cuti Sakit lebih dari 1 hari. "
                        "Diwajibkan upload Surat Dokter."
                    ))

                if total_sick_days > 7:
                    raise ValidationError(_(
                        "Anda mengajukan Cuti Sakit lebih dari 7 hari. "
                        "Diwajibkan upload Surat Dokter dan Rekam Medis / Hasil Lab."
                    ))

            res = super(HrLeave, self).create(vals)
            for rec in res:
                if rec.holiday_status_id and rec.holiday_status_id.leave_validation_type == 'dynamic_approval':
                    rec.state = 'draft'

                    approval_workflow_obj = self.env['approval.workflow'].search([
                        ('synced', '=', True),
                        ('holiday_status_id', '=', rec.holiday_status_id.id)
                    ], limit=1)

                    if approval_workflow_obj:
                        approval_workflow = approval_workflow_obj[0]
                        model_obj = self.env[f'{approval_workflow.res_model.model}'].sudo()

                        # Pastikan bahwa model target memiliki field approval line
                        field_approval_line_ids = f'x_x_{model_obj._name.replace(".", "_")}_approval_line_ids'
                        if hasattr(model_obj, field_approval_line_ids):
                            line_model_name = f'x_{model_obj._name.replace(".", "_")}_approval_line'

                            # Cari record dalam target model yang belum memiliki approval lines
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
                                            f'x_{model_obj._name.replace(".", "_")}_id': target_record.id,
                                            'x_holiday_status_id': approval_workflow.holiday_status_id.id
                                        }

                                        # Tambahkan rentang nominal jika ada
                                        if approval_workflow.approval_type == 'nominal':
                                            line_data['x_min_nominal'] = line.min_nominal
                                            line_data['x_max_nominal'] = line.max_nominal

                                        line_data_list.append(line_data)

                                if line_data_list:
                                    self.env[line_model_name].sudo().create(line_data_list)

                    else:
                        raise ValidationError(_(
                            "Approval workflow for holiday status '%s' is not set. "
                            "Please check the approval workflow settings, "
                            "or select a holiday type with a leave validation type other than dynamic approval."
                        ) % rec.holiday_status_id.name)

            return res
        else:
            return super().create(vals)

    def action_approve_dynamic_approval(self):
        if self._name == 'hr.leave':
            current_user = self.env.user
            current_employee = self.env['hr.employee'].search([('user_id', '=', current_user.id)], limit=1)

            if not current_employee:
                raise ValidationError("Employee terkait user ini tidak ditemukan.")

            if self.state == 'validate':
                raise ValidationError("Pengajuan ini sudah tervalidasi.")

            current_date = fields.Date.context_today(self)

            # Not approved line
            line_not_approve = self.env['x_hr_leave_approval_line'].search([
                ('x_name', '!=', 'approved'),
                ('x_hr_leave_id', '=', self.id),
                ('x_holiday_status_id', '=', self.holiday_status_id.id)
            ])

            # Cache untuk approver efektif
            approver_cache = {}

            def get_effective_approver(employee):
                if employee.id in approver_cache:
                    return approver_cache[employee.id]

                checked_employees = set()
                while employee and employee not in checked_employees:
                    checked_employees.add(employee)
                    leave = self.env['hr.leave'].search([
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

                    # Approval Type
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
                        next_approvals = self.x_x_hr_leave_approval_line_ids.filtered(
                            lambda l: l.x_name != "approved").sorted('x_sequence')
                        if next_approvals:
                            self._send_email_to_approvers(next_approvals[0], next_approvals)

                        if all(line.x_name == "approved" for line in self.x_x_hr_leave_approval_line_ids):
                            self.write({'state': 'validate'})
                            self._send_final_approval_email()

                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': _("Approval Successful"),
                                'message': _('You have successfully approved this leave request.'),
                                'type': 'success',
                                'sticky': False,
                                'next': {'type': 'ir.actions.client', 'tag': 'reload'}
                            }
                        }
                    else:
                        raise ValidationError("Anda bukan approver yang sesuai untuk level persetujuan ini.")

            raise ValidationError("Tidak ada line approval yang tersedia.")

    def _send_email_to_approvers(self, approver_lines, approval_record):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        record_url = f"{base_url}/web#id={self.id}&model=hr.leave&view_type=form"
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
                    'subject': _('Approval Required for Leave Request'),
                    'email_to': email,
                    'body_html': _(
                        "<p>Dear Approver,</p>"
                        "<p>A leave request from %(employee_name)s requires your approval.</p>"
                        "<p><a href='%(record_url)s'>Click here to review and approve the leave request</a>.</p>"
                    ) % {
                                     'employee_name': self.employee_id.name,
                                     'record_url': record_url,
                                 },
                })

            self.env['mail.mail'].sudo().create(mail_values_list)

    def _send_final_approval_email(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        record_url = f"{base_url}/web#id={self.id}&model=hr.leave&view_type=form"

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
                'subject': _('Your Leave Request Has Been Approved'),
                'email_to': employee_email,
                'body_html': _(
                    "<p>Dear %(employee_name)s,</p>"
                    "<p>Your leave request has been approved.</p>"
                    "<p><a href='%(record_url)s'>Click here to view your leave request</a>.</p>"
                ) % {
                                 'employee_name': self.employee_id.name,
                                 'record_url': record_url,
                             },
            })

        if hr_manager_emails:
            mail_values_list.append({
                'subject': _('Leave Request Approved Notification'),
                'email_to': ",".join(hr_manager_emails),
                'body_html': _(
                    "<p>Dear HR Manager,</p>"
                    "<p>A leave request from %(employee_name)s has been fully approved.</p>"
                    "<p><a href='%(record_url)s'>Click here to view the leave request</a>.</p>"
                ) % {
                                 'employee_name': self.employee_id.name,
                                 'record_url': record_url,
                             },
            })

        if mail_values_list:
            self.env['mail.mail'].sudo().create(mail_values_list)

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['draft', 'confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Leave request must be in draft, confirmed, or validated state to be refused.'))

        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})

        # Deactivate related meetings if any
        self.mapped('meeting_id').write({'active': False})

        # If the time off request is linked to others, refuse all linked requests
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()

        # Post a message to the employee notifying them of the refusal
        for holiday in self:
            if holiday.employee_id.user_id:
                holiday.message_post(
                    body=_('Your %(leave_type)s planned on %(date)s has been refused',
                           leave_type=holiday.holiday_status_id.display_name,
                           date=holiday.date_from),
                    partner_ids=holiday.employee_id.user_id.partner_id.ids)

        self.activity_update()
        return True

    is_visible_to_current_user = fields.Boolean(
        string="Visible to Current User",
        compute="_compute_is_visible_to_current_user"
    )

    def _compute_is_visible_to_current_user(self):
        current_user = self.env.user
        current_employee = current_user.employee_id

        for record in self:
            approval_lines = getattr(record, 'x_x_hr_leave_approval_line_ids', False)
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

    def _check_ds_level_approver(self, line, current_employee):
        """Check if the current employee meets the `x_approver_ds_level`."""
        manager = self.employee_id
        for _ in range(int(line.x_approver_ds_level)):
            manager = manager.parent_id if manager else None
        return manager == current_employee

    def _search_panel_domain_image(self, field_name, domain, set_count=False, limit=False):
        try:
            return super(HrLeave, self)._search_panel_domain_image(field_name, domain, set_count, limit)
        except KeyError as e:
            raise ValidationError(
                _("Gagal memuat data karena referensi '%s' tidak valid. "
                  "Silakan hubungi administrator untuk memperbaiki data.") % str(e)
            )
        except Exception as e:
            raise ValidationError(_("Terjadi kesalahan saat memuat data: %s") % str(e))

    def create_sample_leave_data(self):
        """
        Create sample records for hr.leave with non-overlapping dates for each employee.
        Ensures no overlapping dates and respects allocation limits for leave types that require allocation.
        """
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = datetime.now()
        _logger.info("Starting sample leave data creation process")

        try:
            # Get all leave types (hr.leave.type)
            leave_types = self.env['hr.leave.type'].search([])
            if not leave_types:
                raise ValidationError(_("No leave types found in the system. Please add leave types first."))

            _logger.info(f"Found {len(leave_types)} leave types")

            # Get 100 random employees with managers
            all_employees = self.env['hr.employee'].search([('parent_id', '!=', False)])
            employees = random.sample(all_employees, min(100, len(all_employees)))
            if not employees:
                raise ValidationError(_("No employees with managers found in the system. Please add employees first."))

            _logger.info(f"Found {len(employees)} employees with managers")

            # Dictionary to track existing leaves by employee
            employee_leave_tracker = {employee.id: [] for employee in employees}

            # Prepare for batch creation
            leave_records = []
            batch_size = 150

            leave_types_obj = self.env['hr.leave.type']

            for i in range(1000):
                leave_type = leave_types[i % len(leave_types)]
                leave_types_obj |= leave_type
                employee = random.choice(employees)

                if leave_type.requires_allocation == 'yes':
                    allocation = self.env['hr.leave.allocation'].search([
                        ('holiday_status_id', '=', leave_type.id),
                        ('employee_id', '=', employee.id),
                        ('state', '=', 'validate'),
                    ], limit=1)

                    if not allocation or allocation.leaves_taken == allocation.max_leaves:
                        continue

                start_date = datetime(2024, 1, 1) + timedelta(days=(i * 10) % 365)
                end_date = start_date + timedelta(days=random.randint(1, 10))

                overlaps = any(
                    (start_date <= existing['date_to'] and end_date >= existing['date_from'])
                    for existing in employee_leave_tracker[employee.id]
                )

                if overlaps:
                    continue

                employee_leave_tracker[employee.id].append({
                    'date_from': start_date,
                    'date_to': end_date
                })

                leave_record = {
                    'name': f'{leave_type.name}: {employee.name}',
                    'employee_id': employee.id,
                    'delegation_id': employee.parent_id.id if employee.parent_id else False,
                    'holiday_status_id': leave_type.id,
                    'date_from': start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'date_to': end_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'request_date_from': start_date.strftime('%Y-%m-%d'),
                    'request_date_to': end_date.strftime('%Y-%m-%d'),
                    'state': 'draft',
                }
                leave_records.append(leave_record)

                if len(leave_records) >= batch_size:
                    self.env['hr.leave'].create(leave_records)
                    _logger.info(f"Created {len(leave_records)} leave records")
                    leave_records = []

            if leave_records:
                self.env['hr.leave'].create(leave_records)
                _logger.info(f"Created remaining {len(leave_records)} leave records")

            self._cr.commit()

            _logger.info(
                f"Sample leave data creation completed in {(datetime.now() - start_time).total_seconds()} seconds")
        finally:
            profiler.disable()
            stats = pstats.Stats(profiler).sort_stats('time')
            stats.dump_stats('/tmp/create_sample_leave_data.prof')
            _logger.info("Profile data written to /tmp/create_sample_leave_data.prof")

        return _("Successfully created sample leave records.")