frappe.ui.form.on("Tarabut Connector Settings", {
  refresh(frm) {
    frm.set_df_property(
      "enabled",
      "description",
      frm.doc.enabled
        ? __("This ERPNext site is connected to Tarabut.")
        : __("Connect this ERPNext site from Tarabut's seller panel.")
    )

    frm.fields_dict.connect_with_tarabut?.$input.off("click.tarabut")
    frm.fields_dict.connect_with_tarabut?.$input.on("click.tarabut", () => {
      try {
        const baseUrl = new URL(
          frm.doc.tarabut_base_url || "https://api.tarabut.app"
        )
        if (baseUrl.hostname.startsWith("api.")) {
          baseUrl.hostname = `seller.${baseUrl.hostname.slice(4)}`
        }
        baseUrl.pathname = "/settings/integrations/erpnext"
        baseUrl.search = new URLSearchParams({
          site_url: window.location.origin,
        }).toString()
        window.open(baseUrl.toString(), "_blank", "noopener,noreferrer")
      } catch {
        frappe.msgprint(
          __("Save a valid Tarabut Base URL before connecting.")
        )
      }
    })
  },
})
