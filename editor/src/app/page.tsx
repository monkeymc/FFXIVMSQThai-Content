"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import TranslationRow from "@/components/TranslationRow";
import SearchBox from "@/components/SearchBox";
import StickyHeader from "@/components/StickyHeader";
import EditorForm from "@/components/EditorForm";
import ThemeToggle from "@/components/ThemeToggle";
import { parseEnglishText, GlossaryEntry } from "@/lib/parser";

interface Dialogue {
  key: string;
  text_en: string;
  text: string;
}

interface Quest {
  quest_id: string;
  dialogues: Dialogue[];
  filePath: string;
  originalData?: any;
  format?: string;
}

function MainApp() {
  const searchParams = useSearchParams();
  const selectedFile = searchParams.get("file") || "";
  const searchQuery = searchParams.get("search") || "";

  const [fileList, setFileList] = useState<string[]>([]);
  const [filteredFiles, setFilteredFiles] = useState<string[]>([]);
  const [quest, setQuest] = useState<Quest | null>(null);
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load Glossary and File List
  useEffect(() => {
    async function loadInitialData() {
      try {
        const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
        
        // Load file list
        const filesRes = await fetch(`${basePath}/file-list.json`);
        if (filesRes.ok) {
          const files = await filesRes.json();
          setFileList(files);
        }

        // Load glossary
        const glossRes = await fetch(`${basePath}/glossary.md`);
        if (glossRes.ok) {
          const content = await glossRes.text();
          const lines = content.split("\n");
          const parsedGlossary: GlossaryEntry[] = [];
          for (const line of lines) {
            if (line.trim().startsWith("|") && !line.includes("English") && !line.includes("---")) {
              const parts = line.split("|").map((p) => p.trim());
              if (parts.length >= 3) {
                const en = parts[1];
                let th = parts[2];
                th = th.replace(/<[^>]+>/g, ""); // remove html tags
                if (en && th) {
                  parsedGlossary.push({ en, th });
                }
              }
            }
          }
          // Sort by length
          parsedGlossary.sort((a, b) => b.en.length - a.en.length);
          setGlossary(parsedGlossary);
        }
      } catch (err) {
        console.error("Failed to load initial data", err);
      } finally {
        setIsLoading(false);
      }
    }
    loadInitialData();
  }, []);

  // Filter files based on search
  useEffect(() => {
    if (!searchQuery) {
      setFilteredFiles(fileList);
    } else {
      const q = searchQuery.toLowerCase();
      setFilteredFiles(fileList.filter(f => f.toLowerCase().includes(q)));
    }
  }, [fileList, searchQuery]);

  // Load Quest data
  useEffect(() => {
    async function loadQuest() {
      if (!selectedFile) {
        setQuest(null);
        return;
      }
      
      try {
        const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
        const res = await fetch(`${basePath}/th/${selectedFile}`);
        if (res.ok) {
          const data = await res.json();
          let dialogues: any[] = [];
          
          let format = 'flat';
          if (data.dialogues && Array.isArray(data.dialogues)) {
            format = 'array';
            dialogues = data.dialogues;
          } else if (data.Scene) {
            format = 'scene';
            for (const [key, value] of Object.entries(data.Scene)) {
              if (value && typeof value === "object" && "text_en" in value) {
                dialogues.push({
                  key,
                  text_en: (value as any).text_en,
                  text: (value as any).text || "",
                });
              }
            }
          } else {
            format = 'flat';
            for (const [key, value] of Object.entries(data)) {
              if (value && typeof value === "object" && "text_en" in value) {
                dialogues.push({
                  key,
                  text_en: (value as any).text_en,
                  text: (value as any).text || "",
                });
              }
            }
          }
          
          setQuest({
            quest_id: selectedFile.split("/").pop()?.replace(".json", "") || selectedFile,
            dialogues,
            filePath: selectedFile,
            originalData: data,
            format,
          });
        } else {
          setQuest(null);
        }
      } catch (err) {
        console.error("Failed to load quest", err);
        setQuest(null);
      }
    }
    loadQuest();
  }, [selectedFile]);

  return (
    <div className="min-h-screen p-4 sm:p-8 font-sans flex flex-col gap-6">
      {/* Header */}
      <header className="ffxiv-panel p-6 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex flex-col md:flex-row items-center md:items-start gap-6 text-center md:text-left">
          <img src="/logo_dark.png" alt="FFXIV Header Dark" className="hide-in-light h-20 md:h-28 w-auto object-contain drop-shadow-lg shrink-0" />
          <img src="/logo_light.png" alt="FFXIV Header Light" className="show-in-light h-20 md:h-28 w-auto object-contain drop-shadow-lg shrink-0" />
          <div className="flex flex-col justify-center h-full pt-1">
            <h1 className="text-3xl md:text-4xl font-bold text-[var(--color-ffxiv-gold-light)] mb-2">
              FFXIV MSQ Translation Editor
            </h1>
            <p className="text-[var(--color-ffxiv-muted)] text-sm md:text-base">
              เลือกไฟล์ JSON ทางซ้ายมือ เพื่อเริ่มต้นแปลบทสนทนา<br className="hidden md:block" /> 
              แก้ไขคำแปลในช่องขวามือ แล้วกดบันทึกเพื่อดาวน์โหลดไฟล์ที่แปลเสร็จแล้ว
            </p>
          </div>
        </div>
        <ThemeToggle />
      </header>

      <div className="flex flex-col md:flex-row gap-6 items-start relative h-[80vh]">
        
        {/* Sidebar for File Selection */}
        <aside className="w-full md:w-80 ffxiv-panel flex flex-col max-h-[80vh]">
          {/* Pinned Header */}
          <div className="p-4 flex flex-col gap-4 border-b border-[var(--color-panel-border)]">
            <h2 className="text-lg font-bold text-[var(--color-ffxiv-gold)]">
              <span>Select Quest</span>
            </h2>
            <SearchBox defaultValue={searchQuery} />
          </div>
          
          <div className="p-4 flex-1 overflow-y-auto custom-scrollbar">
            {isLoading ? (
              <p className="text-[var(--color-ffxiv-muted)] text-sm italic">Loading quests...</p>
            ) : filteredFiles.length === 0 ? (
              <p className="text-[var(--color-ffxiv-muted)] text-sm italic">No quests found matching your search.</p>
            ) : (
              <ul className="space-y-1">
                {filteredFiles.map((file) => (
                  <li key={file}>
                    <Link 
                      href={`/?file=${encodeURIComponent(file)}${searchQuery ? `&search=${encodeURIComponent(searchQuery)}` : ''}`}
                      className={`block px-3 py-2 text-sm rounded transition-colors ${selectedFile === file ? 'bg-[var(--color-ffxiv-gold)] text-[var(--background)] font-semibold shadow-sm' : 'text-[var(--color-ffxiv-text)] hover:bg-[var(--color-input-bg)]'}`}
                    >
                      {file}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>

        {/* Main Editor Area */}
        <main className="flex-1 w-full flex flex-col h-full ffxiv-panel relative overflow-hidden min-h-0">
          {!quest ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center h-full">
              <img 
                src="/quests.png" 
                alt="Select Quest" 
                className="w-48 h-48 mb-8 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.1)] opacity-80"
              />
              <h2 className="text-2xl font-bold text-[var(--color-ffxiv-gold-light)] mb-4">
                เลือกเควสต์ที่ต้องการแปล
              </h2>
              <p className="text-[var(--color-ffxiv-muted)] max-w-md mx-auto leading-relaxed">
                กรุณาเลือกไฟล์ <span className="font-mono bg-[var(--color-btn-from)] text-[var(--color-btn-text)] px-2 py-0.5 rounded shadow-sm">.json</span> จากเมนูด้านซ้ายมือ<br/>
                เพื่อเริ่มแก้ไขคำแปลและตรวจสอบความถูกต้อง
              </p>
            </div>
          ) : (
            <div className="flex flex-col relative h-full overflow-hidden min-h-0">
              <StickyHeader filePath={quest.filePath} dialogueCount={quest.dialogues.length} />
              
              <div className="flex-1 relative min-h-0">
                <EditorForm quest={quest}>
                  <div id="scroll-container" className="absolute inset-0 overflow-y-auto custom-scrollbar flex flex-col gap-6 p-6 pr-8">
                  {quest.dialogues.map((dialogue) => {
                    const parsedChunks = parseEnglishText(dialogue.text_en, glossary);
                    return (
                      <TranslationRow 
                        key={dialogue.key}
                        name={`dialogue_${dialogue.key}`}
                        chunks={parsedChunks}
                        defaultTextTh={dialogue.text}
                      />
                    );
                  })}
                  {/* Submit Section (Appended to Content) */}
                  <div className="shrink-0 ffxiv-panel flex flex-col items-center justify-center gap-4 p-6 sm:p-10 relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[var(--color-ffxiv-gold-light)] to-transparent opacity-5"></div>
                      <img 
                        src="/done.png" 
                        alt="Quest Complete" 
                        className="w-24 h-24 sm:w-32 sm:h-32 object-contain drop-shadow-md z-10"
                      />
                      <h3 className="text-xl font-bold text-[var(--color-ffxiv-gold-light)] mb-2 relative z-10">
                        ขอขอบคุณเหล่านักรบแห่งแสงทุกท่าน!
                      </h3>
                      <p className="text-[var(--color-ffxiv-text)] text-center mb-2 relative z-10">
                        โปรเจกต์นี้จะสมบูรณ์ไม่ได้เลยหากขาดความช่วยเหลือจากทุกคน<br/>
                        ขอบคุณที่สละเวลามาช่วยเกลาภาษาให้ Eorzea น่าอยู่ยิ่งขึ้นนะครับ
                      </p>
                      <p className="text-[var(--color-ffxiv-muted)] text-sm border-t border-[var(--color-panel-border)] pt-4 mb-4 relative z-10 w-full text-center max-w-md mx-auto">
                        ตรวจสอบความถูกต้องเรียบร้อยแล้ว กดบันทึกผลงานของคุณได้เลย!
                      </p>
                      
                      <div className="flex justify-center relative z-10">
                        <button 
                          type="submit" 
                          className="group relative px-10 py-3 ffxiv-submit-btn font-bold text-lg rounded-full overflow-hidden shadow-lg hover:shadow-xl transition-all"
                        >
                          <span className="relative z-10 flex items-center justify-center">
                            บันทึกการแก้ไข
                          </span>
                          <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-in-out"></div>
                        </button>
                      </div>
                    </div>
                  </div>
                </EditorForm>
              </div>
            </div>
          )}
        </main>

      </div>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="min-h-screen p-8 text-center text-[var(--color-ffxiv-gold)]">Loading application...</div>}>
      <MainApp />
    </Suspense>
  );
}
