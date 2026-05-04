"""
Two-stage parallel enrichment pipeline.

Stage 1 (fetch_pool):   N_FETCH workers fetch job pages concurrently.
Stage 2 (enrich_pool):  N_ENRICH workers consume from a queue and call the LLM.

The two stages run simultaneously — while enrichers are waiting on the LLM,
fetchers are already pulling the next batch of pages. Neither pool blocks the other.

                   ┌──────────────┐       queue.Queue       ┌───────────────┐
  records ──────►  │  fetch_pool  │  ──── (idx, page) ──►   │  enrich_pool  │  ──► out[]
  (N targets)      │  N_FETCH=8   │                         │  N_ENRICH=4   │
                   └──────────────┘                         └───────────────┘
"""
from __future__ import annotations

import json
import logging
import queue
import sys
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError, as_completed
from pathlib import Path
from typing import Any

from .colors import bold, bright_green, bright_red, bright_white, counter, cyan, dim, err, eta, header, label, ok, sep, tag, warn, yellow
from .enrichment_worker import EnrichConfig, EnrichWorker, _DEFAULT_CFG, _attach_error, azure_configured

logger = logging.getLogger(__name__)

_SENTINEL = object()  # poison-pill to shut down enrich workers

# ---------------------------------------------------------------------------
# Progress tracker — thread-safe live output
# ---------------------------------------------------------------------------

class _ProgressTracker:
    """Thread-safe progress printer for the enrichment pipeline.

    Prints one line per completed record and a periodic stats banner every
    ``_BANNER_EVERY`` records so you can always see where the run stands.
    """

    _BANNER_EVERY = 50

    def __init__(
        self,
        total: int,
        fetch_workers: int,
        enrich_workers: int,
        live_stream_path: str = "",
    ) -> None:
        self._lock = threading.Lock()
        self._total = total
        self._width = len(str(total))
        self._done = 0
        self._enriched = 0
        self._weak = 0
        self._failed = 0
        self._playwright = 0
        self._start = time.monotonic()
        self._stream_path = live_stream_path.strip()
        # Truncate the live stream file at the start of each run so it only
        # contains results from this session.
        if self._stream_path:
            Path(self._stream_path).write_text("", encoding="utf-8")
        self._print_header(fetch_workers, enrich_workers)

    def _print_header(self, fetch_workers: int, enrich_workers: int) -> None:
        print(
            f"\n{header(f'Enriching {self._total:,} records')}  "
            f"{dim(f'[fetch={fetch_workers}  llm={enrich_workers}]')}",
            flush=True,
        )
        print(sep("─" * 72), flush=True)

    def report(
        self,
        record: dict[str, Any],
        page: dict[str, Any],
        enriched: dict[str, Any],
    ) -> None:
        """Called by each enrich worker after it finishes a record."""
        with self._lock:
            self._done += 1
            n = self._done

            # Classify the outcome.
            raw = enriched.get("raw_listing") or {}
            enrich_err = raw.get("enrichment_error", "") if isinstance(raw, dict) else ""
            has_content = bool(enriched.get("keywords") or enriched.get("required_skills"))
            fetch_method = page.get("_fetch_method", "http")

            if enrich_err:
                self._failed += 1
                if "page_fetch_error" in enrich_err or "playwright_error" in enrich_err:
                    status_str = err(f"✗  page blocked  {dim('(' + enrich_err.split(':')[0] + ')')}")
                else:
                    status_str = err(f"✗  llm failed    {dim('(' + enrich_err[:40] + ')')}")
            elif has_content:
                conf = enriched.get("confidence", "")
                if conf == "high":
                    self._enriched += 1
                    status_str = ok("✓  enriched")
                else:
                    self._weak += 1
                    status_str = warn(f"~  enriched  {dim('(conf=' + (conf or '?') + ')')}")
            else:
                self._weak += 1
                status_str = warn("~  no content extracted")

            if fetch_method == "playwright":
                self._playwright += 1
                method_tag = "  " + tag("[pw]")
            else:
                method_tag = ""

            # Build a compact label: "Company — Job Title"
            company = (record.get("company") or "?")[:20]
            title_str = (record.get("job_title") or "?")[:34]
            record_label = label(f"{company} — {title_str}")

            # ETA estimate
            elapsed = time.monotonic() - self._start
            rate = n / elapsed if elapsed > 0 else 0
            remaining = self._total - n
            if rate > 0 and remaining > 0:
                eta_s = remaining / rate
                eta_str = eta(f"ETA ~{int(eta_s // 60)}m{int(eta_s % 60):02d}s")
            else:
                eta_str = eta("ETA --")

            print(
                f"  {counter(f'[{n:{self._width}}/{self._total}]')} "
                f"{record_label:<56} "
                f"{status_str}{method_tag}  {eta_str}",
                flush=True,
            )

            # Stream completed record to live file for real-time inspection.
            if self._stream_path:
                try:
                    with open(self._stream_path, "a", encoding="utf-8") as sf:
                        sf.write(json.dumps(enriched, ensure_ascii=False) + "\n")
                        sf.flush()
                except Exception:
                    pass

            # Periodic stats banner
            if n % self._BANNER_EVERY == 0 or n == self._total:
                self._print_banner(elapsed)

    def _print_banner(self, elapsed: float) -> None:
        mins, secs = divmod(int(elapsed), 60)
        rate = self._done / elapsed if elapsed > 0 else 0
        print(
            f"  {sep('─' * 68)}\n"
            f"  {bold('Progress:')} {bright_white(f'{self._done}/{self._total}')}"
            f"  │  {ok(f'✓ {self._enriched}')}"
            f"  {warn(f'~ {self._weak}')}"
            f"  {err(f'✗ {self._failed}')}"
            f"  │  {tag(f'[pw] {self._playwright}')}"
            f"  │  {dim(f'{mins}m{secs:02d}s  ({rate:.1f}/s)')}\n"
            f"  {sep('─' * 68)}",
            flush=True,
        )

    def summary(self) -> None:
        """Print the final summary line after the pipeline completes."""
        elapsed = time.monotonic() - self._start
        mins, secs = divmod(int(elapsed), 60)
        print(sep("─" * 72), flush=True)
        print(
            f"{bold('Enrichment complete')} {dim(f'in {mins}m{secs:02d}s')}"
            f"  │  {ok(f'✓ enriched: {self._enriched + self._weak}')}"
            f"  │  {err(f'✗ failed: {self._failed}')}"
            f"  │  {tag(f'[pw] playwright: {self._playwright}')}"
            f"  │  {dim(f'total: {self._done}')}",
            flush=True,
        )
        print(sep("─" * 72), flush=True)


