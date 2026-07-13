-- Query 1: Minimum Cost Supplier
SELECT s.s_acctbal, s.s_name, n.n_name, p.p_partkey, p.p_mfgr, s.s_address, s.s_phone, s.s_comment
FROM snowflake_sample_data.tpch_sf1.part p
JOIN snowflake_sample_data.tpch_sf1.partsupp ps ON p.p_partkey = ps.ps_partkey
JOIN snowflake_sample_data.tpch_sf1.supplier s ON s.s_suppkey = ps.ps_suppkey
JOIN snowflake_sample_data.tpch_sf1.nation n ON s.s_nationkey = n.n_nationkey
JOIN snowflake_sample_data.tpch_sf1.region r ON n.n_regionkey = r.r_regionkey
WHERE p.p_size = 15 AND p.p_type LIKE '%BRASS' AND r.r_name = 'EUROPE';

-- Query 2: Shipping Priority Query (Target for optimization, implicit cross-joins)
SELECT
    l.l_orderkey,
    SUM(l.l_extendedprice * (1 - l.l_discount)) as revenue,
    o.o_orderdate,
    o.o_shippriority
FROM
    snowflake_sample_data.tpch_sf1.customer c,
    snowflake_sample_data.tpch_sf1.orders o,
    snowflake_sample_data.tpch_sf1.lineitem l
WHERE
    c.c_mktsegment = 'BUILDING'
    AND c.c_custkey = o.o_custkey
    AND l.l_orderkey = o.o_orderkey
    AND o.o_orderdate < '1995-03-15'
    AND l.l_shipdate > '1995-03-15'
GROUP BY
    l.l_orderkey,
    o.o_orderdate,
    o.o_shippriority
ORDER BY
    revenue DESC,
    o.o_orderdate;

-- Query 3: Order Priority Checking
SELECT o_orderpriority, COUNT(*) as order_count
FROM snowflake_sample_data.tpch_sf1.orders
WHERE o_orderdate >= '1993-07-01' AND o_orderdate < '1993-10-01'
GROUP BY o_orderpriority
ORDER BY o_orderpriority;





-- Query 4: Using SELECT * with a function on a column in WHERE (prevents pruning)
SELECT *
FROM MALL_CUSTOMERS
WHERE CAST(AGE AS VARCHAR) LIKE '3%'
ORDER BY TO_VARCHAR(ANNUAL_INCOME_K) || ' thousand';

-- Query 5: Correlated subquery that re-scans the table for every row
SELECT
    CUSTOMER_ID,
    GENRE,
    AGE,
    ANNUAL_INCOME_K,
    SPENDING_SCORE,
    (SELECT AVG(SPENDING_SCORE) FROM MALL_CUSTOMERS WHERE GENRE = m.GENRE) AS AVG_GENRE_SCORE,
    (SELECT MAX(ANNUAL_INCOME_K) FROM MALL_CUSTOMERS WHERE AGE = m.AGE) AS MAX_INCOME_SAME_AGE,
    (SELECT COUNT(*) FROM MALL_CUSTOMERS WHERE ANNUAL_INCOME_K > m.ANNUAL_INCOME_K) AS RANK_BY_INCOME
FROM MALL_CUSTOMERS m
ORDER BY RANK_BY_INCOME;

-- Query 6: DISTINCT on large result set instead of proper GROUP BY
SELECT DISTINCT
    C_NAME,
    C_NATIONKEY,
    O_ORDERSTATUS
FROM CUSTOMER, ORDERS
WHERE CUSTOMER.C_CUSTKEY = ORDERS.O_CUSTKEY;

-- Query 7: Function on filter column prevents pruning/pushdown
SELECT L_ORDERKEY, L_QUANTITY, L_EXTENDEDPRICE FROM LINEITEM WHERE L_SHIPDATE BETWEEN '1995-03-01' AND '1995-03-31';

-- Query 8: NOT IN with subquery (poor performance vs NOT EXISTS/anti-join)
SELECT
    P_PARTKEY,
    P_NAME,
    P_RETAILPRICE
FROM PART
WHERE P_PARTKEY NOT IN (
    SELECT L_PARTKEY
    FROM LINEITEM
    WHERE L_RETURNFLAG = 'R'
);