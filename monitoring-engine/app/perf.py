"""
Browser Performance Metrics Collection
Extracts detailed timing data from the browser's Performance API.
Works with ASP.NET (.aspx), React, and any web page.
"""
import logging

logger = logging.getLogger(__name__)


async def collect_performance_metrics(page) -> dict:
    """Collect detailed performance metrics from the browser Performance API."""
    try:
        metrics = await page.evaluate("""() => {
            const perf = window.performance;
            if (!perf) return null;

            const nav = perf.getEntriesByType('navigation')[0] || {};
            const paint = perf.getEntriesByType('paint') || [];

            // Resource breakdown
            const resources = perf.getEntriesByType('resource') || [];
            const scripts = resources.filter(r => r.initiatorType === 'script');
            const styles = resources.filter(r => r.initiatorType === 'css' || r.initiatorType === 'link');
            const images = resources.filter(r => r.initiatorType === 'img');
            const xhr = resources.filter(r => r.initiatorType === 'xmlhttprequest' || r.initiatorType === 'fetch');
            const slowResources = resources
                .filter(r => r.duration > 1000)
                .sort((a, b) => b.duration - a.duration)
                .slice(0, 5)
                .map(r => ({
                    name: r.name.split('/').pop().split('?')[0] || r.name.substring(0, 80),
                    type: r.initiatorType,
                    duration: Math.round(r.duration),
                    size: r.transferSize || 0,
                }));

            // Failed resources (0 transfer size or 0 duration for non-cache)
            const failedResources = resources
                .filter(r => r.responseStatus >= 400 || (r.transferSize === 0 && r.duration === 0 && r.decodedBodySize === 0))
                .slice(0, 5)
                .map(r => ({
                    name: r.name.split('/').pop().split('?')[0] || r.name.substring(0, 80),
                    type: r.initiatorType,
                    status: r.responseStatus || 0,
                }));

            // Timing breakdown
            const timing = {
                dns: Math.round((nav.domainLookupEnd || 0) - (nav.domainLookupStart || 0)),
                tcp: Math.round((nav.connectEnd || 0) - (nav.connectStart || 0)),
                tls: Math.round((nav.connectEnd || 0) - (nav.secureConnectionStart || nav.connectStart || 0)),
                ttfb: Math.round((nav.responseStart || 0) - (nav.requestStart || 0)),
                download: Math.round((nav.responseEnd || 0) - (nav.responseStart || 0)),
                dom_interactive: Math.round(nav.domInteractive || 0),
                dom_content_loaded: Math.round(nav.domContentLoadedEventEnd || 0),
                dom_complete: Math.round(nav.domComplete || 0),
                load_event: Math.round(nav.loadEventEnd || 0),
                total_load: Math.round(nav.loadEventEnd || nav.domComplete || 0),
            };

            // Paint timings
            const fcp = paint.find(p => p.name === 'first-contentful-paint');
            const fp = paint.find(p => p.name === 'first-paint');

            return {
                timing: timing,
                first_paint_ms: fp ? Math.round(fp.startTime) : null,
                first_contentful_paint_ms: fcp ? Math.round(fcp.startTime) : null,
                resource_count: resources.length,
                script_count: scripts.length,
                style_count: styles.length,
                image_count: images.length,
                api_call_count: xhr.length,
                total_transfer_kb: Math.round(resources.reduce((s, r) => s + (r.transferSize || 0), 0) / 1024),
                slow_resources: slowResources,
                failed_resources: failedResources,
                slow_api_calls: xhr
                    .filter(r => r.duration > 2000)
                    .sort((a, b) => b.duration - a.duration)
                    .slice(0, 5)
                    .map(r => ({
                        url: r.name.split('/').slice(-2).join('/').split('?')[0] || r.name.substring(0, 80),
                        duration: Math.round(r.duration),
                        size: r.transferSize || 0,
                    })),
            };
        }""")

        return metrics or {}
    except Exception as e:
        logger.warning(f"Performance metrics collection failed: {e}")
        return {}


def format_perf_summary(metrics: dict, region: str = "") -> dict:
    """Create a summary dict suitable for storing in the details field."""
    if not metrics:
        return {"region": region}

    timing = metrics.get("timing", {})

    summary = {
        "region": region,
        "ttfb_ms": timing.get("ttfb", 0),
        "dom_content_loaded_ms": timing.get("dom_content_loaded", 0),
        "dom_complete_ms": timing.get("dom_complete", 0),
        "total_load_ms": timing.get("total_load", 0),
        "first_paint_ms": metrics.get("first_paint_ms"),
        "first_contentful_paint_ms": metrics.get("first_contentful_paint_ms"),
        "dns_ms": timing.get("dns", 0),
        "tcp_ms": timing.get("tcp", 0),
        "tls_ms": timing.get("tls", 0),
        "download_ms": timing.get("download", 0),
        "resource_count": metrics.get("resource_count", 0),
        "script_count": metrics.get("script_count", 0),
        "style_count": metrics.get("style_count", 0),
        "api_call_count": metrics.get("api_call_count", 0),
        "total_transfer_kb": metrics.get("total_transfer_kb", 0),
        "slow_resources": metrics.get("slow_resources", []),
        "failed_resources": metrics.get("failed_resources", []),
        "slow_api_calls": metrics.get("slow_api_calls", []),
    }

    return summary
