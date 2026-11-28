"""Read-only accessibility for the existing transient Qt status message."""


def bind_status_inspector(status_bar):
    """Expose the whole current message without retaining stale notifications."""
    status_bar.setAccessibleName("Application status")

    def update(message):
        status_bar.setToolTip(message)
        status_bar.setAccessibleDescription(
            message or "No current notification. Workflow readiness is shown separately."
        )

    status_bar.messageChanged.connect(update)
    update(status_bar.currentMessage())
