from __future__ import annotations

import logging
import queue
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable

from itosub.contracts import TranslationRequest
from itosub.live.live_transcribe import LiveUtteranceTranscriber
from itosub.nlp.segmenter import SubtitleSegmenter
from itosub.ui.bridge import SubtitleBus

from itosub.app.services import build_live_overlay_services

_PUNCT_END = re.compile(r"[.!?]$")


@dataclass(frozen=True)
class _TranslateJob:
    t0: float
    t1: float
    en: str


def _drain_subtitle_bus(bus: SubtitleBus, overlay: Any, max_items: int) -> int:
    drained = 0
    while drained < max_items:
        line = bus.pop()
        if line is None:
            break
        overlay.add_line(line)
        drained += 1
    return drained


def _dedupe_repeated_words(text: str, max_repeat: int = 2) -> str:
    words = text.split()
    if not words:
        return ""
    out = []
    prev = None
    run = 0
    for w in words:
        wl = w.lower()
        if wl == prev:
            run += 1
        else:
            prev = wl
            run = 1
        if run <= max_repeat:
            out.append(w)
    return " ".join(out).strip()


def _is_low_value_fragment(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    words = t.split()
    if len(words) == 1 and not _PUNCT_END.search(t):
        return True
    if len(t) <= 2:
        return True
    return False


def _translate_text(translator: Any, en: str) -> str:
    req = TranslationRequest(text=en, source_lang="en", target_lang="ja")
    res = translator.translate(req)
    return str(getattr(res, "translated_text", None) or getattr(res, "text", None) or res)


def _queue_put_drop_oldest(q: "queue.Queue[_TranslateJob]", item: _TranslateJob) -> bool:
    try:
        q.put_nowait(item)
        return False
    except queue.Full:
        try:
            _ = q.get_nowait()
        except queue.Empty:
            return False
        try:
            q.put_nowait(item)
            return True
        except queue.Full:
            return True


def _iter_committed_lines(
    segmenter: SubtitleSegmenter,
    t0: float,
    t1: float,
    text: str,
) -> Iterable[tuple[float, float, str]]:
    en = _dedupe_repeated_words((text or "").strip(), max_repeat=2)
    if _is_low_value_fragment(en):
        return ()
    return ((float(line.t0), float(line.t1), str(line.text)) for line in segmenter.push(en, t0, t1))


def _log_event(logger: logging.Logger | None, level: int, event: str, **fields: Any) -> None:
    if logger is None:
        return
    logger.log(level, event, extra=fields)


def _run_worker(
    args: Any,
    bus: SubtitleBus,
    stop_event: threading.Event,
    logger: logging.Logger | None = None,
) -> None:
    from itosub.ui.overlay_qt import SubtitleLine

    services = build_live_overlay_services(args)
    mic = services.mic
    translator = services.translator
    segmenter = services.segmenter
    jobs: "queue.Queue[_TranslateJob]" = queue.Queue(maxsize=200)
    metrics: dict[str, int | float] = {
        "en_commits": 0,
        "ja_commits": 0,
        "queue_drops": 0,
        "translate_samples": 0,
        "translate_ms_total": 0.0,
    }

    _log_event(
        logger,
        logging.INFO,
        "worker_start",
        translator=str(args.translator),
        model=str(args.model),
        async_translate=bool(args.async_translate),
        sr=int(args.sr),
        chunk_sec=float(args.chunk_sec),
    )

    def _translator_loop() -> None:
        while not stop_event.is_set():
            try:
                job = jobs.get(timeout=0.2)
            except queue.Empty:
                continue
            t0 = time.perf_counter()
            ja = _translate_text(translator, job.en)
            dur_ms = (time.perf_counter() - t0) * 1000.0
            metrics["translate_samples"] = int(metrics["translate_samples"]) + 1
            metrics["translate_ms_total"] = float(metrics["translate_ms_total"]) + dur_ms
            metrics["ja_commits"] = int(metrics["ja_commits"]) + 1
            _log_event(
                logger,
                logging.INFO,
                "translate_async_done",
                t0=job.t0,
                t1=job.t1,
                chars_en=len(job.en),
                ms=round(dur_ms, 2),
                queue_depth=jobs.qsize(),
            )
            if args.print_console:
                print(f"[utt {job.t0:.2f}-{job.t1:.2f}] JA: {ja}")
            bus.push(SubtitleLine(en=job.en, ja=ja, t0=job.t0, t1=job.t1))

    if args.async_translate:
        threading.Thread(
            target=_translator_loop,
            name="itosub-translate-worker",
            daemon=True,
        ).start()

    def _on_asr(t0: float, t1: float, text: str) -> None:
        for line_t0, line_t1, en in _iter_committed_lines(segmenter, t0, t1, text):
            metrics["en_commits"] = int(metrics["en_commits"]) + 1
            if args.print_console:
                print(f"[utt {line_t0:.2f}-{line_t1:.2f}] EN: {en}")
            if args.async_translate:
                bus.push(SubtitleLine(en=en, ja="", t0=line_t0, t1=line_t1))
                dropped = _queue_put_drop_oldest(jobs, _TranslateJob(t0=line_t0, t1=line_t1, en=en))
                if dropped:
                    metrics["queue_drops"] = int(metrics["queue_drops"]) + 1
                    _log_event(
                        logger,
                        logging.WARNING,
                        "translate_queue_drop_oldest",
                        t0=line_t0,
                        t1=line_t1,
                        chars_en=len(en),
                        queue_depth=jobs.qsize(),
                    )
                else:
                    _log_event(
                        logger,
                        logging.INFO,
                        "translate_async_enqueued",
                        t0=line_t0,
                        t1=line_t1,
                        chars_en=len(en),
                        queue_depth=jobs.qsize(),
                    )
                continue
            t_sync = time.perf_counter()
            ja = _translate_text(translator, en)
            dur_ms = (time.perf_counter() - t_sync) * 1000.0
            metrics["translate_samples"] = int(metrics["translate_samples"]) + 1
            metrics["translate_ms_total"] = float(metrics["translate_ms_total"]) + dur_ms
            metrics["ja_commits"] = int(metrics["ja_commits"]) + 1
            _log_event(
                logger,
                logging.INFO,
                "translate_sync_done",
                t0=line_t0,
                t1=line_t1,
                chars_en=len(en),
                ms=round(dur_ms, 2),
            )
            if args.print_console:
                print(f"[utt {line_t0:.2f}-{line_t1:.2f}] JA: {ja}")
            bus.push(SubtitleLine(en=en, ja=ja, t0=line_t0, t1=line_t1))

    def _chunks_until_stop():
        for chunk in mic.chunks():
            if stop_event.is_set():
                return
            yield chunk

    runner = LiveUtteranceTranscriber(
        chunk_iter=_chunks_until_stop(),
        transcriber=services.transcriber,
        vad=services.vad,
        on_asr=_on_asr,
        silence_chunks_to_finalize=int(args.silence_chunks),
        min_utter_sec=float(args.min_utter_sec),
        max_utter_sec=(
            None if getattr(args, "max_utter_sec", None) is None else float(args.max_utter_sec)
        ),
        debug=bool(args.debug),
    )

    try:
        runner.run()
    except KeyboardInterrupt:
        _log_event(logger, logging.INFO, "worker_keyboard_interrupt")
        return
    finally:
        for line in segmenter.flush():
            en = (line.text or "").strip()
            if not en:
                continue
            metrics["en_commits"] = int(metrics["en_commits"]) + 1
            if args.print_console:
                print(f"[utt {line.t0:.2f}-{line.t1:.2f}] EN: {en}")
            if args.async_translate:
                bus.push(SubtitleLine(en=en, ja="", t0=float(line.t0), t1=float(line.t1)))
                dropped = _queue_put_drop_oldest(
                    jobs,
                    _TranslateJob(t0=float(line.t0), t1=float(line.t1), en=en),
                )
                if dropped:
                    metrics["queue_drops"] = int(metrics["queue_drops"]) + 1
                    _log_event(
                        logger,
                        logging.WARNING,
                        "translate_queue_drop_oldest",
                        t0=float(line.t0),
                        t1=float(line.t1),
                        chars_en=len(en),
                        queue_depth=jobs.qsize(),
                    )
            else:
                t_sync = time.perf_counter()
                ja = _translate_text(translator, en)
                dur_ms = (time.perf_counter() - t_sync) * 1000.0
                metrics["translate_samples"] = int(metrics["translate_samples"]) + 1
                metrics["translate_ms_total"] = float(metrics["translate_ms_total"]) + dur_ms
                metrics["ja_commits"] = int(metrics["ja_commits"]) + 1
                _log_event(
                    logger,
                    logging.INFO,
                    "translate_sync_done",
                    t0=float(line.t0),
                    t1=float(line.t1),
                    chars_en=len(en),
                    ms=round(dur_ms, 2),
                )
                if args.print_console:
                    print(f"[utt {line.t0:.2f}-{line.t1:.2f}] JA: {ja}")
                bus.push(SubtitleLine(en=en, ja=ja, t0=float(line.t0), t1=float(line.t1)))
        stop_event.set()
        avg_ms = (
            float(metrics["translate_ms_total"]) / int(metrics["translate_samples"])
            if int(metrics["translate_samples"]) > 0
            else 0.0
        )
        _log_event(
            logger,
            logging.INFO,
            "worker_stop",
            en_commits=int(metrics["en_commits"]),
            ja_commits=int(metrics["ja_commits"]),
            queue_drops=int(metrics["queue_drops"]),
            translate_samples=int(metrics["translate_samples"]),
            translate_avg_ms=round(avg_ms, 2),
        )


def _preload_asr_runtime() -> None:
    import ctranslate2  # noqa: F401
    import torch  # noqa: F401
    from faster_whisper import WhisperModel  # noqa: F401
