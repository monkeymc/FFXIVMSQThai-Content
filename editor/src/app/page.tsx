"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
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
  // ดัชนีค้นหาเนื้อหาภาษาอังกฤษ (โหลดแบบ lazy ตอนเริ่มค้นหา)
  const [searchIndex, setSearchIndex] = useState<{ files: string[]; inv: Record<string, number[]> } | null>(null);
  const indexLoadRef = useRef<"idle" | "loading" | "done">("idle");
  const [quest, setQuest] = useState<Quest | null>(null);
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  // ไฟล์ที่กำลังโหลดอยู่ (ใช้โชว์ spinner และกันการคลิกรัว ๆ)
  const [navigatingFile, setNavigatingFile] = useState<string | null>(null);

  // เลือกเควสต์จากรายการด้านซ้าย
  const handleSelectFile = (file: string) => {
    if (navigatingFile) return;        // กำลังโหลดอยู่ ห้ามคลิกซ้ำ
    if (file === selectedFile) return; // ไฟล์นี้เปิดอยู่แล้ว
    setNavigatingFile(file);

    const params = new URLSearchParams();
    params.set("file", file);
    if (searchQuery) params.set("search", searchQuery);
    // ใช้ History API (shallow routing) อัปเดต ?file= โดยไม่ผ่าน router ของ Next
    // เพื่อไม่ให้เกิดการนำทาง/รีโหลดหน้า ซึ่งบน GitHub Pages (static export + basePath)
    // การ router.push จะ fallback เป็น hard reload ทำให้ทั้งหน้าเด้งขึ้นบนสุด
    // useSearchParams จะ sync ค่าใหม่ให้เอง แล้ว useEffect ด้านล่างจะเลื่อนเฉพาะเนื้อหา
    window.history.pushState(null, "", `?${params.toString()}`);
  };

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

  // โหลด search index แบบ lazy ครั้งแรกที่ผู้ใช้เริ่มค้นหา (ไม่กระทบเวลาโหลดหน้าแรก)
  useEffect(() => {
    if (!searchQuery || indexLoadRef.current !== "idle") return;
    indexLoadRef.current = "loading";
    (async () => {
      try {
        const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
        const res = await fetch(`${basePath}/search-index.json`);
        if (res.ok) {
          setSearchIndex(await res.json());
          indexLoadRef.current = "done";
        } else {
          indexLoadRef.current = "idle";
        }
      } catch (err) {
        console.error("Failed to load search index", err);
        indexLoadRef.current = "idle";
      }
    })();
  }, [searchQuery]);

  // Filter files based on search (ชื่อไฟล์ + เนื้อหาประโยคภาษาอังกฤษ)
  useEffect(() => {
    if (!searchQuery) {
      setFilteredFiles(fileList);
      return;
    }
    const q = searchQuery.toLowerCase();
    const nameMatches = (f: string) => f.toLowerCase().includes(q);

    // ดัชนียังโหลดไม่เสร็จ → ค้นด้วยชื่อไฟล์ไปก่อน
    if (!searchIndex) {
      setFilteredFiles(fileList.filter(nameMatches));
      return;
    }

    // ค้นในเนื้อหา: แตกคำค้นเป็น token แล้วหาไฟล์ที่มี "ครบทุก token" (AND)
    // แต่ละ token จับแบบ substring กับคำในดัชนี เช่น "aeth" จะเจอ "aether"
    const tokens = q.split(/[^a-z0-9]+/).filter((t) => t.length >= 2);
    const words = Object.keys(searchIndex.inv);
    let matched: Set<number> | null = null;
    for (const tok of tokens) {
      const hits = new Set<number>();
      for (const w of words) {
        if (w.includes(tok)) {
          for (const fi of searchIndex.inv[w]) hits.add(fi);
        }
      }
      if (matched === null) {
        matched = hits;
      } else {
        const prev: Set<number> = matched;
        matched = new Set<number>(Array.from(hits).filter((x) => prev.has(x)));
      }
      if (matched.size === 0) break;
    }
    const contentSet = new Set<string>(matched ? Array.from(matched).map((i) => searchIndex.files[i]) : []);

    setFilteredFiles(fileList.filter((f) => nameMatches(f) || contentSet.has(f)));
  }, [fileList, searchQuery, searchIndex]);

  // Load Quest data
  useEffect(() => {
    async function loadQuest() {
      if (!selectedFile) {
        setQuest(null);
        setNavigatingFile(null);
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
      } finally {
        // โหลดเสร็จแล้ว (สำเร็จหรือล้มเหลว) ปลดล็อกให้คลิกเลือกไฟล์อื่นได้
        setNavigatingFile(null);
      }
    }
    loadQuest();
  }, [selectedFile]);

  // เมื่อเลือกเควสต์ใหม่ ให้เลื่อนเนื้อหากลับขึ้นบนสุด
  useEffect(() => {
    if (quest) {
      document.getElementById("scroll-container")?.scrollTo({ top: 0 });
    }
  }, [quest]);

  return (
    <div className="min-h-screen p-4 sm:p-8 font-sans flex flex-col gap-6">
      {/* Header */}
      <header className="ffxiv-panel p-4 md:p-6 flex flex-row items-center justify-between gap-3 md:gap-6">
        <div className="flex flex-row items-center md:items-start gap-3 md:gap-6 text-left min-w-0">
          <img src={`${process.env.NEXT_PUBLIC_BASE_PATH || ""}/logo_dark.png`} alt="FFXIV Header Dark" className="hide-in-light h-12 sm:h-20 md:h-28 w-auto object-contain drop-shadow-lg shrink-0" />
          <img src={`${process.env.NEXT_PUBLIC_BASE_PATH || ""}/logo_light.png`} alt="FFXIV Header Light" className="show-in-light h-12 sm:h-20 md:h-28 w-auto object-contain drop-shadow-lg shrink-0" />
          <div className="flex flex-col justify-center h-full md:pt-1 min-w-0">
            <h1 className="text-lg sm:text-3xl md:text-4xl font-bold text-[var(--color-ffxiv-gold-light)] mb-0 md:mb-2 leading-tight">
              FFXIV MSQ Translation Editor
            </h1>
            <p className="hidden sm:block text-[var(--color-ffxiv-muted)] text-sm md:text-base">
              เลือกไฟล์ JSON ทางซ้ายมือ เพื่อเริ่มต้นแปลบทสนทนา<br className="hidden md:block" />
              แก้ไขคำแปลในช่องขวามือ แล้วกดบันทึกเพื่อดาวน์โหลดไฟล์ที่แปลเสร็จแล้ว
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <a
            href="https://www.facebook.com/groups/341335123402321/posts/2040960610106422"
            target="_blank"
            rel="noopener noreferrer"
            title="เปิดโพสต์ Facebook"
            className="p-3 rounded-full bg-[var(--color-ffxiv-panel)] border border-[var(--color-panel-border)] shadow-md hover:bg-[#1877F2] hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
          </a>
          <ThemeToggle />
        </div>
      </header>

      <div className="flex flex-col md:flex-row gap-6 items-start relative h-auto md:h-[80vh]">

        {/* Sidebar for File Selection */}
        <aside className="w-full md:w-80 ffxiv-panel flex flex-col max-h-none md:max-h-[80vh]">
          {/* Pinned Header */}
          <div className="p-4 flex flex-col gap-4 border-b border-[var(--color-panel-border)]">
            <h2 className="text-lg font-bold text-[var(--color-ffxiv-gold)]">
              <span>Select Quest</span>
            </h2>
            <SearchBox defaultValue={searchQuery} />
          </div>

          <div className="p-4 flex-1 overflow-y-auto custom-scrollbar max-h-[150px] md:max-h-none">
            {isLoading ? (
              <p className="text-[var(--color-ffxiv-muted)] text-sm italic">Loading quests...</p>
            ) : filteredFiles.length === 0 ? (
              <p className="text-[var(--color-ffxiv-muted)] text-sm italic">No quests found matching your search.</p>
            ) : (
              <ul className="space-y-1">
                {filteredFiles.map((file) => {
                  const isActive = selectedFile === file;
                  const isItemLoading = navigatingFile === file;
                  const isBusy = navigatingFile !== null;
                  return (
                    <li key={file}>
                      <button
                        type="button"
                        onClick={() => handleSelectFile(file)}
                        disabled={isBusy}
                        aria-busy={isItemLoading}
                        className={`w-full text-left flex items-center justify-between gap-2 px-3 py-2 text-sm rounded transition-colors ${
                          isActive
                            ? 'bg-[var(--color-ffxiv-gold)] text-[var(--background)] font-semibold shadow-sm'
                            : 'text-[var(--color-ffxiv-text)] hover:bg-[var(--color-input-bg)]'
                        } ${isBusy && !isItemLoading ? 'opacity-50 cursor-not-allowed' : ''} ${isItemLoading ? 'cursor-wait' : ''}`}
                      >
                        <span className="truncate">{file}</span>
                        {isItemLoading && (
                          <svg
                            className="animate-spin h-4 w-4 shrink-0"
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            aria-hidden="true"
                          >
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </aside>

        {/* Main Editor Area */}
        <main className="w-full md:flex-1 flex flex-col h-auto md:h-full ffxiv-panel relative overflow-visible md:overflow-hidden min-h-0">
          {!quest ? (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center min-h-[60vh] md:min-h-0 md:h-full">
              <img 
                src={`${process.env.NEXT_PUBLIC_BASE_PATH || ""}/quests.png`} 
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
            <div className="flex flex-col relative h-auto md:h-full overflow-visible md:overflow-hidden min-h-0">
              <StickyHeader filePath={quest.filePath} dialogueCount={quest.dialogues.length} />

              <div className="relative md:flex-1 min-h-0">
                <EditorForm quest={quest}>
                  <div id="scroll-container" className="relative md:absolute md:inset-0 overflow-visible md:overflow-y-auto custom-scrollbar flex flex-col gap-6 p-4 md:p-6 md:pr-8">
                  {quest.dialogues.map((dialogue, index) => {
                    const parsedChunks = parseEnglishText(dialogue.text_en, glossary, searchQuery);
                    return (
                      <TranslationRow
                        key={`${dialogue.key}_${index}`}
                        name={`dialogue_${index}`}
                        chunks={parsedChunks}
                        defaultTextTh={dialogue.text}
                      />
                    );
                  })}
                  {/* Submit Section (Appended to Content) */}
                  <div className="shrink-0 ffxiv-panel flex flex-col items-center justify-center gap-4 p-6 sm:p-10 relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[var(--color-ffxiv-gold-light)] to-transparent opacity-5"></div>
                      <img 
                        src={`${process.env.NEXT_PUBLIC_BASE_PATH || ""}/done.png`} 
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
