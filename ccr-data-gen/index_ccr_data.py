import os
import random
import datetime
import threading
import signal
import time
from elasticsearch import Elasticsearch, helpers
from dotenv import load_dotenv
from faker import Faker
from queue import Queue

# Load environment variables
load_dotenv()

# Function to get environment variable or raise error if not found
def get_env_var(var_name):
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Environment variable '{var_name}' is not set")
    return value

# Get environment variables
LEADER_CLOUD_ID = os.getenv("LEADER_ELASTIC_CLOUD_ID")
LEADER_USERNAME = get_env_var("LEADER_ELASTIC_USERNAME")
LEADER_PASSWORD = get_env_var("LEADER_ELASTIC_PASSWORD")
LEADER_HOST = os.getenv("LEADER_ELASTIC_HOST")
LEADER_PORT = os.getenv("LEADER_ELASTIC_PORT", "9200")
FOLLOWER_CLOUD_ID = os.getenv("FOLLOWER_ELASTIC_CLOUD_ID")
FOLLOWER_USERNAME = get_env_var("FOLLOWER_ELASTIC_USERNAME")
FOLLOWER_PASSWORD = get_env_var("FOLLOWER_ELASTIC_PASSWORD")
FOLLOWER_HOST = os.getenv("FOLLOWER_ELASTIC_HOST")
FOLLOWER_PORT = os.getenv("FOLLOWER_ELASTIC_PORT", "9200")
INDEX_NAME = get_env_var("INDEX_NAME")
COUNT_INDEX_NAME = os.getenv("COUNT_INDEX_NAME", "test-count-index")
EPS = int(get_env_var("EVENTS_PER_SECOND"))
SCHEME = os.getenv("SCHEME", "https")

# Get environment variables for extra Elasticsearch cluster
EXTRA_CLOUD_ID = os.getenv("EXTRA_ELASTIC_CLOUD_ID")
EXTRA_USERNAME = os.getenv("EXTRA_ELASTIC_USERNAME")
EXTRA_PASSWORD = os.getenv("EXTRA_ELASTIC_PASSWORD")
EXTRA_HOST = os.getenv("EXTRA_ELASTIC_HOST")
EXTRA_PORT = os.getenv("EXTRA_ELASTIC_PORT", "9200")
EXTRA_INDEX_NAME = os.getenv("EXTRA_INDEX_NAME", COUNT_INDEX_NAME)



# Initialize Elasticsearch clients
def create_es_client(cloud_id, username, password, host, port, scheme):
    if cloud_id:
        return Elasticsearch(
            cloud_id=cloud_id,
            basic_auth=(username, password)
        )
    elif host:
        return Elasticsearch(
            hosts=[{"host": host, "port": int(port), "scheme": scheme}],
            basic_auth=(username, password), verify_certs=False, ssl_show_warn=False
        )
    else:
        raise ValueError("Either cloud_id or host must be provided")


es_leader = create_es_client(LEADER_CLOUD_ID, LEADER_USERNAME, LEADER_PASSWORD, LEADER_HOST, LEADER_PORT, SCHEME)
es_follower = create_es_client(FOLLOWER_CLOUD_ID, FOLLOWER_USERNAME, FOLLOWER_PASSWORD, FOLLOWER_HOST, FOLLOWER_PORT, SCHEME)

# Initialize extra Elasticsearch client if provided
es_extra = None
if EXTRA_CLOUD_ID or EXTRA_HOST:
    es_extra = create_es_client(EXTRA_CLOUD_ID, EXTRA_USERNAME, EXTRA_PASSWORD, EXTRA_HOST, EXTRA_PORT, SCHEME)


# Initialize Faker
faker = Faker()

