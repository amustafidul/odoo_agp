/** @odoo-module **/

import ListController from 'web.ListController';
import rpc from 'web.rpc';
import viewRegistry from 'web.view_registry';
import ListView from 'web.ListView';

const CustomListController = ListController.extend({
    willStart: async function () {

        await this._super.apply(this, arguments);
        try {
            const result = await rpc.query({
                model: 'res.users',
                method: 'search_read',
                args: [[['id', '=', this.getSession().uid]]],
                kwargs: {
                    fields: ['level', 'groups_id']
                }
            });

            if (result && result.length > 0) {
                const groupResult = await rpc.query({
                    model: 'res.groups',
                    method: 'search_count',
                    args: [[
                        ['id', 'in', result[0].groups_id],
                        ['name', '=', 'Board of Director of Adhiguna Putera']
                    ]]
                });

                if (result[0].level === 'bod' && groupResult > 0) {
                    this.isBOD = true;
                }
            }
        } catch (error) {
            console.error('ORM error:', error);
        }
    },

    renderButtons: function () {
        this._super.apply(this, arguments);
        
        if (this.isBOD) {
            if (this.$buttons) {
                this.$buttons.find('.o_list_button_add').hide();
            }
        }

        if (this.user && this.user.level === 'usaha') {
            if (this.$buttons) {
                this.$buttons.find('.o_list_button_add').remove();
                this.$buttons.find('.o_button_import').remove();
            }
        }
    },

    _onDeleteRecord: function () {
        if (this.user && this.user.level === 'usaha') {
            this.do_notify('Access Denied', 'You are not allowed to delete records.');
            return;
        }
        this._super.apply(this, arguments);
    },
});

const CustomListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: CustomListController,
    }),
});

viewRegistry.add('custom_list_view', CustomListView);