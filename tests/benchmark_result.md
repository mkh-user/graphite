# Graphite Benchmark Report

## System Configuration

- Python: 3.12
- OS: Windows 11 24H2
- CPU: Intel(R) Core(TM) i5-10210U CPU @ 1.60GHz
- RAM: 32/0 GB, 2667 MT/s
- Storage: SSD

## Test Parameters

- Size factor: 100,000 nodes, 50,000 relations
- Runs: 10
- Warm cache: Yes

## Result

- Memory overhead: 119.0 MB (total: 124,831,064 B, per node: 1,248 B)

| Metric                                                |     Avg     |     Min     |     Max     |    StDev    |
|:------------------------------------------------------|:-----------:|:-----------:|:-----------:|:-----------:|
| dsl_parse(7503 lines)                                 |  62.226 ms  |  61.091 ms  |  63.228 ms  |  0.759 ms   |
| get_node(n: 100.0K)                                   |  0.005 ms   |  0.004 ms   |  0.006 ms   |  0.001 ms   |
| get_nodes_of_type(n: 100.0K, with subtypes)           |  10.549 ms  |  10.002 ms  |  11.283 ms  |  0.378 ms   |
| node_creation(n: 100.0K)                              | 683.150 ms  | 669.467 ms  | 703.855 ms  |  10.930 ms  |
| query_avg(n: 100)                                     |  0.092 ms   |  0.079 ms   |  0.166 ms   |  0.026 ms   |
| query_both(n: 100.0K, typed)                          | 182.928 ms  | 180.651 ms  | 185.288 ms  |  1.722 ms   |
| query_count(n: 100)                                   |  0.004 ms   |  0.003 ms   |  0.004 ms   |  0.000 ms   |
| query_exclude(n: 20.1K)                               |  1.611 ms   |  1.473 ms   |  2.359 ms   |  0.265 ms   |
| query_get_relations_from(n: 100.0K)                   |  0.007 ms   |  0.005 ms   |  0.009 ms   |  0.001 ms   |
| query_get_relations_to(n: 100.0K)                     |  0.007 ms   |  0.007 ms   |  0.009 ms   |  0.001 ms   |
| query_group_by(n: 100)                                |  0.070 ms   |  0.058 ms   |  0.155 ms   |  0.030 ms   |
| query_incoming(n: 100.0K, typed)                      | 122.587 ms  | 109.638 ms  | 227.114 ms  |  36.748 ms  |
| query_intersect(n: 20.1K)                             |  5.381 ms   |  4.692 ms   |  6.940 ms   |  0.613 ms   |
| query_max(n: 100)                                     |  0.098 ms   |  0.093 ms   |  0.108 ms   |  0.006 ms   |
| query_min(n: 100)                                     |  0.131 ms   |  0.104 ms   |  0.204 ms   |  0.035 ms   |
| query_order_by(n: 100)                                |  0.073 ms   |  0.067 ms   |  0.097 ms   |  0.009 ms   |
| query_outgoing(n: 100.0K, typed)                      | 118.769 ms  | 106.039 ms  | 210.549 ms  |  32.293 ms  |
| query_remove_node(n: 100)                             |  36.600 ms  |  35.747 ms  |  37.926 ms  |  0.722 ms   |
| query_set(n: 100)                                     |  0.057 ms   |  0.055 ms   |  0.065 ms   |  0.003 ms   |
| query_sum(n: 100)                                     |  0.071 ms   |  0.058 ms   |  0.097 ms   |  0.016 ms   |
| query_union(n: 20.1K)                                 |  6.226 ms   |  5.853 ms   |  6.991 ms   |  0.409 ms   |
| query_validate(n: 20.0K)                              |  28.335 ms  |  27.517 ms  |  29.526 ms  |  0.701 ms   |
| query_where_lambda(n: 100.0K)                         |  60.840 ms  |  60.032 ms  |  62.313 ms  |  0.631 ms   |
| query_where_string(n: 100.0K)                         |  63.303 ms  |  61.900 ms  |  64.757 ms  |  0.929 ms   |
| relation_creation(r: 100.0K)                          | 531.875 ms  | 456.695 ms  | 626.298 ms  |  52.348 ms  |
| schema_define_node_types(nt: 5)                       |  0.059 ms   |  0.047 ms   |  0.082 ms   |  0.012 ms   |
| schema_define_relation_types (rt: 2)                  |  0.057 ms   |  0.038 ms   |  0.114 ms   |  0.026 ms   |
| serialization_load(n: 100.0K, r: 50.0K, unsafe mode)  | 847.646 ms  | 841.883 ms  | 854.023 ms  |  3.453 ms   |
| serialization_load(n: 100.0K, r: 50.0K, validate off) | 854.516 ms  | 846.302 ms  | 884.937 ms  |  11.545 ms  |
| serialization_load(n: 100.0K, r: 50.0K, validate on)  | 985.792 ms  | 851.355 ms  | 1714.460 ms | 288.975 ms  |
| serialization_save(n: 100.0K, r: 50.0K)               | 5416.604 ms | 4372.291 ms | 7434.451 ms | 1202.704 ms |