# Define the index settings and mappings
index_settings = {
    "settings": {
        "index": {
            "number_of_replicas": "1",
            "number_of_shards": "2"
        }
    },
    "mappings": {
        "properties": {
            "@timestamp": {
                "type": "date"
            },
            "@version": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "command": {
                "type": "keyword"
            },
            "currcpu": {
                "type": "float"
            },
            "machine": {
                "type": "keyword"
            },
            "meta": {
                "properties": {
                    "aggregate": {
                        "properties": {
                            "count": {
                                "type": "long"
                            },
                            "window": {
                                "properties": {
                                    "begin": {
                                        "type": "date",
                                        "format": "strict_date_time"
                                    },
                                    "duration": {
                                        "type": "integer"
                                    },
                                    "end": {
                                        "type": "date",
                                        "format": "strict_date_time"
                                    }
                                }
                            }
                        }
                    },
                    "count": {
                        "type": "long"
                    },
                    "cpu": {
                        "properties": {
                            "utilization": {
                                "type": "float"
                            },
                            "cores": {
                                "type": "integer"
                            },
                            "timestamp": {
                                "type": "date",
                                "format": "strict_date_time"
                            }
                        }
                    },
                    "memory": {
                        "properties": {
                            "utilization": {
                                "type": "long"
                            },
                            "rss": {
                                "type": "long"
                            },
                            "timestamp": {
                                "type": "date",
                                "format": "strict_date_time"
                            }
                        }
                    }
                }
            },
            "pid": {
                "type": "long"
            },
            "rss": {
                "type": "long"
            }
        }
    }
}

# Define the count index settings and mappings
count_index_settings = {
    "settings": {
        "index": {
            "number_of_replicas": "1",
            "number_of_shards": "1"
        }
    },
    "mappings": {
        "properties": {
            "@timestamp": {
                "type": "date"
            },
            "leader_count": {
                "type": "integer"
            },
            "follower_count": {
                "type": "integer"
            },
            "global_index_lag": {
                "type": "long"
            }
        }
    }
}

# Check if the indices exist, and if not, create them
if not es_leader.indices.exists(index=INDEX_NAME):
    es_leader.indices.create(index=INDEX_NAME, body=index_settings)
    print(f"Index '{INDEX_NAME}' created on leader.")
    print("#################################################################################################")
    print(f"Please create the corresponding follower index ({INDEX_NAME}) in the follower cluster under your Cross-Cluster Replication settings.")
    print(f"Verify that the follower index ({INDEX_NAME}) is in active replication")
    print("#################################################################################################\n\n")
    input("Press Enter to continue after setting up the follower index...")

# Check if the follower index exists and is set up correctly
if not es_follower.indices.exists(index=INDEX_NAME):
    raise ValueError(f"Follower index '{INDEX_NAME}' does not exist on the follower cluster. Please create and set up the follower index for cross-cluster replication.")

# Verify follower index settings
follower_settings = es_follower.ccr.follow_info(index=INDEX_NAME)
if follower_settings['follower_indices'] and follower_settings['follower_indices'][0]['follower_index'] == INDEX_NAME:
    print(f"Follower index {follower_settings['follower_indices'][0]['follower_index']} following leader index {follower_settings['follower_indices'][0]['leader_index']}")
else:
    raise ValueError(f"Follower index '{INDEX_NAME}' is not correctly set up for cross-cluster replication. Please ensure the index is configured with the correct tier preference.")

print(f"Follower index '{INDEX_NAME}' is correctly set up.")

# Setup count_index in follower cluster
if not es_follower.indices.exists(index=COUNT_INDEX_NAME):
    es_follower.indices.create(index=COUNT_INDEX_NAME, body=count_index_settings)
    print(f"Index '{COUNT_INDEX_NAME}' created.")

# Initialize threading event for graceful shutdown
shutdown_event = threading.Event()

# Generate sample document based on the provided mapping
def generate_document(timestamp):
    date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    document = {
        "@timestamp": timestamp.strftime(date_format),
        "@version": "1",
        "command": faker.word(),
        "currcpu": round(random.uniform(0.0, 100.0), 2),
        "machine": faker.hostname(),
        "meta": {
            "aggregate": {
                "count": random.randint(1, 1000),
                "window": {
                    "begin": timestamp.strftime(date_format),
                    "duration": random.randint(1, 3600),
                    "end": (timestamp + datetime.timedelta(seconds=random.randint(1, 3600))).strftime(date_format)
                }
            },
            "count": random.randint(1, 1000),
            "cpu": {
                "utilization": round(random.uniform(0.0, 100.0), 2),
                "cores": random.randint(0, 10),
                "timestamp": timestamp.strftime(date_format),
                "topic": faker.word()
            },
            "memory": {
                "utilization": random.randint(1, 10000),
                "rss": faker.random_number(digits=7),
                "timestamp": timestamp.strftime(date_format)
            }
        },
        "pid": random.randint(1, 65535),
        "rss": random.randint(1, 1000000)
    }
    return document

