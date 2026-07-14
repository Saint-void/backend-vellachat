# app/knowledge/sweep_cli.py
"""Scheduled sweep for stuck knowledge-processing jobs.
Run from a Render Cron Job, not from an HTTP route:
    python -m app.knowledge.sweep_cli
"""

import asyncio

from app.knowledge.tasks import sweep_stuck_documents


async def main() -> None:
    count = await sweep_stuck_documents()
    print(f"Swept {count} stuck knowledge documents")


if __name__ == "__main__":
    asyncio.run(main())