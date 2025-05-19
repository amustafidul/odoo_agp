from odoo import models, fields, api


class InvoiceReport(models.AbstractModel):
    _name = 'report.agp_report_py3o.invoice_grt'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Mengambil invoice yang dilaporkan
        docs = self.env['account.keuangan.invoice'].browse(docids)
        
        # Mengambil data perusahaan yang terkait dengan invoice (company_id)
        company = docs[0].company_id  # Mengambil company_id dari invoice pertama (docs[0])

        # Mendapatkan logo dan informasi lainnya
        company_logo = company.logo  # Logo perusahaan (binary)
        company_name = company.name  # Nama perusahaan
        company_address = company.street  # Alamat perusahaan
        company_phone = company.phone  # Nomor telepon perusahaan

        return {
            'docs': docs,
            'company_logo': company_logo,
            'company_name': company_name,
            'company_address': company_address,
            'company_phone': company_phone,
        }