# Function for indexing data for a specific day
def index_data_for_day(day):
    total_events = EPS * 86400  # Total events for the day
    start_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=day)
    end_date = start_date + datetime.timedelta(days=1)

    actions = []
    for _ in range(total_events):
        if shutdown_event.is_set():
            break
        random_second = random.randint(0, 86400 - 1)
        event_timestamp = start_date + datetime.timedelta(seconds=random_second)
        document = generate_document(event_timestamp)
        action = {
            "_index": INDEX_NAME,
            "_source": document
        }
        actions.append(action)
        if len(actions) >= 1000:  # Bulk insert every 1000 documents
            try:
                helpers.bulk(es_leader, actions)
            except helpers.BulkIndexError as e:
                print(f"Leader bulk index error: {e.errors}")
            actions = []

    if actions:
        try:
            helpers.bulk(es_leader, actions)
        except helpers.BulkIndexError as e:
            print(f"Leader bulk index error: {e.errors}")

# Index real-time data
def index_realtime_data():
    while not shutdown_event.is_set():
        current_timestamp = datetime.datetime.now(datetime.timezone.utc)
        actions = []
        for _ in range(EPS):
            if shutdown_event.is_set():
                break
            document = generate_document(current_timestamp)
            action = {
                "_index": INDEX_NAME,
                "_source": document
            }
            actions.append(action)
        if actions:
            try:
                helpers.bulk(es_leader, actions)
            except helpers.BulkIndexError as e:
                print(f"Leader bulk index error: {e.errors}")

# Thread worker function
def thread_worker(queue):
    while not queue.empty():
        if shutdown_event.is_set():
            break
        day = queue.get()
        index_data_for_day(day)
        queue.task_done()

# Index historical data with threads based on the number of processors
def index_historical_data():
    num_threads = os.cpu_count()
    queue = Queue()

    # Enqueue days from 1 to 30
    for day in range(1, 31):
        queue.put(day)

    # Create and start threads
    threads = []
    for _ in range(num_threads):
        thread = threading.Thread(target=thread_worker, args=(queue,))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

# Function to query and log the counts
def query_and_log_counts():
    while not shutdown_event.is_set():
        # Get the current timestamp in ISO format
        current_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Query the document count from the follower index
        follower_count = es_follower.count(index=INDEX_NAME)['count']

        # Get CCR stats from follower
        es_follower_stats = es_follower.ccr.stats()
        global_lag = -1
        if es_follower_stats['follow_stats']['indices']:
            idx = next((i for i, d in enumerate(es_follower_stats['follow_stats']['indices']) 
                        if any(INDEX_NAME in str(value) for value in d.values())))
            if idx is not None:
                global_lag = es_follower_stats['follow_stats']['indices'][idx]['total_global_checkpoint_lag']

        # Query the document count from the leader index
        leader_count = es_leader.count(index=INDEX_NAME)['count']

        # Prepare the log document
        log_document = {
            "@timestamp": current_timestamp,
            "leader_count": leader_count,
            "follower_count": follower_count,
            "global_index_lag": global_lag
        }

        # Index the log document into the count index
        es_follower.index(index=COUNT_INDEX_NAME, document=log_document)

        # Optionally index the log document into the extra cluster if provided
        if es_extra:
            es_extra.index(index=EXTRA_INDEX_NAME, document=log_document)
        # Print the counts to the console (optional)
        print(f"{current_timestamp} - Leader Count: {leader_count}, Follower Count: {follower_count}, Lag ops:  {global_lag}")

        # Sleep for a specified interval before querying again
        time.sleep(15)

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    print('Received Ctrl-C, shutting down...')
    shutdown_event.set()

# Register signal handler
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    # Create and start historical data indexing thread
    historical_thread = threading.Thread(target=index_historical_data)
    historical_thread.start()

    # Create and start real-time data indexing thread
    realtime_thread = threading.Thread(target=index_realtime_data)
    realtime_thread.start()

    # Create and start the query and log thread
    query_log_thread = threading.Thread(target=query_and_log_counts)
    query_log_thread.start()

    # Wait for historical thread to complete
    historical_thread.join()

    # Keep the real-time and query log threads running
    realtime_thread.join()
    query_log_thread.join()
