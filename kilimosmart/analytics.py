"""Aggregate platform insights across all registered farmers.

Represents the operator-facing view of the platform (adoption, regional
reach, which crops are being recommended most) — distinct from the
per-farmer USSD session, which only ever sees one phone number at a time.
"""

from collections import Counter

from kilimosmart.repository import FarmerRepository


class PlatformAnalytics:
    def __init__(self, repo: FarmerRepository):
        self._repo = repo

    def summary(self) -> str:
        farmers = self._repo.all()
        if not farmers:
            return "No farmers registered yet."

        region_counts = Counter(f.region for f in farmers)
        sms_opt_in_count = sum(1 for f in farmers if f.sms_opt_in)

        crop_counts: Counter = Counter()
        for farmer in farmers:
            for entry in self._repo.get_history(farmer.id):
                crop_counts[entry.top_crop] += 1

        lines = [
            "KilimoSmart Platform Insights",
            "=" * 32,
            f"Registered farmers: {len(farmers)}",
            f"SMS opt-in rate: {sms_opt_in_count}/{len(farmers)} ({sms_opt_in_count / len(farmers):.0%})",
            "Farmers by region:",
        ]
        for region, count in region_counts.most_common():
            lines.append(f"  {region}: {count}")

        if crop_counts:
            lines.append("Most recommended crops:")
            for crop, count in crop_counts.most_common(5):
                lines.append(f"  {crop}: {count} time(s)")

        return "\n".join(lines)
