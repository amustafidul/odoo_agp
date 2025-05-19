import json
import ast
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, AccessError

import re

import logging
_logger = logging.getLogger(__name__)


BLACKLISTED_MODELS = [
    'res.users',
    'res.partner',
    'res.company',
    'account.move',
    'account.payment',
    'account.bank.statement',
    'account.journal',
    'account.asset',
    'account.tax',
    'account.fiscal.position',
    'stock.picking',
    'stock.move',
    'stock.quant',
    'stock.location',
    'stock.inventory',
    'hr.employee',
    'hr.contract',
    'hr.payslip',
    'hr.payslip.run',
    'hr.expense',
    'project.project',
    'project.task',
    'sale.order',
    'purchase.order',
    'website',
    'website.page',
    'ir.cron',
    'ir.rule',
    'ir.model',
    'ir.model.access',
    'ir.model.fields',
    'mail.mail',
    'mail.message',
    'mail.template',
    'mail.activity',
    'base.automation',
    'base.import.mapping',
    'base.import.tests.models.o2m',
    'base.import.tests.models.char',
    'digest.digest',
    'utm.campaign',
    'utm.medium',
    'utm.source',
    'utm.stage',
]


class ApprovalWorkflow(models.Model):
    _name = 'approval.workflow'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Approval Workflow'
    _order = 'res_model asc'

    name = fields.Char(string='Workflow Name')
    res_model = fields.Many2one('ir.model', string='Model', ondelete='cascade', domain=[('model', 'not in', BLACKLISTED_MODELS)])
    line_ids = fields.One2many(comodel_name='approval.workflow.line', inverse_name='workflow_id', string='Approval Lines', auto_join=True)
    approval_type = fields.Selection([
        ('nominal', 'Rentang Nominal'),
        ('non_nominal', 'Non Nominal')
    ], string="Jenis Approval", required=True, default='non_nominal')
    workflow_type = fields.Selection([
        ('user', 'User'),
        ('jabatan', 'Jabatan'),
        ('ds', 'Direct Supervisor'),
        ('role', 'Role Group')
    ], string="Jenis Workflow", default='user')
    synced = fields.Boolean(string='Synced to Model', default=False)
    is_nominal = fields.Boolean('is Nominal?', compute='_compute_is_nominal')
    is_user = fields.Boolean(compute='_compute_workflow_type')
    is_jabatan = fields.Boolean(compute='_compute_workflow_type')
    is_ds = fields.Boolean(compute='_compute_workflow_type')
    is_role = fields.Boolean(compute='_compute_workflow_type')
    holiday_status_id = fields.Many2one('hr.leave.type', string="Time Off Type")
    is_hr_leave_model = fields.Boolean(compute='_compute_is_hr_leave_model')
    is_admin_override = fields.Boolean(string='Admin Override', default=False)
    is_superuser = fields.Boolean(string='Is Superuser', compute='_compute_is_superuser', store=False)
    user_id = fields.Many2one(
        'res.users',
        string='Current User',
        default=lambda self: self.env.user,
        readonly=True
    )
    original_state = fields.Text(string="Original State")

    @api.depends('user_id')
    def _compute_is_superuser(self):
        for record in self:
            record.is_superuser = self.env.user._is_admin

    @api.depends('res_model')
    def _compute_is_hr_leave_model(self):
        self.is_hr_leave_model = False
        for rec in self:
            rec.is_hr_leave_model = rec.res_model.model == 'hr.leave'

    @api.depends('line_ids.is_user','line_ids.is_jabatan','line_ids.is_ds','line_ids.is_role')
    def _compute_workflow_type(self):
        self.is_user = False
        self.is_jabatan = False
        self.is_ds = False
        self.is_role = False
        for line in self.line_ids:
            if line.is_user:
                self.is_user = True
            elif line.is_jabatan:
                self.is_jabatan = True
            elif line.is_ds:
                self.is_ds = True
            elif line.is_role:
                self.is_role = True

    @api.depends('approval_type')
    def _compute_is_nominal(self):
        for rec in self:
            if rec.approval_type == 'nominal':
                rec.is_nominal = True
            else:
                rec.is_nominal = False

    def _sync_to_model_new_rec_action(self):
        self = self.search([('synced', '=', True)])
        for rec in self:
            rec.remove_sync()
            rec.sync_to_model()

    def sync_to_model(self):
        for rec in self:
            if not rec.name:
                raise ValidationError(_("Field 'Workflow Name' tidak boleh kosong."))
            if not rec.res_model:
                raise ValidationError(_("Field 'Model' tidak boleh kosong."))
            if rec.res_model.model == 'hr.leave' and not rec.holiday_status_id:
                raise ValidationError(_("Field 'Time Off Type' tidak boleh kosong untuk model 'hr.leave'."))
            if not rec.line_ids:
                raise UserError(_("Approval Line masih kosong. Anda harus menambahkannya."))

            # Step 1: Get the target model object and model ID
            model_obj = self.env[rec.res_model.model].sudo()
            model_record = self.env['ir.model'].sudo().search([('model', '=', model_obj._name)], limit=1)
            if not model_record:
                raise ValueError(f"Model {model_obj._name} not found in ir.model")

            line_model_name = f'x_{model_obj._name.replace(".", "_")}_approval_line'
            line_model_description = f'{model_obj._description} Approval Line'

            # Step 2: Create the dynamic line model if it does not exist
            line_model_record = self.env['ir.model'].sudo().search([('model', '=', line_model_name)], limit=1)
            if not line_model_record:
                line_model_record = self.env['ir.model'].sudo().create({
                    'name': line_model_description,
                    'model': line_model_name
                })
                self._create_line_model_fields(line_model_record, model_obj, rec)

            # Step 3: Add One2many field to the target model if it doesn't exist
            if not self.env['ir.model.fields'].sudo().search(
                    [('model', '=', model_obj._name), ('name', '=', f'x_{line_model_name}_ids')], limit=1):
                self.env['ir.model.fields'].sudo().create({
                    'model_id': model_record.id,
                    'name': f'x_{line_model_name}_ids',
                    'field_description': f'{line_model_description}',
                    'ttype': 'one2many',
                    'relation': line_model_name,
                    'relation_field': f'x_{model_obj._name.replace(".", "_")}_id',
                    'state': 'manual',
                })

            # Step 4: Handle state field in the target model
            if hasattr(model_obj, 'state'):
                # If the state field is generated by a function
                if callable(model_obj._fields['state'].selection):
                    _logger.info(f"State field in model {model_obj._name} is generated by a function.")
                    original_function = model_obj._fields['state'].selection
                    original_selection = original_function(self.env[model_obj._name])
                    rec.original_state = json.dumps(original_selection)

                    def new_selection_function(self):
                        original_selection = original_function(self)
                        new_states = [
                            ('draft', 'Draft'),
                            ('on_review', 'On Review'),
                            ('approved', 'Approved'),
                            ('rejected', 'Rejected'),
                            ('ask_for_revision', 'Ask for Revision')
                        ]
                        return original_selection + [s for s in new_states if s[0] not in dict(original_selection)]

                    model_obj._fields['state'].selection = new_selection_function
                else:
                    # If the state field is a static selection, add new states if not present
                    original_state = model_obj._fields['state'].selection

                    new_states = [
                        ('draft', 'Draft'),
                        ('on_review', 'On Review'),
                        ('approved', 'Approved'),
                        ('rejected', 'Rejected'),
                        ('ask_for_revision', 'Ask for Revision')
                    ]
                    existing_states = dict(original_state)
                    missing_states = [s for s in new_states if s[0] not in existing_states]

                    if missing_states:
                        rec.original_state = json.dumps(original_state)
                        model_obj._fields['state'].selection += missing_states
                        field_record = self.env['ir.model.fields'].sudo().search([
                            ('name', '=', 'state'),
                            ('model', '=', model_obj._name)
                        ], limit=1)

                        if field_record:
                            self.env.cr.execute(f"""
                                DELETE FROM ir_model_fields_selection
                                WHERE id in %s
                            """, (tuple(field_record.selection_ids.ids),))
                            # Tambahkan state baru ke selection_ids
                            for idx, state in enumerate(model_obj._fields['state'].selection, start=1):
                                name_json = json.dumps({"en_US": state[1]})
                                self.env.cr.execute(f"""
                                            INSERT INTO ir_model_fields_selection (field_id, value, name, sequence)
                                            VALUES (%s, %s, %s::jsonb, %s)
                                        """, (
                                    field_record.id,
                                    state[0],
                                    name_json,
                                    idx
                                ))
            else:
                # Step 4.1: Add x_approval_status field to the target model if it doesn't exist
                if not self.env['ir.model.fields'].sudo().search(
                        [('model', '=', model_obj._name), ('name', '=', 'x_approval_status')], limit=1):
                    self.env['ir.model.fields'].sudo().create({
                        'model_id': model_record.id,
                        'name': 'x_approval_status',
                        'field_description': 'Approval Status',
                        'ttype': 'selection',
                        'selection': "[('draft', 'Draft'), ('on_review', 'On Review'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('ask_for_revision', 'Ask for Revision')]",
                        'state': 'manual',
                    })

            # Step 5: Sync the data from approval.workflow.line to the target model's new line model
            target_model_records = model_obj.sudo().search([])
            if target_model_records:
                self._sync_line_data(rec, target_model_records, line_model_name, model_obj)

            # Step 6: Add view customization for approval status if needed
            if not hasattr(model_obj, 'state'):
                self._add_approval_status_view(model_obj)

            # Step 7: Set synced to True
            rec.synced = True

            if hasattr(model_obj, f'x_{line_model_name}_ids'):
                x_model_approval_line_obj = self.env['ir.model'].search(
                    [('model', '=', f'x_{model_obj._name.replace(".", "_")}_approval_line')], limit=1)

                self.env['ir.model.access'].sudo().create({
                    'name': f'{model_obj._name} user access',
                    'model_id': x_model_approval_line_obj.id,
                    'group_id': self.env.ref('base.group_user').id,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': True,
                    'perm_unlink': True,
                })

        self.env['ir.model'].sudo().clear_caches()
        self.env['ir.ui.view'].sudo().clear_caches()
        self.env.registry.setup_models(self.env.cr)

    def _create_line_model_fields(self, line_model_record, model_obj, rec):
        """ Helper function to create fields for the dynamic line model """
        self.env['ir.model.fields'].sudo().create({
            'model_id': line_model_record.id,
            'name': f'x_{model_obj._name.replace(".", "_")}_id',
            'field_description': f'{model_obj._description} Reference',
            'ttype': 'many2one',
            'relation': model_obj._name,
            'state': 'manual',
        })
        self.env['ir.model.fields'].sudo().create({
            'model_id': line_model_record.id,
            'name': 'x_sequence',
            'field_description': 'Approval Sequence',
            'ttype': 'integer',
            'state': 'manual',
        })
        self.env['ir.model.fields'].sudo().create({
            'model_id': line_model_record.id,
            'name': 'x_approver_user_id',
            'field_description': 'Approver User',
            'ttype': 'many2one',
            'relation': 'res.users',
            'state': 'manual',
        })
        self.env['ir.model.fields'].sudo().create({
            'model_id': line_model_record.id,
            'name': 'x_approver_jabatan_id',
            'field_description': 'Approver Jabatan',
            'ttype': 'many2one',
            'relation': 'hr.employee.fungsi.penugasan',
            'state': 'manual',
        })
        self.env['ir.model.fields'].sudo().create({
            'model_id': line_model_record.id,
            'name': 'x_approver_ds_level',
            'field_description': 'DS Level Approver',
            'ttype': 'char',
            'state': 'manual',
        })
        self.env['ir.model.fields'].sudo().create({
            'model_id': line_model_record.id,
            'name': 'x_approver_role_id',
            'field_description': 'Approver Role',
            'ttype': 'many2one',
            'relation': 'res.groups',
            'state': 'manual',
        })
        if rec.approval_type == 'nominal':
            self.env['ir.model.fields'].sudo().create({
                'model_id': line_model_record.id,
                'name': 'x_min_nominal',
                'field_description': 'Minimum Nominal',
                'ttype': 'float',
                'state': 'manual',
            })
            self.env['ir.model.fields'].sudo().create({
                'model_id': line_model_record.id,
                'name': 'x_max_nominal',
                'field_description': 'Maximum Nominal',
                'ttype': 'float',
                'state': 'manual',
            })
        if rec.res_model.model == 'hr.leave':
            self.env['ir.model.fields'].sudo().create({
                'model_id': line_model_record.id,
                'name': 'x_holiday_status_id',
                'field_description': 'Time Off Type',
                'ttype': 'many2one',
                'relation': 'hr.leave.type',
                'state': 'manual',
            })

    def _sync_line_data(self, rec, target_model_records, line_model_name, model_obj):
        """ Helper function to sync line data from approval.workflow.line to the target model """
        for target_record in target_model_records:
            for line in rec.line_ids:
                line_data = {
                    'x_sequence': line.sequence,
                    'x_approver_user_id': line.user_id.id if line.workflow_type == 'user' else None,
                    'x_approver_jabatan_id': line.approver_jabatan_id.id if line.workflow_type == 'jabatan' else None,
                    'x_approver_ds_level': line.approver_ds_level if line.workflow_type == 'ds' else None,
                    'x_approver_role_id': line.approver_role_id.id if line.workflow_type == 'role' else None,
                    f'x_{model_obj._name.replace(".", "_")}_id': target_record.id
                }
                if rec.approval_type == 'nominal':
                    line_data['x_min_nominal'] = line.min_nominal
                    line_data['x_max_nominal'] = line.max_nominal
                if rec.res_model.model == 'hr.leave':
                    if target_record.holiday_status_id.id == rec.holiday_status_id.id:
                        line_data['x_holiday_status_id'] = rec.holiday_status_id.id
                        self.env[line_model_name].sudo().create(line_data)
                else:
                    self.env[line_model_name].sudo().create(line_data)

    def _add_approval_status_view(self, model_obj):
        """ Helper function to add or update approval status view in the target model """
        form_view = self.env['ir.ui.view'].sudo().search([
            ('model', '=', model_obj._name),
            ('type', '=', 'form')
        ], limit=1)
        if not form_view:
            raise UserError(_("Form view for the model %s not found." % model_obj._name))

        self.env.cr.execute("""
            UPDATE %s
            SET x_approval_status = 'draft'
        """ % (model_obj._table,))

        view_name = f"{model_obj._name}_approval_statusbar_form"
        view_arch = f"""
            <data>
                <xpath expr="//header" position="inside">
                    <field name="x_approval_status" widget="statusbar"
                           statusbar_visible="draft,on_review,approved,rejected,ask_for_revision"/>
                </xpath>
            </data>
        """

        self.env['ir.ui.view'].sudo().create({
            'name': view_name,
            'type': 'form',
            'model': model_obj._name,
            'inherit_id': form_view.id,
            'arch_base': view_arch,
        })

    def remove_sync(self):
        for rec in self:
            if not rec.synced:
                raise UserError(_("Workflow belum disinkronkan, tidak ada sinkronisasi yang dapat dihapus."))

            # Step 1: Get the target model object and model ID
            model_obj = self.env[rec.res_model.model].sudo()
            model_record = self.env['ir.model'].sudo().search([('model', '=', model_obj._name)], limit=1)

            if not model_record:
                raise ValueError(f"Model {model_obj._name} not found in ir.model")

            line_model_name = f'x_{model_obj._name.replace(".", "_")}_approval_line'

            # Step 2: Remove approval line records
            if rec.res_model.model == 'hr.leave' and rec.holiday_status_id:
                self.env.cr.execute(f"""
                    DELETE FROM {line_model_name}
                    WHERE x_holiday_status_id = %s
                """, (rec.holiday_status_id.id,))
            else:
                self.env.cr.execute(f"DELETE FROM {line_model_name}")

            # Step 3: Remove fields related to workflow engine
            fields_to_remove = [
                f'x_{line_model_name}_ids'
            ]

            for field_name in fields_to_remove:
                field_record = self.env['ir.model.fields'].sudo().search([
                    ('model', '=', model_obj._name),
                    ('name', '=', field_name)
                ], limit=1)
                if field_record:
                    field_record.unlink()

            models_to_remove = [
                line_model_name
            ]

            for model_name in models_to_remove:
                self.env['ir.model'].sudo().search([
                    ('model', '=', model_name)
                ]).unlink()

            # Step 4: Restore original state selection if applicable
            if hasattr(model_obj, 'state') and rec.original_state:
                if callable(model_obj._fields['state'].selection):
                    try:
                        original_function = model_obj._fields['state'].selection  # Get the original function
                        original_selection = original_function(model_obj)  # Call the function to get current selections

                        # Convert selections to list if needed
                        current_selection = list(original_selection)
                        current_selection = [list(item) if isinstance(item, tuple) else item for item in
                                             current_selection]

                        # Optionally, restore to `original_state_list` if required
                        if rec.original_state:
                            original_state_list = ast.literal_eval(rec.original_state.strip())
                            current_selection += [list(item) for item in original_state_list if
                                                  list(item) not in current_selection]

                        # Overwrite selection with the updated list
                        def new_selection_function(self):
                            return current_selection

                        model_obj._fields['state'].selection = new_selection_function
                    except Exception as e:
                        _logger.warning(
                            f"Failed to handle callable state selection for model {model_obj._name}: {str(e)}")
                else:
                    try:
                        original_state_list = ast.literal_eval(rec.original_state.strip())
                        current_selection = [list(item) if isinstance(item, tuple) else item for item in original_state_list]

                        field_record = self.env['ir.model.fields'].sudo().search([
                            ('name', '=', 'state'),
                            ('model', '=', model_obj._name)
                        ])

                        if field_record:
                            for field_rec in field_record:
                                self.env.cr.execute(f"""
                                                            DELETE FROM ir_model_fields_selection
                                                            WHERE id in %s
                                                        """, (tuple(field_rec.selection_ids.ids),))
                                # Tambahkan state baru ke selection_ids
                                for idx, state in enumerate(current_selection, start=1):
                                    name_json = json.dumps({"en_US": state[1]})
                                    self.env.cr.execute(f"""
                                                                        INSERT INTO ir_model_fields_selection (field_id, value, name, sequence)
                                                                        VALUES (%s, %s, %s::jsonb, %s)
                                                                    """, (
                                        field_rec.id,
                                        state[0],
                                        name_json,
                                        idx
                                    ))

                                self.env.registry.setup_models(self.env.cr)

                    except (SyntaxError, ValueError):
                        _logger.warning(f"Invalid format in original_state for model {model_obj._name}")

            # Step 5: Remove view customization for approval status if x_approval_status was used
            if not hasattr(model_obj, 'state'):
                view_name = f"{model_obj._name}_approval_statusbar_form"
                view_record = self.env['ir.ui.view'].search([('name', '=', view_name)], limit=1)
                if view_record:
                    view_record.unlink()

            # Step 6: Remove access rights for the dynamic approval line model
            x_model_approval_line_obj = self.env['ir.model'].search([('model', '=', line_model_name)], limit=1)
            ir_model_access = self.env['ir.model.access'].search([('model_id', '=', x_model_approval_line_obj.id)])
            if ir_model_access:
                ir_model_access.unlink()

            # Step 7: Clear cache related to the model and views
            self.env['ir.model'].sudo().clear_caches()
            self.env['ir.ui.view'].sudo().clear_caches()
            self.env.registry.setup_models(self.env.cr)

            # Step 8: Set synced to False to indicate the sync has been removed
            rec.sudo().synced = False

    @api.constrains('holiday_status_id', 'res_model')
    def _check_unique_holiday_status_id(self):
        for rec in self:
            if rec.res_model.model == 'hr.leave':
                existing_workflow = self.search([
                    ('id', '!=', rec.id),
                    ('res_model.model', '=', 'hr.leave'),
                    ('holiday_status_id', '=', rec.holiday_status_id.id)
                ], limit=1)

                if existing_workflow:
                    raise ValidationError(_(
                        "Tipe time off '%s' telah digunakan di workflow lain. Anda harus memilih yang berbeda." % rec.holiday_status_id.name
                    ))

    @api.model
    def create(self, vals):
        if vals.get('res_model'):
            model_name = self.env['ir.model'].browse(vals.get('res_model')).model

            if model_name == 'hr.leave':
                if not vals.get('holiday_status_id'):
                    raise ValidationError(_("You must provide a Time Off Type for 'hr.leave' workflows."))

                existing_workflow_with_holiday = self.search([
                    ('res_model', '=', vals.get('res_model')),
                    ('holiday_status_id', '=', vals.get('holiday_status_id')),
                    ('synced', '=', True)
                ], limit=1)

                if existing_workflow_with_holiday:
                    raise ValidationError(
                        _("Time off type '%s' has already been used in another workflow. Please choose a different one." %
                          self.env['hr.leave.type'].browse(vals.get('holiday_status_id')).name)
                    )

            else:
                existing_workflow = self.search([
                    ('res_model', '=', vals['res_model']),
                    ('synced', '=', True)
                ], limit=1)

                if existing_workflow:
                    raise UserError(
                        _("The model '%s' already has a synced approval workflow. You cannot create another one." % existing_workflow.res_model.model))

        return super(ApprovalWorkflow, self).create(vals)

    def write(self, vals):
        if vals.get('name') is not None and not vals.get('name'):
            raise ValidationError(_("Field 'Workflow Name' tidak boleh kosong."))
        if vals.get('res_model') is not None and not vals.get('res_model'):
            raise ValidationError(_("Field 'Model' tidak boleh kosong."))
        if vals.get('line_ids') is not None and not vals.get('line_ids'):
            raise UserError(_("Approval Line tidak boleh kosong."))

        if vals.get('res_model'):
            model_name = self.env['ir.model'].browse(vals.get('res_model')).model

            if model_name == 'hr.leave':
                for workflow in self:
                    if vals.get('holiday_status_id'):
                        existing_workflow_with_holiday = self.search([
                            ('res_model', '=', vals['res_model']),
                            ('holiday_status_id', '=', vals.get('holiday_status_id')),
                            ('synced', '=', True),
                            ('id', '!=', workflow.id)
                        ], limit=1)

                        if existing_workflow_with_holiday:
                            raise ValidationError(
                                _("Time off type '%s' has already been used in another workflow. Please choose a different one." %
                                  self.env['hr.leave.type'].browse(vals.get('holiday_status_id')).name)
                            )

            else:
                for workflow in self:
                    existing_workflow = self.search([
                        ('res_model', '=', vals['res_model']),
                        ('synced', '=', True),
                        ('id', '!=', workflow.id)
                    ], limit=1)

                    if existing_workflow:
                        raise UserError(
                            _("The model '%s' already has a synced approval workflow. You cannot create another one." % existing_workflow.res_model.model))

        return super(ApprovalWorkflow, self).write(vals)

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = False
        default['res_model'] = False
        default['holiday_status_id'] = False
        default['synced'] = False
        return super(ApprovalWorkflow, self).copy(default)


