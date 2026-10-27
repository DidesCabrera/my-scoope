"""Navigation targets for notifications on web and native clients."""

from django.urls import reverse


def notification_destinations(item):
    kind = item["kind"]
    if kind == "proposal":
        return reverse("proposal_detail", args=[item["id"]]), f"/proposals/{item['id']}"
    if kind == "share":
        return reverse("inbox_detail", args=["share", item["id"]]), f"/share/{item['public_id']}"
    if kind == "invitation":
        return reverse("share_invitation_preview", args=[item["public_id"]]), ""
    return reverse("notifications_list"), "/notifications"


def present_notifications(items):
    presented = []
    for item in items:
        web_url, mobile_path = notification_destinations(item)
        presented.append({
            **{key: value for key, value in item.items() if key != "public_id"},
            "web_url": web_url,
            "mobile_path": mobile_path,
        })
    return presented
