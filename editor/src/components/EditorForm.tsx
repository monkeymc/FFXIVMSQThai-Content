"use client";
import { FormEvent, useState, useEffect } from "react";

export default function EditorForm({ 
  quest, 
  children 
}: { 
  quest: any; 
  children: React.ReactNode;
}) {
  const [showModal, setShowModal] = useState(false);
  const [downloadedFileName, setDownloadedFileName] = useState("");
  const [downloadUrl, setDownloadUrl] = useState("");
  const [downloadBlob, setDownloadBlob] = useState<Blob | null>(null);

  // Clean up object URL to prevent memory leaks
  useEffect(() => {
    return () => {
      if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    };
  }, [downloadUrl]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    
    // อัปเดตข้อมูล JSON จากสิ่งที่กรอก
    const updatedDialogues = quest.dialogues.map((item: any, index: number) => {
      const newText = formData.get(`dialogue_${index}`);
      return {
        ...item,
        text: newText !== null ? newText.toString() : item.text
      };
    });

    // สร้างไฟล์ JSON สำหรับดาวน์โหลด
    let outputJson: any;

    if (quest.format === 'array') {
      outputJson = { ...quest.originalData };
      outputJson.dialogues = updatedDialogues;
    } else if (quest.format === 'scene') {
      outputJson = { ...quest.originalData };
      outputJson.Scene = { ...outputJson.Scene };
      for (const d of updatedDialogues) {
        if (outputJson.Scene[d.key]) {
          outputJson.Scene[d.key].text = d.text;
        }
      }
    } else {
      // flat format
      outputJson = { ...quest.originalData };
      for (const d of updatedDialogues) {
        if (outputJson[d.key]) {
          outputJson[d.key].text = d.text;
        }
      }
    }
    
    const jsonString = JSON.stringify(outputJson, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    setDownloadBlob(blob);
    
    // ถ้าเคยมี URL เก่า ให้ลบทิ้งก่อน
    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    
    const url = URL.createObjectURL(blob);
    setDownloadUrl(url);
    
    // ดึงชื่อไฟล์ เช่น "F0000.json"
    const fileName = quest.filePath.split('/').pop() || "translation.json";
    setDownloadedFileName(fileName);
    
    // แค่โชว์ Modal ยังไม่บังคับดาวน์โหลด
    setShowModal(true);
  };

  const handleDownload = async () => {
    if ('showSaveFilePicker' in window && downloadBlob) {
      try {
        // เปิดหน้าต่าง "Save As" ให้เลือกที่บันทึก
        const handle = await (window as any).showSaveFilePicker({
          suggestedName: downloadedFileName,
          types: [{
            description: 'JSON Files',
            accept: { 'application/json': ['.json'] },
          }],
        });
        
        const writable = await handle.createWritable();
        await writable.write(downloadBlob);
        await writable.close();
        
      } catch (err: any) {
        // ถ้ายกเลิกการเซฟ (AbortError) ก็ไม่ต้องทำอะไร
        if (err.name !== 'AbortError') {
          console.error("Save As error:", err);
          fallbackDownload(); // ถ้าพัง ค่อยใช้วิธีโหลดปกติ
        }
      }
    } else {
      // สำหรับ Browser ที่ไม่รองรับ (Firefox/Safari)
      fallbackDownload();
    }
  };

  const fallbackDownload = () => {
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = downloadedFileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

  return (
    <>
      <form onSubmit={handleSubmit} className="flex flex-col gap-6 h-full relative">
        {children}
      </form>

      {/* Modal แจ้งเตือนเมื่อเซฟเสร็จ */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="ffxiv-panel p-8 max-w-lg w-full flex flex-col gap-6 animate-in fade-in zoom-in duration-300 border-2 sm:border-4 border-[var(--color-ffxiv-gold)] shadow-[0_0_30px_rgba(0,0,0,0.8)] relative">
            <div className="text-center">
              <div className="flex justify-center mb-4">
                <img 
                  src={`${basePath}/thank_you_sticker.png`} 
                  alt="Thank You" 
                  className="w-32 h-32 object-contain drop-shadow-[0_0_15px_rgba(255,255,255,0.2)] animate-bounce"
                />
              </div>
              <h2 className="text-2xl font-bold text-[var(--color-ffxiv-gold-light)] mb-2">
                จัดเตรียมไฟล์เสร็จสมบูรณ์ คุปโปะ!
              </h2>
              <p className="text-[var(--color-ffxiv-text)]">
                ระบบได้รวบรวมคำแปลทั้งหมดของคุณเตรียมไว้ให้แล้วครับ
              </p>
            </div>
            
            <div className="bg-[var(--color-input-bg)] border border-[var(--color-panel-border)] p-5 rounded-lg">
              <h3 className="text-[var(--color-ffxiv-gold)] font-bold mb-3 flex items-center gap-2">
                📌 วิธีการส่งผลงาน
              </h3>
              <ul className="text-[var(--color-ffxiv-text)] text-sm leading-relaxed list-decimal list-inside space-y-2">
                <li>กดปุ่ม <strong>เลือกที่บันทึกไฟล์</strong> เพื่อบันทึกไฟล์ <span className="font-mono text-[var(--color-ffxiv-gold-light)] font-bold">{downloadedFileName}</span> ลงเครื่อง</li>
                <li>กดปุ่ม <strong>เปิดโพสต์ Facebook</strong> เพื่อไปยังโพสต์รับส่งงาน</li>
                <li><strong>แนบไฟล์ที่คุณโหลดไว้</strong> ลงในช่องคอมเมนต์เพื่อส่งผลงานได้เลยครับ!</li>
              </ul>
            </div>
            
            <div className="flex flex-col gap-3 mt-2">
              <button 
                type="button"
                onClick={handleDownload}
                className="w-full py-3 px-4 ffxiv-submit-btn font-bold rounded-lg flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                เลือกที่บันทึกไฟล์ .json
              </button>
              <div className="flex flex-col sm:flex-row gap-3">
                <a 
                  href="https://www.facebook.com/groups/341335123402321/posts/2040960610106422" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="flex-1 text-center py-3 px-4 bg-[#1877F2] hover:bg-[#166fe5] text-white font-bold rounded-lg shadow-lg transition-colors"
                >
                  เปิดโพสต์ Facebook
                </a>
                <button 
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="py-3 px-6 border border-[var(--color-panel-border)] text-[var(--color-ffxiv-text)] hover:bg-[var(--color-input-bg)] rounded-lg font-semibold transition-colors"
                >
                  ปิด
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
