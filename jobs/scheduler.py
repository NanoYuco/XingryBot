from jobs.patrol import schedule_initial_patrol
from jobs.weekly_report import schedule_next_weekly_report


def register_jobs(job_queue) -> None:
    """Register the first run of every background job."""
    schedule_initial_patrol(job_queue)
    schedule_next_weekly_report(job_queue)
