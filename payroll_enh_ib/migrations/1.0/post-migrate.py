from odoo import api, SUPERUSER_ID
from cryptography.fernet import Fernet
import logging

_logger = logging.getLogger(__name__)


def migrate_existing_wage(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    param = env['ir.config_parameter'].sudo().get_param('hr_contract.fernet_key')
    if not param:
        _logger.error("FERNET key not found in system parameters during migration!")
        raise ValueError("FERNET key missing (key: hr_contract.fernet_key). Please set it before migration.")

    cipher = Fernet(param.encode())

    contracts = env['hr.contract'].search([
        ('wage', '!=', False),
        ('wage_encrypted', '=', False)
    ])

    _logger.info(f"Found {len(contracts)} contracts to migrate.")

    for contract in contracts:
        try:
            encrypted_wage = cipher.encrypt(str(contract.wage).encode()).decode()
            contract.write({
                'wage_encrypted': encrypted_wage,
                'wage': 0  # penting: kosongin wage supaya tidak bocor
            })
            _logger.info(f"Migrated contract ID {contract.id}: wage encrypted.")
        except Exception as e:
            _logger.error(f"Failed to migrate contract ID {contract.id}: {e}")