# ---------------------------------------------------------------------------
# Pipeline internals
# ---------------------------------------------------------------------------

def _fetch_stage(
    records: list[dict[str, Any]],
    targets: list[int],
    cfg: EnrichConfig,
    work_queue: queue.Queue,
    n_enrich_workers: int,
) -> None:
    """
    Runs in its own thread. Submits all fetch tasks to a pool, then pushes
    (idx, page) pairs onto work_queue as they complete.
    Sends n_enrich_workers sentinel poison-pills when done.
    """
    with ThreadPoolExecutor(max_workers=cfg.fetch_workers, thread_name_prefix="fetcher") as pool:
        futures: dict[Future, int] = {
            pool.submit(_safe_fetch, records[i], cfg): i
            for i in targets
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                page = future.result(timeout=cfg.fetch_timeout + 5)
            except FutureTimeoutError:
                logger.debug("Fetch timed out for record %d (%s)", idx, records[idx].get("job_url"))
                page = {
                    "final_url": records[idx].get("job_url", ""),
                    "page_title": "", "page_text": "", "jobposting_jsonld": [],
                    "error": "fetch_timeout", "_fetch_method": "http",
                }
            except Exception as exc:
                logger.debug("Fetch raised for record %d: %s", idx, exc)
                page = {
                    "final_url": records[idx].get("job_url", ""),
                    "page_title": "", "page_text": "", "jobposting_jsonld": [],
                    "error": str(exc), "_fetch_method": "http",
                }
            work_queue.put((idx, page))

    # Shut down all enrich workers
    for _ in range(n_enrich_workers):
        work_queue.put(_SENTINEL)


def _safe_fetch(record: dict[str, Any], cfg: EnrichConfig) -> dict[str, Any]:
    """Thin wrapper so fetch_job_page errors never kill a pool thread."""
    from .enrichment_worker import fetch_job_page, _validate_url
    url = (record.get("job_url") or "").strip()
    try:
        url = _validate_url(url, cfg)
        return fetch_job_page(url, cfg)
    except Exception as exc:
        return {
            "final_url": url, "page_title": "", "page_text": "",
            "jobposting_jsonld": [], "error": str(exc), "_fetch_method": "http",
        }


def _enrich_worker_loop(
    records: list[dict[str, Any]],
    out: list[dict[str, Any]],
    out_lock: threading.Lock,
    work_queue: queue.Queue,
    cfg: EnrichConfig,
    tracker: _ProgressTracker,
) -> None:
    """
    Runs in each enrich worker thread. Consumes (idx, page) pairs from the queue
    and calls the LLM. Writes results back into `out` under a lock.
    """
    worker = EnrichWorker(cfg)
    while True:
        item = work_queue.get()
        if item is _SENTINEL:
            work_queue.task_done()
            break
        idx, page = item
        record = records[idx]
        try:
            enriched = worker.enrich_with_page(record, page)
        except Exception as exc:
            logger.error(
                "Enrich raised for record %d (%s): %s",
                idx, record.get("job_url"), exc, exc_info=True,
            )
            enriched = _attach_error(record, str(exc))
        finally:
            work_queue.task_done()

        tracker.report(record, page, enriched)

        with out_lock:
            out[idx] = enriched


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def enrich_records(
    records: list[dict[str, Any]],
    cfg: EnrichConfig = _DEFAULT_CFG,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Enrich a list of job records using a two-stage parallel pipeline.

    Stage 1 — Fetch:   cfg.fetch_workers threads fetch job pages.
    Stage 2 — Enrich:  cfg.enrich_workers threads call the LLM.

    Both stages run concurrently. Total wall-clock time ≈
        max(total_fetch_time / fetch_workers, total_llm_time / enrich_workers)
    instead of sum(fetch + llm) per record.

    ``limit`` caps the number of unenriched records processed this run.
    Already-enriched records are always preserved in the output regardless
    of this value. Useful for smoke-testing before a full run.
    """
    if not azure_configured():
        print(warn("⚠  Azure OpenAI not configured — skipping enrichment."), flush=True)
        return records

    if not records:
        return records

    out = list(records)
    targets = [
        i for i, r in enumerate(out)
        if (r.get("job_url") or "").strip()
        and (not r.get("keywords") or not r.get("required_skills"))
    ]

    if limit is not None and limit > 0:
        capped = targets[:limit]
        skipped = len(targets) - len(capped)
        if skipped:
            print(
                dim(f"  --enrich-limit {limit}: capping to {limit} records "
                    f"({skipped} unenriched skipped for this run)."),
                flush=True,
            )
        targets = capped

    already_done = len(records) - len(targets)
    if already_done:
        label_str = "already-enriched or deferred by --enrich-limit" if limit is not None else "already-enriched"
        print(dim(f"  Skipping {already_done:,} {label_str} records."), flush=True)

    if not targets:
        print(ok("  ✓ All records already enriched — nothing to do."), flush=True)
        return out

    tracker = _ProgressTracker(
        len(targets),
        cfg.fetch_workers,
        cfg.enrich_workers,
        live_stream_path=cfg.live_stream_path,
    )
    if cfg.live_stream_path:
        print(
            dim(f"  Live stream → {cfg.live_stream_path}  (tail -f to follow)"),
            flush=True,
        )

    # Bounded queue prevents fetch stage from racing too far ahead and
    # consuming unbounded memory on large batches.
    work_queue: queue.Queue = queue.Queue(maxsize=cfg.queue_max_size)
    out_lock = threading.Lock()
    n_enrich = cfg.enrich_workers

    # Start the fetch stage in a background thread so it runs concurrently
    # with the enrich pool below.
    fetch_thread = threading.Thread(
        target=_fetch_stage,
        args=(records, targets, cfg, work_queue, n_enrich),
        name="fetch-dispatcher",
        daemon=True,
    )
    fetch_thread.start()

    # Start enrich workers
    enrich_threads = []
    for i in range(n_enrich):
        t = threading.Thread(
            target=_enrich_worker_loop,
            args=(records, out, out_lock, work_queue, cfg, tracker),
            name=f"enricher-{i}",
            daemon=True,
        )
        t.start()
        enrich_threads.append(t)

    # Wait for all work to drain
    fetch_thread.join()
    work_queue.join()
    for t in enrich_threads:
        t.join(timeout=cfg.per_record_timeout)
        if t.is_alive():
            print(warn(f"  ⚠  Enrich thread {t.name} did not finish in time."), file=sys.stderr, flush=True)

    tracker.summary()
    return out
