# -*- coding:utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, time
from pytz import timezone
from dateutil.relativedelta import relativedelta


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    from odoo import models, fields, api

    class HrPayslip(models.Model):
        _inherit = 'hr.payslip'

        x_lembur_hours = fields.Float("Total Lembur (Jam)", compute='_compute_lembur_hours', store=True)

        @api.depends('employee_id', 'date_from', 'date_to')
        def _compute_lembur_hours(self):
            for slip in self:
                total_lembur = 0.0
                lembur_records = slip.env['hr.leave.lembur'].search([
                    ('employee_id', '=', slip.employee_id.id),
                    ('state', '=', 'validate'),
                    ('date_from', '>=', slip.date_from),
                    ('date_to', '<=', slip.date_to),
                ])
                for lembur in lembur_records:
                    s = lembur.duration_waktu_lembur or ''
                    jam = 0
                    menit = 0
                    idx_hour = s.find('hour')
                    idx_minute = s.find('minute')
                    if idx_hour != -1:
                        jam_str = s[:idx_hour].strip().replace(',', '')
                        jam = int(jam_str) if jam_str.isdigit() else 0
                    if idx_minute != -1:
                        if idx_hour != -1:
                            menit_str = s[idx_hour + 4:idx_minute].replace(',', '').strip()
                            menit = int(menit_str) if menit_str.isdigit() else 0
                        else:
                            menit_str = s[:idx_minute].replace(',', '').strip()
                            menit = int(menit_str) if menit_str.isdigit() else 0
                    total_lembur += jam + (menit / 60.0)
                slip.x_lembur_hours = total_lembur

    def compute_sheet(self):
        for payslip in self:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')

            payslip.line_ids.unlink()

            contract_ids = payslip.contract_id.ids or self.get_contract(
                payslip.employee_id, payslip.date_from, payslip.date_to
            )
            contracts = self.env['hr.contract'].browse(contract_ids)

            wage_total = 0.0

            for contract in contracts:
                calendar = contract.resource_calendar_id
                if calendar:
                    tz = timezone(calendar.tz or 'UTC')

                    start_date = max(contract.date_start, payslip.date_from)
                    end_date = min(contract.date_end or payslip.date_to, payslip.date_to)

                    work_data = contract.employee_id.get_work_days_data(
                        datetime.combine(start_date, time.min).replace(tzinfo=tz),
                        datetime.combine(end_date, time.max).replace(tzinfo=tz),
                        compute_leaves=True,
                        calendar=calendar
                    )
                    work_days = work_data['days']  # Hari kerja efektif

                    total_month_days = contract.employee_id.get_work_days_data(
                        datetime.combine(start_date.replace(day=1), time.min).replace(tzinfo=tz),
                        datetime.combine(end_date.replace(day=28 if end_date.month == 2 else 30), time.max).replace(
                            tzinfo=tz),
                        compute_leaves=True,
                        calendar=calendar
                    )['days']

                    decrypted_wage = contract._decrypt_wage()
                    daily_wage = decrypted_wage / total_month_days if total_month_days else 0
                    wage_total += daily_wage * work_days

                contract.prorata_wage = wage_total

            payslip_lines = self._get_payslip_lines(contract_ids, payslip.id)

            for line in payslip_lines:
                if line['code'] == 'BASIC':
                    line['amount'] = wage_total

            payslip.write({'line_ids': [(0, 0, line) for line in payslip_lines], 'number': number})

        return True

    def is_prorated(self):
        self.ensure_one()
        contract = self.contract_id
        employee = self.employee_id

        if not contract:
            return False, None

        # Join tengah bulan
        if contract.date_start and contract.date_start > self.date_from:
            return True, contract.date_start

        # Resign tengah bulan
        if contract.date_end and contract.date_end < self.date_to:
            return True, contract.date_end

        # Perubahan Branch (yang tidak tercatat di histori)
        if contract.dearness_id and hasattr(contract.dearness_id, 'hr_branch_id'):
            if employee.hr_branch_id and contract.dearness_id.hr_branch_id and employee.hr_branch_id.id != contract.dearness_id.hr_branch_id.id:
                return True, self.date_from + relativedelta(days=15)

        # Cek histori jabatan (grade/branch) selama periode payslip
        histories = self.env['hr.employee.histori.jabatan'].search([
            ('employee_id', '=', employee.id),
            ('tmt_date', '>', self.date_from),
            ('tmt_date', '<=', self.date_to),
        ], order='tmt_date ASC')

        if histories:
            return True, histories[0].tmt_date

        return False, None