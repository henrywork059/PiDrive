/* Pure operator display formatting; no DOM, network or persistence. */
(function(root){
  'use strict';
function normalizeHexColor(value, fallback = "#000000") {
  const raw = String(value || "").trim();
  const short = raw.match(/^#([0-9a-f]{3})$/i);
  if (short) {
    return `#${short[1].split("").map((part) => part + part).join("")}`.toLowerCase();
  }
  const full = raw.match(/^#([0-9a-f]{6})$/i);
  if (full) return `#${full[1]}`.toLowerCase();
  return fallback;
}

function hexToRgbTriplet(value) {
  const hex = normalizeHexColor(value, "#000000").slice(1);
  return [0, 2, 4].map((start) => parseInt(hex.slice(start, start + 2), 16)).join(', ');
}

function parseNumericStyleValue(value, fallback = 0) {
  const match = String(value || "").match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : fallback;
}


function shortLastSaveLabel(value) {
  const raw = String(value || "").trim();
  if (!raw || raw === "none") return "none";
  const clean = raw.replace(/\\/g, "/");
  const parts = clean.split("/").filter(Boolean);
  const tail = parts[parts.length - 1] || clean;
  return tail.length > 24 ? `${tail.slice(0, 21)}…` : tail;
}

function formatElapsed(totalSeconds) {
  const whole = Math.max(0, Math.floor(Number(totalSeconds || 0)));
  const minutes = Math.floor(whole / 60);
  const seconds = whole % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}


function formatDateTime(value) {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}


  const api={normalizeHexColor,hexToRgbTriplet,parseNumericStyleValue,shortLastSaveLabel,formatElapsed,formatDateTime};
  if (typeof module !== 'undefined' && module.exports) module.exports=api;
  else root.PiServerOperatorFormat=api;
})(typeof window !== 'undefined' ? window : globalThis);
