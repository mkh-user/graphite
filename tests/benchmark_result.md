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

- Memory overhead: 124.8 MB (total: 130,895,024 B, per node: 1,309 B)

| Metric                                             |     Avg     |     Min     |     Max     |    StDev    | Change |
|:---------------------------------------------------|:-----------:|:-----------:|:-----------:|:-----------:|:------:|
| dsl_parse(7503 lines)                              |  61.964 ms  |  58.601 ms  |  76.801 ms  |  5.418 ms   | +19.2% |
| get_node(n: 100K)                                  |  0.006 ms   |  0.006 ms   |  0.007 ms   |  0.001 ms   |  +0%   |
| get_nodes_of_type(n: 100K, with subtypes)          |  15.468 ms  |  12.919 ms  |  16.516 ms  |  1.041 ms   | +7.4%  |
| node_creation(n: 100K)                             | 301.740 ms  | 288.730 ms  | 333.709 ms  |  13.755 ms  | -85.6% |
| query_avg(n: 100)                                  |  0.098 ms   |  0.091 ms   |  0.115 ms   |  0.007 ms   | +3.9%  |
| query_both(n: 100K, typed)                         | 195.034 ms  | 189.477 ms  | 204.606 ms  |  4.764 ms   |  +0%   |
| query_count(n: 100)                                |  0.004 ms   |  0.003 ms   |  0.006 ms   |  0.001 ms   |  -20%  |
| query_exclude(n: 100 + 20K)                        |  1.912 ms   |  1.724 ms   |  2.304 ms   |  0.172 ms   | +7.2%  |
| query_get_relations_from(n: 100K)                  |  0.011 ms   |  0.008 ms   |  0.023 ms   |  0.004 ms   | +62.5% |
| query_get_relations_to(n: 100K)                    |  0.010 ms   |  0.008 ms   |  0.014 ms   |  0.002 ms   |  +0%   |
| query_group_by(n: 100)                             |  0.069 ms   |  0.065 ms   |  0.074 ms   |  0.003 ms   | +13.4% |
| query_incoming(n: 100K, typed)                     | 135.086 ms  | 117.255 ms  | 267.652 ms  |  46.798 ms  |  +0%   |
| query_intersect(n: 100 + 20K)                      |  5.790 ms   |  5.234 ms   |  6.805 ms   |  0.540 ms   | +5.4%  |
| query_max(n: 100)                                  |  0.129 ms   |  0.099 ms   |  0.196 ms   |  0.040 ms   | +5.1%  |
| query_min(n: 100)                                  |  0.111 ms   |  0.101 ms   |  0.127 ms   |  0.008 ms   | -6.9%  |
| query_order_by(n: 100)                             |  0.081 ms   |  0.073 ms   |  0.090 ms   |  0.005 ms   | -2.2%  |
| query_outgoing(n: 100K, typed)                     | 131.143 ms  | 115.709 ms  | 241.468 ms  |  38.826 ms  | -12.8% |
| query_remove_node(n: 100)                          |  43.450 ms  |  40.624 ms  |  53.300 ms  |  4.201 ms   | +167%  |
| query_set(n: 100)                                  |  0.072 ms   |  0.065 ms   |  0.085 ms   |  0.007 ms   | -1.4%  |
| query_sum(n: 100)                                  |  0.075 ms   |  0.067 ms   |  0.107 ms   |  0.012 ms   | +8.2%  |
| query_union(n: 100 + 20K)                          |  7.327 ms   |  6.687 ms   |  9.985 ms   |  0.955 ms   | +11.3% |
| query_validate(n: 20K)                             |  33.920 ms  |  31.080 ms  |  45.623 ms  |  4.230 ms   |  +0%   |
| query_where_lambda(n: 100K)                        |  78.284 ms  |  67.698 ms  |  82.306 ms  |  4.643 ms   | +36.7% |
| query_where_string(n: 100K)                        |  78.466 ms  |  67.983 ms  |  83.883 ms  |  5.069 ms   | -60.6% |
| relation_creation(r: 100K)                         | 438.663 ms  | 423.957 ms  | 457.225 ms  |  11.702 ms  | -18.2% |
| schema_define_node_types(nt: 10K)                  |  67.347 ms  |  54.461 ms  |  87.304 ms  |  11.304 ms  | +27.2% |
| schema_define_relation_types (rt: 5K)              |  20.182 ms  |  19.462 ms  |  20.852 ms  |  0.418 ms   | +1.0%  |
| serialization_load(n: 100K, r: 50K, unsafe mode)   | 791.404 ms  | 776.707 ms  | 804.799 ms  |  8.502 ms   | +0.8%  |
| serialization_load(n: 100K, r: 50K, validate off)  | 802.408 ms  | 787.580 ms  | 822.288 ms  |  11.478 ms  | -21.1% |
| serialization_load(n: 100K, r: 50K, validate on)   | 804.917 ms  | 778.111 ms  | 819.606 ms  |  12.180 ms  | -21.4% |
| serialization_save(n: 100K, r: 50K)                | 3513.375 ms | 3412.588 ms | 3663.904 ms |  84.831 ms  | -28.9% |

## Summary

- Faster: 10
- Fixed: 9
- Slower: 9
