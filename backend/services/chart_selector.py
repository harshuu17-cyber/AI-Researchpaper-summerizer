from collections import defaultdict


def select_charts(numerical_data: dict):
    """
    Convert extracted numerical results into chart-ready data.

    No values are invented. Only values extracted from the paper
    are used.
    """

    results = numerical_data.get("results", [])

    if not results:
        return {
            "charts": [],
            "message": "No suitable numerical data was found in the paper."
        }

    # Group results by metric
    grouped = defaultdict(list)

    for item in results:

        label = item.get("label", "").strip()
        metric = item.get("metric", "").strip()
        value = item.get("value")
        unit = item.get("unit", "").strip()

        if not label or not metric or value is None:
            continue

        grouped[metric].append({
            "label": label,
            "value": value,
            "unit": unit
        })

    charts = []

    for metric, values in grouped.items():

        if not values:
            continue

        # Remove duplicate labels
        unique_values = []
        seen = set()

        for item in values:

            key = (
                item["label"],
                item["value"],
                item["unit"]
            )

            if key not in seen:
                seen.add(key)
                unique_values.append(item)

        values = unique_values

        # -----------------------------------------
        # Choose chart type
        # -----------------------------------------

        metric_lower = metric.lower()

        if len(values) == 1:
            chart_type = "stat"

        elif any(
            word in metric_lower
            for word in [
                "accuracy",
                "precision",
                "recall",
                "f1",
                "score",
                "error",
                "rate"
            ]
        ):
            chart_type = "bar"

        elif any(
            word in metric_lower
            for word in [
                "time",
                "year",
                "epoch",
                "iteration"
            ]
        ):
            chart_type = "line"

        elif any(
            word in metric_lower
            for word in [
                "size",
                "number",
                "count",
                "images",
                "samples"
            ]
        ):
            chart_type = "bar"

        else:
            chart_type = "bar"

        # -----------------------------------------
        # Create chart object
        # -----------------------------------------

        chart = {
            "id": f"chart_{len(charts) + 1}",

            "title": metric,

            "metric": metric,

            "chart_type": chart_type,

            "unit": values[0]["unit"],

            "data": [
                {
                    "label": item["label"],
                    "value": item["value"]
                }
                for item in values
            ]
        }

        charts.append(chart)

    return {
        "charts": charts,
        "chart_count": len(charts)
    }