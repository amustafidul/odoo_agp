from odoo import models, fields, api, _


class BulkUploadAttachmentWizard(models.TransientModel):
    _name = 'hr.employee.bulk.upload.attachment.wizard'
    _description = 'Wizard for Bulk Uploading Attachment File'

    attachment_filetype = fields.Selection([
        ('ijazah', 'Ijazah'),
        ('kk', 'KK'),
        ('ktp', 'KTP'),
        ('sertifikat', 'Sertifikat'),
        ('npwp', 'NPWP'),
        ('kis', 'KIS'),
        ('foto', 'Foto'),
    ], string='Filetype', default='ijazah')
    attachment_ids = fields.Many2many('ir.attachment', string="Upload Files")

    def action_bulk_upload(self):
        attachment_ids = self.attachment_ids
        employees = self.env['hr.employee'].search([])

        for employee in employees:
            if self.attachment_filetype == 'ijazah':
                employee.bulk_upload_ijazah(attachment_ids)
            elif self.attachment_filetype == 'kk':
                employee.bulk_upload_kk(attachment_ids)
            elif self.attachment_filetype == 'ktp':
                employee.bulk_upload_ktp(attachment_ids)
            elif self.attachment_filetype == 'sertifikat':
                employee.bulk_upload_sertifikat(attachment_ids)
            elif self.attachment_filetype == 'npwp':
                employee.bulk_upload_npwp(attachment_ids)
            elif self.attachment_filetype == 'kis':
                employee.bulk_upload_kis(attachment_ids)
            elif self.attachment_filetype == 'foto':
                employee.bulk_upload_foto(attachment_ids)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'{self.attachment_filetype} attachments uploaded successfully.',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }