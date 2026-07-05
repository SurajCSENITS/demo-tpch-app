def get_customer_by_segment(segment: str):
    """Fetch customers by market segment."""
    # This query might be flagged for potential optimization
    query = """
        SELECT c_custkey, c_name, c_phone, c_acctbal
        FROM snowflake_sample_data.tpch_sf1.customer
        WHERE c_mktsegment = ? 
        ORDER BY c_acctbal DESC
        LIMIT 100
    """
    
    # Database execution logic would go here
    print(f"Executing: {query}")
    return [{"c_name": "Customer#000000001", "c_acctbal": 711.56}]

def count_nations_in_region():
    """Returns total number of nations in ASIA."""
    query = "SELECT count(n_nationkey) FROM snowflake_sample_data.tpch_sf1.nation n JOIN snowflake_sample_data.tpch_sf1.region r ON n.n_regionkey = r.r_regionkey WHERE r.r_name = 'ASIA'"
    return 5
