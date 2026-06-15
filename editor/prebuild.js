const fs = require('fs');
const path = require('path');

const rootDir = path.join(__dirname, '..', '..');
const contentDir = path.join(__dirname, '..');
const publicDir = path.join(__dirname, 'public');
const publicThDir = path.join(publicDir, 'th');

if (!fs.existsSync(publicDir)) fs.mkdirSync(publicDir, { recursive: true });
if (!fs.existsSync(publicThDir)) fs.mkdirSync(publicThDir, { recursive: true });

const glossaryPath = path.join(rootDir, 'glossary.md');
if (fs.existsSync(glossaryPath)) {
  fs.copyFileSync(glossaryPath, path.join(publicDir, 'glossary.md'));
  console.log('Copied glossary.md');
}

function getAllFiles(dirPath, arrayOfFiles) {
  const files = fs.readdirSync(dirPath);
  arrayOfFiles = arrayOfFiles || [];
  files.forEach(function(file) {
    if (fs.statSync(dirPath + "/" + file).isDirectory()) {
      arrayOfFiles = getAllFiles(dirPath + "/" + file, arrayOfFiles);
    } else {
      arrayOfFiles.push(path.join(dirPath, "/", file));
    }
  });
  return arrayOfFiles;
}

const thDir = path.join(contentDir, 'th');
if (fs.existsSync(thDir)) {
  fs.cpSync(thDir, publicThDir, { recursive: true });
  const allFiles = getAllFiles(thDir);
  const jsonFiles = allFiles
    .filter(f => f.endsWith('.json'))
    .map(f => f.replace(thDir + '/', '').replace(thDir + '\\', '').replace(/\\/g, '/'));
    
  fs.writeFileSync(path.join(publicDir, 'file-list.json'), JSON.stringify(jsonFiles));
  console.log('Copied th/ and generated file-list.json with ' + jsonFiles.length + ' files.');

  // สร้าง inverted index สำหรับค้นหาคำในประโยคภาษาอังกฤษ (text_en)
  // โครงสร้าง: { files: [...], inv: { word: [fileIndex, ...] } }
  // โหลดฝั่ง client แบบ lazy (ตอนผู้ใช้เริ่มพิมพ์ค้นหา) จึงไม่กระทบเวลาโหลดหน้าแรก
  function extractEnglish(data) {
    const out = [];
    if (data.dialogues && Array.isArray(data.dialogues)) {
      for (const d of data.dialogues) if (d && d.text_en) out.push(d.text_en);
    } else if (data.Scene) {
      for (const v of Object.values(data.Scene)) {
        if (v && typeof v === 'object' && 'text_en' in v) out.push(v.text_en);
      }
    } else {
      for (const v of Object.values(data)) {
        if (v && typeof v === 'object' && 'text_en' in v) out.push(v.text_en);
      }
    }
    return out.join(' ');
  }

  const inv = {};
  jsonFiles.forEach((f, i) => {
    try {
      const data = JSON.parse(fs.readFileSync(path.join(publicThDir, f), 'utf8'));
      const text = extractEnglish(data).toLowerCase();
      const words = new Set(text.split(/[^a-z0-9]+/).filter((w) => w.length >= 3));
      for (const w of words) (inv[w] = inv[w] || []).push(i);
    } catch (e) {
      console.warn('Skip indexing ' + f + ': ' + e.message);
    }
  });

  fs.writeFileSync(
    path.join(publicDir, 'search-index.json'),
    JSON.stringify({ files: jsonFiles, inv })
  );
  console.log('Generated search-index.json with ' + Object.keys(inv).length + ' unique words.');
}
