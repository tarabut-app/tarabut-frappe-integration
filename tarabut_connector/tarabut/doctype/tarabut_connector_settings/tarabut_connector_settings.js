frappe.ui.form.on("Tarabut Connector Settings", {
  refresh(frm) {
    frm.set_df_property(
      "enabled",
      "description",
      frm.doc.enabled
        ? __("This ERPNext site is connected to Tarabut.")
        : __("Click Connect with Tarabut to authorize this ERPNext site.")
    )

    frm.fields_dict.connect_with_tarabut?.$input.off("click.tarabut")
    frm.fields_dict.connect_with_tarabut?.$input.on("click.tarabut", async () => {
      try {
        if (frm.is_dirty()) {
          await frm.save()
        }
        const response = await frappe.call({
          method: "tarabut_connector.api.pairing.create_pairing_session",
          freeze: true,
          freeze_message: __("Preparing a secure Tarabut connection..."),
        })
        const connectUrl = response.message?.connect_url
        if (!connectUrl) {
          throw new Error(__("Tarabut did not return a connection link."))
        }
        const popup = window.open(connectUrl, "_blank", "noopener,noreferrer")
        if (!popup) {
          window.location.assign(connectUrl)
        }
      } catch (error) {
        frappe.msgprint({
          title: __("Unable to connect with Tarabut"),
          indicator: "red",
          message:
            error?.message ||
            __("Check the advanced Tarabut URL and try again."),
        })
      }
    })
  },
})
