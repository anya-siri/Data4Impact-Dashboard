-- analysis_queries.sql
-- Analytical SQL queries answering key business questions about
-- Data4Impact's nonprofit program performance.
-- Run against database/data4impact.db (table: impact_metrics).

-- ============================================================
-- 1. Total beneficiaries served by program
-- Business question: Which programs reach the most people overall?
-- ============================================================
SELECT
    program_name,
    SUM(beneficiaries_served) AS total_beneficiaries
FROM impact_metrics
GROUP BY program_name
ORDER BY total_beneficiaries DESC;


-- ============================================================
-- 2. Total funding received by program
-- Business question: Where is the organization's funding concentrated?
-- ============================================================
SELECT
    program_name,
    SUM(funding_received) AS total_funding
FROM impact_metrics
GROUP BY program_name
ORDER BY total_funding DESC;


-- ============================================================
-- 3. Average cost per beneficiary by program
-- Business question: Which programs are most cost-efficient per person served?
-- ============================================================
SELECT
    program_name,
    ROUND(AVG(cost_per_beneficiary), 2) AS avg_cost_per_beneficiary
FROM impact_metrics
GROUP BY program_name
ORDER BY avg_cost_per_beneficiary ASC;


-- ============================================================
-- 4. Program target achievement
-- Business question: Which programs are meeting or missing their
-- beneficiary targets?
-- ============================================================
SELECT
    program_name,
    SUM(beneficiaries_served) AS total_served,
    SUM(target_beneficiaries) AS total_target,
    ROUND(SUM(beneficiaries_served) * 100.0 / NULLIF(SUM(target_beneficiaries), 0), 2) AS achievement_rate_pct
FROM impact_metrics
GROUP BY program_name
ORDER BY achievement_rate_pct DESC;


-- ============================================================
-- 5. Funding utilization by program
-- Business question: Which programs spend a high vs. low share of the
-- funding they receive?
-- ============================================================
SELECT
    program_name,
    ROUND(SUM(program_expenses) * 100.0 / NULLIF(SUM(funding_received), 0), 2) AS funding_utilization_pct
FROM impact_metrics
GROUP BY program_name
ORDER BY funding_utilization_pct DESC;


-- ============================================================
-- 6. Year-over-year beneficiary trends
-- Business question: Is overall impact (people served) growing year to year?
-- ============================================================
SELECT
    year,
    SUM(beneficiaries_served) AS total_beneficiaries,
    ROUND(
        (SUM(beneficiaries_served) - LAG(SUM(beneficiaries_served)) OVER (ORDER BY year))
        * 100.0 / NULLIF(LAG(SUM(beneficiaries_served)) OVER (ORDER BY year), 0), 2
    ) AS yoy_growth_pct
FROM impact_metrics
GROUP BY year
ORDER BY year;


-- ============================================================
-- 7. Regional impact
-- Business question: Which regions receive the most funding and serve the
-- most beneficiaries?
-- ============================================================
SELECT
    region,
    SUM(beneficiaries_served) AS total_beneficiaries,
    SUM(funding_received) AS total_funding,
    COUNT(DISTINCT state) AS states_active
FROM impact_metrics
GROUP BY region
ORDER BY total_beneficiaries DESC;


-- ============================================================
-- 8. Programs with outcome success above the overall average
-- Business question: Which programs are outperforming the org-wide
-- average outcome success rate? (Uses a CTE for the overall average.)
-- ============================================================
WITH overall_avg AS (
    SELECT AVG(outcome_success_rate) AS avg_rate
    FROM impact_metrics
)
SELECT
    im.program_name,
    ROUND(AVG(im.outcome_success_rate), 2) AS program_avg_success_rate,
    ROUND((SELECT avg_rate FROM overall_avg), 2) AS overall_avg_success_rate
FROM impact_metrics im
GROUP BY im.program_name
HAVING AVG(im.outcome_success_rate) > (SELECT avg_rate FROM overall_avg)
ORDER BY program_avg_success_rate DESC;


-- ============================================================
-- 9. Program performance classification by outcome success rate
-- Business question: How can programs be grouped by their average outcome
-- success rate? Uses CASE WHEN to classify programs as High Performing,
-- Medium Performing, or Needs Attention. Cost per beneficiary is included
-- as an additional efficiency metric for comparison.
-- ============================================================
SELECT
    program_name,
    ROUND(AVG(outcome_success_rate), 2) AS avg_success_rate,
    ROUND(AVG(cost_per_beneficiary), 2) AS avg_cost_per_beneficiary,
    CASE
        WHEN AVG(outcome_success_rate) >= 80 THEN 'High Performing'
        WHEN AVG(outcome_success_rate) >= 65 THEN 'Medium Performing'
        ELSE 'Needs Attention'
    END AS performance_tier
FROM impact_metrics
GROUP BY program_name
ORDER BY avg_success_rate DESC;


-- ============================================================
-- 10. Programs requiring attention
-- Business question: Which programs have below-average outcomes AND
-- below-target beneficiary achievement, signaling they may need review?
-- ============================================================
WITH program_summary AS (
    SELECT
        program_name,
        AVG(outcome_success_rate) AS avg_success_rate,
        SUM(beneficiaries_served) * 100.0 / NULLIF(SUM(target_beneficiaries), 0) AS achievement_rate
    FROM impact_metrics
    GROUP BY program_name
)
SELECT
    program_name,
    ROUND(avg_success_rate, 2) AS avg_success_rate,
    ROUND(achievement_rate, 2) AS achievement_rate
FROM program_summary
WHERE avg_success_rate < (SELECT AVG(outcome_success_rate) FROM impact_metrics)
   AND achievement_rate < 100
ORDER BY avg_success_rate ASC;


-- ============================================================
-- 11. Volunteer contribution by program
-- Business question: Which programs rely most heavily on volunteer labor,
-- and how efficient is that labor?
-- ============================================================
SELECT
    program_name,
    SUM(volunteer_hours) AS total_volunteer_hours,
    SUM(number_of_volunteers) AS total_volunteers,
    ROUND(SUM(beneficiaries_served) * 1.0 / NULLIF(SUM(volunteer_hours), 0), 3) AS beneficiaries_per_volunteer_hour
FROM impact_metrics
GROUP BY program_name
ORDER BY total_volunteer_hours DESC;


-- ============================================================
-- 12. Annual funding versus program expenses
-- Business question: Is the organization spending within its funding
-- envelope each year, and how large is the funding surplus/deficit?
-- ============================================================
SELECT
    year,
    ROUND(SUM(funding_received), 2) AS total_funding,
    ROUND(SUM(program_expenses), 2) AS total_expenses,
    ROUND(SUM(funding_received) - SUM(program_expenses), 2) AS net_funding_remaining
FROM impact_metrics
GROUP BY year
ORDER BY year;
