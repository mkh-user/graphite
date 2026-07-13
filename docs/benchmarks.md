# Graphite Benchmarks

Graphite uses a benchmark suite to observe performance. You can run this suite yourself to test database performance on
you hardware.

## Official Benchmark Results

The latest version of results is always available at [Source Code Benchmark Result File](https://github.com/mkh-user/graphite/blob/main/tests/benchmark_result.md).
This is result of 10 runs on 100K-nodes database, more information about benchmarking environment and size can be found
in that page. Also, an archive of bigger benchmarks is available at [GitHub Wiki](https://github.com/mkh-user/graphite/wiki).

## Benchmark Suite

Graphite tests include a CLI that can be used to run customized benchmarks, here is an example of running `--help` on it:
```shell
>>> python benchmark.py --help
Source of Graphite found, using latest dev version
                                                                                                                                             
 Usage: benchmark.py [OPTIONS]                                                                                                               
                                                                                                                                             
 Advanced benchmark suite for Graphite embedded graph database

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --size                                                 INTEGER  Database size (nodes) [default: 100000]            │
│ --runs                                                 INTEGER  Runs to benchmark [default: 10]                    │
│ --node-types                                           INTEGER  Number of node types [default: 5]                  │
│ --relation-types                                       INTEGER  Number of relation types [default: 3]              │
│ --relations-ratio                                      FLOAT    Relation ratio [default: 0.5]                      │
│ --inheritance-depth                                    INTEGER  Inheritance depth on node types [default: 1]       │
│ --json                                                          Output to JSON instead of table                    │
│ --run-all                 --no-run-all                          Run all benchmarks [default: run-all]              │
│ --on-schema               --no-on-schema                        Benchmark node type and relation type definitions  │
│ --on-node-creation        --no-on-node-creation                 Benchmark node creation                            │
│ --on-relation-creation    --no-on-relation-creation             Benchmark relation creation                        │
│ --on-queries              --no-on-queries                       Benchmark queries                                  │
│ --on-serialization        --no-on-serialization                 Benchmark save and load                            │
│ --on-dsl-parse            --no-on-dsl-parse                     Benchmark a complete DSL parsing                   │
│ --on-memory               --no-on-memory                        Benchmark memory usage                             │
│ --help                                                          Show this message and exit.                        │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

It can be used to run benchmark in custom scale and runs on selected sections and to get JSON result. While running
benchmarks progress bars will show elapsed and estimated time and current running benchmark information:
```shell
Running 7 benchmarks: on_schema, on_node_creation, on_relation_creation, on_queries, on_serialization, on_dsl_parse, on_memory
Running benchmarks:  14%|████████████▏                                                                        | 1/7 [00:00<00:00,  7.51it/s]
Benchmark: Node Creation:   0%|                                                                                       | 0/1 [00:00<?, ?it/s]
Running create_many_nodes:  10%|███████▋                                                                     | 1/10 [00:04<00:44,  4.90s/it]
Creating nodes:  54%|███████████████████████████████████████▉                                  | 539073/1000000 [00:02<00:01, 288488.92it/s]
```

## Run Benchmarks Yourself

You may want to run a new benchmark to validate results on your target platform or server or on special scale. Graphite
benchmark suite provides a complete CLI to you to run benchmarks with complete information. We will explain how you can
run a custom benchmark now:

### Benchmark installed version of Graphite

When you have an installed version of Graphite on your Python or virtual environment, you can benchmark it directly.

1. Install Dependencies: Run this command to install graphite and benchmark suite dependencies:
    ```shell
    pip install "graphitedb[benchmark]"
    ```
2. Download Benchmark Suite: Go to [this page](https://github.com/mkh-user/graphite/blob/main/tests/benchmark.py) and
   download showed `benchmark.py` file.
3. Open Terminal in where you downloaded benchmark code.
4. Run this command to see available options:
    ```shell
    python benchmark.py --help
    ```
5. For example, you can run a fast benchmark (10 runs of 10K nodes, takes about 10 seconds) with this command:
    ```shell
    python benchmark.py --size 10000 --runs 10
    ```

### Benchmark Graphite source code

You can use source code to benchmark Graphite.

1. Get source code: Download source code zip from GitHub or clone it with Git.
2. Install dependencies: Open project folder in terminal and run one of these commands:
    ```shell
    # Install Graphite with benchmark dependencies to your Python
    pip install ".[benchmark]"
    ```
3. Change directory to `tests/`:
    ```shell
    cd tests
    ```
4. Run this command to see available options:
    ```shell
    python benchmark.py --help
    ```
5. For example, you can run a fast benchmark (10 runs of 10K nodes, takes about 10 seconds) with this command:
    ```shell
    python benchmark.py --size 10000 --runs 10
    ```
