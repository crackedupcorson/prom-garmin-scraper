import datetime
from typing import List, Dict, Any, Tuple


class FatigueChecker:
    """Pure, rule-based primitives for the fatigue-mismatch pipeline.

    This module implements the "pure data" building blocks required by
    the higher-level interpretation logic. It intentionally does NOT
    perform final classifications or produce composite scores.
    """

    def __init__(self):
        # Default IF bands (lower inclusive, upper exclusive)
        self.if_bands = self.define_if_bands()

    def define_if_bands(self) -> List[Tuple[float, float, str]]:
        """Return IF bands as (low, high, label).

        This is a pure definition step (task 3). No interpretation.
        """
        return [
            (0.50, 0.60, "IF_50_60"),
            (0.60, 0.65, "IF_60_65"),
        ]

    def history_gating(self, rides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Basic gating checks over ride history (task 2).

        Expects `rides` to be a list of dicts with at least a `date` key
        (ISO date string) and indicators that HR/power are present.

        Returns a dict describing sufficiency (pure check, no rules).
        """
        result = {"sufficient_history": False, "reasons": []}
        if not rides:
            result["reasons"].append("no_rides")
            return result

        # Parse unique days present in history
        try:
            dates = [datetime.datetime.strptime(r.get("date"), "%Y-%m-%d").date() for r in rides if r.get("date")]
        except Exception:
            result["reasons"].append("bad_date_format")
            return result

        if not dates:
            result["reasons"].append("no_valid_dates")
            return result

        span_days = (max(dates) - min(dates)).days + 1
        if span_days < 21:
            result["reasons"].append("insufficient_history_days")

        # Check HR/power availability: require at least one ride with both
        hr_power_count = 0
        for r in rides:
            if r.get("avg_power") is not None and r.get("avg_heartrate") is not None:
                hr_power_count += 1

        if hr_power_count == 0:
            result["reasons"].append("no_reliable_hr_power")

        if not result["reasons"]:
            result["sufficient_history"] = True

        return result

    def assign_if_band(self, intensity_factor: float) -> str:
        """Assign a simple IF band label for a given IF value (pure function).

        Returns band label or empty string if none match.
        """
        if intensity_factor is None:
            return ""
        for low, high, label in self.if_bands:
            if intensity_factor >= low and intensity_factor < high:
                return label
        return ""

    def is_easy_ride(self, ride: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Detect whether a ride satisfies the easy-ride eligibility (task 4).

        Expects keys (any of): `intensity_factor` (or `IF`), `total_time` (seconds),
        `zone_percentages` (dict keyed by zone labels) or `pace_zone_percentages`.

        Returns (is_easy, reasons_list). Pure gating logic only.
        """
        reasons: List[str] = []
        # Intensity factor
        if_val = None
        if ride.get("intensity_factor") is not None:
            if_val = ride.get("intensity_factor")
        elif ride.get("IF") is not None:
            if_val = ride.get("IF")

        if if_val is None:
            reasons.append("missing_if")
        else:
            try:
                if_val = float(if_val)
            except Exception:
                reasons.append("invalid_if")

        # Duration (require >= 60 minutes)
        total_seconds = ride.get("total_time")
        if total_seconds is None:
            # try minutes
            total_minutes = ride.get("total_minutes")
            if total_minutes is None:
                reasons.append("missing_duration")
                total_seconds = 0
            else:
                total_seconds = float(total_minutes) * 60.0

        minutes = float(total_seconds) / 60.0 if total_seconds else 0.0
        if minutes < 60.0:
            reasons.append("short_duration")

        # Percent time in Z2 or below (require >= 60%)
        pct_z2_or_below = None
        zp = ride.get("zone_percentages") or ride.get("pace_zone_percentages")
        if isinstance(zp, dict):
            # sum any zones that look like Z1/Z2 or lower labels
            candidates = [k for k in zp.keys() if k.upper().startswith("Z")]
            # conservative: sum Z1 and Z2 if present
            pct = 0.0
            if "Z1" in zp:
                pct += float(zp.get("Z1") or 0.0)
            if "Z2" in zp:
                pct += float(zp.get("Z2") or 0.0)
            # If percentages are 0..1, convert to percent
            if pct <= 1.0:
                pct *= 100.0
            pct_z2_or_below = pct
        else:
            reasons.append("missing_zones")

        if pct_z2_or_below is None or pct_z2_or_below < 60.0:
            reasons.append("insufficient_time_in_z2")

        # IF check must be < 0.65
        if if_val is not None:
            try:
                if if_val >= 0.65:
                    reasons.append("if_too_high")
            except Exception:
                pass

        is_easy = ("missing_if" not in reasons and
                   "short_duration" not in reasons and
                   "missing_zones" not in reasons and
                   "insufficient_time_in_z2" not in reasons and
                   "if_too_high" not in reasons)

        return is_easy, reasons

    def compute_per_ride_strain(self, ride: Dict[str, Any]) -> Dict[str, Any]:
        """Compute core per-ride strain metrics (task 5).

        Pure data extractor / aggregator. No thresholds or interpretations.
        """
        out: Dict[str, Any] = {}

        out["avg_heartrate"] = None if ride.get("avg_heartrate") is None else float(ride.get("avg_heartrate"))
        out["max_heartrate"] = None if ride.get("max_heartrate") is None else float(ride.get("max_heartrate"))
        out["hr_drift"] = None if ride.get("hr_drift") is None else float(ride.get("hr_drift"))

        out["avg_power"] = None if ride.get("avg_power") is None else float(ride.get("avg_power"))
        out["normalized_power"] = None if ride.get("normalized_power") is None else float(ride.get("normalized_power"))
        out["intensity_factor"] = None if ride.get("intensity_factor") is None else float(ride.get("intensity_factor"))

        out["total_time"] = None
        if ride.get("total_time") is not None:
            try:
                out["total_time"] = float(ride.get("total_time"))
            except Exception:
                out["total_time"] = None

        if out.get("avg_heartrate") is not None and out.get("avg_power") is not None and out.get("avg_power") > 0:
            out["cardiac_cost"] = out["avg_heartrate"] / out["avg_power"]
        else:
            out["cardiac_cost"] = None

        if out["hr_drift"] is None and isinstance(ride.get("heartrate_series"), list) and len(ride.get("heartrate_series")) > 1:
            hr_series = [v for v in ride.get("heartrate_series") if v is not None]
            if len(hr_series) >= 2:
                mid = len(hr_series) // 2
                first = sum(hr_series[:mid]) / max(1, len(hr_series[:mid]))
                second = sum(hr_series[mid:]) / max(1, len(hr_series[mid:]))
                out["hr_drift"] = float(second - first)

        out["tss"] = None if ride.get("tss") is None else float(ride.get("tss"))

        return out

    def build_baseline_statistics(self, rides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build baseline statistics per IF band (task 6).

        Returns mapping band_label -> {metric: {mean, stdev, count}}.
        Pure aggregation only.
        """
        import statistics

        bands: Dict[str, List[Dict[str, Any]]] = {}
        for r in rides:
            if_val = r.get("intensity_factor") or r.get("IF")
            band_label = self.assign_if_band(if_val)
            if not band_label:
                continue
            bands.setdefault(band_label, []).append(r)

        result: Dict[str, Any] = {}
        for band, items in bands.items():
            metrics_list = {"avg_heartrate": [], "hr_drift": [], "cardiac_cost": [], "tss": []}
            for it in items:
                vals = self.compute_per_ride_strain(it)
                for k in list(metrics_list.keys()):
                    v = vals.get(k)
                    if v is not None:
                        metrics_list[k].append(v)

            stats: Dict[str, Any] = {}
            for k, arr in metrics_list.items():
                if len(arr) == 0:
                    stats[k] = {"mean": None, "stdev": None, "count": 0}
                elif len(arr) == 1:
                    stats[k] = {"mean": float(arr[0]), "stdev": 0.0, "count": 1}
                else:
                    try:
                        stats[k] = {"mean": float(statistics.mean(arr)), "stdev": float(statistics.pstdev(arr)), "count": len(arr)}
                    except Exception:
                        stats[k] = {"mean": None, "stdev": None, "count": len(arr)}

            result[band] = stats

        return result

    def compare_ride_to_baseline(self, ride: Dict[str, Any], baseline_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Compare a ride to a band's baseline (task 7).

        Returns raw deltas and z-scores; no interpretation.
        """
        out: Dict[str, Any] = {}
        if_val = ride.get("intensity_factor") or ride.get("IF")
        band_label = self.assign_if_band(if_val)
        if not band_label or band_label not in baseline_stats:
            out["band"] = band_label
            out["comparison"] = None
            return out

        metrics = self.compute_per_ride_strain(ride)
        stats = baseline_stats[band_label]
        comp: Dict[str, Any] = {}
        for k in ["avg_heartrate", "hr_drift", "cardiac_cost", "tss"]:
            val = metrics.get(k)
            b = stats.get(k, {})
            mean = b.get("mean")
            stdev = b.get("stdev")
            if val is None or mean is None:
                comp[k] = {"value": val, "delta": None, "zscore": None}
            else:
                delta = val - mean
                z = None
                try:
                    if stdev and stdev > 0:
                        z = delta / stdev
                except Exception:
                    z = None
                comp[k] = {"value": val, "delta": delta, "zscore": z}

        out["band"] = band_label
        out["comparison"] = comp
        return out


__all__ = ["FatigueChecker"]
