import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { StylePicker } from "@/components/StylePicker";
import { PromptInput } from "@/components/PromptInput";
import { VideoGallery } from "@/components/VideoGallery";
import { VideoGenerationProgress } from "@/components/VideoGenerationProgress";
import { Menu, X } from "lucide-react";

const Index = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isStyleHovering, setIsStyleHovering] = useState(false);
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = (text: string, duration?: number) => {
    console.log("Generating video for:", text, "Duration:", duration);
    setIsGenerating(true);
  };

  const handleGenerationComplete = () => {
    setIsGenerating(false);
    // Here you could scroll to the video gallery or show the new video
  };

  return (
    <div className="min-h-screen bg-black lg:pl-[200px]">
      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-sidebar-bg border-b border-sidebar-border px-4 py-3 flex items-center gap-3">
        <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-foreground">
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-foreground flex items-center justify-center">
            <span className="text-background font-bold text-[10px]">ET</span>
          </div>
          <span className="text-foreground font-semibold text-sm">ET NewsStudio</span>
        </div>
      </div>

      {/* Overlay */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 bg-black/50 z-40" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <div className={`fixed top-0 bottom-0 left-0 z-50 transition-transform duration-300 lg:translate-x-0 ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <Sidebar />
      </div>

      <main className="w-full px-4 sm:px-6 lg:px-8 py-6 lg:py-8 pt-16 lg:pt-8">
        {/* Hero heading */}
        <div className="flex w-full max-w-[792px] min-h-[116px] flex-col items-center justify-center gap-2 py-6 text-center transition-all duration-300 mx-auto" style={{ opacity: 0, animation: "fade-in-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) 100ms forwards", filter: isStyleHovering ? 'blur(4px)' : 'blur(0px)' }}>
          <div className="flex w-full flex-wrap items-center justify-center gap-2">
            <h1 className="text-primary text-center text-[32px] font-semibold leading-[36px] tracking-tight sm:text-[40px] sm:leading-[44px]">
              News to video
            </h1>
          </div>
          <p className="text-white text-base font-normal leading-6 text-center w-full opacity-80">
            Add an url of news or article and choose your preferred style.
          </p>
        </div>

        {/* Style picker */}
        <div className="flex justify-center mb-5 lg:mb-6" style={{ opacity: 0, animation: "fade-in-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) 200ms forwards" }}>
          <StylePicker onHoverChange={setIsStyleHovering} onStyleSelect={setSelectedStyle} />
        </div>

        {/* Prompt input */}
        <div className="max-w-[640px] mx-auto mb-8 lg:mb-12" style={{ opacity: 0, animation: "fade-in-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) 300ms forwards" }}>
          <PromptInput selectedStyle={selectedStyle} onGenerate={handleGenerate} />
        </div>

        {/* Video gallery */}
        <div id="video-gallery" style={{ opacity: 0, animation: "fade-in-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) 400ms forwards" }}>
          <VideoGallery />
        </div>
      </main>

      {/* Video Generation Progress Overlay */}
      {isGenerating && (
        <VideoGenerationProgress
          selectedStyle={selectedStyle}
          onComplete={handleGenerationComplete}
        />
      )}
    </div>
  );
};

export default Index;
