/** @odoo-module **/

import { ActionMenus } from "@web/search/action_menus/action_menus";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

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

patch(ActionMenus.prototype, "agp_report_extended_invoice_print_action_patch", {
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
            this._fetchKegiatanInvoice(recordId);
        } else {
            console.log("⚠️ No record ID found in the URL!");
        }

        return printActions.map((action) => ({
            action,
            description: action.name,
            key: action.id,
        }));
    },

    async _fetchKegiatanInvoice(recordId) {
        const recordModel = getModelFromUrl();
        if (recordModel === 'account.keuangan.invoice') {
            try {
                const [record] = await this.orm.read("account.keuangan.invoice", [recordId], ["jenis_kegiatan_name"]);

                if (record) {
                    console.log('Record data:', record);
                    await new Promise(resolve => setTimeout(resolve, 100));
                    
                    const printItems = document.querySelectorAll('.o-dropdown--menu .dropdown-item.o_menu_item');
                    console.log('Print items found:', printItems);
                    
                    printItems.forEach((item) => {
                        const itemText = item.innerText.trim();
                        console.log('Checking item:', itemText);
                        
                        if (record.jenis_kegiatan_name === 'Jetty Manajemen') {
                            if (!["Invoice Jetty Manajemen PDF", "Proforma", "Kwitansi PDF"].includes(itemText)) {
                                item.style.display = "none";
                            }
                        }
                        if (record.jenis_kegiatan_name === 'EMKL') {
                            if (!["Invoice Emkl PDF", "Proforma", "Kwitansi PDF"].includes(itemText)) {
                                item.style.display = "none";
                            }
                        }
                        if (record.jenis_kegiatan_name === 'Assist Tug') {
                            if (!["Invoice Lumpsum PDF", "Invoice GRT PDF", "Invoice MT PDF", "Proforma", "Kwitansi PDF"].includes(itemText)) {
                                item.style.display = "none";
                            }
                        }
                        if (record.jenis_kegiatan_name === 'Bongkar Muat') {
                            if (!["Invoice Bongkar Muat Darat PDF", "Invoice Bongkar Muat Laut PDF", "Proforma", "Kwitansi PDF"].includes(itemText)) {
                                item.style.display = "none";
                            }
                        }
                        if (record.jenis_kegiatan_name === 'Logistik') {
                            if (!["Invoice Logistik PDF", "Proforma", "Kwitansi PDF"].includes(itemText)) {
                                item.style.display = "none";
                            }
                        }
                        if (record.jenis_kegiatan_name === 'Keagenan') {
                            if (!["Invoice Keagenan PDF", "Proforma", "Kwitansi PDF"].includes(itemText)) {
                                item.style.display = "none";
                            }
                        }
                        if (record.jenis_kegiatan_name === 'Kegiatan Lainnya') {
                            if (!["Invoice Lainnya PDF", "Proforma", "Kwitansi PDF"].includes(itemText)) {
                                item.style.display = "none";
                            }
                        }
                        if (record.jenis_kegiatan_name === 'Dredging') {
                            if (!["Invoice Dredging PDF", "Proforma", "Kwitansi PDF"].includes(itemText)) {
                                item.style.display = "none";
                            }
                        }

                    });
                }
            } catch (error) {
                console.error("Error while processing print items:", error);
            }

        } else if (recordModel === 'account.keuangan.nota.dinas') {
            try {
                const [record] = await this.orm.read("account.keuangan.nota.dinas", [recordId], ["tipe_nodin"]);
        
                if (record) {
                    console.log('Record data:', record);
                    await new Promise(resolve => setTimeout(resolve, 100));
                    
                    const printItems = document.querySelectorAll('.o-dropdown--menu .dropdown-item.o_menu_item');
                    console.log('Print items found:', printItems);
                    
                    printItems.forEach((item) => {
                        const itemText = item.innerText.trim();
                        console.log('Checking item:', itemText);
                        
                        if (record.tipe_nodin === 'business') {
                            if (itemText === "Nota Dinas - Umum (Full Approved)") {
                                item.style.display = "none";
                            }
                            if (itemText === "Nota Dinas - Umum (With Rejected)") {
                                item.style.display = "none";
                            }
                        }
                        if (record.tipe_nodin === 'common') {
                            if (itemText === "Nota Dinas - Usaha (Full Approved)") {
                                item.style.display = "none";
                            }
                            if (itemText === "Nota Dinas - Usaha (With Rejected)") {
                                item.style.display = "none";
                            }
                        }
    
                    });
                }
            } catch (error) {
                console.error("Error while processing print items:", error);
            }
        }
}});
