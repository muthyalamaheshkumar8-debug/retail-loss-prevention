# Power BI integration

Export CSV from **Reports**, then use **Get Data → Text/CSV** in Power BI Desktop. Name the table `incidents`. Convert `created_at` and `reviewed_at` to Date/Time/Timezone, and `timestamp` to Decimal Number. No .pbix binary is included; these instructions and measures build the dashboard from your real records.

```dax
Total Incidents = COUNTROWS(incidents)
Reviewed Incidents = COUNTROWS(FILTER(incidents, NOT(ISBLANK(incidents[reviewed_at]))))
Review Completion % = DIVIDE([Reviewed Incidents], [Total Incidents], 0)
Escalated Incidents = CALCULATE([Total Incidents], incidents[status] = "ESCALATED")
Escalation % = DIVIDE([Escalated Incidents], [Reviewed Incidents], 0)
Not Incident = CALCULATE([Total Incidents], incidents[status] = "NOT_AN_INCIDENT")
```

Use a line chart of incidents by creation date, bar charts by store and category, and a donut chart by status. Add store, camera, date, and reviewer filters. Reviewer decisions are not labeled ground truth and these measures are not model accuracy or false-positive rates.

For Python and SQL: `pip install -r analytics/requirements.txt`, then `python analytics/analyze.py incidents.csv`. This creates a cleaned store/outcome CSV, an SQLite database, and a daily chart. In SQLite:

```sql
SELECT store_id, status, COUNT(*) AS total
FROM incidents
GROUP BY store_id, status;
```
