-- ============================================
-- SupplyIQ: Business Analysis Queries
-- Run after 01_schema_setup.sql has loaded all data
-- USE supplyiq; -- uncomment if not already selected
-- ============================================


-- ============================================
-- Q1. Which shipping mode has the highest late-delivery rate, and by how much?
-- ============================================
SELECT
    s.shipping_mode,
    COUNT(*) AS total_shipments,
    SUM(s.late_delivery_risk) AS late_shipments,
    ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
FROM shipments s
GROUP BY s.shipping_mode
ORDER BY late_rate_pct DESC;


-- ============================================
-- Q2. Which regions/countries have the worst on-time delivery performance?
-- ============================================
SELECT
    o.order_region,
    o.order_country,
    COUNT(*) AS total_shipments,
    SUM(s.late_delivery_risk) AS late_shipments,
    ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN shipments s ON oi.order_item_id = s.order_item_id
GROUP BY o.order_region, o.order_country
HAVING total_shipments >= 100          -- filter out tiny/noisy country counts
ORDER BY late_rate_pct DESC
LIMIT 15;


-- ============================================
-- Q3. How does late delivery risk vary by product category?
-- ============================================
SELECT
    c.category_name,
    COUNT(*) AS total_shipments,
    SUM(s.late_delivery_risk) AS late_shipments,
    ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
FROM order_items oi
JOIN products p ON oi.product_card_id = p.product_card_id
JOIN categories c ON p.category_id = c.category_id
JOIN shipments s ON oi.order_item_id = s.order_item_id
GROUP BY c.category_name
ORDER BY late_rate_pct DESC;


-- ============================================
-- Q4. Monthly/yearly order and revenue trend
-- ============================================
SELECT
    YEAR(o.order_date) AS order_year,
    MONTH(o.order_date) AS order_month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(oi.sales), 2) AS total_revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY order_year, order_month
ORDER BY order_year, order_month;


-- ============================================
-- Q5. Which customer segments generate the most profit vs. the most late-delivery complaints?
-- ============================================
SELECT
    cu.segment,
    ROUND(SUM(oi.profit_per_order), 2) AS total_profit,
    COUNT(*) AS total_shipments,
    SUM(s.late_delivery_risk) AS late_shipments,
    ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN customers cu ON o.customer_id = cu.customer_id
JOIN shipments s ON oi.order_item_id = s.order_item_id
GROUP BY cu.segment
ORDER BY total_profit DESC;


-- ============================================
-- Q6. Relationship between order quantity/discount and late delivery
-- ============================================
SELECT
    CASE
        WHEN oi.discount_rate = 0 THEN 'No Discount'
        WHEN oi.discount_rate <= 0.10 THEN 'Low (0-10%)'
        WHEN oi.discount_rate <= 0.20 THEN 'Medium (10-20%)'
        ELSE 'High (20%+)'
    END AS discount_bucket,
    COUNT(*) AS total_shipments,
    ROUND(AVG(oi.quantity), 2) AS avg_quantity,
    SUM(s.late_delivery_risk) AS late_shipments,
    ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
FROM order_items oi
JOIN shipments s ON oi.order_item_id = s.order_item_id
GROUP BY discount_bucket
ORDER BY late_rate_pct DESC;


-- ============================================
-- Q7. Which markets are most profitable vs. most operationally unreliable?
-- ============================================
SELECT
    o.market,
    ROUND(SUM(oi.profit_per_order), 2) AS total_profit,
    COUNT(*) AS total_shipments,
    ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN shipments s ON oi.order_item_id = s.order_item_id
GROUP BY o.market
ORDER BY total_profit DESC;


-- ============================================
-- Q8. Average shipping delay (real days - scheduled days) by mode and region
-- ============================================
SELECT
    s.shipping_mode,
    o.order_region,
    ROUND(AVG(s.days_for_shipping_real - s.days_for_shipment_scheduled), 2) AS avg_delay_days,
    COUNT(*) AS total_shipments
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN shipments s ON oi.order_item_id = s.order_item_id
GROUP BY s.shipping_mode, o.order_region
ORDER BY avg_delay_days DESC
LIMIT 20;


-- ============================================
-- Q9. Which weekdays see the highest order volume?
-- ============================================
SELECT
    DAYNAME(o.order_date) AS order_weekday,
    COUNT(DISTINCT o.order_id) AS total_orders,
    ROUND(SUM(oi.sales), 2) AS total_revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY order_weekday
ORDER BY total_orders DESC;


-- ============================================
-- Q10. Top 10 products by sales, and their individual late-delivery rates
-- ============================================
SELECT
    p.product_name,
    ROUND(SUM(oi.sales), 2) AS total_sales,
    COUNT(*) AS total_shipments,
    ROUND(SUM(s.late_delivery_risk) * 100.0 / COUNT(*), 2) AS late_rate_pct
FROM order_items oi
JOIN products p ON oi.product_card_id = p.product_card_id
JOIN shipments s ON oi.order_item_id = s.order_item_id
GROUP BY p.product_name
ORDER BY total_sales DESC
LIMIT 10;