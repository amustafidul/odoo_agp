from odoo import models, fields, api
from datetime import datetime, timedelta
import logging
import random

_logger = logging.getLogger(__name__)


class TrainingCourse(models.Model):
    _name = 'training.course'
    _description = 'Training Needs Analysis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string="Nama Diklat/ Workshop/ Sertifikasi", required=True, tracking=True, index="trigram")
    lingkup_diklat = fields.Char(string="Lingkup Diklat", tracking=True, index="trigram")
    participant_id = fields.Many2one('res.partner', string="Nama Peserta", domain=[('is_company', '=', False)])
    participant_ids = fields.Many2many('res.partner', string="Nama Peserta", domain=[('is_company', '=', False)])
    employee_ids = fields.Many2many('hr.employee', string="Nama Peserta")
    branch_id = fields.Many2one(
        'res.branch',
        string="Cabang",
        required=True,
        domain="[('company_id', 'child_of', company_id)]"
    )
    training_date_from = fields.Date(string="Waktu Pelaksanaan Dari", tracking=True)
    training_date_to = fields.Date(string="Waktu Pelaksanaan Sampai", tracking=True)
    duration = fields.Char(string="Durasi", compute='_compute_duration', store=True)
    cost = fields.Monetary(string="Biaya", currency_field='currency_id')
    organizer = fields.Char(string="Penyelenggara")
    status = fields.Selection([
        ('draft', 'Draft'),
        ('on_review', 'On Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string="Status", default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    training_date_range = fields.Char(string="Waktu Pelaksanaan", compute='_compute_training_date_range', store=True)
    description = fields.Text()

    training_year = fields.Char(
        string="Tahun Pelaksanaan",
        compute='_compute_training_year',
        store=True
    )

    evaluation_count = fields.Integer(
        string="Evaluation Count",
        compute='_compute_evaluation_count'
    )

    def _compute_evaluation_count(self):
        for record in self:
            record.evaluation_count = self.env['training.evaluation'].search_count([('course_id', '=', record.id)])

    @api.depends('training_date_from')
    def _compute_training_year(self):
        for record in self:
            if record.training_date_from:
                record.training_year = record.training_date_from.strftime('%Y')
            else:
                record.training_year = False

    @api.depends('training_date_from', 'training_date_to')
    def _compute_training_date_range(self):
        for record in self:
            if record.training_date_from and record.training_date_to:
                record.training_date_range = f"{record.training_date_from.strftime('%d %B %Y')} - {record.training_date_to.strftime('%d %B %Y')}"
            else:
                record.training_date_range = ""

    @api.depends('training_date_from', 'training_date_to')
    def _compute_duration(self):
        for record in self:
            if record.training_date_from and record.training_date_to:
                duration_days = (record.training_date_to - record.training_date_from).days + 1
                record.duration = f"{duration_days} Hari"
            else:
                record.duration = "0 Hari"

    @api.model
    def create_training_evaluation(self):
        tiga_bulan_lalu = fields.Date.context_today(self) - timedelta(days=90)
        courses = self.search([('training_date_to', '<=', tiga_bulan_lalu)])
        for course in courses:
            for employee in course.employee_ids:
                existing_evaluation = self.env['training.evaluation'].search([
                    ('employee_id', '=', employee.id),
                    ('course_id', '=', course.id)
                ], limit=1)
                if not existing_evaluation:
                    default_indicators = [
                        {'indicator': 'Penerapan ilmu yang didapat dari training berdampak pada kinerja karyawan',
                         'score': False},
                        {'indicator': 'Pengaruh training terhadap sikap kerja karyawan sehari-hari', 'score': False},
                        {'indicator': 'Inisiatif karyawan dalam membagikan ilmu training ke rekan kerja',
                         'score': False},
                        {'indicator': 'Manfaat training terhadap kemajuan perusahaan', 'score': False},
                    ]

                    self.env['training.evaluation'].create({
                        'employee_id': employee.id,
                        'training_date_from': course.training_date_from,
                        'training_date_to': course.training_date_to,
                        'training_organizer': course.organizer,
                        'course_id': course.id,
                        'status': 'draft',
                        'evaluation_line_ids': [(0, 0, line) for line in default_indicators],
                    })

    def action_view_evaluations(self):
        evaluations = self.env['training.evaluation'].search([('course_id', '=', self.id)])
        evaluation_count = len(evaluations)

        if evaluation_count == 1:
            return {
                'name': 'Evaluation',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'training.evaluation',
                'res_id': evaluations.id,
                'target': 'current',
            }
        else:
            return {
                'name': 'Evaluations',
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'training.evaluation',
                'domain': [('course_id', '=', self.id)],
                'context': {'default_course_id': self.id},
                'target': 'current',
            }

    def action_submit(self):
        for rec in self:
            rec.status = 'approved'

    def action_set_to_draft(self):
        for rec in self:
            rec.status = 'draft'

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        result = super(TrainingCourse, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                        orderby=orderby, lazy=lazy)
        current_year = datetime.now().year
        next_year = str(current_year + 1)
        year_exists = any(group.get('training_year') == next_year for group in result)
        if not year_exists:
            dummy_group = {
                'training_year': next_year,
                '__domain': [('training_year', '=', next_year)],
                '__count': 0,
            }
            result.append(dummy_group)
        return result

    def action_generate_sample_data(self):
        """
        Generate sample data
        """
        _logger.info("Starting sample data generation for training.course...")

        partner_ids = self.env['res.partner'].search([], limit=100).ids
        employee_ids = self.env['hr.employee'].search([], limit=100).ids
        branch_ids = self.env['res.branch'].search([], limit=10).ids

        if not partner_ids or not employee_ids or not branch_ids:
            raise ValueError("Missing required reference data: partners, employees, or branches.")

        # Generate sample data
        courses = []
        for i in range(5000):
            random_year = random.randint(2018, 2025)

            random_month = random.randint(1, 12)
            random_day = random.randint(1, 28)

            random_date_from = datetime(random_year, random_month, random_day)
            random_date_to = random_date_from + timedelta(days=random.randint(1, 5))

            courses.append({
                'name': f"Training Course {i + 1}",
                'lingkup_diklat': f"Lingkup {random.randint(1, 10)}",
                'participant_ids': [(6, 0, random.sample(partner_ids, random.randint(1, 5)))],
                'employee_ids': [(6, 0, random.sample(employee_ids, random.randint(1, 5)))],
                'branch_id': random.choice(branch_ids),
                'training_date_from': random_date_from.date(),
                'training_date_to': random_date_to.date(),
                'cost': random.randint(1000000, 10000000),
                'organizer': f"Penyelenggara {random.randint(1, 20)}",
                'status': random.choice(['draft', 'on_review', 'approved', 'rejected']),
            })

        self.create(courses)
        _logger.info("Sample data generation completed.")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Data Sample Created',
                'message': '5000 training courses have been successfully created!',
                'sticky': False,
            }
        }