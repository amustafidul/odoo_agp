/** @odoo-module **/

import { TagsList } from "@web/views/fields/many2many_tags/tags_list";
import { patch } from "@web/core/utils/patch";

patch(TagsList.prototype, "agp_keuangan_ib.CustomTagsList", {
    get visibleTags() {
        console.log("CustomTagsList: Running visibleTags()");
        console.log("🔍 Debugging visibleTags()");
        console.log("🌐 Current URL:", window.location.href);
        
        // return processedTags;        
        
        let isTargetModel = window.location.href.includes("&model=account.keuangan.kkhc.line");
        console.log("Is Target Model?", isTargetModel);
        
        let tags = this.props.tags.map((tag, index) => {
            console.log(`Tag ${index}:`, tag);
            
            if (isTargetModel) {
                if (tag.record && tag.record.data) {
                    console.log(`✅ Using line_name for Tag ${index}:`, tag.record.data.line_name);
                    return { ...tag, text: tag.record.data.line_name || tag.text };
                } else {
                    console.warn(`⚠️ Missing record or data for Tag ${index}, using default text.`);
                }
            }
            return tag;
        });

        console.log("🔍 Checking tags...");
        tags.forEach((tag, index) => {
            console.log(`🟢 Tag ${index}:`, tag);
            if (!tag.resId || !tag.text) {
                console.warn(`⚠️ Warning: Missing data for Tag ${index}`, tag);
            }
        });
        
        // console.log("✅ Final Processed Tags:", processedTags);

        console.log("Final Processed Tags:", tags);

        if (this.props.itemsVisible && tags.length > this.props.itemsVisible) {
            let visible = tags.slice(0, this.props.itemsVisible - 1);
            console.log("Returning Visible Tags:", visible);
            return visible;
        }

        console.log("Returning All Tags:", tags);
        return tags;
    },
});
