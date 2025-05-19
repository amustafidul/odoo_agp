from odoo import http
from odoo.http import request
import base64


class PreviewXLSXController(http.Controller):

    @http.route(['/xlsx/preview/<int:attachment_id>'], type='http', auth='user')
    def preview_from_attachment(self, attachment_id, **kwargs):
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not attachment or not attachment.datas:
            return "<h3>File tidak ditemukan</h3>"

        file_data = base64.b64decode(attachment.datas)
        encoded_file = base64.b64encode(file_data).decode()

        return f"""
        <html>
        <head>
            <title>Preview Excel - {attachment.name}</title>
            <script src="https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js"></script>
            <style>
                body {{ font-family: sans-serif; }}
                #excel-preview table {{
                    border-collapse: collapse;
                    width: 100%;
                }}
                #excel-preview th, #excel-preview td {{
                    border: 1px solid #aaa;
                    padding: 4px;
                    text-align: left;
                }}
                #download-btn {{
                    margin-top: 10px;
                    display: inline-block;
                }}
            </style>
        </head>
        <body>
            <h2>Preview: {attachment.name}</h2>
            <div id="excel-preview">Loading...</div>
            <br>
            <a id="download-btn" href="/web/content/{attachment.id}?download=true" target="_blank">⬇️ Unduh File XLSX</a>

            <script>
                const base64 = "{encoded_file}";
                const data = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
                const workbook = XLSX.read(data, {{type: "array"}});
                const sheetName = workbook.SheetNames[0];
                const sheet = workbook.Sheets[sheetName];
                const html = XLSX.utils.sheet_to_html(sheet, {{ editable: false }});
                document.getElementById("excel-preview").innerHTML = html;
            </script>
        </body>
        </html>
        """