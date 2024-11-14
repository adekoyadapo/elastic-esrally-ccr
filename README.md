# ESrally for CCR benchmarking

This project is designed to generate and index random data into an Elasticsearch Leader index and then verify replication in a Follower index whilst also leveraging ESRALLY to write and run searches against either the leader or follower cluster and offload the results to a designated cluster for review.

The script located in [ccr-data-gen](./ccr-data-gen) supports both Elastic Cloud and self-managed clusters, review the [README](./ccr-data-gen/README.md) for usage and more information

The Esrally track t located in [ccr-data-gen](./cutom-track) supports both Elastic Cloud and self-managed clusters.

## Prerequisites

- Python 3.x
- Elasticsearch 8.x
- Virtual Environment (recommended)
- docker

## Usage

- Copy the rally.ini_example to rally.ini
- Update the section of the file with the details of the cluster to write the rally data to if reports is needed for futher review

```
[reporting]
datastore.type = elasticsearch
datastore.host = localhost
datastore.port = 9200
datastore.secure = True
datastore.user = elastic
datastore.password = somepassword
``` 

## Track information

This ESRally track is designed to benchmark the performance of an Elasticsearch index for employee data using various queries and operations. It tests the system’s ability to handle different scales of operations, categorized into small, medium, and large tests:

- Small Scale: Use fewer clients (default 10) and moderate bulk size (default 200) for indexing operations. Focus on simple queries like match_all and term queries, with moderate throughput (default 500).
- Medium Scale: Similar to small scale, but you may increase the number of clients and bulk size slightly to simulate more load.
- Large Scale: Requires scaling up bulk indexing clients and target throughput significantly to stress test the system under heavy load. Also includes more complex queries like range and multi_match to evaluate how the system handles advanced search scenarios.

## Parameters information

- Clients: Number of parallel operations for all tasks.
- Bulk size: Number of documents indexed in each batch.
- Target throughput: Desired operations per second for testing.
- bulk_indexing_clients: Parallel clients handling bulk indexing operations.
- raw_data_volume_per_day: Simulates daily data ingestion volume.
- data_index_clients: Parallel clients for general data indexing.

## Usage

1. Generate the employee data.

```
cd custom-track/employee-track
python generate.py --filename employee.json --num-employees 1000000
```

2. Update the [`track.json`](./custom-track/employee-track/track.json) with the number of employees generated

3. Run the command in a dockerized setup and adjust the track parameters to suite the test scale

```bash
docker run --platform=linux/amd64 --rm \
  -v $(pwd)/custom-track:/rally/tracks/custom \
  -v $(pwd)/rally.ini:/rally/.rally/rally.ini \ # to load the tweaked rally ini file
  elastic/rally race --pipeline=benchmark-only \
  --track-path=/rally/tracks/custom/employee-track \ # load employee track
  --target-hosts=http://localhost:9200 \
  --client-options="use_ssl:true,verify_certs:true,basic_auth_user:'elastic',basic_auth_password:'somepassword'" \
  --track-params="data_generation_clients:10,iterations:100,warmup_iterations:10,target_throughput:500,raw_data_volume_per_day:100GB,bulk_indexing_clients:500,data_index_clients:10"
```

## Example Recommendations

### Bulk_indexing_clients

This controls the number of parallel clients specifically for bulk indexing operations, determining how many concurrent index requests are processed.

- Small Scale: 5-10: Lower client numbers to simulate light indexing activity, focusing on basic performance.
- Medium Scale: 20-30: A moderate number of clients, testing Elasticsearch’s ability to handle a higher level of indexing activity.
- Large Scale: 50+: High client numbers for bulk indexing, putting the system under significant load to test its limits.

### raw_data_volume_per_day

This simulates the amount of data ingested per day, useful for testing how well Elasticsearch handles large datasets over time.

- Small Scale: 1GB-10GB: Simulates light daily ingestion to test Elasticsearch in a controlled environment.
- Medium Scale: 50GB-100GB: Simulates medium data ingestion rates, useful for real-world scenarios where more data is indexed daily.
- Large Scale: 500GB+: Simulates high-volume data ingestion, stress-testing Elasticsearch’s capacity to handle very large datasets efficiently.

### data_index_clients

These clients control the number of parallel operations for data indexing, similar to bulk_indexing_clients but used in the overall data index process.

- Small Scale: 5-10: Simulates light parallel activity during the data indexing process.
- Medium Scale: 15-25: More clients are used to increase the load on the system and test moderate indexing throughput.
- Large Scale: 50+: Tests maximum parallel indexing activity, challenging Elasticsearch to handle simultaneous heavy load.