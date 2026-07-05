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
