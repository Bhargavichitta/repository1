import time
import google.auth
from googleapiclient import discovery
from google.cloud import monitoring_v3
from datetime import datetime, timedelta, timezone

# CONFIGURATION
PROJECT_ID = 'your-gcp-project-id'
ZONE = 'your-vm-zone'  # e.g. 'us-central1-a'
INSTANCE_NAME = 'your-instance-name'
IDLE_CPU_THRESHOLD = 0.05  # 5% CPU
IDLE_DURATION_MINUTES = 5

# AUTH
credentials, _ = google.auth.default()
compute = discovery.build('compute', 'v1', credentials=credentials)
monitoring_client = monitoring_v3.MetricServiceClient()
instance_id_path = f"projects/{PROJECT_ID}"

def is_instance_idle():
    now = datetime.now(timezone.utc)
    interval = monitoring_v3.TimeInterval(
        end_time=now,
        start_time=now - timedelta(minutes=IDLE_DURATION_MINUTES)
    )

    aggregation = monitoring_v3.Aggregation(
        alignment_period={"seconds": 60},
        per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
        cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_MEAN,
        group_by_fields=["resource.label.instance_id"]
    )

    results = monitoring_client.list_time_series(
        request={
            "name": instance_id_path,
            "filter": f'metric.type="compute.googleapis.com/instance/cpu/utilization" AND '
                      f'resource.labels.instance_id="{get_instance_id()}"',
            "interval": interval,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            "aggregation": aggregation,
        }
    )

    for result in results:
        points = result.points
        if points:
            avg_cpu = sum(point.value.double_value for point in points) / len(points)
            print(f"[INFO] Average CPU usage over {IDLE_DURATION_MINUTES} min: {avg_cpu:.4f}")
            return avg_cpu < IDLE_CPU_THRESHOLD

    print("[WARN] No monitoring data found.")
    return False

def get_instance_id():
    # Get instance metadata
    import requests
    metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/id"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(metadata_url, headers=headers)
    return response.text.strip()

def stop_instance():
    print(f"[ACTION] Stopping instance: {INSTANCE_NAME}")
    compute.instances().stop(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME).execute()

def main():
    print("[CHECK] Checking if instance is idle...")
    if is_instance_idle():
        stop_instance()
    else:
        print("[INFO] Instance is active. No action taken.")

if __name__ == "__main__":
    main()

