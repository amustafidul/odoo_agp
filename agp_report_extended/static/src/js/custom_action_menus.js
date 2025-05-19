/** @odoo-module **/

import { ActionMenus } from "@web/search/action_menus/action_menus";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

console.log("New JS Loaded!");

function getRecordIdFromUrl() {
    const hash = window.location.hash;
    const match = hash.match(/id=(\d+)/);
    return match ? parseInt(match[1]) : null;
}

function getModelFromUrl() {
    const hash = window.location.hash;
    const match = hash.match(/model=([^&]+)/);
    return match ? match[1] : null;
}

patch(ActionMenus.prototype, "agp_report_extended_nodin_print_action_patch", {
    setup() {
        this._super.apply(this, arguments);
        this.orm = useService("orm");
    },

    get printItems() {
        const printActions = this.props.items.print || [];
        if (printActions.length === 0) {
            return [];
        }

        const recordId = getRecordIdFromUrl();

        if (recordId) {
            debugger;
            this._fetchTipeNodin(recordId);
        } else {
            console.log("⚠️ No record ID found in the URL!");
        }

        return printActions.map((action) => ({
            action,
            description: action.name,
            key: action.id,
        }));
    },

    async _fetchTipeNodin(recordId) {
        const recordModel = getModelFromUrl();
        // if (recordModel === 'account.keuangan.nota.dinas' || recordModel === 'account.keuangan.nota.dinas.bod') {
        // if (recordModel === 'account.keuangan.nota.dinas') {
        //     try {
        //         const [record] = await this.orm.read("account.keuangan.nota.dinas", [recordId], ["tipe_nodin"]);
        
        //         if (record) {
        //             console.log('Record data:', record);
        //             await new Promise(resolve => setTimeout(resolve, 100));
                    
        //             const printItems = document.querySelectorAll('.o-dropdown--menu .dropdown-item.o_menu_item');
        //             console.log('Print items found:', printItems);
                    
        //             printItems.forEach((item) => {
        //                 const itemText = item.innerText.trim();
        //                 console.log('Checking item:', itemText);
                        
        //                 console.log('record.tipe_nodin', record.tipe_nodin);
        //                 console.log('record.tipe_nodin', record.tipe_nodin);
        //                 console.log('record.tipe_nodin', record.tipe_nodin);
        //                 if (record.tipe_nodin === 'business') {
        //                     if (itemText === "Nota Dinas - Umum (Full Approved)") {
        //                         item.style.display = "none";
        //                     }
        //                     if (itemText === "Nota Dinas - Umum (With Rejected)") {
        //                         item.style.display = "none";
        //                     }
        //                 }
        //                 if (record.tipe_nodin === 'common') {
        //                     if (itemText === "Nota Dinas - Usaha (Full Approved)") {
        //                         item.style.display = "none";
        //                     }
        //                     if (itemText === "Nota Dinas - Usaha (With Rejected)") {
        //                         item.style.display = "none";
        //                     }
        //                 }
    
        //             });
        //         }
        //     } catch (error) {
        //         console.error("Error while processing print items:", error);
        //     }
        // }
    }
});
