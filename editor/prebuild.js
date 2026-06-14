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
}
