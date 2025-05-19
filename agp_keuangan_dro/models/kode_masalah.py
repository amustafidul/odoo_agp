from odoo import models, fields, api
import mysql.connector
import logging

_logger = logging.getLogger(__name__)

class KodeMasalahMaster(models.Model):
    _name = 'agp.kode.masalah'

    kode_masalah = fields.Char(string='Kode', required=True, index=True, unique=True)
    uraian = fields.Char(string='Uraian')

    @api.model
    def init(self):
        # Fetch database configuration from ams.sql.config
        sql_config = self.env['ams.sql.config'].search([
            ('type', '=', 'direct_sql'),
            ('name', 'ilike', 'AGP')
        ], limit=1)

        if not sql_config:
            _logger.error("No SQL configuration found for AGP Odoo x AMS. Skipping data import.")
            return

        config = {
            'host': sql_config.host,
            'port': sql_config.port,
            'user': sql_config.user,
            'password': sql_config.password,
            'database': sql_config.database,
        }
        print(config)

        try:
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor(dictionary=True)

            # Fetch data from the remote MySQL database
            cursor.execute("SELECT kode_masalah, uraian FROM m_masalah WHERE kode_masalah LIKE '2%'")
            masalah_records = cursor.fetchall()

            for record in masalah_records:
                kode_masalah = record['kode_masalah']
                uraian = record['uraian']

                # Check if the record already exists in Odoo
                existing_record = self.env['agp.kode.masalah'].search([('kode_masalah', '=', kode_masalah)], limit=1)
                
                if not existing_record:
                    # Create the record only if it does not exist
                    self.create({
                        'kode_masalah': kode_masalah,
                        'uraian': uraian,
                    })

            cursor.close()
            conn.close()

        except mysql.connector.Error as err:
            _logger.error(f"Error connecting to MySQL: {err}")
