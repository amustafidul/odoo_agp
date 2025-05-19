#
#   file: /models/helpers.py
#   author: Andromeda (github.com/ademoord)
#   desc: A co-routine file to help developers summarizing computed queries in single file only
#

def _get_qry_init_vendor_bills():
    return """
        DROP VIEW IF EXISTS wika_vendor_bills_report;

        CREATE OR REPLACE VIEW wika_vendor_bills_report AS (
            SELECT MIN(pc.id) AS id,
                pc.branch_id,
                pc.biro AS biro,
                pc.date AS invoice_date,
                pcl.partner_id,
                'opex'::character varying AS tipe_budget,
                false AS is_beban,
                pcl.account_id,
                SUM(ABS(pcl.amount)) AS price_subtotal,
                'Petty Cash'::text AS form,
                pcl.petty_id AS id_trx,
                pc.nomor_budget,
                pcl.product_id,
                    CASE
                        WHEN branch.parent_id IS NOT NULL THEN branch.parent_id
                        ELSE branch.id
                    END AS parent_id
            FROM wika_petty_cash_line pcl
                LEFT JOIN wika_petty_cash pc ON pc.id = pcl.petty_id
                LEFT JOIN res_branch branch ON pc.branch_id = branch.id
                LEFT JOIN res_branch branch2 ON pc.biro = branch2.id
                LEFT JOIN res_partner partner ON pcl.partner_id = partner.id
                LEFT JOIN account_account coa ON pcl.account_id = coa.id
            WHERE pc.is_petty_cash = True
            GROUP BY pc.branch_id, pcl.petty_id, pc.biro, pc.date, pcl.partner_id, pcl.account_id, pc.nomor_budget, pcl.product_id, branch.id, branch.parent_id
        );
"""