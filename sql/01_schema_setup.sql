-- SupplyIQ: MySQL Schema Setup

CREATE DATABASE IF NOT EXISTS supplyiq;
USE supplyiq;

-- Drop tables for clean re-runs
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;

-- ---------- categories ----------
CREATE TABLE categories (
    category_id      INT PRIMARY KEY,
    category_name    VARCHAR(100),
    department_id     INT,
    department_name   VARCHAR(100)
);

-- ---------- products ----------
CREATE TABLE products (
    product_card_id   INT PRIMARY KEY,
    product_name      VARCHAR(255),
    product_price     DECIMAL(10,2),
    product_status    INT,
    category_id       INT,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- ---------- customers ----------
CREATE TABLE customers (
    customer_id    INT PRIMARY KEY,
    first_name     VARCHAR(100),
    last_name      VARCHAR(100),
    email          VARCHAR(150),
    segment        VARCHAR(50),
    city           VARCHAR(100),
    state          VARCHAR(100),
    street         VARCHAR(255),
    country        VARCHAR(100),
    zipcode        VARCHAR(20)
);

-- ---------- orders ----------
CREATE TABLE orders (
    order_id        INT PRIMARY KEY,
    customer_id     INT,
    order_date      DATETIME,
    order_status    VARCHAR(50),
    order_region    VARCHAR(100),
    order_state     VARCHAR(100),
    order_city      VARCHAR(100),
    order_country   VARCHAR(100),
    order_zipcode   VARCHAR(20),
    market          VARCHAR(50),
    payment_type    VARCHAR(50),
    latitude        DECIMAL(10,6),
    longitude       DECIMAL(10,6),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- ---------- order_items ----------
CREATE TABLE order_items (
    order_item_id       INT PRIMARY KEY,
    order_id            INT,
    product_card_id     INT,
    quantity            INT,
    product_price       DECIMAL(10,2),
    discount             DECIMAL(10,2),
    discount_rate        DECIMAL(6,4),
    profit_ratio         DECIMAL(10,4),
    sales                DECIMAL(10,2),
    order_item_total     DECIMAL(10,2),
    profit_per_order     DECIMAL(10,2),
    benefit_per_order    DECIMAL(10,2),
    sales_per_customer   DECIMAL(10,2),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_card_id) REFERENCES products(product_card_id)
);

-- ---------- shipments ----------
CREATE TABLE shipments (
    order_item_id                 INT PRIMARY KEY,
    shipping_date                 DATETIME,
    shipping_mode                 VARCHAR(50),
    delivery_status               VARCHAR(50),
    days_for_shipping_real        INT,
    days_for_shipment_scheduled   INT,
    late_delivery_risk            TINYINT,
    FOREIGN KEY (order_item_id) REFERENCES order_items(order_item_id)
);

-- ============================================
-- LOAD DATA: run these AFTER the CSVs exist in data/processed/
-- Adjust the file path below to match YOUR machine's absolute path.
-- ============================================

LOAD DATA LOCAL INFILE '/Users/anjalisingh/Desktop/SupplyIQ/data/processed/categories.csv'
INTO TABLE categories
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/anjalisingh/Desktop/SupplyIQ/data/processed/products.csv'
INTO TABLE products
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/anjalisingh/Desktop/SupplyIQ/data/processed/customers.csv'
INTO TABLE customers
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/anjalisingh/Desktop/SupplyIQ/data/processed/orders.csv'
INTO TABLE orders
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/anjalisingh/Desktop/SupplyIQ/data/processed/order_items.csv'
INTO TABLE order_items
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

LOAD DATA LOCAL INFILE '/Users/anjalisingh/Desktop/SupplyIQ/data/processed/shipments.csv'
INTO TABLE shipments
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- ============================================
-- Sanity check row counts after loading
-- ============================================
SELECT 'categories' AS tbl, COUNT(*) AS rows_count FROM categories
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'shipments', COUNT(*) FROM shipments;