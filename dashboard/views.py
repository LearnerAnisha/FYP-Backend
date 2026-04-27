from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from CropDiseaseDetection.models import ScanResult
from chatbot.models import ChatConversation


def _human_delta(dt):
    now = timezone.now()
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        m = seconds // 60
        return f"{m} minute{'s' if m > 1 else ''} ago"
    if seconds < 86400:
        h = seconds // 3600
        return f"{h} hour{'s' if h > 1 else ''} ago"
    d = seconds // 86400
    return (
        "1 day ago"
        if d == 1
        else (f"{d} days ago" if d < 7 else dt.strftime("%d %b %Y"))
    )


def _pct_change(current, previous):
    if previous == 0:
        return f"+{current * 100}%" if current > 0 else "0%"
    change = round(((current - previous) / previous) * 100)
    return f"{'+' if change >= 0 else ''}{change}%"


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_start = (month_start - timedelta(days=1)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        def month_count(qs_filter):
            return ScanResult.objects.filter(**qs_filter).count()

        scans_now = month_count({"created_at__gte": month_start})
        scans_prev = month_count(
            {"created_at__gte": prev_month_start, "created_at__lt": month_start}
        )

        healthy_now = month_count({"created_at__gte": month_start, "is_healthy": True})
        healthy_prev = month_count(
            {
                "created_at__gte": prev_month_start,
                "created_at__lt": month_start,
                "is_healthy": True,
            }
        )

        alerts_now = month_count({"created_at__gte": month_start, "is_healthy": False})
        alerts_prev = month_count(
            {
                "created_at__gte": prev_month_start,
                "created_at__lt": month_start,
                "is_healthy": False,
            }
        )

        chats_now = ChatConversation.objects.filter(created_at__gte=month_start).count()
        chats_prev = ChatConversation.objects.filter(
            created_at__gte=prev_month_start, created_at__lt=month_start
        ).count()

        stats = [
            {
                "label": "Scans This Month",
                "value": str(scans_now),
                "change": _pct_change(scans_now, scans_prev),
            },
            {
                "label": "Healthy Crops",
                "value": str(healthy_now),
                "change": _pct_change(healthy_now, healthy_prev),
            },
            {
                "label": "Alerts Received",
                "value": str(alerts_now),
                "change": _pct_change(alerts_now, alerts_prev),
            },
            {
                "label": "AI Chats",
                "value": str(chats_now),
                "change": _pct_change(chats_now, chats_prev),
            },
        ]

        # Recent activity — last 5 scans
        recent_activity = []
        for scan in ScanResult.objects.order_by("-created_at")[:5]:
            if scan.is_healthy:
                recent_activity.append(
                    {
                        "type": "success",
                        "activityType": "scan",
                        "title": "Disease Detection Completed",
                        "description": f"{scan.crop_type} leaf analysed — No disease detected",
                        "time": _human_delta(scan.created_at),
                    }
                )
            else:
                recent_activity.append(
                    {
                        "type": "warning",
                        "activityType": "scan",
                        "title": "Disease Detected",
                        "description": f"{scan.crop_type}: {scan.disease} ({scan.severity} severity)",
                        "time": _human_delta(scan.created_at),
                    }
                )

        # Latest chat session
        latest_chat = ChatConversation.objects.order_by("-updated_at").first()
        if latest_chat:
            recent_activity.append(
                {
                    "type": "info",
                    "activityType": "chat",
                    "title": "AI Chat Session",
                    "description": "You started a conversation with Krishi AI",
                    "time": _human_delta(latest_chat.updated_at),
                }
            )

        return Response({"stats": stats, "recent_activity": recent_activity[:5]})
