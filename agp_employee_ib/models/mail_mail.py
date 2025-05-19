from odoo import models, fields, api, SUPERUSER_ID

import logging

_logger = logging.getLogger(__name__)


class MailCronJob(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def process_email_queue_ib(self):
        _logger.info("Start sending email queue (max 300 emails, batched 50)...")

        ir_cron_mail_scheduler_action = self.env['ir.cron'].search([
            ('name', '=', 'Mail: Email Queue Manager'),
            ('active', '=', True)
        ], limit=1)
        if ir_cron_mail_scheduler_action:
            ir_cron_mail_scheduler_action.write({'active': False})

        batch_size = 50
        max_process = 300
        processed = 0
        offset = 0

        while processed < max_process:
            limit = min(batch_size, max_process - processed)
            emails = self.search([('state', '=', 'outgoing')], limit=limit, offset=offset)
            if not emails:
                break

            for email in emails:
                try:
                    email.send()
                except Exception as e:
                    _logger.exception("Error sending email: %s", e)

            offset += limit
            processed += len(emails)

        _logger.info(f"Finished sending emails (total processed: {processed})")