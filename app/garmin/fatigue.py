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

        Returns band label, "ignored_for_strain" if IF is out of easy-ride bands,
        or empty string if IF is None.

        High-IF rides (>= 0.65) are explicitly excluded from strain baselines.
        They still contribute to training load context (task 10) but do NOT
        influence easy-ride fatigue interpretation. This is by design, not a bug.
        """
        if intensity_factor is None:
            return ""
        for low, high, label in self.if_bands:
            if intensity_factor >= low and intensity_factor < high:
                return label
        # Out-of-band rides (usually high-IF) are explicitly ignored for strain
        return "ignored_for_strain"

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
        
        Returns a dict with strain metrics plus a "strain_applicable" flag
        indicating whether this ride can contribute to fatigue interpretation.
        """
        out: Dict[str, Any] = {}

        # Try primary keys first, then fallback to ICU metadata keys
        avg_hr = ride.get("avg_heartrate")
        if avg_hr is None:
            avg_hr = ride.get("average_heartrate")
        out["avg_heartrate"] = None if avg_hr is None else float(avg_hr)

        max_hr = ride.get("max_heartrate")
        if max_hr is None:
            max_hr = ride.get("max_heartrate")  # Fallback to same key if available
        out["max_heartrate"] = None if max_hr is None else float(max_hr)

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

        # Explicit marker: is this ride eligible for strain/fatigue interpretation?
        # Applies only to easy rides (IF < 0.65, meets duration/zone criteria).
        # High-IF rides still count toward training load but are excluded from strain.
        is_easy, _ = self.is_easy_ride(ride)
        out["strain_applicable"] = is_easy

        return out

    def build_baseline_statistics(self, rides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build baseline statistics per IF band (task 6).

        Returns mapping band_label -> {metric: {mean, stdev, count}}.
        Pure aggregation only.

        Note: Rides with band="ignored_for_strain" are explicitly excluded.
        High-IF efforts do not contribute to easy-ride baselines.
        """
        import statistics

        bands: Dict[str, List[Dict[str, Any]]] = {}
        for r in rides:
            if_val = r.get("intensity_factor") or r.get("IF")
            band_label = self.assign_if_band(if_val)
            if not band_label or band_label == "ignored_for_strain":
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

    def rolling_window_gating(self, rides: List[Dict[str, Any]], window_days: int = 7) -> Dict[str, Any]:
        """Check rolling window eligibility (task 9).

        Returns gating status for a window. Rules:
        - >= 2 eligible easy rides in window
        - >= 5 total rides in window
        - No gap > 3 days with zero riding

        Returns dict with `eligible: bool` and `reasons` list.
        """
        import datetime as dt

        reasons: List[str] = []

        if not rides:
            reasons.append("no_rides_in_window")
            return {"eligible": False, "reasons": reasons}

        # Parse dates
        try:
            dates = [dt.datetime.strptime(r.get("date"), "%Y-%m-%d").date() for r in rides if r.get("date")]
        except Exception:
            reasons.append("bad_date_format")
            return {"eligible": False, "reasons": reasons}

        if not dates:
            reasons.append("no_valid_dates")
            return {"eligible": False, "reasons": reasons}

        sorted_dates = sorted(set(dates))
        
        # Check for gaps > 3 days
        for i in range(len(sorted_dates) - 1):
            gap = (sorted_dates[i + 1] - sorted_dates[i]).days
            if gap > 3:
                reasons.append(f"gap_of_{gap}_days")

        # Count total rides
        total_rides = len(rides)
        if total_rides < 5:
            reasons.append(f"only_{total_rides}_rides")

        # Count easy rides (strain_applicable = true)
        easy_count = sum(1 for r in rides if self.compute_per_ride_strain(r).get("strain_applicable"))
        if easy_count < 2:
            reasons.append(f"only_{easy_count}_easy_rides")

        eligible = len(reasons) == 0
        return {"eligible": eligible, "reasons": reasons, "total_rides": total_rides, "easy_rides": easy_count}

    def training_load_context(self, rides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check training load context (task 10).

        Ensures TSS values are reliable and not skewed by single outliers.

        Returns dict with `reliable: bool`, `reasons`, and `tss_stats`.
        """
        reasons: List[str] = []
        tss_values = [r.get("tss") for r in rides if r.get("tss") is not None]

        if len(tss_values) < 3:
            reasons.append(f"only_{len(tss_values)}_rides_with_tss")
            return {"reliable": False, "reasons": reasons, "tss_stats": {}}

        total_tss = sum(tss_values)
        max_tss = max(tss_values)
        max_pct = (max_tss / total_tss * 100.0) if total_tss > 0 else 0.0

        if max_pct > 60.0:
            reasons.append(f"single_ride_is_{max_pct:.1f}pct_of_weekly")

        reliable = len(reasons) == 0
        return {
            "reliable": reliable,
            "reasons": reasons,
            "tss_stats": {
                "total": float(total_tss),
                "count": len(tss_values),
                "max": float(max_tss),
                "max_percent": float(max_pct),
            },
        }

    def aggregate_7day_classification(self, rides: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate 7-day classifications (task 8).

        Produces a conservative label for the 7-day window.
        Returns classification with reasoning (never interprets causality).
        """
        # Pre-check: gating and load context
        gating = self.rolling_window_gating(rides)
        load_ctx = self.training_load_context(rides)

        result: Dict[str, Any] = {
            "classification": "neutral_noisy",
            "reasons": [],
            "gating": gating,
            "load_context": load_ctx,
        }

        if not gating["eligible"]:
            result["reasons"].extend(gating["reasons"])
            return result

        if not load_ctx["reliable"]:
            result["reasons"].extend(load_ctx["reasons"])
            return result

        # Baseline: build from all rides
        baseline = self.build_baseline_statistics(rides)
        if not baseline:
            result["reasons"].append("no_eligible_bands_in_baseline")
            return result

        # Count strain flags in easy rides
        easy_rides = [r for r in rides if self.compute_per_ride_strain(r).get("strain_applicable")]
        if not easy_rides:
            result["reasons"].append("no_easy_rides_to_evaluate")
            return result

        strain_flags = []
        for ride in easy_rides:
            comp = self.compare_ride_to_baseline(ride, baseline)
            if comp.get("comparison"):
                # Flag if any metric is elevated (zscore > 1.0)
                for metric, vals in comp["comparison"].items():
                    z = vals.get("zscore")
                    if z is not None and z > 1.0:
                        strain_flags.append({"ride_date": ride.get("date"), "metric": metric, "zscore": z})

        flagged_rides = len(set(sf["ride_date"] for sf in strain_flags))

        # Conservative classification rules
        if flagged_rides >= 3:
            result["classification"] = "fatigue_accumulating"
            result["reasons"].append(f"{flagged_rides}_of_{len(easy_rides)}_easy_rides_elevated")
        elif flagged_rides >= 2:
            result["classification"] = "non_training_fatigue_likely"
            result["reasons"].append(f"{flagged_rides}_rides_show_strain_pattern")
        elif flagged_rides >= 1:
            result["reasons"].append(f"{flagged_rides}_ride_elevated_strain")
        else:
            result["reasons"].append("no_elevated_strain_detected")

        result["strain_flags"] = strain_flags
        return result

    def text_summary(self, classification: Dict[str, Any], baseline: Dict[str, Any], rides: List[Dict[str, Any]]) -> str:
        """Generate plain-English summary of fatigue status (task 12).

        Returns a conservative, non-prescriptive summary suitable for an athlete.
        Never claims causality; only describes patterns and gating status.
        """
        if not classification:
            return "Insufficient data to interpret fatigue status."

        lines = []
        class_label = classification.get("classification", "neutral_noisy")
        gating = classification.get("gating", {})
        load_ctx = classification.get("load_context", {})

        # Header
        lines.append("=== FATIGUE STATUS SUMMARY ===")
        lines.append("")

        # Gating status
        if not gating.get("eligible"):
            lines.append("⚠️  INSUFFICIENT DATA FOR INTERPRETATION")
            reasons = gating.get("reasons", [])
            if reasons:
                lines.append(f"Gating failures: {', '.join(reasons)}")
            lines.append("")
            lines.append("Once the rolling window stabilizes (no >3-day gaps), strain patterns will be analyzed.")
            return "\n".join(lines)

        # Load context
        if not load_ctx.get("reliable"):
            lines.append("⚠️  TRAINING LOAD SKEWED")
            reasons = load_ctx.get("reasons", [])
            if reasons:
                lines.append(f"Load issues: {', '.join(reasons)}")
            lines.append("")
            lines.append("Classification is muted due to unreliable TSS distribution.")
            return "\n".join(lines)

        # Classification output (plain English, no jargon)
        if class_label == "absorbing_well":
            lines.append("✅ ABSORBING WELL")
            lines.append("Easy rides show normal strain patterns relative to baseline.")
            lines.append("Recovery appears adequate. No fatigue mismatch detected.")
        elif class_label == "neutral_noisy":
            lines.append("📊 NEUTRAL (NOISY)")
            lines.append("No clear pattern of elevated strain in easy rides.")
            lines.append("Data is sufficient but strain signals are inconsistent.")
        elif class_label == "non_training_fatigue_likely":
            lines.append("⚠️  POSSIBLE NON-TRAINING FATIGUE")
            lines.append("Multiple easy rides show elevated strain (HR, cardiac cost) relative to baseline.")
            lines.append("This pattern is consistent with external stress (work, illness, sleep, etc.)")
            lines.append("not training load. Consider recovery and non-training factors.")
        elif class_label == "fatigue_accumulating":
            lines.append("⚠️  FATIGUE ACCUMULATING")
            lines.append("≥3 easy rides in the window show elevated strain markers.")
            lines.append("Physiological strain is elevated relative to training load.")
            lines.append("Consider additional rest or reduced intensity on upcoming easy rides.")

        lines.append("")

        # Baseline context
        total_rides = gating.get("total_rides", 0)
        easy_rides = gating.get("easy_rides", 0)
        lines.append(f"📈 CONTEXT: {total_rides} total rides ({easy_rides} easy rides) over 7 days")

        tss_stats = load_ctx.get("tss_stats", {})
        tss_total = tss_stats.get("total", 0)
        lines.append(f"   Total TSS: {tss_total:.0f} | Max ride: {tss_stats.get('max_percent', 0):.1f}% of weekly")

        # Baseline HR/cardiac cost
        if_50_60 = baseline.get("IF_50_60", {})
        hr_50_60 = if_50_60.get("avg_heartrate", {}).get("mean")
        if hr_50_60:
            lines.append(f"   IF 0.50–0.60 baseline: {hr_50_60:.0f} bpm (n={if_50_60.get('avg_heartrate', {}).get('count')})")

        if_60_65 = baseline.get("IF_60_65", {})
        hr_60_65 = if_60_65.get("avg_heartrate", {}).get("mean")
        if hr_60_65:
            lines.append(f"   IF 0.60–0.65 baseline: {hr_60_65:.0f} bpm (n={if_60_65.get('avg_heartrate', {}).get('count')})")

        lines.append("")
        lines.append("NOTE: This system detects strain mismatch during easy riding only.")
        lines.append("High-intensity efforts are expected to show elevated strain (by design).")
        lines.append("This is a warning and interpretation layer, not a decision engine.")

        return "\n".join(lines)


__all__ = ["FatigueChecker"]
