#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const root = process.argv[2] || process.cwd();
const allowedHex = new Set([
  "#00405C", "#0097BA", "#CCF5FF", "#A5D867", "#D54941", "#E37318", "#2BA471",
  "#DBDFE7", "#E3E7EE", "#F0F2F5", "#F5F7FA", "#333333", "#666666", "#999999",
  "#EDFAFF", "#DAF4FF", "#B9DFF0", "#67BFE5", "#2495C7", "#036F9E", "#015478", "#063449", "#01283A",
  "#E3F9E9", "#C6F3D7", "#92DAB2", "#56C08D", "#008858", "#006C45", "#005334", "#003B23", "#002515",
  "#FFF1E9", "#FFD9C2", "#FFB98C", "#FA9550", "#BE5A00", "#954500", "#713300", "#532300", "#3B1700",
  "#FFF0ED", "#FFD8D2", "#FFB9B0", "#FF9285", "#F6685D", "#AD352F", "#881F1C", "#68070A", "#490002",
  "#FFFFFF", "#000000"
].map((v) => v.toLowerCase()));

const ignoredDirs = new Set(["node_modules", ".git", "dist", "build", ".next", "coverage", ".agents"]);
const exts = new Set([".css", ".scss", ".less", ".ts", ".tsx", ".js", ".jsx", ".vue"]);
const hexPattern = /#[0-9a-fA-F]{3,8}\b/g;
const findings = [];

function normalizeHex(value) {
  const hex = value.toLowerCase();
  if (hex.length === 4 || hex.length === 5) {
    return `#${[...hex.slice(1)].map((char) => `${char}${char}`).join("")}`;
  }
  return hex;
}

function assertReadableDirectory(dir) {
  let stat;
  try {
    stat = fs.statSync(dir);
  } catch (error) {
    console.error(`Huixin token check failed: cannot access "${dir}".`);
    console.error(error.code ? `Reason: ${error.code}` : error.message);
    process.exit(2);
  }

  if (!stat.isDirectory()) {
    console.error(`Huixin token check failed: "${dir}" is not a directory.`);
    process.exit(2);
  }
}

function walk(dir) {
  for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
    if (ignoredDirs.has(item.name)) continue;
    const full = path.join(dir, item.name);
    if (item.isDirectory()) {
      walk(full);
      continue;
    }
    if (!exts.has(path.extname(item.name))) continue;
    const text = fs.readFileSync(full, "utf8");
    const lines = text.split(/\r?\n/);
    lines.forEach((line, index) => {
      for (const match of line.matchAll(hexPattern)) {
        const value = normalizeHex(match[0]);
        if (!allowedHex.has(value)) {
          findings.push({ file: path.relative(root, full), line: index + 1, value: match[0] });
        }
      }
    });
  }
}

assertReadableDirectory(root);
walk(root);

if (findings.length) {
  console.log("Found non-Huixin raw hex colors. Consider mapping them to design tokens:");
  for (const f of findings.slice(0, 100)) {
    console.log(`${f.file}:${f.line} ${f.value}`);
  }
  if (findings.length > 100) console.log(`...and ${findings.length - 100} more.`);
  process.exitCode = 1;
} else {
  console.log("No non-Huixin raw hex colors found in scanned frontend files.");
}
