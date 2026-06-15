#!/usr/bin/env node
// ===================================================================
// sync-revised.js
// ดึงผลตอบรับจาก Google Form (เผยแพร่เป็น TSV) แล้วแปลงเป็นไฟล์ static
// `editor/public/revised.json` ที่เก็บเฉพาะข้อมูลที่ใช้จริง:
//     { "2.0/a-hearer-is-often-late.json": ["MADbear", ...], ... }
//
// ไฟล์นี้คือ "แหล่งข้อมูลเดียว" ที่แอปใช้แสดง: badge ใน Select Quest,
// คอนเฟตติฉลอง และเครดิตผู้เกลาภาษาในหัวเควสต์
//
// ต้องระบุลิงก์เผยแพร่ของชีตผลตอบรับ (output=tsv) ผ่าน arg หรือ env เสมอ — ไม่ hardcode
// วิธีใช้:
//   node scripts/sync-revised.js "<TSV public link>"
//   REVISED_TSV_URL="<link>" node scripts/sync-revised.js
// ===================================================================
const fs = require('fs');
const path = require('path');

const TSV_URL = process.argv[2] || process.env.REVISED_TSV_URL;

if (!TSV_URL) {
  console.error('ต้องระบุลิงก์ TSV ของชีตผลตอบรับ (เผยแพร่แบบ output=tsv)\n');
  console.error('วิธีใช้:');
  console.error('  node scripts/sync-revised.js "<TSV public link>"');
  console.error('  REVISED_TSV_URL="<link>" node scripts/sync-revised.js');
  process.exit(1);
}

const editorDir = path.join(__dirname, '..');     // editor/
const repoRoot = path.join(editorDir, '..');      // รากโปรเจกต์
const thDir = path.join(repoRoot, 'th');
const publicDir = path.join(editorDir, 'public');
const outFile = path.join(publicDir, 'revised.json');

// ------- 1) รวบรวม path ของไฟล์เควสต์ทั้งหมดใต้ th/ (relative, ใช้ '/') -------
function getAllRelPaths(dir, base, acc) {
  acc = acc || [];
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    if (fs.statSync(full).isDirectory()) {
      getAllRelPaths(full, base, acc);
    } else if (name.endsWith('.json')) {
      acc.push(path.relative(base, full).split(path.sep).join('/'));
    }
  }
  return acc;
}

if (!fs.existsSync(thDir)) {
  console.error('ไม่พบโฟลเดอร์ th/ ที่ ' + thDir);
  process.exit(1);
}

const relPaths = getAllRelPaths(thDir, thDir);
const relPathSet = new Set(relPaths);
// basename (เช่น "a-hearer-is-often-late.json") -> [relpath, ...] สำหรับจับคู่แบบไม่ระบุเวอร์ชัน
const byBasename = {};
for (const rp of relPaths) {
  const base = rp.split('/').pop();
  (byBasename[base] = byBasename[base] || []).push(rp);
}

// ------- 2) ทำความสะอาดค่าในคอลัมน์ Quest ให้กลายเป็น relpath ของไฟล์จริง -------
// รองรับทั้ง "a-hearer-is-often-late", "a-hearer-is-often-late.json",
// "th/2.0/a-hearer-is-often-late", "2.0/a-hearer-is-often-late.json"
function resolveQuest(raw) {
  let s = String(raw || '').trim();
  if (!s) return { error: 'ว่าง' };
  s = s.replace(/\\/g, '/').replace(/^th\//, '').replace(/\.json$/i, '').trim();

  const asPath = s + '.json';
  if (relPathSet.has(asPath)) return { path: asPath };

  const base = s.split('/').pop() + '.json';
  const hits = byBasename[base];
  if (!hits) return { error: 'ไม่พบไฟล์ที่ตรงกับ "' + raw + '"' };
  if (hits.length > 1) {
    return { error: 'ชื่อ "' + base + '" ซ้ำหลายเวอร์ชัน (' + hits.join(', ') + ') โปรดระบุ path เต็มในคอลัมน์ Quest' };
  }
  return { path: hits[0] };
}

// ------- 3) parse TSV -------
function parseTsv(text) {
  const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n').filter((l) => l.length > 0);
  if (lines.length === 0) return { header: [], rows: [] };
  const header = lines[0].split('\t');
  const rows = lines.slice(1).map((l) => l.split('\t'));
  return { header, rows };
}

function findColumn(header, predicate, fallbackIndex) {
  const idx = header.findIndex(predicate);
  return idx >= 0 ? idx : fallbackIndex;
}

(async function main() {
  console.log('ดึงผลตอบรับจาก:\n  ' + TSV_URL);
  let text;
  try {
    const res = await fetch(TSV_URL);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    text = await res.text();
  } catch (e) {
    console.error('ดึง TSV ไม่สำเร็จ: ' + e.message);
    process.exit(1);
  }

  const { header, rows } = parseTsv(text);
  if (rows.length === 0) {
    console.warn('ไม่มีข้อมูลแถวใน TSV');
  }

  // หาคอลัมน์ aka และ Quest จากหัวตาราง (มี fallback เป็นตำแหน่งถ้าหาไม่เจอ)
  const akaCol = findColumn(header, (h) => /aka/i.test(h), 2);
  const questCol = findColumn(header, (h) => /quest/i.test(h), 3);

  const revised = {};   // relpath -> [aka, ...] (dedup, เรียงตามลำดับที่ส่ง)
  const skipped = [];
  let matched = 0;

  rows.forEach((cols, i) => {
    const aka = (cols[akaCol] || '').trim();
    const questRaw = (cols[questCol] || '').trim();
    if (!aka && !questRaw) return; // แถวว่าง

    const r = resolveQuest(questRaw);
    if (r.error) {
      skipped.push('แถว ' + (i + 2) + ': ' + r.error);
      return;
    }
    if (!aka) {
      skipped.push('แถว ' + (i + 2) + ': ไม่มีชื่อผู้แปล (aka) สำหรับ ' + r.path);
      return;
    }
    const list = (revised[r.path] = revised[r.path] || []);
    if (!list.includes(aka)) list.push(aka);
    matched++;
  });

  // เรียง key ให้ diff คงที่
  const sorted = {};
  for (const k of Object.keys(revised).sort()) sorted[k] = revised[k];

  if (!fs.existsSync(publicDir)) fs.mkdirSync(publicDir, { recursive: true });
  fs.writeFileSync(outFile, JSON.stringify(sorted, null, 2) + '\n');

  console.log('');
  console.log('จับคู่สำเร็จ ' + matched + ' แถว -> เควสต์ที่เกลาแล้ว ' + Object.keys(sorted).length + ' รายการ');
  for (const [k, v] of Object.entries(sorted)) console.log('  ✦ ' + k + '  <-  ' + v.join(', '));
  if (skipped.length) {
    console.log('\nข้ามไป ' + skipped.length + ' แถว:');
    for (const s of skipped) console.log('  - ' + s);
  }
  console.log('\nเขียนไฟล์ static แล้ว: ' + path.relative(repoRoot, outFile));
})();
