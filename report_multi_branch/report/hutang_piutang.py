# -*- coding: utf-8 -*-

from odoo import api, models, _


class ReportHutangPiutang(models.AbstractModel):
    _name = 'report.report_multi_branch.report_hutang_piutang'
    _description = 'Kartu Hutang/Piutang'


    @api.model
    def _get_report_values(self, docids, data=None):
        # active_model = self.env.context.get('active_model')
        # docs = self.env[active_model].browse(self.env.context.get('active_id'))
        # vals = {
        #     'docs': docs,
        #     'periode': data['periode'],
        #     'jenis_kartu': data['form']['jenis_kartu'],
        #     'partner_ids': data['form']['partner_ids'],
        #     'jenis_kegiatan': dict([
        #                         ('emkl', 'EMKL'),
        #                         ('bongkar_muat', 'Bongkar Muat'),
        #                         ('keagenan', 'Keagenan'),
        #                         ('assist_tug', 'Assist Tug'),
        #                         ('jetty_manajemen', 'Jetty Manajemen'),
        #                         ('jasa_operasi_lainnya', 'Jasa Operasi Lainnya'),
        #                         ('logistik', 'Logistik')
        #                     ]).get(data['form']['jenis_kegiatan'], '').upper()
        # }
        # return vals
        # active_model = self.env.context.get('active_model')
        # docs = self.env[active_model].browse(self.env.context.get('active_id'))
        # docs = self.env[active_model].browse(docids)
        
        # Extract and format data for the report
        # jenis_kartu = data['form']['jenis_kartu']
        # partner_ids = self.env['res.partner'].browse(data['form']['partner_ids'])
        # jenis_kegiatan = dict([
        #     ('emkl', 'EMKL'),
        #     ('bongkar_muat', 'Bongkar Muat'),
        #     ('keagenan', 'Keagenan'),
        #     ('assist_tug', 'Assist Tug'),
        #     ('jetty_manajemen', 'Jetty Manajemen'),
        #     ('jasa_operasi_lainnya', 'Jasa Operasi Lainnya'),
        #     ('logistik', 'Logistik')
        # ]).get(data['form']['jenis_kegiatan'], '').upper()

        # vals = {
        #     'docs': docs,
        #     'periode': data['periode'],
        #     'jenis_kartu': jenis_kartu,
        #     'partner_ids': partner_ids,
        #     'jenis_kegiatan': jenis_kegiatan,
        # }
        # return vals
    
        active_model = self.env.context.get('active_model')
        docs = self.env[active_model].browse(self.env.context.get('active_id'))
        jenis_kartu = data['jenis_kartu']
        periode = data['periode']
        lines = data['lines']
        vals = {
            'docs': docs,
            'jenis_kartu': jenis_kartu,
            'periode': periode,
            'lines': lines,
        }
        return vals