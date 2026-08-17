from jobs.patrol import scheduled_check_job
from jobs.weekly_report import schedule_next_weekly_report


def register_jobs(job_queue) -> None:
    """Register the first run of every background job."""
    job_queue.run_once(scheduled_check_job, when=10)
    schedule_next_weekly_report(job_queue)
