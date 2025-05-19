import mysql.connector
from mysql.connector import Error
from odoo import models, fields, api

class AMSGetNodinNumber(models.Model):
    _name = 'ams.sql.config'
    _description = 'SQL Configuration for AMS App Integration'

    # def _default_sequence(self):
    #     return self.env['ir.sequence'].next_by_code('ams.sql.config.sequence')

    name = fields.Char(string='No.', store=True)
    type = fields.Selection([
        ('direct_sql', 'Direct SQL'),
        ('api', 'API'),
    ], string='Tipe Tarikan Data')
    host = fields.Char(string='Host')
    port = fields.Integer(string='Port', default=3306)
    user = fields.Char(string='Auth User')
    password = fields.Char(string='Auth Password')
    url = fields.Char(string='URL')
    api_key = fields.Char(string='API Key')
    query_res = fields.Text(string='Query Result')
    query = fields.Text(string="SQL Query")
    database = fields.Char(string='DB Name')

    # @api.depends('type', 'sequence')
    # def _compute_name(self):
    #     for record in self:
    #         seq = str(record.sequence)
    #         if record.type == 'direct_sql':
    #             record.name = f"{seq:04d}/SQL"
    #         elif record.type == 'api':
    #             record.name = f"{seq:04d}/API"

    def test_connection(self):
        """ Test connection to remote MySQL server """
        self.ensure_one()  # Ensure method is called on a single record
        try:
            conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password
            )
            if conn.is_connected():
                conn.close()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': 'Connection to MySQL server successful!',
                        'type': 'success',
                        'sticky': False
                    }
                }
        except Error as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Failed',
                    'message': f'Error: {str(e)}',
                    'type': 'danger',
                    'sticky': True
                }
            }

    def execute_query(self):
        """ Execute a SQL query and store the result in query_res """
        self.ensure_one()
        if not self.query:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'No SQL query provided!',
                    'type': 'danger',
                    'sticky': True
                }
            }
        
        try:
            conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            if conn.is_connected():
                conn.autocommit = True  # Ensure auto-commit is enabled
                cursor = conn.cursor()
                cursor.execute(self.query)

                # Fetch results
                rows = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description] if cursor.description else []

                # Format output
                result_str = f"{column_names}\n"
                result_str += "\n".join([str(row) for row in rows])
                
                self.query_res = result_str  # Store result in Odoo field

                cursor.close()
                conn.close()

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Query Executed',
                        'message': 'Query executed successfully. Check the result field.',
                        'type': 'success',
                        'sticky': False
                    }
                }
        except Error as e:
            self.query_res = f"Error: {str(e)}"
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Query Execution Failed',
                    'message': f'Error: {str(e)}',
                    'type': 'danger',
                    'sticky': True
                }
            }