class ApprovalWorkflowInherit(models.Model):
    _inherit = 'approval.workflow'

    # remove sync section #
    def remove_sync(self):
        super().remove_sync()
        for rec in self:
            model_obj = self.env[rec.res_model.model].sudo()
            model_name = model_obj._name

            self._remove_functions_from_model(model_obj)

            form_views = self.env['ir.ui.view'].sudo()

            ir_ui_view = self.env['ir.ui.view'].search([('model', '=', model_name)])
            for view_type_check in ir_ui_view:
                if view_type_check.type == 'form':
                    arch, view = model_obj._get_view(view_id=None, view_type='form')
                    if not arch or not view:
                        continue
                    form_views |= view
                elif view_type_check.type == 'tree':
                    arch, view = model_obj._get_view(view_id=None, view_type='tree')
                    if not arch or not view:
                        continue
                    form_views |= view
            self._remove_buttons_from_view(model_obj, rec, form_views)

        self.clear_caches()
        self.env['ir.ui.view'].sudo().clear_caches()

        # Step 6: Reload the registry to ensure that all changes are recognized
        self.env.registry.setup_models(self.env.cr)

    def _remove_functions_from_model(self, model_obj):
        dynamic_functions = ['action_approve_dynamic_approval']
        model_class = type(model_obj)

        for func_name in dynamic_functions:
            if hasattr(model_class, func_name) and callable(getattr(model_class, func_name, None)):
                try:
                    _logger.info(f"Removing dynamic function '{func_name}' from model '{model_class._name}'.")
                    delattr(model_class, func_name)
                    _logger.info(f"Dynamic function '{func_name}' removed successfully.")
                except AttributeError as e:
                    _logger.warning(
                        f"Failed to remove function '{func_name}' from model '{model_class._name}': {str(e)}")
            else:
                _logger.warning(
                    f"Function '{func_name}' does not exist or is not callable in model '{model_class._name}'.")
                continue

    def _remove_buttons_from_view(self, model_obj, rec, form_views):
        model_name = model_obj._name

        if model_name == 'hr.leave':
            target_records = model_obj.sudo().search([('holiday_status_id', '=', rec.holiday_status_id.id)])
            if target_records:
                self.env['ir.ui.view'].sudo().search([
                    '|',
                    ('name', 'ilike', f"Add Approve Button to {model_name} View"),
                    ('name', 'ilike', f"Add Submit Button to {model_name} View")
                ]).unlink()
                for form_view in form_views:
                    self.env['ir.model.data'].search([('module','=',form_view._module)]).unlink()
        else:
            view = self.env['ir.ui.view'].sudo().search([
                '|',
                ('name', 'ilike', f"Add Approve Button to {model_name} View"),
                ('name', 'ilike', f"Add Submit Button to {model_name} View"),
            ])
            for view_obj in view:
                view_obj.unlink()
            for form_view in form_views:
                self.env['ir.model.data'].search([('module', '=', form_view._module)]).unlink()

    def write(self, vals):
        """
        Override write to monitor changes in approval lines and trigger remove_sync + sync_to_model.
        """
        res = super().write(vals)
        # List field changes in the approval lines to monitor
        sync_fields = ['user_id', 'approver_jabatan_id', 'approver_ds_level', 'approver_role_id', 'sequence']

        # Flag to determine whether sync_to_model is required
        needs_sync = False

        # Check if approval lines are updated
        if 'line_ids' in vals:
            for command in vals['line_ids']:
                operation = command[0]
                line_data = command[2] if len(command) > 2 and isinstance(command[2], dict) else {}

                # If updating or adding lines and relevant fields are changed
                if operation in [1, 4, 0] and any(field in line_data for field in sync_fields):
                    _logger.info("Detected changes in approval lines: %s", line_data)
                    needs_sync = True
                    break

                # If removing lines
                if operation in [2, 3]:  # unlink/delete operations
                    _logger.info("Approval line removed or unlinked.")
                    needs_sync = True
                    break

        if needs_sync:
            if self.synced:
                _logger.info("Removing existing sync before syncing to model.")
                self.remove_sync()
                _logger.info("Triggering sync_to_model due to changes in approval lines.")
                self.sync_to_model()

        return res


