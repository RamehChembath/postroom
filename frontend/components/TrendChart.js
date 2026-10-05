"use client";
import { useEffect, useRef } from "react";
import {
  Chart, BarController, LineController, BarElement, LineElement,
  PointElement, LinearScale, CategoryScale, Tooltip, Legend,
} from "chart.js";

Chart.register(BarController, LineController, BarElement, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend);

/**
 * series: [{ label, posts, likes, comments }]
 * Renders posts as bars (left axis) and likes/comments as lines (right axis).
 */
export default function TrendChart({ series, height = 260 }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    if (chartRef.current) chartRef.current.destroy();

    const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#0A66C2";
    const like = getComputedStyle(document.documentElement).getPropertyValue("--like").trim() || "#D6336C";
    const line = getComputedStyle(document.documentElement).getPropertyValue("--line").trim() || "#DCE4EB";
    const muted = getComputedStyle(document.documentElement).getPropertyValue("--muted").trim() || "#5B7083";

    chartRef.current = new Chart(canvasRef.current, {
      data: {
        labels: series.map((s) => s.label),
        datasets: [
          { type: "bar", label: "Posts", data: series.map((s) => s.posts), backgroundColor: `${accent}33`, borderColor: accent, borderWidth: 1, borderRadius: 4, yAxisID: "y", order: 2 },
          { type: "line", label: "Likes", data: series.map((s) => s.likes), borderColor: like, backgroundColor: like, tension: 0.3, pointRadius: 3, yAxisID: "y1", order: 1 },
          { type: "line", label: "Comments", data: series.map((s) => s.comments), borderColor: accent, backgroundColor: accent, tension: 0.3, pointRadius: 3, yAxisID: "y1", order: 1 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: {
          x: { grid: { display: false }, ticks: { color: muted, font: { size: 11 } } },
          y: { position: "left", beginAtZero: true, grid: { color: line }, ticks: { color: muted, stepSize: 1, precision: 0 }, title: { display: true, text: "Posts", color: muted, font: { size: 11 } } },
          y1: { position: "right", beginAtZero: true, grid: { display: false }, ticks: { color: muted }, title: { display: true, text: "Likes / Comments", color: muted, font: { size: 11 } } },
        },
        plugins: { legend: { position: "top", labels: { color: muted, boxWidth: 12, font: { size: 12 } } } },
      },
    });

    return () => chartRef.current?.destroy();
  }, [series]);

  if (!series.length) return <p className="hint">Not enough posted data yet for a chart.</p>;
  return <div style={{ height }}><canvas ref={canvasRef} /></div>;
}
