odoo.define('agp_report_extended.buttonAccountKeuanganRkapKonsolidasi', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    // var rpc = require('web.rpc');

    var TreeButton = ListController.extend({
        buttons_template: 'agp_report_extended.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .open_account_keuangan_rkap_konsolidasi_action': '_OpenAccountKeuanganRkapKonsolidasi',
        }),
        // _OpenAccountKeuanganRkapKonsolidasi: function () {
        //     var self = this;
            
        //     console.log('OK');
            
        //     debugger;
        //     // Using RPC call to get the base URL
        //     // rpc.query({
        //     //     model: 'ir.config_parameter',
        //     //     method: 'get_param',
        //     //     args: ['web.base.url']
        //     // }).then(function (base_url) {
        //     //     // Using template literal for URL formation
        //     //     var redirect_url = `${base_url}/pivot-stock-import`;
        //     //     self.do_action({
        //     //         type: 'ir.actions.act_url',
        //     //         url: redirect_url,
        //     //         target: 'self'
        //     //     });
        //     // });
        // }

        _OpenAccountKeuanganRkapKonsolidasi: function () {
            var self = this;
            
            
            this.do_action({
                type: 'ir.actions.report',
                report_name: 'agp_report_extended.report_rkap_konsolidasi',  // Replace with your actual report name
                report_type: 'qweb-pdf',
                model: 'account.keuangan.rkap.konsolidasi',
                context: { active_ids: self.getSelectedIds() }  // Use selected records if applicable
            });

            console.log('OK __ WALHAMDULILLAH');
            // debugger;
        }
        

    });

    var AccountKeuanganRkapKonsolidasiListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: TreeButton,
        }),
    });

    viewRegistry.add('button_account_keuangan_rkap_konsolidasi_list', AccountKeuanganRkapKonsolidasiListView);
});