class ApprovalWorkflowLine(models.Model):
    _name = 'approval.workflow.line'
    _description = 'Approval Workflow Line'
    _order = 'sequence asc'

    name = fields.Char('Name')
    workflow_id = fields.Many2one(comodel_name='approval.workflow', string='Workflow', ondelete='cascade', index=True, required=True)
    sequence = fields.Integer(string='Sequence', required=True)
    workflow_type = fields.Selection([
        ('user', 'User'),
        ('jabatan', 'Jabatan'),
        ('ds', 'Direct Supervisor'),
        ('role', 'Role Group')
    ], string="Jenis Workflow")
    approver_user_id = fields.Many2one('res.users', string='Approver User')
    user_id = fields.Many2one('res.users', string='Approver User')
    approver_user_id_temp = fields.Many2one('res.users', string='Approver User (Temp)')
    approver_jabatan_id = fields.Many2one('hr.employee.fungsi.penugasan', string='Approver Jabatan')
    approver_ds_level = fields.Char(string='DS Level Approver')
    approver_role_id = fields.Many2one('res.groups', string='Approver Role')
    min_nominal = fields.Float(string='Nominal Minimum')
    max_nominal = fields.Float(string='Nominal Maksimum')
    x_approval_sequence = fields.Integer(string='Approval Sequence')
    x_approval_approver_id = fields.Many2one('res.users', string='Approver')
    is_nominal = fields.Boolean(string='Is Nominal Approval', compute='_compute_is_nominal')
    holiday_status_id = fields.Many2one('hr.leave.type', related='workflow_id.holiday_status_id', string="Time Off Type")

    def migrate_data_to_temp_field(self):
        records = self.env['approval.workflow.line'].search([])
        for record in records:
            record.write({
                'approver_user_id_temp': record.approver_user_id.id
            })

    def migrate_data_to_new_field(self):
        records = self.env['approval.workflow.line'].search([])
        for record in records:
            if record.approver_user_id_temp:
                user_obj = record.approver_user_id_temp
                user = self.env['res.users'].search([('id', '=', user_obj.id)], limit=1)
                if user:
                    record.write({
                        'user_id': user.id
                    })

    @api.constrains('sequence')
    def _check_sequence_positive(self):
        for record in self:
            if record.sequence <= 0:
                raise ValidationError(_('Sequence must be greater than 0.'))

    @api.constrains('approver_ds_level')
    def _check_approver_ds_level(self):
        for record in self:
            if record.approver_ds_level and not re.match(r'^\d+$', record.approver_ds_level):
                raise ValidationError(_("The DS Level Approver field can only contain numbers."))

    @api.onchange('workflow_id')
    def _onchange_workflow_type(self):
        if self.workflow_id.approval_type == 'nominal':
            self.min_nominal = 0
            self.max_nominal = 0
        else:
            self.min_nominal = False
            self.max_nominal = False

    @api.depends('workflow_id.is_nominal')
    def _compute_is_nominal(self):
        for line in self:
            line.is_nominal = line.workflow_id.is_nominal

    is_user = fields.Boolean(compute='_compute_workflow_type')
    is_jabatan = fields.Boolean(compute='_compute_workflow_type')
    is_ds = fields.Boolean(compute='_compute_workflow_type')
    is_role = fields.Boolean(compute='_compute_workflow_type')

    @api.depends('workflow_type')
    def _compute_workflow_type(self):
        for rec in self:
            rec.is_user = False
            rec.is_jabatan = False
            rec.is_ds = False
            rec.is_role = False
            if rec.workflow_type == 'user':
                rec.is_user = True
            elif rec.workflow_type == 'jabatan':
                rec.is_jabatan = True
            elif rec.workflow_type == 'ds':
                rec.is_ds = True
            elif rec.workflow_type == 'role':
                rec.is_role = True

    @api.onchange('sequence')
    def _onchange_sequence(self):
        if self.sequence in self.workflow_id.line_ids._origin.mapped('sequence'):
            raise UserError(_("The sequence must be unique per workflow!"))

    @api.model
    def create(self, vals):
        workflow_id = vals.get('workflow_id')
        sequence = vals.get('sequence')

        if workflow_id and sequence:
            existing_records = self.search([
                ('workflow_id', '=', workflow_id),
                ('sequence', '=', sequence)
            ])
            if existing_records:
                raise ValidationError(_('The sequence must be unique per workflow!'))

        return super(ApprovalWorkflowLine, self).create(vals)


class MailThreadInherit(models.AbstractModel):
    _inherit = 'mail.thread'

    def _get_mail_thread_data(self, request_list):
        res = {'hasWriteAccess': False, 'hasReadAccess': True}
        if not self:
            res['hasReadAccess'] = False
            return res
        res['canPostOnReadonly'] = self._mail_post_access == 'read'

        self.ensure_one()
        try:
            self.check_access_rights("write")
            self.check_access_rule("write")
            res['hasWriteAccess'] = True
        except AccessError:
            pass
        if 'activities' in request_list:
            res['activities'] = self.activity_ids.activity_format()
        if 'attachments' in request_list:
            res['attachments'] = self._get_mail_thread_data_attachments()._attachment_format()
            res['mainAttachment'] = {'id': self.message_main_attachment_id.id} if self.message_main_attachment_id else [('clear',)]
        return res