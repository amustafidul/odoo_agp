

odoo.define('agp_keuangan_ib.kkhc_line_visibility', function (require) {
    'use strict';

    const ListRenderer = require('web.ListRenderer');
    const ajax = require('web.ajax');

    console.log('KKHC Line Visibility Loaded');
    console.log("Starting _renderView and preparing RPC...");

    async function fetchUserLevel(uid, req_type) {
        try {
            const response = await fetch('/api/anggaran/user_level', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    uid: uid,
                    req_type: req_type,
                }),
            });

            if (!response.ok) {
                console.error(`HTTP error! status: ${response.status}`);
                const errorText = await response.text();
                console.error("Server response:", errorText);
                return;
            }

            const data = await response.json();
            console.log('User level response:', data);
            console.dir(data);
            return data;
        } catch (error) {
            console.error('Error fetching user level:', error);
        }
    }

    async function processUserLevel() {
        try {
            const userLevelData = await fetchUserLevel(53, 'finance_budgetting');
            if (userLevelData) {
                // Handle the response here (e.g., adjust visibility based on user level)
                // Access data from userLevelData, for example:
                // console.log(userLevelData.data.level);
                
                // Select all <tr> elements inside the tbody with class 'ui-sortable'
                // const rows = document.querySelectorAll('.ui-sortable tr');
                debugger;
                // const tbl = document.querySelectorAll('[name="rkap_line_ids"] .o_field_x2many .o_list_renderer table tr');
                const tbl = document.querySelectorAll('.o_field_widget .o_field_x2many .o_list_renderer table tr');
                console.log('Alhamdulillah', tbl);

                // Ambil div berdasarkan name
                const divElement = document.querySelector('div[name="rkap_line_ids"]');

                // Cari tabel di dalam div
                const table = divElement.querySelector('table');

                // Ambil semua elemen <tr> di dalam tabel
                const rows = table.querySelectorAll('tr');

                // Tampilkan hasil
                rows.forEach((row, index) => {
                    console.log('Alhamdulillah')
                });

                // const rows = document.querySelectorAll('.ui-sortable tr');


                tbl.forEach(function (item) {
                    var tr = item.closest('tr');
                    if (tr) {
                        console.log('>>> TR:', tr);
                    }


                }); 

                

                // console.log('ROWSSSS', rows.length);
                // debugger;

                for (let i = 0; i < rows.length; i++) {
                const cells = rows[i].querySelectorAll('td'); // Get all <td> elements in the current row

                for (let j = 0; j < cells.length; j++) {
                    const cell = cells[j];
                    if (cell.getAttribute('name') === 'kode_anggaran_id') {
                    console.log(cell.textContent.trim()); // Log the text value of the <td>
                    }
                }
                }


            }
        } catch (error) {
            // Error already handled in fetchUserLevel
        }
    }
    
    $(function () {
        processUserLevel(); // Call the async function to start the process

    });

});

