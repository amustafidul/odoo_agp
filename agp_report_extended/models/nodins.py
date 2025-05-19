from odoo import models, fields, api, _
from datetime import datetime
from babel.dates import format_date

class NodinInheritReportODT(models.Model):
    _inherit = 'account.keuangan.nota.dinas.bod'

    def _get_current_time(self):
        now = datetime.now()
        
        id_month_names = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        return f"{now.day} {id_month_names[now.month]} {now.year}"

    def get_subtotals_per_branch(self):
        result = []
        if not self.monitored_kkhc_ids:
            return result

        branch_map = {}
        grand_total = 0

        for line in self.monitored_kkhc_ids:
            branch = line.branch_id.name or 'Tanpa Cabang'
            if branch not in branch_map:
                branch_map[branch] = {
                    'branch_name': branch,
                    'lines': [],
                    'subtotal': 0,
                }
            branch_map[branch]['lines'].append(line)
            branch_map[branch]['subtotal'] += line.nominal_final or 0

            grand_total += line.nominal_final or 0

        result = list(branch_map.values())

        result.append({
            'branch_name': 'Total Keseluruhan',
            'lines': [],
            'subtotal': grand_total,
        })

        return result

class NotaDinasInheritReportODT(models.Model):
    _inherit = 'account.keuangan.nota.dinas'

    total_nominal_cabang_terakhir = fields.Float(
        string='Total Nominal Cabang Terakhir',
        compute='_compute_last_branch_total',
        store=True
    )
    nama_cabang_terakhir = fields.Char(
        string='Nama Cabang Terakhir',
        compute='_compute_last_branch_total',
        store=True
    )

    @api.depends('monitored_kkhc_ids.nominal_final', 'monitored_kkhc_ids.branch_id')
    def _compute_last_branch_total(self):
        for rec in self:
            lines = rec.monitored_kkhc_ids.filtered(lambda l: l.active and l.branch_id)

            if not lines:
                rec.total_nominal_cabang_terakhir = 0.0
                rec.nama_cabang_terakhir = ''
                continue

            last_line = lines[-1]
            last_branch = last_line.branch_id
            last_branch_id = last_branch.id

            related_lines = lines.filtered(lambda l: l.branch_id.id == last_branch_id)

            rec.total_nominal_cabang_terakhir = sum(l.nominal_final for l in related_lines)
            rec.nama_cabang_terakhir = last_branch.name or ''

    def read(self, fields=None, load='_classic_read'):
        records = super(NotaDinasInheritReportODT, self).read(fields, load)

        if fields:
            self._compute_last_branch_total()

        return records

    def _get_current_time(self):
        now = datetime.now()
        
        id_month_names = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        return f"{now.day} {id_month_names[now.month]} {now.year}"

    def get_subtotals_per_branch(self):
        result = []
        if not self.monitored_kkhc_ids:
            return result

        branch_map = {}
        grand_total = 0

        for line in self.monitored_kkhc_ids:
            branch = line.branch_id.name or 'Tanpa Cabang'
            if branch not in branch_map:
                branch_map[branch] = {
                    'branch_name': branch,
                    'lines': [],
                    'subtotal': 0,
                }
            branch_map[branch]['lines'].append(line)
            branch_map[branch]['subtotal'] += line.nominal_final or 0

            grand_total += line.nominal_final or 0

        result = list(branch_map.values())

        result.append({
            'branch_name': 'Total Keseluruhan',
            'lines': [],
            'subtotal': grand_total,
        })

        return result
