app_name = "tarabut_connector"
app_title = "Tarabut"
app_publisher = "Tarabut"
app_description = "Frappe and ERPNext integration for Tarabut marketplace sync"
app_email = "dev@tarabut.app"
app_license = "MIT"
app_logo_url = "/assets/tarabut_connector/images/tarabut-icon.png"

after_install = "tarabut_connector.install.after_install"
after_migrate = "tarabut_connector.install.after_migrate"
before_uninstall = "tarabut_connector.install.before_uninstall"

scheduler_events = {
    "hourly": ["tarabut_connector.api.webhook.retry_failed_notifications"],
}

doc_events = {
    "Sales Order": {
        "on_update": "tarabut_connector.api.webhook.enqueue_document_change"
    },
    "Purchase Order": {
        "on_update": "tarabut_connector.api.webhook.enqueue_document_change"
    },
    "Item": {"on_update": "tarabut_connector.api.webhook.enqueue_document_change"},
    "Item Price": {
        "on_update": "tarabut_connector.api.webhook.enqueue_document_change"
    },
    "Bin": {"on_update": "tarabut_connector.api.webhook.enqueue_document_change"},
}
