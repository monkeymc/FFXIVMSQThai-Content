export interface TextChunk {
  type: "text" | "glossary" | "search";
  content: string;
  tooltip?: string;
}

export interface GlossaryEntry {
  en: string;
  th: string;
}

export function parseEnglishText(
  text: string,
  glossary: GlossaryEntry[],
  searchQuery?: string
): TextChunk[] {
  let chunks: TextChunk[] = [{ type: "text", content: text }];

  // 1. ไฮไลต์คำใน Glossary ก่อน (ถ้ามี Glossary)
  if (glossary && glossary.length > 0) {
    for (const { en, th } of glossary) {
      if (!en) continue;
      // Regex สำหรับหาคำเป๊ะๆ โดยไม่สนใจตัวพิมพ์ใหญ่-เล็ก
      const regex = new RegExp(`\\b${escapeRegExp(en)}\\b`, "gi");
      
      const newChunks: TextChunk[] = [];
      for (const chunk of chunks) {
        if (chunk.type !== "text") {
          newChunks.push(chunk);
          continue;
        }

        let lastIndex = 0;
        let match;
        while ((match = regex.exec(chunk.content)) !== null) {
          if (match.index > lastIndex) {
            newChunks.push({ type: "text", content: chunk.content.substring(lastIndex, match.index) });
          }
          newChunks.push({ type: "glossary", content: match[0], tooltip: th });
          lastIndex = match.index + match[0].length;
        }
        if (lastIndex < chunk.content.length) {
          newChunks.push({ type: "text", content: chunk.content.substring(lastIndex) });
        }
      }
      chunks = newChunks;
    }
  }

  // 2. ไฮไลต์คำค้นหา (Search Query) ซ้อนทับไปอีกชั้น (ถ้ามีคำค้นหา)
  // แตกคำค้นเป็น token แล้วไฮไลต์ทีละคำให้ตรงกับตรรกะการค้นหา (substring ต่อ token)
  if (searchQuery && searchQuery.trim() !== "") {
    const tokens = searchQuery
      .trim()
      .split(/\s+/)
      .filter((t) => t.length >= 2)
      .map(escapeRegExp);

    if (tokens.length > 0) {
    const regex = new RegExp(`(${tokens.join("|")})`, "gi");

    const newChunks: TextChunk[] = [];
    for (const chunk of chunks) {
      if (chunk.type !== "text") {
        newChunks.push(chunk);
        continue;
      }

      let lastIndex = 0;
      let match;
      while ((match = regex.exec(chunk.content)) !== null) {
        if (match.index > lastIndex) {
          newChunks.push({ type: "text", content: chunk.content.substring(lastIndex, match.index) });
        }
        newChunks.push({ type: "search", content: match[0] });
        lastIndex = match.index + match[0].length;
      }
      if (lastIndex < chunk.content.length) {
        newChunks.push({ type: "text", content: chunk.content.substring(lastIndex) });
      }
    }
    chunks = newChunks;
    }
  }

  return chunks;
}

function escapeRegExp(string: string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); // $& means the whole matched string
}
