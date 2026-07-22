SELECT o.o_orderkey, o.o_custkey, o.o_orderdate, c.c_custkey, c.c_name FROM ORDERS o JOIN CUSTOMER c ON o.o_custkey = c.c_custkey WHERE o.o_orderdate >= '1995-01-01' AND o.o_orderdate < '1996-01-01'
